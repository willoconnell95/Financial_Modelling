"""
Extraction engine: converts ParsedDocument tables/text into
normalised FinancialLineItem records stored in the database.
"""
from __future__ import annotations

import re
from typing import Optional
from loguru import logger

from sqlalchemy.orm import Session

from app.models.financial_data import FinancialLineItem, ExtractedTable
from app.services.document_parser import ParsedDocument, ParsedTable
from app.utils.normalizer import normalize_line_item, normalize_period, clean_numeric_value


class ExtractionEngine:
    """
    Iterates over ParsedDocument tables, attempts to identify financial
    line items, normalise them, and persist to the database.
    """

    def extract(self, document_id: int, parsed_doc: ParsedDocument, db: Session) -> dict:
        """
        Main entry point.
        Returns a summary dict with counts and average confidence.
        """
        extracted_count = 0
        confidence_scores: list[float] = []
        tables_saved = 0

        for parsed_table in parsed_doc.tables:
            # Save raw table
            self._save_raw_table(document_id, parsed_table, db)
            tables_saved += 1

            # Try to extract financial line items
            items, table_confidence = self._extract_from_table(document_id, parsed_table, db)
            extracted_count += items
            if table_confidence is not None:
                confidence_scores.append(table_confidence)

        # Also try to extract from raw text (for narrative financial data)
        text_items = self._extract_from_text(document_id, parsed_doc.raw_text, db)
        extracted_count += text_items

        db.commit()

        avg_confidence = (
            sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.5
        )

        return {
            "tables_found": tables_saved,
            "line_items_extracted": extracted_count,
            "average_confidence": avg_confidence,
        }

    # ------------------------------------------------------------------
    # Raw table persistence
    # ------------------------------------------------------------------
    def _save_raw_table(self, document_id: int, table: ParsedTable, db: Session):
        db_table = ExtractedTable(
            document_id=document_id,
            table_index=table.table_index,
            page_number=table.page_number,
            headers=table.headers,
            raw_data=table.rows,
            confidence_score=table.confidence,
        )
        db.add(db_table)

    # ------------------------------------------------------------------
    # Table-based extraction
    # ------------------------------------------------------------------
    def _extract_from_table(
        self, document_id: int, table: ParsedTable, db: Session
    ) -> tuple[int, Optional[float]]:
        """
        Tries to interpret the table as a financial statement.
        Returns (items_extracted, confidence).
        """
        if not table.headers or not table.rows:
            return 0, None

        # Detect period columns
        period_columns = self._detect_period_columns(table.headers)
        label_column = self._detect_label_column(table.headers)

        if label_column is None or not period_columns:
            return 0, None

        items_extracted = 0
        row_confidences: list[float] = []

        for row in table.rows:
            label_raw = row.get(label_column, "")
            if not label_raw or not str(label_raw).strip():
                continue

            norm_name, category = normalize_line_item(str(label_raw))
            if norm_name is None:
                continue  # not a recognised financial line item

            for period_col, (period_norm, period_type) in period_columns.items():
                raw_val = row.get(period_col)
                if raw_val is None:
                    continue

                value = clean_numeric_value(str(raw_val))
                if value is None:
                    continue

                confidence = self._compute_confidence(norm_name, value, table.confidence)

                item = FinancialLineItem(
                    document_id=document_id,
                    category=category,
                    line_item_name=str(label_raw).strip(),
                    normalized_name=norm_name,
                    period=period_norm,
                    period_type=period_type,
                    value=value,
                    unit=self._infer_unit(norm_name, raw_val),
                    confidence_score=confidence,
                    raw_text=f"{label_raw} | {period_col}: {raw_val}",
                )
                db.add(item)
                items_extracted += 1
                row_confidences.append(confidence)

        avg_conf = sum(row_confidences) / len(row_confidences) if row_confidences else None
        return items_extracted, avg_conf

    def _detect_period_columns(self, headers: list[str]) -> dict[str, tuple[str, str]]:
        """
        Returns {column_name: (normalised_period, period_type)} for
        columns that look like time periods.
        """
        result = {}
        for h in headers:
            if not h or not str(h).strip():
                continue
            norm, ptype = normalize_period(str(h))
            if ptype not in {"unknown"}:
                result[h] = (norm, ptype)
        return result

    def _detect_label_column(self, headers: list[str]) -> Optional[str]:
        """Return the column most likely to contain line-item labels."""
        label_keywords = {
            "item", "description", "line item", "account", "category",
            "particulars", "metric", "kpi", ""
        }
        for h in headers:
            if str(h).lower().strip() in label_keywords:
                return h
        # Default: first column
        if headers:
            return headers[0]
        return None

    # ------------------------------------------------------------------
    # Text-based extraction (regex patterns for inline financials)
    # ------------------------------------------------------------------
    def _extract_from_text(self, document_id: int, text: str, db: Session) -> int:
        """
        Extract financial data mentioned inline in narrative text.
        e.g. "Revenue was £2.4M in FY2023"
        """
        CURRENCY_RE = r"(?:£|\$|€|GBP|USD|EUR)?\s?"
        NUM_RE = r"(\d[\d,.]*(?:\.\d+)?(?:\s?[KMBkmb])?)"
        PERIOD_RE = r"(?:in|for|during|as of)?\s*((?:FY|Q[1-4]\s)?\d{4}(?:\s*[-/]\s*\d{2,4})?)"

        patterns = [
            # "Revenue was £2.4M in FY2023"
            (r"(revenue|sales|turnover)\s+(?:was|were|of|:)?\s*" + CURRENCY_RE + NUM_RE + r"\s*" + PERIOD_RE, "revenue"),
            (r"(ebitda)\s+(?:was|were|of|:)?\s*" + CURRENCY_RE + NUM_RE + r"\s*" + PERIOD_RE, "ebitda"),
            (r"(net\s+(?:income|profit|loss))\s+(?:was|were|of|:)?\s*" + CURRENCY_RE + NUM_RE + r"\s*" + PERIOD_RE, "net_income"),
            (r"(gross\s+profit)\s+(?:was|were|of|:)?\s*" + CURRENCY_RE + NUM_RE + r"\s*" + PERIOD_RE, "gross_profit"),
            (r"(arr|annual\s+recurring\s+revenue)\s+(?:was|were|of|:)?\s*" + CURRENCY_RE + NUM_RE + r"\s*" + PERIOD_RE, "arr"),
            (r"(mrr|monthly\s+recurring\s+revenue)\s+(?:was|were|of|:)?\s*" + CURRENCY_RE + NUM_RE + r"\s*" + PERIOD_RE, "mrr"),
            (r"(headcount|employees?|fte)\s+(?:was|were|of|:)?\s*" + NUM_RE + r"\s*" + PERIOD_RE, "headcount"),
        ]

        count = 0
        for pattern, norm_name in patterns:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                groups = m.groups()
                raw_val = groups[-2] if len(groups) >= 2 else None
                raw_period = groups[-1] if len(groups) >= 1 else None
                if raw_val is None or raw_period is None:
                    continue
                value = clean_numeric_value(raw_val)
                period, period_type = normalize_period(raw_period) if raw_period else (None, None)
                if value is None or period is None:
                    continue
                _, category = normalize_line_item(norm_name)
                item = FinancialLineItem(
                    document_id=document_id,
                    category=category or "other",
                    line_item_name=norm_name,
                    normalized_name=norm_name,
                    period=period,
                    period_type=period_type,
                    value=value,
                    unit="GBP",
                    confidence_score=0.65,
                    raw_text=m.group(0),
                )
                db.add(item)
                count += 1

        return count

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _compute_confidence(self, norm_name: str, value: float, base: float) -> float:
        score = base
        # Penalty for suspiciously large values
        if abs(value) > 1e12:
            score -= 0.2
        # Bonus for known high-signal names
        high_signal = {"revenue", "ebitda", "net_income", "arr", "headcount"}
        if norm_name in high_signal:
            score += 0.05
        return round(min(max(score, 0.0), 1.0), 3)

    def _infer_unit(self, norm_name: str, raw_val: str) -> str:
        raw_str = str(raw_val)
        if "%" in raw_str:
            return "%"
        if norm_name in {"headcount", "customers"}:
            return "count"
        if norm_name in {"churn_rate", "gross_margin_pct", "nrr", "grr"}:
            return "%"
        # Detect currency symbol in raw
        if "£" in raw_str:
            return "GBP"
        if "$" in raw_str:
            return "USD"
        if "€" in raw_str:
            return "EUR"
        return "GBP"  # default
