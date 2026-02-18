"""CSV parser using pandas with encoding detection."""
import logging
import chardet
import pandas as pd

logger = logging.getLogger(__name__)


def parse_csv(file_path: str) -> dict:
    result = {
        "page_count": 1,
        "tables": [],
        "texts": [],
        "confidence": 0.0,
        "errors": [],
    }

    try:
        encoding = _detect_encoding(file_path)
        df = pd.read_csv(file_path, encoding=encoding, header=0)

        if df.empty:
            result["errors"].append("CSV file is empty")
            return result

        headers = [str(c).strip() for c in df.columns.tolist()]
        rows = []
        for _, row in df.iterrows():
            rows.append([str(v).strip() if pd.notna(v) else "" for v in row])

        result["tables"].append(
            {
                "page": 1,
                "index": 0,
                "headers": headers,
                "data": {"columns": headers, "rows": rows},
                "raw_text": df.to_string(),
                "confidence": 0.9,
            }
        )
        result["confidence"] = 0.9

    except Exception as e:
        result["errors"].append(f"CSV parse error: {str(e)}")
        logger.error(f"Failed to parse CSV {file_path}: {e}")

    return result


def _detect_encoding(file_path: str) -> str:
    with open(file_path, "rb") as f:
        raw = f.read(10_000)
    detected = chardet.detect(raw)
    return detected.get("encoding") or "utf-8"
