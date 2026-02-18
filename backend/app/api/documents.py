"""
Document management API endpoints.
POST /documents/upload        - Upload one or more files
GET  /documents               - List all documents
GET  /documents/{id}          - Get document detail
DELETE /documents/{id}        - Delete a document
POST /documents/{id}/parse    - Trigger (re)parsing
GET  /documents/{id}/tables   - Get extracted tables
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import List

import aiofiles
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from loguru import logger
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.document import Document, DocumentStatus
from app.models.financial_data import ExtractedTable
from app.services.document_parser import DocumentParser
from app.services.extraction_engine import ExtractionEngine
from app.utils.validators import validate_file_extension, validate_file_size, safe_filename

router = APIRouter(prefix="/documents", tags=["documents"])

parser = DocumentParser()
extractor = ExtractionEngine()


async def _process_document(document_id: int, file_path: str, file_type: str):
    """Background task: parse + extract a document."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return

        # Parse
        doc.status = DocumentStatus.PARSING.value
        db.commit()

        parsed = parser.parse(file_path, file_type)

        if parsed.errors and not parsed.tables and not parsed.raw_text:
            doc.status = DocumentStatus.FAILED.value
            doc.error_message = "; ".join(parsed.errors)
            db.commit()
            return

        doc.page_count = parsed.page_count
        doc.doc_metadata = parsed.metadata
        doc.status = DocumentStatus.EXTRACTING.value
        db.commit()

        # Extract
        result = extractor.extract(document_id, parsed, db)

        doc.status = DocumentStatus.EXTRACTED.value
        doc.extraction_confidence = result.get("average_confidence", 0.5)
        db.commit()

        logger.info(
            f"Document {document_id} processed: "
            f"{result['tables_found']} tables, "
            f"{result['line_items_extracted']} line items, "
            f"confidence={doc.extraction_confidence:.2f}"
        )

    except Exception as e:
        logger.error(f"Background processing error for doc {document_id}: {e}")
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.status = DocumentStatus.FAILED.value
            doc.error_message = str(e)
            db.commit()
    finally:
        db.close()


@router.post("/upload")
async def upload_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """Upload one or more documents for ingestion."""
    results = []

    for upload_file in files:
        # Validate
        if not validate_file_extension(upload_file.filename):
            results.append({
                "filename": upload_file.filename,
                "status": "rejected",
                "error": f"Unsupported file type. Allowed: {', '.join(settings.allowed_extensions)}",
            })
            continue

        # Read content to check size
        content = await upload_file.read()
        if not validate_file_size(len(content)):
            results.append({
                "filename": upload_file.filename,
                "status": "rejected",
                "error": f"File too large (max {settings.MAX_FILE_SIZE_MB}MB)",
            })
            continue

        # Generate safe stored filename
        ext = Path(upload_file.filename).suffix.lower()
        stored_name = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(settings.UPLOAD_DIR, stored_name)

        # Save to disk
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        # Determine file type
        file_type = ext.lstrip(".")

        # Create DB record
        doc = Document(
            filename=stored_name,
            original_filename=safe_filename(upload_file.filename),
            file_type=file_type,
            file_size=len(content),
            file_path=file_path,
            status=DocumentStatus.UPLOADED.value,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        # Schedule background processing
        background_tasks.add_task(_process_document, doc.id, file_path, file_type)

        results.append({
            "id": doc.id,
            "filename": upload_file.filename,
            "stored_as": stored_name,
            "size_bytes": len(content),
            "status": "uploaded",
        })

    return {"uploaded": results}


@router.get("")
def list_documents(db: Session = Depends(get_db)):
    """Return all documents."""
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    return {"documents": [d.to_dict() for d in docs]}


@router.get("/{document_id}")
def get_document(document_id: int, db: Session = Depends(get_db)):
    """Return a single document."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc.to_dict()


@router.delete("/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db)):
    """Delete a document and its extracted data."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Remove file from disk
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    db.delete(doc)
    db.commit()
    return {"deleted": document_id}


@router.post("/{document_id}/parse")
async def reparse_document(
    document_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Re-trigger parsing and extraction for a document."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=400, detail="Source file no longer available")

    doc.status = DocumentStatus.UPLOADED.value
    doc.error_message = None
    db.commit()

    background_tasks.add_task(_process_document, doc.id, doc.file_path, doc.file_type)
    return {"status": "reprocessing_started", "document_id": document_id}


@router.get("/{document_id}/tables")
def get_document_tables(document_id: int, db: Session = Depends(get_db)):
    """Return raw extracted tables for a document."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    tables = db.query(ExtractedTable).filter(ExtractedTable.document_id == document_id).all()
    return {"tables": [t.to_dict() for t in tables]}
