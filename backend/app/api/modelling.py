"""Modelling engine API endpoints."""
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.model_state import ModelState, Scenario, ModelVariable, ModelStatus
from app.models.financial_data import FinancialRecord, FinancialPeriod
from app.schemas.modelling import (
    ModelStateSchema,
    ModelStateDetail,
    ScenarioSchema,
    ScenarioCreate,
    CommandRequest,
    CommandResult,
    ModelOutput,
    SensitivityInput,
    SensitivityResult,
    ModelVariableCreate,
    ModelVariableSchema,
)
from app.services.nlp_command_parser import parse_command
from app.services.modelling_engine import (
    FinancialModel,
    generate_periods,
    execute_command,
    build_model_from_records,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/models", tags=["modelling"])


# ─── Model state CRUD ─────────────────────────────────────────────────────────

@router.get("", response_model=list[ModelStateSchema])
async def list_models(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ModelState).where(ModelState.status != ModelStatus.ARCHIVED)
        .order_by(ModelState.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=ModelStateSchema, status_code=201)
async def create_model(
    name: str = Body(...),
    description: Optional[str] = Body(None),
    forecast_start: str = Body("FY2024"),
    forecast_end: str = Body("FY2028"),
    forecast_frequency: str = Body("annual"),
    currency: str = Body("USD"),
    unit_scale: str = Body("thousands"),
    db: AsyncSession = Depends(get_db),
):
    model = ModelState(
        name=name,
        description=description,
        forecast_start=forecast_start,
        forecast_end=forecast_end,
        forecast_frequency=forecast_frequency,
        currency=currency,
        unit_scale=unit_scale,
        assumptions={"tax_rate": 20.0, "discount_rate": 10.0},
        command_history=[],
    )
    db.add(model)
    await db.flush()

    # Create base scenario
    base_scenario = Scenario(
        model_state_id=model.id,
        name="Base Case",
        description="Base financial model",
        is_base=True,
        overrides={},
    )
    db.add(base_scenario)
    await db.flush()
    await db.refresh(model)
    return model


@router.get("/{model_id}", response_model=ModelStateDetail)
async def get_model(model_id: int, db: AsyncSession = Depends(get_db)):
    model = await db.get(ModelState, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.delete("/{model_id}", status_code=204)
async def delete_model(model_id: int, db: AsyncSession = Depends(get_db)):
    model = await db.get(ModelState, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    model.status = ModelStatus.ARCHIVED


# ─── Command execution ─────────────────────────────────────────────────────────

@router.post("/command", response_model=CommandResult)
async def execute_nl_command(
    request: CommandRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Parse and execute a natural-language modelling command.
    """
    model_state = await db.get(ModelState, request.model_state_id)
    if not model_state:
        raise HTTPException(status_code=404, detail="Model state not found")

    # Parse command
    parsed = parse_command(request.command)

    # Load financial records
    records_result = await db.execute(
        select(FinancialRecord, FinancialPeriod)
        .join(FinancialPeriod, FinancialRecord.period_id == FinancialPeriod.id, isouter=True)
    )
    raw_records = records_result.all()
    record_dicts = [
        {
            "category": r.category,
            "period_label": p.label if p else None,
            "value": r.value,
            "currency": r.currency,
            "line_item": r.line_item,
        }
        for r, p in raw_records
    ]

    # Build model
    periods = generate_periods(
        model_state.forecast_start or "FY2022",
        model_state.forecast_end or "FY2028",
        model_state.forecast_frequency,
    )
    financial_model = build_model_from_records(
        record_dicts, periods, model_state.currency, model_state.unit_scale
    )

    # Apply scenario overrides if requested
    if request.scenario_id:
        scenario = await db.get(Scenario, request.scenario_id)
        if scenario and scenario.overrides:
            financial_model = financial_model.apply_scenario_overrides(scenario.overrides)

    # Execute command
    try:
        updated_model, operations = execute_command(parsed, financial_model, record_dicts)
    except Exception as e:
        logger.exception(f"Command execution failed: {e}")
        return CommandResult(
            success=False,
            command=request.command,
            interpreted_as=parsed.interpreted_as,
            operations_performed=[],
            updated_variables=[],
            message=f"Execution error: {str(e)}",
            errors=[str(e)],
        )

    # Persist variables back to DB
    updated_keys = await _persist_model_variables(
        db, model_state.id, request.scenario_id, updated_model
    )

    # Update command history
    history = list(model_state.command_history or [])
    history.append({"command": request.command, "interpreted_as": parsed.interpreted_as})
    model_state.command_history = history[-50:]  # keep last 50

    # If there's an active scenario, update computed_data
    if request.scenario_id:
        scenario = await db.get(Scenario, request.scenario_id)
        if scenario:
            scenario.computed_data = updated_model.to_output()
    else:
        # Update base scenario
        base_result = await db.execute(
            select(Scenario).where(
                Scenario.model_state_id == request.model_state_id,
                Scenario.is_base == True,
            )
        )
        base_scenario = base_result.scalar_one_or_none()
        if base_scenario:
            base_scenario.computed_data = updated_model.to_output()

    await db.commit()

    return CommandResult(
        success=True,
        command=request.command,
        interpreted_as=parsed.interpreted_as,
        operations_performed=operations,
        updated_variables=updated_keys,
        message=f"Command executed successfully. {len(operations)} operation(s) performed.",
        model_output=updated_model.to_output(),
    )


async def _persist_model_variables(
    db: AsyncSession,
    model_state_id: int,
    scenario_id: Optional[int],
    financial_model: FinancialModel,
) -> list[str]:
    """Save/update model variables from in-memory model to DB."""
    updated = []
    for key, series in financial_model.data.items():
        # Upsert: find existing or create
        q = select(ModelVariable).where(
            ModelVariable.model_state_id == model_state_id,
            ModelVariable.key == key,
            ModelVariable.scenario_id == scenario_id,
        )
        existing = (await db.execute(q)).scalar_one_or_none()

        if existing:
            existing.values = series
        else:
            mv = ModelVariable(
                model_state_id=model_state_id,
                scenario_id=scenario_id,
                section=_key_to_section(key),
                key=key,
                label=key.replace("_", " ").title(),
                value_type="number",
                values=series,
            )
            db.add(mv)
        updated.append(key)

    return updated


def _key_to_section(key: str) -> str:
    income_keys = {"revenue", "cogs", "gross_profit", "opex", "ebitda", "ebit", "net_income", "interest", "tax"}
    bs_keys = {"cash", "receivables", "inventory", "fixed_assets", "payables", "debt", "equity"}
    cf_keys = {"operating_cf", "investing_cf", "financing_cf", "net_cf", "capex"}
    if key in income_keys:
        return "income_statement"
    if key in bs_keys:
        return "balance_sheet"
    if key in cf_keys:
        return "cashflow"
    return "other"


# ─── Model output ──────────────────────────────────────────────────────────────

@router.get("/{model_id}/output", response_model=ModelOutput)
async def get_model_output(
    model_id: int,
    scenario_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    model_state = await db.get(ModelState, model_id)
    if not model_state:
        raise HTTPException(status_code=404, detail="Model not found")

    # Try to get computed data from scenario
    if scenario_id:
        scenario = await db.get(Scenario, scenario_id)
        if scenario and scenario.computed_data:
            data = scenario.computed_data
            return ModelOutput(
                model_state_id=model_id,
                scenario_id=scenario_id,
                periods=data.get("periods", []),
                income_statement=data.get("income_statement", {}),
                balance_sheet=data.get("balance_sheet", {}),
                cashflow=data.get("cashflow", {}),
                kpis=data.get("kpis", {}),
                assumptions=data.get("assumptions", {}),
                charts=_build_chart_specs(data),
            )

    # Build fresh from records
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
    data = fm.to_output()

    return ModelOutput(
        model_state_id=model_id,
        scenario_id=None,
        periods=data.get("periods", []),
        income_statement=data.get("income_statement", {}),
        balance_sheet=data.get("balance_sheet", {}),
        cashflow=data.get("cashflow", {}),
        kpis=data.get("kpis", {}),
        assumptions=data.get("assumptions", {}),
        charts=_build_chart_specs(data),
    )


def _build_chart_specs(data: dict) -> list[dict]:
    """Generate chart configuration objects for the frontend."""
    charts = []
    periods = data.get("periods", [])
    is_data = data.get("income_statement", {})

    if "revenue" in is_data and periods:
        charts.append({
            "id": "revenue_chart",
            "title": "Revenue",
            "type": "bar",
            "data": [
                {"period": p, "value": is_data["revenue"].get(p)}
                for p in periods
            ],
            "xKey": "period",
            "yKey": "value",
            "color": "#3b82f6",
        })

    if "ebitda" in is_data and periods:
        charts.append({
            "id": "ebitda_chart",
            "title": "EBITDA",
            "type": "bar",
            "data": [
                {"period": p, "value": is_data["ebitda"].get(p)}
                for p in periods
            ],
            "xKey": "period",
            "yKey": "value",
            "color": "#10b981",
        })

    if "gross_margin_pct" in data.get("kpis", {}) or "gross_margin_pct" in is_data:
        margin_data = data.get("kpis", {}).get("gross_margin_pct") or is_data.get("gross_margin_pct", {})
        if margin_data:
            charts.append({
                "id": "margin_chart",
                "title": "Gross Margin %",
                "type": "line",
                "data": [{"period": p, "value": margin_data.get(p)} for p in periods],
                "xKey": "period",
                "yKey": "value",
                "color": "#f59e0b",
            })

    return charts


# ─── Scenarios ────────────────────────────────────────────────────────────────

@router.get("/{model_id}/scenarios", response_model=list[ScenarioSchema])
async def list_scenarios(model_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Scenario).where(Scenario.model_state_id == model_id)
    )
    return result.scalars().all()


@router.post("/{model_id}/scenarios", response_model=ScenarioSchema, status_code=201)
async def create_scenario(
    model_id: int,
    data: ScenarioCreate,
    db: AsyncSession = Depends(get_db),
):
    model_state = await db.get(ModelState, model_id)
    if not model_state:
        raise HTTPException(status_code=404, detail="Model not found")

    scenario = Scenario(model_state_id=model_id, **data.model_dump())
    db.add(scenario)
    await db.flush()
    await db.refresh(scenario)
    return scenario


# ─── Sensitivity ──────────────────────────────────────────────────────────────

@router.post("/sensitivity", response_model=SensitivityResult)
async def run_sensitivity(
    request: SensitivityInput,
    db: AsyncSession = Depends(get_db),
):
    model_state = await db.get(ModelState, request.model_state_id)
    if not model_state:
        raise HTTPException(status_code=404, detail="Model not found")

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

    data_points = fm.sensitivity_analysis(
        request.variable_key,
        request.output_metric,
        request.range_pct / 100,
        request.steps,
    )

    return SensitivityResult(
        variable_key=request.variable_key,
        variable_label=request.variable_key.replace("_", " ").title(),
        output_metric=request.output_metric,
        data_points=data_points,
    )
