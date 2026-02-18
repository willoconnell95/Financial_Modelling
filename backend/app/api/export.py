"""Export endpoints - generate Excel and CSV downloads."""
import io
import csv
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.model_state import ModelState, Scenario
from app.models.financial_data import FinancialRecord, FinancialPeriod
from app.services.modelling_engine import generate_periods, build_model_from_records

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/export", tags=["export"])


@router.get("/excel/{model_id}")
async def export_excel(
    model_id: int,
    scenario_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Export model output as an Excel workbook with multiple sheets."""
    data = await _get_model_data(model_id, scenario_id, db)

    try:
        import xlsxwriter

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})

        # Formats
        header_fmt = workbook.add_format({"bold": True, "bg_color": "#1e3a5f", "font_color": "white", "border": 1})
        number_fmt = workbook.add_format({"num_format": "#,##0.0", "border": 1})
        pct_fmt = workbook.add_format({"num_format": "0.0%", "border": 1})
        label_fmt = workbook.add_format({"bold": False, "border": 1})
        section_fmt = workbook.add_format({"bold": True, "bg_color": "#dbeafe", "border": 1})

        periods = data.get("periods", [])

        sheets_config = [
            ("P&L", data.get("income_statement", {})),
            ("Balance Sheet", data.get("balance_sheet", {})),
            ("Cash Flow", data.get("cashflow", {})),
            ("KPIs", data.get("kpis", {})),
        ]

        for sheet_name, section_data in sheets_config:
            if not section_data:
                continue
            ws = workbook.add_worksheet(sheet_name)
            ws.set_column(0, 0, 30)
            ws.set_column(1, len(periods) + 1, 15)

            # Header row
            ws.write(0, 0, "Line Item", header_fmt)
            for col_idx, period in enumerate(periods):
                ws.write(0, col_idx + 1, period, header_fmt)

            # Data rows
            for row_idx, (key, series) in enumerate(section_data.items(), start=1):
                label = key.replace("_", " ").title()
                ws.write(row_idx, 0, label, label_fmt)
                for col_idx, period in enumerate(periods):
                    val = series.get(period)
                    if val is not None:
                        ws.write(row_idx, col_idx + 1, val, number_fmt)
                    else:
                        ws.write(row_idx, col_idx + 1, "-", label_fmt)

        # Assumptions sheet
        assumptions = data.get("assumptions", {})
        if assumptions:
            ws = workbook.add_worksheet("Assumptions")
            ws.set_column(0, 0, 30)
            ws.set_column(1, 1, 20)
            ws.write(0, 0, "Assumption", header_fmt)
            ws.write(0, 1, "Value", header_fmt)
            for row_idx, (k, v) in enumerate(assumptions.items(), start=1):
                ws.write(row_idx, 0, k.replace("_", " ").title(), label_fmt)
                ws.write(row_idx, 1, v, number_fmt)

        workbook.close()
        output.seek(0)

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=financial_model_{model_id}.xlsx"},
        )

    except ImportError:
        raise HTTPException(status_code=500, detail="xlsxwriter not installed")
    except Exception as e:
        logger.exception(f"Excel export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/csv/{model_id}")
async def export_csv(
    model_id: int,
    section: str = Query("income_statement", description="income_statement|balance_sheet|cashflow|kpis"),
    scenario_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Export a single section as CSV."""
    data = await _get_model_data(model_id, scenario_id, db)
    periods = data.get("periods", [])
    section_data = data.get(section, {})

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(["Line Item"] + periods)

    # Rows
    for key, series in section_data.items():
        label = key.replace("_", " ").title()
        row = [label] + [series.get(p, "") for p in periods]
        writer.writerow(row)

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={section}_{model_id}.csv"},
    )


async def _get_model_data(
    model_id: int,
    scenario_id: Optional[int],
    db: AsyncSession,
) -> dict:
    model_state = await db.get(ModelState, model_id)
    if not model_state:
        raise HTTPException(status_code=404, detail="Model not found")

    if scenario_id:
        scenario = await db.get(Scenario, scenario_id)
        if scenario and scenario.computed_data:
            return scenario.computed_data

    # Build from DB records
    records_result = await db.execute(
        select(FinancialRecord, FinancialPeriod)
        .join(FinancialPeriod, FinancialRecord.period_id == FinancialPeriod.id, isouter=True)
    )
    raw = records_result.all()
    record_dicts = [
        {"category": r.category, "period_label": p.label if p else None, "value": r.value, "line_item": r.line_item}
        for r, p in raw
    ]

    periods = generate_periods(
        model_state.forecast_start or "FY2022",
        model_state.forecast_end or "FY2028",
        model_state.forecast_frequency,
    )
    fm = build_model_from_records(record_dicts, periods, model_state.currency, model_state.unit_scale)
    return fm.to_output()
