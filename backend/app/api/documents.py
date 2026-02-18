"""Document upload and management endpoints."""
import os
import shutil
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.document import Document, DocumentStatus, ExtractedTable, ExtractedText
from app.models.financial_data import FinancialRecord, FinancialPeriod
from app.schemas.document import (
    DocumentSchema,
    DocumentDetailSchema,
    DocumentListResponse,
    ExtractionResult,
)
from app.config import settings
from app.utils.file_utils import get_document_type, generate_unique_filename, safe_file_path
from app.services.document_parser import parse_document
from app.services.data_normalizer import DataNormalizer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentSchema, status_code=201)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a document and trigger async extraction."""
    # Validate file size
    content = await file.read()
    file_size = len(content)
    max_size = settings.max_upload_size_mb * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {settings.max_upload_size_mb} MB",
        )

    # Save file
    unique_name = generate_unique_filename(file.filename or "upload")
    file_path = safe_file_path(settings.upload_dir, unique_name)

    with open(file_path, "wb") as f:
        f.write(content)

    doc_type = get_document_type(file.filename or "", file.content_type)

    doc = Document(
        filename=unique_name,
        original_filename=file.filename or "upload",
        file_path=file_path,
        file_size=file_size,
        mime_type=file.content_type,
        document_type=doc_type,
        status=DocumentStatus.UPLOADED,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)

    doc_id = doc.id
    background_tasks.add_task(_extract_document, doc_id, file_path, doc_type)

    return doc


async def _extract_document(doc_id: int, file_path: str, doc_type):
    """Background task: parse and extract financial data from document."""
    from app.database import AsyncSessionLocal
    from app.models.financial_data import FinancialPeriod, PeriodType
    from app.models.document import DocumentType

    async with AsyncSessionLocal() as db:
        try:
            # Update status to processing
            doc = await db.get(Document, doc_id)
            if not doc:
                return
            doc.status = DocumentStatus.PROCESSING
            await db.commit()

            # Parse
            result = parse_document(file_path, doc_type)

            # Store extracted tables
            for tbl in result.get("tables", []):
                et = ExtractedTable(
                    document_id=doc_id,
                    page_number=tbl.get("page"),
                    table_index=tbl.get("index", 0),
                    headers=tbl.get("headers", []),
                    data=tbl.get("data", {}),
                    raw_text=tbl.get("raw_text", "")[:5000],
                    confidence=tbl.get("confidence"),
                    table_type=tbl.get("table_type"),
                )
                db.add(et)

            # Store extracted texts
            for txt in result.get("texts", []):
                et2 = ExtractedText(
                    document_id=doc_id,
                    page_number=txt.get("page"),
                    content=txt.get("content", "")[:10000],
                    text_type=txt.get("type"),
                )
                db.add(et2)

            await db.flush()

            # Normalise and create financial records
            normalizer = DataNormalizer()
            norm_records = normalizer.normalise_tables(
                result.get("tables", []),
                result.get("texts", []),
                doc_id,
            )

            period_cache: dict[str, int] = {}
            for nr in norm_records:
                period_id = None
                if nr.period_label:
                    if nr.period_label not in period_cache:
                        fp = FinancialPeriod(
                            label=nr.period_label,
                            period_type=PeriodType.ANNUAL,
                        )
                        db.add(fp)
                        await db.flush()
                        period_cache[nr.period_label] = fp.id
                    period_id = period_cache[nr.period_label]

                fr = FinancialRecord(
                    document_id=doc_id,
                    period_id=period_id,
                    category=nr.category,
                    line_item=nr.line_item,
                    value=nr.value,
                    currency=nr.currency,
                    unit=nr.unit,
                    confidence=nr.confidence,
                    source_text=(nr.source_text or "")[:500],
                    tags=nr.tags,
                )
                db.add(fr)

            doc = await db.get(Document, doc_id)
            doc.status = DocumentStatus.PROCESSED
            doc.page_count = result.get("page_count", 0)
            doc.extraction_confidence = result.get("confidence", 0.0)
            doc.extraction_errors = {
                "errors": result.get("errors", []),
                "warnings": result.get("warnings", []),
            }

            await db.commit()
            logger.info(f"Document {doc_id} processed: {len(norm_records)} financial records")

        except Exception as e:
            logger.exception(f"Extraction failed for document {doc_id}: {e}")
            async with AsyncSessionLocal() as db2:
                doc2 = await db2.get(Document, doc_id)
                if doc2:
                    doc2.status = DocumentStatus.FAILED
                    doc2.extraction_errors = {"errors": [str(e)]}
                    await db2.commit()


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    total_result = await db.execute(select(func.count(Document.id)))
    total = total_result.scalar()

    result = await db.execute(
        select(Document).order_by(Document.created_at.desc()).offset(skip).limit(limit)
    )
    docs = result.scalars().all()
    return DocumentListResponse(total=total, documents=list(docs))


@router.get("/{doc_id}", response_model=DocumentDetailSchema)
async def get_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/{doc_id}", status_code=204)
async def delete_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    # Remove file
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)
    await db.delete(doc)


@router.get("/{doc_id}/extraction-status")
async def get_extraction_status(doc_id: int, db: AsyncSession = Depends(get_db)):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Count records
    rec_count = await db.execute(
        select(func.count(FinancialRecord.id)).where(FinancialRecord.document_id == doc_id)
    )
    tbl_count = await db.execute(
        select(func.count(ExtractedTable.id)).where(ExtractedTable.document_id == doc_id)
    )
    txt_count = await db.execute(
        select(func.count(ExtractedText.id)).where(ExtractedText.document_id == doc_id)
    )

    return {
        "document_id": doc_id,
        "status": doc.status,
        "financial_records": rec_count.scalar(),
        "tables_extracted": tbl_count.scalar(),
        "text_blocks_extracted": txt_count.scalar(),
        "extraction_confidence": doc.extraction_confidence,
        "errors": (doc.extraction_errors or {}).get("errors", []),
        "warnings": (doc.extraction_errors or {}).get("warnings", []),
    }
