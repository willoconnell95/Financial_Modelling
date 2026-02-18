"""
Modelling API endpoints.
POST /modelling/init          - Initialise model from extracted data
GET  /modelling/state         - Get current model state
GET  /modelling/summary       - Get formatted summary table
GET  /modelling/chart-data    - Get chart-ready data
POST /modelling/command       - Execute a natural-language command
GET  /modelling/scenarios     - List all scenarios
POST /modelling/scenarios     - Create a new scenario
PUT  /modelling/scenarios/{name}/activate
GET  /modelling/commands      - Command history
POST /modelling/sensitivity   - Run sensitivity analysis
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.financial_data import FinancialLineItem
from app.models.model_state import CommandHistory, ModelState
from app.services.modelling_engine import ModellingEngine
from app.services.nlp_command_parser import NLPCommandParser

router = APIRouter(prefix="/modelling", tags=["modelling"])

engine = ModellingEngine()
nlp_parser = NLPCommandParser()


# ── Pydantic schemas ────────────────────────────────────────────────────────


class InitModelRequest(BaseModel):
    period_type: str = "annual"   # monthly | quarterly | annual
    forecast_periods: int = 3
    scenario: str = "base"
    document_ids: Optional[List[int]] = None   # filter by document


class CommandRequest(BaseModel):
    command: str
    scenario: str = "base"


class ScenarioCreateRequest(BaseModel):
    name: str
    base_scenario: str = "base"
    description: Optional[str] = None


class SensitivityRequest(BaseModel):
    variable: str
    output_metric: str
    range_pct: float = 0.2
    steps: int = 5
    scenario: str = "base"


# ── Helpers ────────────────────────────────────────────────────────────────


def _get_model_state(db: Session, scenario: str = "base") -> Optional[dict]:
    record = (
        db.query(ModelState)
        .filter(ModelState.scenario == scenario, ModelState.is_active == True)
        .order_by(ModelState.updated_at.desc())
        .first()
    )
    if not record:
        return None
    return {
        "id": record.id,
        "name": record.name,
        "scenario": record.scenario,
        "time_config": record.time_config or {},
        "assumptions": record.assumptions or {},
        "line_items": record.line_items or {},
        "formulas": record.formulas or {},
    }


def _save_model_state(db: Session, state: dict) -> ModelState:
    existing = (
        db.query(ModelState)
        .filter(ModelState.scenario == state["scenario"], ModelState.is_active == True)
        .first()
    )
    if existing:
        existing.time_config = state.get("time_config")
        existing.assumptions = state.get("assumptions")
        existing.line_items = state.get("line_items")
        existing.formulas = state.get("formulas")
        db.commit()
        db.refresh(existing)
        return existing
    else:
        record = ModelState(
            name=state.get("name", "Base Model"),
            scenario=state.get("scenario", "base"),
            time_config=state.get("time_config"),
            assumptions=state.get("assumptions"),
            line_items=state.get("line_items"),
            formulas=state.get("formulas"),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record


# ── Endpoints ──────────────────────────────────────────────────────────────


@router.post("/init")
def init_model(req: InitModelRequest, db: Session = Depends(get_db)):
    """
    Initialise (or reinitialise) a model from extracted financial data.
    """
    query = db.query(FinancialLineItem)
    if req.document_ids:
        query = query.filter(FinancialLineItem.document_id.in_(req.document_ids))
    line_items = [i.to_dict() for i in query.all()]

    if not line_items:
        raise HTTPException(
            status_code=400,
            detail="No extracted data available. Upload and process documents first."
        )

    state = engine.build_from_extracted(
        line_items,
        period_type=req.period_type,
        forecast_periods=req.forecast_periods,
    )
    state["scenario"] = req.scenario

    record = _save_model_state(db, state)
    return {
        "status": "initialised",
        "model_id": record.id,
        "scenario": record.scenario,
        "periods": state["time_config"].get("all_periods", []),
        "line_items_loaded": len(line_items),
    }


@router.get("/state")
def get_model_state(scenario: str = "base", db: Session = Depends(get_db)):
    """Return the raw model state for a scenario."""
    state = _get_model_state(db, scenario)
    if not state:
        raise HTTPException(status_code=404, detail=f"No model found for scenario '{scenario}'")
    return state


@router.get("/summary")
def get_model_summary(scenario: str = "base", db: Session = Depends(get_db)):
    """Return formatted summary table for the frontend."""
    state = _get_model_state(db, scenario)
    if not state:
        raise HTTPException(status_code=404, detail=f"No model for scenario '{scenario}'")
    summary = engine.get_summary_table(state)
    return summary


@router.get("/chart-data")
def get_chart_data(
    metrics: str = "revenue,ebitda,net_income",
    scenario: str = "base",
    db: Session = Depends(get_db),
):
    """Return chart-ready time-series data."""
    state = _get_model_state(db, scenario)
    if not state:
        raise HTTPException(status_code=404, detail=f"No model for scenario '{scenario}'")
    metric_list = [m.strip() for m in metrics.split(",") if m.strip()]
    data = engine.get_chart_data(state, metric_list)
    return {"chart_data": data, "metrics": metric_list}


@router.post("/command")
def execute_command(req: CommandRequest, db: Session = Depends(get_db)):
    """
    Execute a natural-language modelling command.
    Updates the model state and logs to command history.
    """
    state = _get_model_state(db, req.scenario)
    if not state:
        raise HTTPException(
            status_code=400,
            detail=f"Model not initialised for scenario '{req.scenario}'. Call /modelling/init first."
        )

    # Parse command
    parsed = nlp_parser.parse(req.command)

    if parsed.operation == "unknown":
        # Log failed command
        history = CommandHistory(
            command=req.command,
            parsed_intent={"operation": "unknown"},
            result_summary=parsed.explanation,
            status="failed",
            scenario=req.scenario,
        )
        db.add(history)
        db.commit()
        return {
            "status": "failed",
            "explanation": parsed.explanation,
            "suggestion": "Try commands like: 'Model revenue using 15% CAGR', 'Set gross margin to 65%', 'Build monthly cashflow for 36 months'",
        }

    # Handle scenario creation specially
    if parsed.operation == "add_scenario":
        scenario_name = parsed.params.get("scenario_name", "custom")
        base_state = _get_model_state(db, req.scenario)
        new_state = engine.create_scenario(base_state, scenario_name)

        # Apply modifications
        modifications = parsed.params.get("modifications", [])
        for mod in modifications:
            from app.services.modelling_engine import ModelOperation
            op = ModelOperation(operation=mod["operation"], params=mod["params"])
            new_state = engine.apply_operation(new_state, op)

        _save_model_state(db, new_state)

        history = CommandHistory(
            command=req.command,
            parsed_intent={"operation": parsed.operation, "params": parsed.params},
            result_summary=f"Created scenario '{scenario_name}'",
            status="success",
            scenario=scenario_name,
        )
        db.add(history)
        db.commit()

        return {
            "status": "success",
            "operation": parsed.operation,
            "explanation": parsed.explanation,
            "scenario_created": scenario_name,
        }

    # Handle sensitivity analysis
    if parsed.operation == "sensitivity_analysis":
        results = engine.sensitivity_analysis(
            state,
            variable=parsed.params.get("variable", "revenue_growth_rate"),
            output_metric=parsed.params.get("output_metric", "ebitda"),
            range_pct=parsed.params.get("range_pct", 0.2),
            steps=parsed.params.get("steps", 5),
        )
        history = CommandHistory(
            command=req.command,
            parsed_intent={"operation": parsed.operation, "params": parsed.params},
            result_summary=f"Sensitivity analysis: {len(results)} data points",
            status="success",
            scenario=req.scenario,
        )
        db.add(history)
        db.commit()
        return {
            "status": "success",
            "operation": "sensitivity_analysis",
            "explanation": parsed.explanation,
            "results": results,
        }

    # Apply operation to model
    try:
        from app.services.modelling_engine import ModelOperation
        op = ModelOperation(operation=parsed.operation, params=parsed.params)
        updated_state = engine.apply_operation(state, op)
        updated_state["scenario"] = req.scenario

        record = _save_model_state(db, updated_state)
        summary = engine.get_summary_table(updated_state)

        history = CommandHistory(
            command=req.command,
            parsed_intent={"operation": parsed.operation, "params": parsed.params},
            result_summary=parsed.explanation,
            status="success",
            model_state_id=record.id,
            scenario=req.scenario,
        )
        db.add(history)
        db.commit()

        return {
            "status": "success",
            "operation": parsed.operation,
            "explanation": parsed.explanation,
            "model_id": record.id,
            "summary": summary,
        }
    except Exception as e:
        history = CommandHistory(
            command=req.command,
            parsed_intent={"operation": parsed.operation, "params": parsed.params},
            result_summary=str(e),
            status="failed",
            scenario=req.scenario,
        )
        db.add(history)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Operation failed: {e}")


@router.get("/scenarios")
def list_scenarios(db: Session = Depends(get_db)):
    """List all available scenarios."""
    records = db.query(ModelState).filter(ModelState.is_active == True).all()
    return {
        "scenarios": [
            {
                "id": r.id,
                "name": r.name,
                "scenario": r.scenario,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in records
        ]
    }


@router.post("/scenarios")
def create_scenario(req: ScenarioCreateRequest, db: Session = Depends(get_db)):
    """Clone an existing scenario into a new named one."""
    base_state = _get_model_state(db, req.base_scenario)
    if not base_state:
        raise HTTPException(status_code=404, detail=f"Base scenario '{req.base_scenario}' not found")

    new_state = engine.create_scenario(base_state, req.name)
    new_state["name"] = req.description or req.name
    record = _save_model_state(db, new_state)

    return {
        "created": req.name,
        "model_id": record.id,
        "based_on": req.base_scenario,
    }


@router.put("/scenarios/{scenario_name}/activate")
def activate_scenario(scenario_name: str, db: Session = Depends(get_db)):
    """Set a scenario as the active one (for display purposes)."""
    record = (
        db.query(ModelState)
        .filter(ModelState.scenario == scenario_name)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_name}' not found")
    return {"active": scenario_name}


@router.get("/commands")
def list_commands(limit: int = 50, db: Session = Depends(get_db)):
    """Return command history."""
    commands = (
        db.query(CommandHistory)
        .order_by(CommandHistory.created_at.desc())
        .limit(limit)
        .all()
    )
    return {"commands": [c.to_dict() for c in commands]}


@router.post("/sensitivity")
def run_sensitivity(req: SensitivityRequest, db: Session = Depends(get_db)):
    """Run a sensitivity analysis."""
    state = _get_model_state(db, req.scenario)
    if not state:
        raise HTTPException(status_code=404, detail=f"No model for scenario '{req.scenario}'")

    results = engine.sensitivity_analysis(
        state,
        variable=req.variable,
        output_metric=req.output_metric,
        range_pct=req.range_pct,
        steps=req.steps,
    )
    return {"results": results, "variable": req.variable, "output_metric": req.output_metric}
