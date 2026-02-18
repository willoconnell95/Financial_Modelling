"""
Export API endpoints.
GET /export/excel          - Download model as Excel
GET /export/csv            - Download model as CSV
GET /export/raw-data/csv   - Download raw extracted data as CSV
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.financial_data import FinancialLineItem
from app.services.export_service import ExportService
from app.services.modelling_engine import ModellingEngine

router = APIRouter(prefix="/export", tags=["export"])

export_svc = ExportService()
model_engine = ModellingEngine()


def _get_state(db: Session, scenario: str):
    from app.models.model_state import ModelState
    record = (
        db.query(ModelState)
        .filter(ModelState.scenario == scenario, ModelState.is_active == True)
        .order_by(ModelState.updated_at.desc())
        .first()
    )
    if not record:
        return None
    return {
        "scenario": record.scenario,
        "time_config": record.time_config or {},
        "assumptions": record.assumptions or {},
        "line_items": record.line_items or {},
        "formulas": record.formulas or {},
    }


@router.get("/excel")
def export_excel(scenario: str = "base", db: Session = Depends(get_db)):
    """Download the financial model as an Excel workbook."""
    state = _get_state(db, scenario)
    if not state:
        raise HTTPException(status_code=404, detail=f"No model for scenario '{scenario}'")

    # Get all scenarios for comparison sheet
    from app.models.model_state import ModelState
    all_records = db.query(ModelState).filter(ModelState.is_active == True).all()
    scenarios = []
    for r in all_records:
        scenarios.append({
            "scenario": r.scenario,
            "line_items": r.line_items or {},
        })

    summary = model_engine.get_summary_table(state)
    excel_bytes = export_svc.export_excel(summary, scenarios)

    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="financial_model_{scenario}.xlsx"'
        },
    )


@router.get("/csv")
def export_csv(scenario: str = "base", db: Session = Depends(get_db)):
    """Download the financial model as CSV."""
    state = _get_state(db, scenario)
    if not state:
        raise HTTPException(status_code=404, detail=f"No model for scenario '{scenario}'")

    summary = model_engine.get_summary_table(state)
    csv_bytes = export_svc.export_csv(summary)

    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="financial_model_{scenario}.csv"'
        },
    )


@router.get("/raw-data/csv")
def export_raw_data(db: Session = Depends(get_db)):
    """Download all extracted line items as CSV."""
    items = db.query(FinancialLineItem).all()
    csv_bytes = export_svc.export_raw_data_csv([i.to_dict() for i in items])

    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="extracted_data.csv"'
        },
    )
