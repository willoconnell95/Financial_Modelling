"""PDF parsing using pdfplumber (primary) with PyMuPDF fallback."""
import io
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def parse_pdf(file_path: str) -> dict:
    """
    Extract tables and text from a PDF file.
    Returns: {
        page_count: int,
        tables: [{page, index, headers, data, confidence}],
        texts: [{page, content, type}],
        confidence: float,
        errors: [str]
    }
    """
    result = {
        "page_count": 0,
        "tables": [],
        "texts": [],
        "confidence": 0.0,
        "errors": [],
    }

    try:
        import pdfplumber
        result = _parse_with_pdfplumber(file_path, result)
    except ImportError:
        result["errors"].append("pdfplumber not available")
    except Exception as e:
        result["errors"].append(f"pdfplumber error: {str(e)}")
        logger.warning(f"pdfplumber failed for {file_path}: {e}")

    # Fallback / supplement with PyMuPDF if tables were empty
    if not result["tables"] or result["confidence"] < 0.3:
        try:
            result = _supplement_with_pymupdf(file_path, result)
        except ImportError:
            result["errors"].append("PyMuPDF not available")
        except Exception as e:
            result["errors"].append(f"PyMuPDF error: {str(e)}")
            logger.warning(f"PyMuPDF failed for {file_path}: {e}")

    # Calculate overall confidence
    if result["tables"] or result["texts"]:
        table_conf = (
            sum(t.get("confidence", 0.5) for t in result["tables"]) / len(result["tables"])
            if result["tables"]
            else 0.5
        )
        text_conf = 0.8 if result["texts"] else 0.0
        result["confidence"] = round((table_conf + text_conf) / 2, 3)

    return result


def _parse_with_pdfplumber(file_path: str, result: dict) -> dict:
    import pdfplumber

    with pdfplumber.open(file_path) as pdf:
        result["page_count"] = len(pdf.pages)

        for page_num, page in enumerate(pdf.pages, start=1):
            # Extract tables
            tables = page.extract_tables()
            for tbl_idx, table in enumerate(tables):
                if not table:
                    continue
                cleaned = _clean_pdfplumber_table(table)
                if cleaned and len(cleaned) > 1:
                    headers = cleaned[0] if cleaned else []
                    rows = cleaned[1:] if len(cleaned) > 1 else []
                    result["tables"].append(
                        {
                            "page": page_num,
                            "index": tbl_idx,
                            "headers": headers,
                            "data": {"columns": headers, "rows": rows},
                            "raw_text": str(table),
                            "confidence": 0.85,
                        }
                    )

            # Extract text
            text = page.extract_text()
            if text and text.strip():
                result["texts"].append(
                    {
                        "page": page_num,
                        "content": text.strip(),
                        "type": "body",
                    }
                )

    return result


def _supplement_with_pymupdf(file_path: str, result: dict) -> dict:
    import fitz  # PyMuPDF

    doc = fitz.open(file_path)
    if result["page_count"] == 0:
        result["page_count"] = len(doc)

    for page_num, page in enumerate(doc, start=1):
        # Only add text if pdfplumber didn't get it
        existing_pages = {t["page"] for t in result["texts"]}
        if page_num not in existing_pages:
            text = page.get_text("text")
            if text and text.strip():
                result["texts"].append(
                    {"page": page_num, "content": text.strip(), "type": "body"}
                )

        # Extract tables via PyMuPDF's find_tables
        try:
            tabs = page.find_tables()
            for tbl_idx, tab in enumerate(tabs.tables):
                df = tab.to_pandas()
                if df.empty:
                    continue
                existing_indices = {(t["page"], t["index"]) for t in result["tables"]}
                if (page_num, tbl_idx) not in existing_indices:
                    headers = list(df.columns)
                    rows = df.values.tolist()
                    result["tables"].append(
                        {
                            "page": page_num,
                            "index": tbl_idx,
                            "headers": headers,
                            "data": {"columns": headers, "rows": rows},
                            "raw_text": df.to_string(),
                            "confidence": 0.70,
                        }
                    )
        except Exception:
            pass

    doc.close()
    return result


def _clean_pdfplumber_table(table: list) -> list:
    """Remove empty rows/cols and strip whitespace."""
    cleaned = []
    for row in table:
        if row is None:
            continue
        cleaned_row = [str(cell).strip() if cell is not None else "" for cell in row]
        if any(c for c in cleaned_row):  # skip fully empty rows
            cleaned.append(cleaned_row)
    return cleaned
