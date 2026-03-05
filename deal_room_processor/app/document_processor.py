"""
Document text extraction for PDF, DOCX, TXT, XLSX, CSV, and PPTX files.

Each extractor returns a plain-text string or raises a DocumentProcessingError
so the caller can surface the failure clearly in the UI.
"""
import csv
import io
import os
from pathlib import Path
from typing import List

import openpyxl
import pdfplumber
from docx import Document as DocxDocument


class DocumentProcessingError(Exception):
    """Raised when a document cannot be parsed."""


# ---------------------------------------------------------------------------
# Per-format extractors
# ---------------------------------------------------------------------------

def _extract_pdf(path: str) -> str:
    """Extract text from a PDF using pdfplumber; fall back to PyPDF2."""
    text_parts: List[str] = []
    try:
        with pdfplumber.open(path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
                # Also capture any tables on the page
                for table in page.extract_tables():
                    for row in table:
                        cleaned = [cell or "" for cell in row]
                        text_parts.append(" | ".join(cleaned))
        if text_parts:
            return "\n".join(text_parts)
    except Exception as primary_exc:
        # Try PyPDF2 as a fallback
        try:
            import PyPDF2  # type: ignore
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            if text_parts:
                return "\n".join(text_parts)
        except Exception as fallback_exc:
            raise DocumentProcessingError(
                f"PDF extraction failed (pdfplumber: {primary_exc}; "
                f"PyPDF2 fallback: {fallback_exc})"
            ) from fallback_exc

    raise DocumentProcessingError(
        "PDF appears to contain no extractable text (may be a scanned image)."
    )


def _extract_docx(path: str) -> str:
    try:
        doc = DocxDocument(path)
        parts: List[str] = []
        for para in doc.paragraphs:
            if para.text.strip():
                parts.append(para.text)
        # Extract text from tables too
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(
                    cell.text.strip() for cell in row.cells if cell.text.strip()
                )
                if row_text:
                    parts.append(row_text)
        if not parts:
            raise DocumentProcessingError("DOCX file appears to be empty.")
        return "\n".join(parts)
    except DocumentProcessingError:
        raise
    except Exception as exc:
        raise DocumentProcessingError(f"DOCX extraction failed: {exc}") from exc


def _extract_txt(path: str) -> str:
    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            with open(path, "r", encoding=encoding) as f:
                content = f.read().strip()
            if content:
                return content
        except (UnicodeDecodeError, LookupError):
            continue
    raise DocumentProcessingError(
        "TXT file could not be decoded with any supported encoding."
    )


def _extract_xlsx(path: str) -> str:
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        parts: List[str] = []
        for sheet in wb.worksheets:
            parts.append(f"[Sheet: {sheet.title}]")
            for row in sheet.iter_rows(values_only=True):
                cells = [str(c) if c is not None else "" for c in row]
                row_text = " | ".join(cells).strip(" |")
                if row_text.replace("|", "").strip():
                    parts.append(row_text)
        wb.close()
        if not parts:
            raise DocumentProcessingError("XLSX file appears to be empty.")
        return "\n".join(parts)
    except DocumentProcessingError:
        raise
    except Exception as exc:
        raise DocumentProcessingError(f"XLSX extraction failed: {exc}") from exc


def _extract_csv(path: str) -> str:
    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            with open(path, newline="", encoding=encoding) as f:
                reader = csv.reader(f)
                rows = [" | ".join(row) for row in reader if any(c.strip() for c in row)]
            if rows:
                return "\n".join(rows)
        except (UnicodeDecodeError, LookupError):
            continue
    raise DocumentProcessingError(
        "CSV file could not be decoded with any supported encoding."
    )


def _extract_pptx(path: str) -> str:
    try:
        from pptx import Presentation  # type: ignore
        prs = Presentation(path)
        parts: List[str] = []
        for slide_num, slide in enumerate(prs.slides, start=1):
            parts.append(f"[Slide {slide_num}]")
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for para in shape.text_frame.paragraphs:
                        text = para.text.strip()
                        if text:
                            parts.append(text)
        if not parts:
            raise DocumentProcessingError("PPTX file appears to be empty.")
        return "\n".join(parts)
    except DocumentProcessingError:
        raise
    except ImportError:
        raise DocumentProcessingError(
            "python-pptx is not installed. Run: pip install python-pptx"
        )
    except Exception as exc:
        raise DocumentProcessingError(f"PPTX extraction failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

SUPPORTED_EXTENSIONS = {
    ".pdf": _extract_pdf,
    ".docx": _extract_docx,
    ".doc": _extract_docx,
    ".txt": _extract_txt,
    ".md": _extract_txt,
    ".xlsx": _extract_xlsx,
    ".xls": _extract_xlsx,
    ".csv": _extract_csv,
    ".pptx": _extract_pptx,
}


def extract_text(file_path: str) -> str:
    """
    Extract text from a document file.

    Returns the extracted plain text.
    Raises DocumentProcessingError on failure.
    Raises ValueError for unsupported file types.
    """
    ext = Path(file_path).suffix.lower()
    extractor = SUPPORTED_EXTENSIONS.get(ext)
    if extractor is None:
        raise ValueError(
            f"Unsupported file type '{ext}'. "
            f"Supported types: {', '.join(sorted(SUPPORTED_EXTENSIONS.keys()))}"
        )
    return extractor(file_path)


def extract_all(file_paths: List[str]) -> dict:
    """
    Extract text from multiple files.

    Returns a dict with keys:
      - 'combined_text': str  — all successfully extracted text joined together
      - 'results': list of dicts with 'filename', 'text', 'error'
    """
    results = []
    combined_parts: List[str] = []

    for path in file_paths:
        filename = os.path.basename(path)
        try:
            text = extract_text(path)
            combined_parts.append(f"=== Document: {filename} ===\n{text}")
            results.append({"filename": filename, "text": text, "error": None})
        except (DocumentProcessingError, ValueError) as exc:
            results.append({"filename": filename, "text": None, "error": str(exc)})

    return {
        "combined_text": "\n\n".join(combined_parts),
        "results": results,
    }
