"""
Data normalisation service.
Takes raw parsed tables/text and maps them to structured FinancialRecord objects.
"""
import logging
import re
from typing import Optional
from app.utils.financial_utils import (
    classify_line_item,
    parse_numeric_value,
    detect_currency,
    detect_unit_scale,
    infer_period_label,
)

logger = logging.getLogger(__name__)


class NormalisedRecord:
    """Lightweight DTO before DB insertion."""

    def __init__(self, **kwargs):
        self.category = kwargs.get("category", "other")
        self.subcategory = kwargs.get("subcategory")
        self.line_item = kwargs.get("line_item", "")
        self.period_label = kwargs.get("period_label")
        self.value = kwargs.get("value")
        self.currency = kwargs.get("currency", "USD")
        self.unit = kwargs.get("unit", "units")
        self.confidence = kwargs.get("confidence", 0.5)
        self.source_text = kwargs.get("source_text")
        self.tags = kwargs.get("tags", [])

    def to_dict(self) -> dict:
        return self.__dict__


class DataNormalizer:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def normalise_tables(
        self,
        tables: list[dict],
        texts: list[dict],
        document_id: int,
    ) -> list[NormalisedRecord]:
        """
        Process all extracted tables and return normalised financial records.
        """
        records: list[NormalisedRecord] = []
        # Detect currency / scale from text context
        all_text = " ".join(t.get("content", "") for t in texts)
        currency = detect_currency(all_text)
        unit_scale = detect_unit_scale(all_text)

        for table in tables:
            try:
                table_records = self._normalise_table(table, currency, unit_scale)
                records.extend(table_records)
            except Exception as e:
                self.errors.append(f"Table normalisation error: {str(e)}")
                logger.warning(f"Table normalisation failed: {e}")

        return records

    def _normalise_table(
        self, table: dict, currency: str, unit_scale: str
    ) -> list[NormalisedRecord]:
        records: list[NormalisedRecord] = []
        headers = table.get("headers", [])
        data = table.get("data", {})
        rows = data.get("rows", [])
        confidence = table.get("confidence", 0.5)

        if not headers or not rows:
            return records

        # Identify which columns are period columns (contain numbers/dates)
        period_cols = self._identify_period_columns(headers)
        label_col_idx = self._identify_label_column(headers, rows)

        if label_col_idx is None:
            return records

        for row in rows:
            if len(row) <= label_col_idx:
                continue
            line_item = str(row[label_col_idx]).strip()
            if not line_item or line_item in ("", "nan", "None"):
                continue

            category = classify_line_item(line_item)

            for col_idx, period_label in period_cols:
                if col_idx >= len(row):
                    continue
                raw_val = row[col_idx]
                value = parse_numeric_value(str(raw_val)) if raw_val else None

                if value is None and not str(raw_val).strip():
                    continue

                records.append(
                    NormalisedRecord(
                        category=category,
                        line_item=line_item,
                        period_label=period_label,
                        value=value,
                        currency=currency,
                        unit=unit_scale,
                        confidence=confidence,
                        source_text=f"Table row: {line_item} | Col: {headers[col_idx]}",
                        tags=["extracted"],
                    )
                )

        return records

    def _identify_period_columns(self, headers: list) -> list[tuple[int, Optional[str]]]:
        """
        Return list of (col_index, period_label) for columns that look like periods.
        """
        period_cols = []
        for idx, header in enumerate(headers):
            label = infer_period_label(str(header))
            if label:
                period_cols.append((idx, label))
        # If no period columns found by label heuristic, treat all numeric-looking
        # columns as data columns with their header as the period label
        if not period_cols:
            for idx, header in enumerate(headers[1:], start=1):
                h = str(header).strip()
                if h and h.lower() not in ("total", "sum"):
                    period_cols.append((idx, h if h else f"Col{idx}"))
        return period_cols

    def _identify_label_column(self, headers: list, rows: list) -> Optional[int]:
        """
        Identify which column contains line-item labels (strings, not numbers).
        """
        if not headers:
            return None

        # Score each column by how many string values it has
        col_scores = {}
        for col_idx, header in enumerate(headers):
            string_count = 0
            for row in rows[:20]:  # sample first 20 rows
                if col_idx < len(row):
                    val = str(row[col_idx]).strip()
                    if val and parse_numeric_value(val) is None:
                        string_count += 1
            col_scores[col_idx] = string_count

        if not col_scores:
            return 0

        best_col = max(col_scores, key=lambda k: col_scores[k])
        return best_col if col_scores[best_col] > 0 else 0
