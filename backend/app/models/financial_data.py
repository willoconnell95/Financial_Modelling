from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Integer, Float, DateTime, Date, Text, JSON, ForeignKey, Enum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


class PeriodType(str, enum.Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    LTM = "ltm"
    YTD = "ytd"


class FinancialCategory(str, enum.Enum):
    REVENUE = "revenue"
    COGS = "cogs"
    GROSS_PROFIT = "gross_profit"
    OPEX = "opex"
    EBITDA = "ebitda"
    EBIT = "ebit"
    INTEREST = "interest"
    TAX = "tax"
    NET_INCOME = "net_income"
    # Balance sheet
    CASH = "cash"
    RECEIVABLES = "receivables"
    INVENTORY = "inventory"
    FIXED_ASSETS = "fixed_assets"
    TOTAL_ASSETS = "total_assets"
    PAYABLES = "payables"
    DEBT = "debt"
    EQUITY = "equity"
    TOTAL_LIABILITIES = "total_liabilities"
    # Cashflow
    OPERATING_CF = "operating_cf"
    INVESTING_CF = "investing_cf"
    FINANCING_CF = "financing_cf"
    NET_CF = "net_cf"
    CAPEX = "capex"
    # Operational
    HEADCOUNT = "headcount"
    UNITS_SOLD = "units_sold"
    CHURN_RATE = "churn_rate"
    ARR = "arr"
    MRR = "mrr"
    CAC = "cac"
    LTV = "ltv"
    OTHER = "other"


class FinancialPeriod(Base):
    __tablename__ = "financial_periods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    label: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "FY2023", "Q1 2024"
    period_type: Mapped[PeriodType] = mapped_column(Enum(PeriodType), nullable=False)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_forecast: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    records: Mapped[list["FinancialRecord"]] = relationship(
        "FinancialRecord", back_populates="period"
    )


class FinancialRecord(Base):
    __tablename__ = "financial_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("documents.id"), nullable=True
    )
    period_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("financial_periods.id"), nullable=True
    )
    category: Mapped[FinancialCategory] = mapped_column(Enum(FinancialCategory), nullable=False)
    subcategory: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    line_item: Mapped[str] = mapped_column(String(500), nullable=False)
    value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # thousands, millions
    is_calculated: Mapped[bool] = mapped_column(Boolean, default=False)
    formula: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    document: Mapped[Optional["Document"]] = relationship("Document", back_populates="financial_records")
    period: Mapped[Optional["FinancialPeriod"]] = relationship("FinancialPeriod", back_populates="records")
