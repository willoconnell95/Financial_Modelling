"""Image parser using Tesseract OCR via pytesseract."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def parse_image(file_path: str) -> dict:
    result = {
        "page_count": 1,
        "tables": [],
        "texts": [],
        "confidence": 0.0,
        "errors": [],
    }

    try:
        from PIL import Image
        import pytesseract

        img = Image.open(file_path)
        # OCR to extract all text
        ocr_text = pytesseract.image_to_string(img, config="--psm 6")
        ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

        # Confidence from Tesseract
        confidences = [c for c in ocr_data.get("conf", []) if isinstance(c, (int, float)) and c >= 0]
        avg_conf = sum(confidences) / len(confidences) / 100 if confidences else 0.0

        if ocr_text.strip():
            result["texts"].append(
                {
                    "page": 1,
                    "content": ocr_text.strip(),
                    "type": "ocr",
                }
            )

        # Attempt to find table-like structures in the OCR output
        tables = _extract_tables_from_ocr_text(ocr_text)
        result["tables"].extend(tables)

        result["confidence"] = round(avg_conf, 3)
        result["page_count"] = 1

    except ImportError as e:
        result["errors"].append(f"OCR library not available: {str(e)}")
    except Exception as e:
        result["errors"].append(f"Image parse error: {str(e)}")
        logger.error(f"Failed to parse image {file_path}: {e}")

    return result


def _extract_tables_from_ocr_text(text: str) -> list:
    """Heuristic: split OCR text into rows and detect tabular columns by whitespace alignment."""
    lines = [l.rstrip() for l in text.split("\n") if l.strip()]
    if len(lines) < 3:
        return []

    # Look for lines with multiple tokens that look like numbers
    import re

    number_pattern = re.compile(r"\b\d[\d,.\-()%]+\b")
    tabular_lines = [l for l in lines if len(number_pattern.findall(l)) >= 2]

    if len(tabular_lines) < 2:
        return []

    # Simple split by 2+ spaces
    rows = []
    for line in tabular_lines:
        cols = re.split(r"\s{2,}", line.strip())
        if cols:
            rows.append(cols)

    if not rows:
        return []

    max_cols = max(len(r) for r in rows)
    # Pad short rows
    rows = [r + [""] * (max_cols - len(r)) for r in rows]
    headers = rows[0]
    data_rows = rows[1:]

    return [
        {
            "page": 1,
            "index": 0,
            "headers": headers,
            "data": {"columns": headers, "rows": data_rows},
            "raw_text": "\n".join(tabular_lines),
            "confidence": 0.5,
        }
    ]
