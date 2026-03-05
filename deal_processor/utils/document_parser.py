"""
document_parser.py
------------------
Text extraction utilities for PDF, DOCX, XLSX, CSV, and plain-text files.

Each extract_* function accepts a filesystem path string and returns a single
plain-text string.  extract_text() is the public dispatcher.
"""

import csv
import io
import logging
import os

logger = logging.getLogger(__name__)

# Supported file extensions
ALLOWED_EXTENSIONS = {"pdf", "docx", "doc", "txt", "md", "xlsx", "xls", "csv"}


# --------------------------------------------------------------------------- #
# PDF                                                                          #
# --------------------------------------------------------------------------- #

def extract_text_from_pdf(path: str) -> str:
    """Extract text from a PDF using pdfplumber (preferred) with PyPDF2 fallback."""
    text_parts = []

    # --- pdfplumber (handles complex layouts, tables) ---
    try:
        import pdfplumber  # type: ignore

        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text() or ""
                # Also attempt table extraction and convert to simple text
                tables = page.extract_tables() or []
                table_text = ""
                for table in tables:
                    for row in table:
                        cleaned = [cell or "" for cell in row]
                        table_text += "\t".join(cleaned) + "\n"
                combined = page_text + ("\n" + table_text if table_text else "")
                if combined.strip():
                    text_parts.append(f"[Page {i + 1}]\n{combined.strip()}")

        if text_parts:
            return "\n\n".join(text_parts)
    except ImportError:
        logger.warning("pdfplumber not available; falling back to PyPDF2")
    except Exception as exc:
        logger.warning("pdfplumber failed (%s); falling back to PyPDF2", exc)

    # --- PyPDF2 fallback ---
    try:
        import PyPDF2  # type: ignore

        with open(path, "rb") as fh:
            reader = PyPDF2.PdfReader(fh)
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                if page_text.strip():
                    text_parts.append(f"[Page {i + 1}]\n{page_text.strip()}")

        if text_parts:
            return "\n\n".join(text_parts)
    except ImportError:
        raise RuntimeError(
            "Neither pdfplumber nor PyPDF2 is installed. "
            "Run: pip install pdfplumber PyPDF2"
        )
    except Exception as exc:
        raise RuntimeError(f"PDF extraction failed: {exc}") from exc

    return ""


# --------------------------------------------------------------------------- #
# DOCX / DOC                                                                   #
# --------------------------------------------------------------------------- #

def extract_text_from_docx(path: str) -> str:
    """Extract text from a .docx file using python-docx."""
    try:
        from docx import Document  # type: ignore
    except ImportError:
        raise RuntimeError(
            "python-docx is not installed. Run: pip install python-docx"
        )

    doc = Document(path)
    parts = []

    # Paragraphs
    for para in doc.paragraphs:
        if para.text.strip():
            parts.append(para.text.strip())

    # Tables
    for table in doc.tables:
        for row in table.rows:
            row_text = "\t".join(
                cell.text.strip() for cell in row.cells if cell.text.strip()
            )
            if row_text:
                parts.append(row_text)

    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# XLSX / XLS                                                                   #
# --------------------------------------------------------------------------- #

def extract_text_from_xlsx(path: str) -> str:
    """Extract text from an Excel file using openpyxl (xlsx) or xlrd (xls)."""
    ext = os.path.splitext(path)[1].lower()

    if ext == ".xls":
        return _extract_xls(path)

    # .xlsx via openpyxl
    try:
        import openpyxl  # type: ignore
    except ImportError:
        raise RuntimeError(
            "openpyxl is not installed. Run: pip install openpyxl"
        )

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    parts = []

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        sheet_parts = [f"=== Sheet: {sheet_name} ==="]
        for row in ws.iter_rows(values_only=True):
            cells = [str(cell) if cell is not None else "" for cell in row]
            row_text = "\t".join(cells).strip()
            if row_text.replace("\t", ""):
                sheet_parts.append(row_text)
        if len(sheet_parts) > 1:
            parts.append("\n".join(sheet_parts))

    wb.close()
    return "\n\n".join(parts)


def _extract_xls(path: str) -> str:
    """Extract text from a legacy .xls file via xlrd."""
    try:
        import xlrd  # type: ignore
    except ImportError:
        raise RuntimeError(
            "xlrd is not installed. Run: pip install xlrd"
        )

    wb = xlrd.open_workbook(path)
    parts = []
    for sheet in wb.sheets():
        sheet_parts = [f"=== Sheet: {sheet.name} ==="]
        for row_idx in range(sheet.nrows):
            row_vals = [str(sheet.cell_value(row_idx, col)) for col in range(sheet.ncols)]
            row_text = "\t".join(row_vals).strip()
            if row_text.replace("\t", ""):
                sheet_parts.append(row_text)
        if len(sheet_parts) > 1:
            parts.append("\n".join(sheet_parts))
    return "\n\n".join(parts)


# --------------------------------------------------------------------------- #
# CSV                                                                          #
# --------------------------------------------------------------------------- #

def extract_text_from_csv(path: str) -> str:
    """Extract text from a CSV file."""
    rows = []
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as fh:
        reader = csv.reader(fh)
        for row in reader:
            row_text = "\t".join(row).strip()
            if row_text.replace("\t", ""):
                rows.append(row_text)
    return "\n".join(rows)


# --------------------------------------------------------------------------- #
# Plain text / Markdown                                                        #
# --------------------------------------------------------------------------- #

def extract_text_from_txt(path: str) -> str:
    """Read a plain text or Markdown file."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


# --------------------------------------------------------------------------- #
# Public dispatcher                                                            #
# --------------------------------------------------------------------------- #

def extract_text(path: str, filename: str) -> str:
    """
    Dispatch to the correct extractor based on the file extension.

    Parameters
    ----------
    path : str
        Absolute filesystem path to the saved file.
    filename : str
        Original filename (used for extension detection).

    Returns
    -------
    str
        Extracted plain text.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == "pdf":
        return extract_text_from_pdf(path)
    elif ext in ("docx", "doc"):
        return extract_text_from_docx(path)
    elif ext in ("xlsx", "xls"):
        return extract_text_from_xlsx(path)
    elif ext == "csv":
        return extract_text_from_csv(path)
    elif ext in ("txt", "md", ""):
        return extract_text_from_txt(path)
    else:
        raise ValueError(f"Unsupported file extension: .{ext}")
