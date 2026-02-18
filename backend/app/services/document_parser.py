"""
Document parser service.
Handles PDF, Excel, CSV, DOCX, and image files.
Returns a unified ParsedDocument object.
"""
from __future__ import annotations

import io
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from loguru import logger


@dataclass
class ParsedTable:
    table_index: int
    headers: list[str]
    rows: list[dict[str, Any]]
    page_number: Optional[int] = None
    confidence: float = 0.8


@dataclass
class ParsedDocument:
    file_type: str
    raw_text: str = ""
    tables: list[ParsedTable] = field(default_factory=list)
    page_count: int = 0
    metadata: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


class DocumentParser:
    """
    Unified parser that dispatches to format-specific parsers.
    """

    def parse(self, file_path: str, file_type: str) -> ParsedDocument:
        ext = Path(file_path).suffix.lower().lstrip(".")
        parser_map = {
            "pdf": self._parse_pdf,
            "xlsx": self._parse_excel,
            "xls": self._parse_excel,
            "csv": self._parse_csv,
            "docx": self._parse_docx,
            "doc": self._parse_docx,
            "png": self._parse_image,
            "jpg": self._parse_image,
            "jpeg": self._parse_image,
            "tiff": self._parse_image,
            "tif": self._parse_image,
        }

        parser_fn = parser_map.get(ext)
        if not parser_fn:
            doc = ParsedDocument(file_type=ext)
            doc.errors.append(f"Unsupported file type: {ext}")
            return doc

        try:
            return parser_fn(file_path)
        except Exception as e:
            logger.error(f"Parse error for {file_path}: {e}")
            doc = ParsedDocument(file_type=ext)
            doc.errors.append(str(e))
            return doc

    # ------------------------------------------------------------------
    # PDF
    # ------------------------------------------------------------------
    def _parse_pdf(self, file_path: str) -> ParsedDocument:
        import pdfplumber

        doc = ParsedDocument(file_type="pdf")
        texts: list[str] = []
        table_idx = 0

        try:
            with pdfplumber.open(file_path) as pdf:
                doc.page_count = len(pdf.pages)
                doc.metadata = pdf.metadata or {}

                for page_num, page in enumerate(pdf.pages, start=1):
                    # Extract text
                    text = page.extract_text() or ""
                    texts.append(text)

                    # Extract tables
                    tables = page.extract_tables() or []
                    for raw_table in tables:
                        if not raw_table or len(raw_table) < 2:
                            continue

                        headers, rows = self._process_raw_table(raw_table)
                        if headers and rows:
                            doc.tables.append(ParsedTable(
                                table_index=table_idx,
                                headers=headers,
                                rows=rows,
                                page_number=page_num,
                                confidence=0.85,
                            ))
                            table_idx += 1

            doc.raw_text = "\n\n".join(texts)
        except Exception as e:
            doc.errors.append(f"PDF parse error: {e}")

        # Fallback: try PyMuPDF if pdfplumber gave nothing
        if not doc.raw_text.strip() and not doc.errors:
            doc = self._parse_pdf_fitz(file_path, doc)

        return doc

    def _parse_pdf_fitz(self, file_path: str, doc: ParsedDocument) -> ParsedDocument:
        try:
            import fitz  # PyMuPDF
            pdf = fitz.open(file_path)
            texts = []
            for page in pdf:
                texts.append(page.get_text())
            doc.raw_text = "\n\n".join(texts)
            pdf.close()
        except Exception as e:
            doc.errors.append(f"PyMuPDF fallback error: {e}")
        return doc

    # ------------------------------------------------------------------
    # Excel
    # ------------------------------------------------------------------
    def _parse_excel(self, file_path: str) -> ParsedDocument:
        import pandas as pd

        doc = ParsedDocument(file_type="excel")
        table_idx = 0

        try:
            xl = pd.ExcelFile(file_path, engine="openpyxl")
            doc.metadata = {"sheets": xl.sheet_names}
            all_text: list[str] = []

            for sheet_name in xl.sheet_names:
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet_name, header=None, engine="openpyxl")
                    if df.empty:
                        continue

                    # Try to find the header row (first non-empty row with multiple non-null cols)
                    header_row_idx = self._detect_header_row(df)
                    if header_row_idx is not None:
                        df_data = df.iloc[header_row_idx + 1:].reset_index(drop=True)
                        headers = [str(c) if c is not None else f"Col{i}" for i, c in enumerate(df.iloc[header_row_idx])]
                    else:
                        df_data = df.iloc[1:].reset_index(drop=True)
                        headers = [str(c) if c is not None else f"Col{i}" for i, c in enumerate(df.iloc[0])]

                    rows = []
                    for _, row in df_data.iterrows():
                        row_dict = {}
                        for h, val in zip(headers, row):
                            row_dict[h] = None if (val != val) else val  # nan -> None
                        rows.append(row_dict)

                    # Skip if all values are empty
                    if any(any(v is not None for v in r.values()) for r in rows):
                        doc.tables.append(ParsedTable(
                            table_index=table_idx,
                            headers=headers,
                            rows=rows,
                            page_number=None,
                            confidence=0.9,
                        ))
                        table_idx += 1
                        all_text.append(f"[Sheet: {sheet_name}]\n" + df.to_string())

                except Exception as e:
                    doc.errors.append(f"Sheet '{sheet_name}' error: {e}")

            doc.raw_text = "\n\n".join(all_text)

        except Exception as e:
            # Try xlrd for older .xls files
            try:
                import pandas as pd
                df = pd.read_excel(file_path, header=None, engine="xlrd")
                headers_list = [str(c) for c in df.iloc[0]]
                rows = df.iloc[1:].to_dict(orient="records")
                doc.tables.append(ParsedTable(
                    table_index=0, headers=headers_list, rows=rows, confidence=0.8
                ))
                doc.raw_text = df.to_string()
            except Exception as e2:
                doc.errors.append(f"Excel parse error: {e} / {e2}")

        return doc

    def _detect_header_row(self, df) -> Optional[int]:
        """Find the first row where the majority of cells are non-null strings."""
        for i, row in df.iterrows():
            non_null = row.dropna()
            if len(non_null) >= 2:
                str_count = sum(1 for v in non_null if isinstance(v, str))
                if str_count >= len(non_null) * 0.5:
                    return i
        return None

    # ------------------------------------------------------------------
    # CSV
    # ------------------------------------------------------------------
    def _parse_csv(self, file_path: str) -> ParsedDocument:
        import pandas as pd

        doc = ParsedDocument(file_type="csv")

        try:
            df = pd.read_csv(file_path, encoding="utf-8-sig")
            headers = list(df.columns)
            rows = df.to_dict(orient="records")

            doc.tables.append(ParsedTable(
                table_index=0,
                headers=headers,
                rows=rows,
                confidence=0.95,
            ))
            doc.raw_text = df.to_string()
            doc.page_count = 1

        except Exception as e:
            doc.errors.append(f"CSV parse error: {e}")

        return doc

    # ------------------------------------------------------------------
    # DOCX
    # ------------------------------------------------------------------
    def _parse_docx(self, file_path: str) -> ParsedDocument:
        from docx import Document as DocxDocument
        from docx.oxml.ns import qn

        doc = ParsedDocument(file_type="docx")
        texts: list[str] = []
        table_idx = 0

        try:
            docx = DocxDocument(file_path)

            # Extract paragraphs
            for para in docx.paragraphs:
                if para.text.strip():
                    texts.append(para.text.strip())

            # Extract tables
            for tbl in docx.tables:
                raw_rows = []
                for row in tbl.rows:
                    raw_rows.append([cell.text.strip() for cell in row.cells])

                if len(raw_rows) < 2:
                    continue

                headers, rows = self._process_raw_table(raw_rows)
                if headers and rows:
                    doc.tables.append(ParsedTable(
                        table_index=table_idx,
                        headers=headers,
                        rows=rows,
                        confidence=0.85,
                    ))
                    table_idx += 1

            doc.raw_text = "\n".join(texts)
            doc.page_count = 1

        except Exception as e:
            doc.errors.append(f"DOCX parse error: {e}")

        return doc

    # ------------------------------------------------------------------
    # Image (OCR)
    # ------------------------------------------------------------------
    def _parse_image(self, file_path: str) -> ParsedDocument:
        doc = ParsedDocument(file_type="image")

        try:
            import pytesseract
            from PIL import Image

            img = Image.open(file_path)
            text = pytesseract.image_to_string(img)
            doc.raw_text = text
            doc.page_count = 1

            # Try to extract table-like structures from OCR text
            tables = self._tables_from_text(text)
            doc.tables.extend(tables)

        except ImportError:
            doc.errors.append("pytesseract / Pillow not installed – OCR unavailable")
        except Exception as e:
            doc.errors.append(f"Image parse error: {e}")

        return doc

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _process_raw_table(self, raw_table: list[list]) -> tuple[list[str], list[dict]]:
        """Convert a list-of-lists table into (headers, rows)."""
        if not raw_table:
            return [], []

        # Use first row as header if it looks like headers
        header_row = [str(c).strip() if c is not None else "" for c in raw_table[0]]

        # De-duplicate headers
        seen: dict[str, int] = {}
        clean_headers = []
        for h in header_row:
            if h in seen:
                seen[h] += 1
                clean_headers.append(f"{h}_{seen[h]}")
            else:
                seen[h] = 0
                clean_headers.append(h)

        rows = []
        for raw_row in raw_table[1:]:
            row_dict = {}
            for i, val in enumerate(raw_row):
                key = clean_headers[i] if i < len(clean_headers) else f"col_{i}"
                row_dict[key] = str(val).strip() if val is not None else None
            rows.append(row_dict)

        return clean_headers, rows

    def _tables_from_text(self, text: str) -> list[ParsedTable]:
        """Attempt to parse whitespace-aligned tables from OCR text."""
        import re
        tables: list[ParsedTable] = []
        lines = text.split("\n")
        table_lines: list[str] = []

        for line in lines:
            # Heuristic: line has at least 3 numeric/word columns separated by whitespace
            parts = re.split(r"\s{2,}", line.strip())
            if len(parts) >= 3:
                table_lines.append(line)
            else:
                if len(table_lines) >= 3:
                    parsed = self._parse_text_table(table_lines)
                    if parsed:
                        tables.append(parsed)
                table_lines = []

        return tables

    def _parse_text_table(self, lines: list[str]) -> Optional[ParsedTable]:
        import re
        rows_raw = [re.split(r"\s{2,}", l.strip()) for l in lines]
        if not rows_raw:
            return None
        headers = rows_raw[0]
        rows = []
        for raw_row in rows_raw[1:]:
            row_dict = {}
            for i, val in enumerate(raw_row):
                key = headers[i] if i < len(headers) else f"col_{i}"
                row_dict[key] = val
            rows.append(row_dict)
        return ParsedTable(table_index=0, headers=headers, rows=rows, confidence=0.5)
