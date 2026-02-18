"""Unified document parser dispatcher."""
import logging
from app.models.document import DocumentType
from app.services.pdf_parser import parse_pdf
from app.services.excel_parser import parse_excel
from app.services.csv_parser import parse_csv
from app.services.docx_parser import parse_docx
from app.services.image_parser import parse_image

logger = logging.getLogger(__name__)

PARSERS = {
    DocumentType.PDF: parse_pdf,
    DocumentType.EXCEL: parse_excel,
    DocumentType.CSV: parse_csv,
    DocumentType.DOCX: parse_docx,
    DocumentType.IMAGE: parse_image,
}


def parse_document(file_path: str, document_type: DocumentType) -> dict:
    """
    Dispatch to the appropriate parser and return a unified result dict:
    {
        page_count: int,
        tables: [...],
        texts: [...],
        confidence: float,
        errors: [str],
        warnings: [str]
    }
    """
    parser_fn = PARSERS.get(document_type)
    if parser_fn is None:
        return {
            "page_count": 0,
            "tables": [],
            "texts": [],
            "confidence": 0.0,
            "errors": [f"No parser available for document type: {document_type}"],
            "warnings": [],
        }

    try:
        result = parser_fn(file_path)
        if "warnings" not in result:
            result["warnings"] = []
        return result
    except Exception as e:
        logger.exception(f"Parser crashed for {file_path}: {e}")
        return {
            "page_count": 0,
            "tables": [],
            "texts": [],
            "confidence": 0.0,
            "errors": [f"Parser exception: {str(e)}"],
            "warnings": [],
        }
