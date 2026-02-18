from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict


class ModelVariableSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model_state_id: int
    scenario_id: Optional[int]
    section: str
    key: str
    label: str
    value_type: str
    values: Optional[dict]
    formula: Optional[str]
    unit: Optional[str]
    is_assumption: bool
    is_driver: bool
    sort_order: int
    created_at: datetime


class ModelVariableCreate(BaseModel):
    section: str
    key: str
    label: str
    value_type: str = "number"
    values: Optional[dict] = None
    formula: Optional[str] = None
    unit: Optional[str] = None
    is_assumption: bool = False
    is_driver: bool = False
    sort_order: int = 0


class ScenarioSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model_state_id: int
    name: str
    description: Optional[str]
    is_base: bool
    overrides: Optional[dict]
    computed_data: Optional[dict]
    created_at: datetime
    updated_at: datetime


class ScenarioCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_base: bool = False
    overrides: Optional[dict] = None


class ModelStateSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str]
    status: str
    currency: str
    unit_scale: str
    forecast_start: Optional[str]
    forecast_end: Optional[str]
    forecast_frequency: str
    assumptions: Optional[dict]
    command_history: Optional[list]
    created_at: datetime
    updated_at: datetime


class ModelStateDetail(ModelStateSchema):
    scenarios: list[ScenarioSchema] = []
    variables: list[ModelVariableSchema] = []


class CommandRequest(BaseModel):
    command: str
    model_state_id: int
    scenario_id: Optional[int] = None


class CommandResult(BaseModel):
    success: bool
    command: str
    interpreted_as: str
    operations_performed: list[str]
    updated_variables: list[str]
    message: str
    model_output: Optional[dict] = None
    errors: list[str] = []


class ModelOutput(BaseModel):
    model_state_id: int
    scenario_id: Optional[int]
    periods: list[str]
    income_statement: dict[str, Any]
    balance_sheet: dict[str, Any]
    cashflow: dict[str, Any]
    kpis: dict[str, Any]
    assumptions: dict[str, Any]
    charts: list[dict]


class SensitivityInput(BaseModel):
    model_state_id: int
    scenario_id: Optional[int] = None
    variable_key: str
    range_pct: float = 20.0  # ±20% by default
    steps: int = 5
    output_metric: str = "net_income"


class SensitivityResult(BaseModel):
    variable_key: str
    variable_label: str
    output_metric: str
    data_points: list[dict]  # [{input_value, output_value, pct_change_input, pct_change_output}]
