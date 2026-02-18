"""
Financial data normalisation utilities.
Maps raw extracted line-item names to canonical keys and categories.
"""
import re
from typing import Optional, Tuple

# ---------------------------------------------------------------------------
# Canonical mapping: normalized_name -> list of synonym patterns
# ---------------------------------------------------------------------------
FINANCIAL_SYNONYMS: dict[str, list[str]] = {
    # ── Income Statement ──────────────────────────────────────────────────
    "revenue": [
        r"revenue", r"sales", r"turnover", r"net revenue", r"gross revenue",
        r"income from operations", r"total revenue", r"total sales", r"net sales",
    ],
    "cogs": [
        r"cost of goods sold", r"cogs", r"cost of sales", r"cost of revenue",
        r"direct costs?", r"cost of services",
    ],
    "gross_profit": [r"gross profit", r"gross income"],
    "gross_margin_pct": [r"gross margin\s*%?", r"gross margin percentage"],
    "research_and_development": [r"research and development", r"r&d", r"r & d"],
    "sales_and_marketing": [r"sales and marketing", r"s&m", r"marketing expense"],
    "general_and_admin": [
        r"general and administrative", r"g&a", r"sg&a",
        r"selling general and administrative",
    ],
    "operating_expenses": [
        r"operating expenses?", r"opex", r"total operating expenses?",
        r"operating costs?",
    ],
    "ebitda": [
        r"ebitda", r"earnings before interest.*tax.*depreciation.*amortization",
        r"adjusted ebitda",
    ],
    "depreciation_amortization": [
        r"depreciation and amortization", r"d&a", r"depreciation",
        r"amortization",
    ],
    "ebit": [r"ebit", r"operating profit", r"operating income", r"operating loss"],
    "interest_expense": [r"interest expense", r"finance costs?", r"interest payable"],
    "interest_income": [r"interest income", r"finance income"],
    "net_interest": [r"net interest", r"net finance costs?"],
    "tax": [
        r"income tax", r"tax expense", r"corporation tax", r"corporate tax",
        r"provision for income taxes?",
    ],
    "net_income": [
        r"net income", r"net profit", r"net loss", r"profit after tax",
        r"pat", r"bottom line", r"net earnings",
    ],
    # ── Balance Sheet ─────────────────────────────────────────────────────
    "cash": [r"cash", r"cash and cash equivalents", r"cash and equivalents"],
    "accounts_receivable": [
        r"accounts receivable", r"trade receivables", r"debtors",
        r"trade and other receivables",
    ],
    "inventory": [r"inventory", r"inventories", r"stock"],
    "total_current_assets": [r"total current assets", r"current assets"],
    "total_assets": [r"total assets"],
    "accounts_payable": [
        r"accounts payable", r"trade payables", r"creditors",
        r"trade and other payables",
    ],
    "total_current_liabilities": [r"total current liabilities", r"current liabilities"],
    "total_liabilities": [r"total liabilities"],
    "equity": [
        r"equity", r"shareholders.? equity", r"stockholders.? equity",
        r"net assets", r"total equity",
    ],
    "long_term_debt": [r"long.?term debt", r"long.?term borrowings", r"term loans?"],
    # ── Cash Flow ─────────────────────────────────────────────────────────
    "operating_cashflow": [
        r"cash from operations", r"operating cash flow", r"cfo",
        r"net cash from operating activities",
    ],
    "capex": [
        r"capex", r"capital expenditure", r"purchase of property.*plant.*equipment",
        r"pp&e additions",
    ],
    "investing_cashflow": [
        r"investing cash flow", r"cash from investing",
        r"net cash from investing activities",
    ],
    "financing_cashflow": [
        r"financing cash flow", r"cash from financing",
        r"net cash from financing activities",
    ],
    "free_cash_flow": [r"free cash flow", r"fcf"],
    # ── KPIs ──────────────────────────────────────────────────────────────
    "headcount": [r"headcount", r"employees", r"fte", r"full.?time equivalent", r"staff count"],
    "arr": [r"\barr\b", r"annual recurring revenue"],
    "mrr": [r"\bmrr\b", r"monthly recurring revenue"],
    "arr_growth": [r"arr growth"],
    "churn_rate": [r"churn\s*rate", r"customer churn", r"revenue churn", r"net churn"],
    "nrr": [r"\bnrr\b", r"net revenue retention", r"net dollar retention"],
    "grr": [r"\bgrr\b", r"gross revenue retention", r"gross dollar retention"],
    "customers": [r"customers?", r"clients?", r"accounts?"],
    "average_revenue_per_user": [r"arpu", r"average revenue per user", r"average revenue per account"],
    "cac": [r"\bcac\b", r"customer acquisition cost"],
    "ltv": [r"\bltv\b", r"lifetime value", r"customer lifetime value", r"clv"],
}

# Category lookup
CATEGORY_MAP: dict[str, str] = {}
SUBCATEGORY_MAP: dict[str, str] = {}

_INCOME_ITEMS = {
    "revenue", "cogs", "gross_profit", "gross_margin_pct",
    "research_and_development", "sales_and_marketing", "general_and_admin",
    "operating_expenses", "ebitda", "depreciation_amortization", "ebit",
    "interest_expense", "interest_income", "net_interest", "tax", "net_income",
}
_BALANCE_SHEET_ITEMS = {
    "cash", "accounts_receivable", "inventory", "total_current_assets",
    "total_assets", "accounts_payable", "total_current_liabilities",
    "total_liabilities", "equity", "long_term_debt",
}
_CASHFLOW_ITEMS = {
    "operating_cashflow", "capex", "investing_cashflow",
    "financing_cashflow", "free_cash_flow",
}
_KPI_ITEMS = {
    "headcount", "arr", "mrr", "arr_growth", "churn_rate", "nrr", "grr",
    "customers", "average_revenue_per_user", "cac", "ltv",
}

for name in _INCOME_ITEMS:
    CATEGORY_MAP[name] = "income_statement"
for name in _BALANCE_SHEET_ITEMS:
    CATEGORY_MAP[name] = "balance_sheet"
for name in _CASHFLOW_ITEMS:
    CATEGORY_MAP[name] = "cash_flow"
for name in _KPI_ITEMS:
    CATEGORY_MAP[name] = "kpi"


def normalize_line_item(raw_name: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Map a raw line-item label to (normalized_name, category).
    Returns (None, None) if no match found.
    """
    clean = raw_name.lower().strip()
    clean = re.sub(r"[^\w\s&%/'-]", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()

    for norm_name, patterns in FINANCIAL_SYNONYMS.items():
        for pattern in patterns:
            if re.search(pattern, clean, re.IGNORECASE):
                category = CATEGORY_MAP.get(norm_name, "other")
                return norm_name, category

    return None, None


def normalize_period(raw_period: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Normalize a period string to a canonical form.
    Returns (period, period_type).

    Examples:
        "FY2023"      -> ("FY2023", "annual")
        "Q1 2023"     -> ("2023-Q1", "quarterly")
        "Jan 2023"    -> ("2023-01", "monthly")
        "2023"        -> ("FY2023", "annual")
        "H1 2024"     -> ("H1-2024", "semi_annual")
    """
    raw = raw_period.strip()

    # Annual: FY2023, 2023, FY23
    m = re.match(r"^(?:FY)?(\d{4})$", raw, re.IGNORECASE)
    if m:
        return f"FY{m.group(1)}", "annual"

    m = re.match(r"^FY\s*(\d{2})$", raw, re.IGNORECASE)
    if m:
        year = 2000 + int(m.group(1))
        return f"FY{year}", "annual"

    # Quarterly: Q1 2023, 2023 Q1, Q1-2023
    m = re.match(r"^Q([1-4])\s*[-/]?\s*(\d{4})$", raw, re.IGNORECASE)
    if m:
        return f"{m.group(2)}-Q{m.group(1)}", "quarterly"

    m = re.match(r"^(\d{4})\s*[-/]?\s*Q([1-4])$", raw, re.IGNORECASE)
    if m:
        return f"{m.group(1)}-Q{m.group(2)}", "quarterly"

    # Monthly: Jan 2023, January 2023, 2023-01, 01/2023
    month_names = {
        "jan": "01", "feb": "02", "mar": "03", "apr": "04",
        "may": "05", "jun": "06", "jul": "07", "aug": "08",
        "sep": "09", "oct": "10", "nov": "11", "dec": "12",
        "january": "01", "february": "02", "march": "03", "april": "04",
        "june": "06", "july": "07", "august": "08", "september": "09",
        "october": "10", "november": "11", "december": "12",
    }

    m = re.match(r"^([a-zA-Z]+)\s+(\d{4})$", raw)
    if m:
        mon = m.group(1).lower()
        if mon in month_names:
            return f"{m.group(2)}-{month_names[mon]}", "monthly"

    m = re.match(r"^(\d{4})[- /](\d{2})$", raw)
    if m:
        return f"{m.group(1)}-{m.group(2)}", "monthly"

    m = re.match(r"^(\d{2})/(\d{4})$", raw)
    if m:
        return f"{m.group(2)}-{m.group(1)}", "monthly"

    # Semi-annual: H1 2024
    m = re.match(r"^H([12])\s*[-]?\s*(\d{4})$", raw, re.IGNORECASE)
    if m:
        return f"H{m.group(1)}-{m.group(2)}", "semi_annual"

    # Fallback: return as-is
    return raw, "unknown"


def clean_numeric_value(raw: str) -> Optional[float]:
    """
    Parse a raw string to float, handling:
    - Parentheses for negatives: (1,234) -> -1234
    - Commas: 1,234,567 -> 1234567
    - K/M/B suffixes: 1.5M -> 1500000
    - Percentage signs: 15% -> 0.15  (caller decides interpretation)
    """
    if raw is None:
        return None

    s = str(raw).strip()
    if not s or s in {"-", "—", "n/a", "N/A", "na", "NA", "#N/A", "n.a."}:
        return None

    is_negative = False
    if s.startswith("(") and s.endswith(")"):
        is_negative = True
        s = s[1:-1]
    elif s.startswith("-"):
        is_negative = True
        s = s[1:]

    s = s.replace(",", "").replace(" ", "")

    # Suffix multipliers
    multiplier = 1.0
    if s.endswith("%"):
        s = s[:-1]
        # Return raw percentage (caller normalises)
    elif s.upper().endswith("B"):
        multiplier = 1e9
        s = s[:-1]
    elif s.upper().endswith("M"):
        multiplier = 1e6
        s = s[:-1]
    elif s.upper().endswith("K"):
        multiplier = 1e3
        s = s[:-1]

    try:
        val = float(s) * multiplier
        return -val if is_negative else val
    except ValueError:
        return None
