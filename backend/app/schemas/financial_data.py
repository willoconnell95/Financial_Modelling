from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, ConfigDict


class FinancialPeriodSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    period_type: str
    start_date: Optional[date]
    end_date: Optional[date]
    is_forecast: bool
    created_at: datetime


class FinancialPeriodCreate(BaseModel):
    label: str
    period_type: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_forecast: bool = False


class FinancialRecordSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: Optional[int]
    period_id: Optional[int]
    category: str
    subcategory: Optional[str]
    line_item: str
    value: Optional[float]
    currency: str
    unit: Optional[str]
    is_calculated: bool
    formula: Optional[str]
    confidence: Optional[float]
    source_text: Optional[str]
    tags: Optional[list]
    created_at: datetime
    updated_at: datetime


class FinancialRecordCreate(BaseModel):
    document_id: Optional[int] = None
    period_id: Optional[int] = None
    category: str
    subcategory: Optional[str] = None
    line_item: str
    value: Optional[float] = None
    currency: str = "USD"
    unit: Optional[str] = None
    formula: Optional[str] = None
    tags: Optional[list] = None


class FinancialSummary(BaseModel):
    periods: list[str]
    income_statement: dict[str, dict[str, Optional[float]]]
    balance_sheet: dict[str, dict[str, Optional[float]]]
    cashflow: dict[str, dict[str, Optional[float]]]
    kpis: dict[str, dict[str, Optional[float]]]
