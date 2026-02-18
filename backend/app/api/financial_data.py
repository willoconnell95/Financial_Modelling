"""Financial data query endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.financial_data import FinancialRecord, FinancialPeriod
from app.schemas.financial_data import (
    FinancialRecordSchema,
    FinancialPeriodSchema,
    FinancialSummary,
    FinancialRecordCreate,
)

router = APIRouter(prefix="/financial-data", tags=["financial-data"])


@router.get("/records", response_model=list[FinancialRecordSchema])
async def list_financial_records(
    document_id: Optional[int] = None,
    category: Optional[str] = None,
    period_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
):
    q = select(FinancialRecord)
    if document_id:
        q = q.where(FinancialRecord.document_id == document_id)
    if category:
        q = q.where(FinancialRecord.category == category)
    if period_id:
        q = q.where(FinancialRecord.period_id == period_id)
    q = q.offset(skip).limit(limit).order_by(FinancialRecord.created_at.desc())
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/records", response_model=FinancialRecordSchema, status_code=201)
async def create_financial_record(
    data: FinancialRecordCreate,
    db: AsyncSession = Depends(get_db),
):
    record = FinancialRecord(**data.model_dump())
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record


@router.get("/periods", response_model=list[FinancialPeriodSchema])
async def list_periods(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FinancialPeriod).order_by(FinancialPeriod.start_date))
    return result.scalars().all()


@router.get("/summary", response_model=FinancialSummary)
async def get_financial_summary(
    document_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Return a pivoted summary: {periods, income_statement, balance_sheet, cashflow, kpis}
    """
    q = select(FinancialRecord, FinancialPeriod).join(
        FinancialPeriod, FinancialRecord.period_id == FinancialPeriod.id, isouter=True
    )
    if document_id:
        q = q.where(FinancialRecord.document_id == document_id)

    result = await db.execute(q)
    rows = result.all()

    # Build pivot: category -> {period_label -> value}
    pivot: dict[str, dict[str, Optional[float]]] = {}
    periods_seen: set[str] = set()

    for record, period in rows:
        period_label = period.label if period else "Unknown"
        cat = record.category
        if cat not in pivot:
            pivot[cat] = {}
        pivot[cat][period_label] = record.value
        periods_seen.add(period_label)

    sorted_periods = sorted(periods_seen)

    # Ensure all categories have all periods
    for cat in pivot:
        for p in sorted_periods:
            pivot[cat].setdefault(p, None)

    is_categories = ["revenue", "cogs", "gross_profit", "opex", "ebitda", "ebit",
                     "interest", "tax", "net_income"]
    bs_categories = ["cash", "receivables", "inventory", "fixed_assets", "total_assets",
                     "payables", "debt", "equity", "total_liabilities"]
    cf_categories = ["operating_cf", "investing_cf", "financing_cf", "net_cf", "capex"]
    kpi_categories = ["headcount", "arr", "mrr", "churn_rate", "cac", "ltv"]

    return FinancialSummary(
        periods=sorted_periods,
        income_statement={k: pivot[k] for k in is_categories if k in pivot},
        balance_sheet={k: pivot[k] for k in bs_categories if k in pivot},
        cashflow={k: pivot[k] for k in cf_categories if k in pivot},
        kpis={k: pivot[k] for k in kpi_categories if k in pivot},
    )
