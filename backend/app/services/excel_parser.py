"""Excel / XLSX parser using openpyxl and pandas."""
import logging
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


def parse_excel(file_path: str) -> dict:
    """
    Extract all sheets from an Excel file.
    Returns: {
        page_count: int (sheet count),
        tables: [{page, index, headers, data, sheet_name, confidence}],
        texts: [],
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
        xl = pd.ExcelFile(file_path, engine="openpyxl")
        sheet_names = xl.sheet_names
        result["page_count"] = len(sheet_names)

        for sheet_idx, sheet_name in enumerate(sheet_names):
            try:
                df = xl.parse(sheet_name, header=None)
                if df.empty:
                    continue

                tables = _split_into_tables(df, sheet_name, sheet_idx)
                result["tables"].extend(tables)

                # Also capture any text-only cells as text blocks
                text_content = _extract_text_from_df(df, sheet_name)
                if text_content:
                    result["texts"].append(
                        {
                            "page": sheet_idx + 1,
                            "content": text_content,
                            "type": "sheet_text",
                        }
                    )

            except Exception as e:
                result["errors"].append(f"Sheet '{sheet_name}': {str(e)}")

        result["confidence"] = 0.9 if result["tables"] else 0.3

    except Exception as e:
        result["errors"].append(f"Excel parse error: {str(e)}")
        logger.error(f"Failed to parse Excel {file_path}: {e}")

    return result


def _split_into_tables(df: pd.DataFrame, sheet_name: str, sheet_idx: int) -> list:
    """
    Try to identify coherent table blocks within a sheet.
    Simple heuristic: find the first row that looks like a header.
    """
    tables = []

    # Drop fully empty rows and columns
    df_clean = df.dropna(how="all").dropna(axis=1, how="all")
    if df_clean.empty:
        return tables

    # Find potential header rows (rows where most cells are strings/labels)
    header_rows = []
    for i, row in df_clean.iterrows():
        string_count = sum(1 for v in row if isinstance(v, str) and str(v).strip())
        if string_count >= max(2, len(row) * 0.4):
            header_rows.append(i)

    if not header_rows:
        # No obvious header; treat entire sheet as one table
        headers = [str(c) for c in df_clean.columns.tolist()]
        rows = _df_to_rows(df_clean)
        tables.append(
            {
                "page": sheet_idx + 1,
                "index": 0,
                "headers": headers,
                "data": {"columns": headers, "rows": rows},
                "raw_text": df_clean.to_string(),
                "confidence": 0.7,
                "sheet_name": sheet_name,
            }
        )
        return tables

    # Use first header row
    header_row_idx = header_rows[0]
    header_vals = [str(v).strip() if pd.notna(v) else "" for v in df_clean.loc[header_row_idx]]
    data_df = df_clean.loc[header_row_idx + 1 :]
    rows = _df_to_rows(data_df)

    tables.append(
        {
            "page": sheet_idx + 1,
            "index": 0,
            "headers": header_vals,
            "data": {"columns": header_vals, "rows": rows},
            "raw_text": df_clean.to_string(),
            "confidence": 0.85,
            "sheet_name": sheet_name,
        }
    )
    return tables


def _df_to_rows(df: pd.DataFrame) -> list:
    rows = []
    for _, row in df.iterrows():
        rows.append([str(v).strip() if pd.notna(v) else "" for v in row])
    return rows


def _extract_text_from_df(df: pd.DataFrame, sheet_name: str) -> str:
    """Extract text strings from the dataframe as a text block."""
    texts = []
    for _, row in df.iterrows():
        for v in row:
            if isinstance(v, str) and v.strip():
                texts.append(v.strip())
    return " | ".join(texts[:200]) if texts else ""
