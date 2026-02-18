"""Unit tests for normaliser and extraction utilities."""
import pytest
from app.utils.normalizer import normalize_line_item, normalize_period, clean_numeric_value


# ── Normaliser tests ─────────────────────────────────────────────────────────

class TestNormalizeLineItem:
    def test_revenue_exact(self):
        name, cat = normalize_line_item("Revenue")
        assert name == "revenue"
        assert cat == "income_statement"

    def test_revenue_synonym(self):
        name, cat = normalize_line_item("Net Sales")
        assert name == "revenue"

    def test_cogs(self):
        name, cat = normalize_line_item("Cost of Goods Sold")
        assert name == "cogs"

    def test_ebitda(self):
        name, cat = normalize_line_item("EBITDA")
        assert name == "ebitda"
        assert cat == "income_statement"

    def test_arr(self):
        name, cat = normalize_line_item("Annual Recurring Revenue")
        assert name == "arr"
        assert cat == "kpi"

    def test_headcount(self):
        name, cat = normalize_line_item("FTE")
        assert name == "headcount"
        assert cat == "kpi"

    def test_unknown(self):
        name, cat = normalize_line_item("Some random text")
        assert name is None
        assert cat is None

    def test_case_insensitive(self):
        name, _ = normalize_line_item("REVENUE")
        assert name == "revenue"

    def test_balance_sheet(self):
        name, cat = normalize_line_item("Total Assets")
        assert name == "total_assets"
        assert cat == "balance_sheet"

    def test_cash_flow(self):
        name, cat = normalize_line_item("Operating Cash Flow")
        assert name == "operating_cashflow"
        assert cat == "cash_flow"


class TestNormalizePeriod:
    def test_fy_year(self):
        period, ptype = normalize_period("FY2023")
        assert period == "FY2023"
        assert ptype == "annual"

    def test_bare_year(self):
        period, ptype = normalize_period("2023")
        assert period == "FY2023"
        assert ptype == "annual"

    def test_fy_short(self):
        period, ptype = normalize_period("FY24")
        assert period == "FY2024"
        assert ptype == "annual"

    def test_quarterly(self):
        period, ptype = normalize_period("Q1 2023")
        assert period == "2023-Q1"
        assert ptype == "quarterly"

    def test_quarterly_dash(self):
        period, ptype = normalize_period("Q3-2024")
        assert period == "2024-Q3"
        assert ptype == "quarterly"

    def test_monthly_name(self):
        period, ptype = normalize_period("Jan 2023")
        assert period == "2023-01"
        assert ptype == "monthly"

    def test_monthly_numeric(self):
        period, ptype = normalize_period("2023-06")
        assert period == "2023-06"
        assert ptype == "monthly"

    def test_semi_annual(self):
        period, ptype = normalize_period("H1 2024")
        assert period == "H1-2024"
        assert ptype == "semi_annual"


class TestCleanNumericValue:
    def test_simple(self):
        assert clean_numeric_value("1234") == 1234.0

    def test_comma_separated(self):
        assert clean_numeric_value("1,234,567") == 1234567.0

    def test_parentheses_negative(self):
        assert clean_numeric_value("(1,500)") == -1500.0

    def test_millions(self):
        assert clean_numeric_value("2.5M") == 2_500_000.0

    def test_thousands(self):
        assert clean_numeric_value("500K") == 500_000.0

    def test_billions(self):
        assert clean_numeric_value("1.2B") == 1_200_000_000.0

    def test_percentage(self):
        # Percentage sign stripped, value returned as-is
        val = clean_numeric_value("15%")
        assert val == 15.0

    def test_na_returns_none(self):
        assert clean_numeric_value("N/A") is None
        assert clean_numeric_value("—") is None
        assert clean_numeric_value("") is None

    def test_negative_dash(self):
        assert clean_numeric_value("-500") == -500.0

    def test_decimal(self):
        assert abs(clean_numeric_value("1.23") - 1.23) < 0.0001
