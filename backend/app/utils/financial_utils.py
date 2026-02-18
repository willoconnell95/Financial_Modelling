import re
from typing import Optional


# Common financial line-item keyword → category mapping
CATEGORY_KEYWORDS = {
    "revenue": ["revenue", "sales", "turnover", "income from operations", "net revenue",
                "gross revenue", "total revenue", "arr", "mrr", "subscription revenue"],
    "cogs": ["cost of revenue", "cost of goods sold", "cogs", "cost of sales",
             "cost of services", "direct costs"],
    "gross_profit": ["gross profit", "gross margin"],
    "opex": ["operating expenses", "opex", "sg&a", "selling general", "administrative",
             "research and development", "r&d", "marketing", "general and administrative"],
    "ebitda": ["ebitda", "earnings before interest tax depreciation"],
    "ebit": ["ebit", "operating income", "operating profit", "operating loss"],
    "interest": ["interest expense", "interest income", "net interest", "finance cost"],
    "tax": ["income tax", "tax expense", "provision for taxes", "corporation tax"],
    "net_income": ["net income", "net profit", "net loss", "profit after tax",
                   "earnings", "profit for the year", "net earnings"],
    "cash": ["cash", "cash and cash equivalents", "cash and equivalents", "bank"],
    "receivables": ["accounts receivable", "trade receivables", "debtors", "receivables"],
    "inventory": ["inventory", "stock", "inventories"],
    "fixed_assets": ["property plant equipment", "ppe", "fixed assets", "tangible assets",
                     "intangible assets", "goodwill"],
    "total_assets": ["total assets"],
    "payables": ["accounts payable", "trade payables", "creditors", "accrued liabilities"],
    "debt": ["debt", "loans", "borrowings", "long-term debt", "short-term debt", "notes payable",
             "credit facility"],
    "equity": ["equity", "shareholders equity", "stockholders equity", "retained earnings",
               "share capital", "common stock"],
    "total_liabilities": ["total liabilities"],
    "operating_cf": ["operating cash flow", "cash from operations", "net cash from operating",
                     "cash generated from operations"],
    "investing_cf": ["investing cash flow", "cash from investing", "net cash used in investing"],
    "financing_cf": ["financing cash flow", "cash from financing", "net cash from financing"],
    "net_cf": ["net change in cash", "increase in cash", "decrease in cash", "net cash flow"],
    "capex": ["capital expenditure", "capex", "purchases of property", "purchase of ppe"],
    "headcount": ["headcount", "employees", "staff", "fte", "full-time equivalent", "workforce"],
    "churn_rate": ["churn", "churn rate", "customer churn", "attrition"],
    "arr": ["arr", "annual recurring revenue", "annualised recurring revenue"],
    "mrr": ["mrr", "monthly recurring revenue"],
    "cac": ["cac", "customer acquisition cost"],
    "ltv": ["ltv", "lifetime value", "customer lifetime value", "clv"],
}


def classify_line_item(line_item: str) -> str:
    """Map a line item label to a FinancialCategory key."""
    normalized = line_item.lower().strip()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in normalized:
                return category
    return "other"


def parse_numeric_value(raw: str) -> Optional[float]:
    """Parse a string like '(1,234.56)' or '£1.2m' into a float."""
    if not raw or not isinstance(raw, str):
        return None
    s = raw.strip()
    negative = False

    # Handle parentheses for negatives: (1,234)
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1]

    # Handle leading minus
    if s.startswith("-"):
        negative = True
        s = s[1:]

    # Strip currency symbols and whitespace
    s = re.sub(r"[£$€¥₹,\s]", "", s)

    # Handle scale suffixes
    multiplier = 1.0
    if s.lower().endswith("m"):
        multiplier = 1_000_000
        s = s[:-1]
    elif s.lower().endswith("k"):
        multiplier = 1_000
        s = s[:-1]
    elif s.lower().endswith("b"):
        multiplier = 1_000_000_000
        s = s[:-1]

    # Handle percentage
    if s.endswith("%"):
        s = s[:-1]
        multiplier = 0.01

    try:
        value = float(s) * multiplier
        return -value if negative else value
    except (ValueError, TypeError):
        return None


def detect_currency(text: str) -> str:
    """Detect currency from a text snippet."""
    if "£" in text:
        return "GBP"
    if "€" in text:
        return "EUR"
    if "¥" in text:
        return "JPY"
    if "₹" in text:
        return "INR"
    if "$" in text:
        return "USD"
    return "USD"


def detect_unit_scale(text: str) -> str:
    """Detect unit scale from header/footer text."""
    lower = text.lower()
    if "million" in lower or " m " in lower or "(£m)" in lower or "($m)" in lower:
        return "millions"
    if "thousand" in lower or "'000" in lower or "(£'000)" in lower or "($'000)" in lower:
        return "thousands"
    if "billion" in lower or " bn " in lower:
        return "billions"
    return "units"


def infer_period_label(col_header: str) -> Optional[str]:
    """Try to extract a period label from a column header string."""
    if not col_header:
        return None
    # Match patterns like FY2023, FY23, 2023, Q1 2024, H1 2023, Jan-23, etc.
    patterns = [
        r"(FY\s*\d{2,4})",
        r"(H[12]\s*\d{2,4})",
        r"(Q[1-4]\s*\d{2,4})",
        r"(\b\d{4}\b)",
        r"([A-Z][a-z]{2,8}[-\s]\d{2,4})",
        r"(\d{2}/\d{2,4})",
    ]
    for pattern in patterns:
        m = re.search(pattern, str(col_header), re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return str(col_header).strip() or None


def calculate_cagr(start_value: float, end_value: float, periods: int) -> Optional[float]:
    """Calculate Compound Annual Growth Rate."""
    if start_value <= 0 or periods <= 0:
        return None
    try:
        return (end_value / start_value) ** (1 / periods) - 1
    except (ZeroDivisionError, ValueError):
        return None


def apply_growth_rate(base_value: float, growth_rate: float, periods: int) -> list[float]:
    """Generate a series of values applying a constant growth rate."""
    values = []
    current = base_value
    for _ in range(periods):
        current = current * (1 + growth_rate)
        values.append(round(current, 4))
    return values
