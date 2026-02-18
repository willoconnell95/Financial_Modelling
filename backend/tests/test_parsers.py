"""Tests for document parsers and financial utilities."""
import pytest
import tempfile
import os
import csv

from app.utils.financial_utils import (
    classify_line_item,
    parse_numeric_value,
    detect_currency,
    detect_unit_scale,
    infer_period_label,
    calculate_cagr,
    apply_growth_rate,
)
from app.services.csv_parser import parse_csv
from app.services.data_normalizer import DataNormalizer


# ── Financial utility tests ─────────────────────────────────────────────────

class TestClassifyLineItem:
    def test_revenue_keywords(self):
        assert classify_line_item("Total Revenue") == "revenue"
        assert classify_line_item("Net Sales") == "revenue"
        assert classify_line_item("Turnover") == "revenue"

    def test_cogs_keywords(self):
        assert classify_line_item("Cost of Goods Sold") == "cogs"
        assert classify_line_item("Cost of Revenue") == "cogs"

    def test_ebitda_keyword(self):
        assert classify_line_item("EBITDA") == "ebitda"

    def test_net_income(self):
        assert classify_line_item("Net Income") == "net_income"
        assert classify_line_item("Net Profit") == "net_income"

    def test_headcount(self):
        assert classify_line_item("Total Headcount") == "headcount"
        assert classify_line_item("Full-time Employees") == "headcount"

    def test_unknown(self):
        assert classify_line_item("Random undefined item") == "other"


class TestParseNumericValue:
    def test_plain_number(self):
        assert parse_numeric_value("1234.56") == 1234.56

    def test_comma_separated(self):
        assert parse_numeric_value("1,234,567") == 1_234_567

    def test_parentheses_negative(self):
        assert parse_numeric_value("(1,234.56)") == -1234.56

    def test_leading_minus(self):
        assert parse_numeric_value("-500") == -500

    def test_currency_prefix(self):
        assert parse_numeric_value("£1,000") == 1000
        assert parse_numeric_value("$2,500.00") == 2500.0

    def test_millions_suffix(self):
        assert parse_numeric_value("5m") == 5_000_000
        assert parse_numeric_value("1.5M") == 1_500_000

    def test_thousands_suffix(self):
        assert parse_numeric_value("100k") == 100_000

    def test_percentage(self):
        assert pytest.approx(parse_numeric_value("25%"), 0.001) == 0.25

    def test_empty_string(self):
        assert parse_numeric_value("") is None

    def test_non_numeric(self):
        assert parse_numeric_value("Revenue") is None

    def test_dash(self):
        assert parse_numeric_value("-") is None


class TestDetectCurrency:
    def test_gbp(self):
        assert detect_currency("£1,000") == "GBP"

    def test_eur(self):
        assert detect_currency("€500") == "EUR"

    def test_usd(self):
        assert detect_currency("$100 total") == "USD"

    def test_default_usd(self):
        assert detect_currency("no symbol here") == "USD"


class TestDetectUnitScale:
    def test_millions(self):
        assert detect_unit_scale("(£m)") == "millions"
        assert detect_unit_scale("in millions") == "millions"

    def test_thousands(self):
        assert detect_unit_scale("($'000)") == "thousands"
        assert detect_unit_scale("in thousands") == "thousands"

    def test_billions(self):
        assert detect_unit_scale("figures in bn") == "billions"

    def test_default(self):
        assert detect_unit_scale("no scale hint") == "units"


class TestInferPeriodLabel:
    def test_fy_label(self):
        assert infer_period_label("FY2023") == "FY2023"

    def test_year_only(self):
        result = infer_period_label("2024")
        assert result is not None and "2024" in result

    def test_quarter(self):
        result = infer_period_label("Q1 2024")
        assert result is not None and "Q1" in result

    def test_empty(self):
        assert infer_period_label("") is None


class TestCAGR:
    def test_basic_cagr(self):
        cagr = calculate_cagr(100, 121, 2)
        assert pytest.approx(cagr, 0.001) == 0.1

    def test_zero_start(self):
        assert calculate_cagr(0, 100, 3) is None

    def test_zero_periods(self):
        assert calculate_cagr(100, 200, 0) is None


class TestApplyGrowthRate:
    def test_basic_growth(self):
        values = apply_growth_rate(100, 0.10, 3)
        assert len(values) == 3
        assert pytest.approx(values[0], 0.001) == 110.0
        assert pytest.approx(values[2], 0.01) == 133.1


# ── CSV parser tests ─────────────────────────────────────────────────────────

class TestCsvParser:
    def test_simple_csv(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Line Item", "FY2022", "FY2023"])
            writer.writerow(["Revenue", "1000", "1200"])
            writer.writerow(["COGS", "600", "700"])

        result = parse_csv(str(csv_file))
        assert result["page_count"] == 1
        assert len(result["tables"]) == 1
        table = result["tables"][0]
        assert "FY2022" in table["headers"]
        assert len(table["data"]["rows"]) == 2
        assert result["confidence"] > 0.5

    def test_empty_csv(self, tmp_path):
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("")
        result = parse_csv(str(csv_file))
        assert result["errors"] or result["tables"] == []


# ── Data normalizer tests ────────────────────────────────────────────────────

class TestDataNormalizer:
    def test_normalises_revenue_row(self):
        normalizer = DataNormalizer()
        tables = [
            {
                "headers": ["Line Item", "FY2022", "FY2023"],
                "data": {
                    "columns": ["Line Item", "FY2022", "FY2023"],
                    "rows": [
                        ["Revenue", "1,000", "1,200"],
                        ["COGS", "600", "700"],
                    ],
                },
                "confidence": 0.9,
            }
        ]
        records = normalizer.normalise_tables(tables, [], 1)
        assert len(records) > 0
        rev_records = [r for r in records if r.category == "revenue"]
        assert len(rev_records) > 0
        fy22_rev = next((r for r in rev_records if r.period_label == "FY2022"), None)
        assert fy22_rev is not None
        assert fy22_rev.value == 1000.0

    def test_detects_currency_from_text(self):
        normalizer = DataNormalizer()
        tables = [
            {
                "headers": ["Item", "2023"],
                "data": {"columns": ["Item", "2023"], "rows": [["Net Income", "500"]]},
                "confidence": 0.8,
            }
        ]
        texts = [{"content": "All figures in £000", "type": "body"}]
        records = normalizer.normalise_tables(tables, texts, 1)
        assert any(r.currency == "GBP" for r in records)
