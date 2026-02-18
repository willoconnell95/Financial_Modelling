from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean, Text
from app.database import Base
from datetime import datetime


class ModelState(Base):
    """
    Persisted financial model state.
    Stores all assumptions, periods, line items, and formulas for a scenario.
    """
    __tablename__ = "model_states"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default="Base Model")
    scenario = Column(String, default="base", index=True)  # base | upside | downside | custom_*

    # Model configuration
    time_config = Column(JSON, nullable=True)
    # {
    #   "period_type": "monthly" | "quarterly" | "annual",
    #   "start_period": "2024-01",
    #   "end_period": "2026-12",
    #   "forecast_start": "2025-01",
    #   "periods": ["2024-01", "2024-02", ...]
    # }

    assumptions = Column(JSON, nullable=True)
    # {
    #   "revenue_growth_rate": 0.15,
    #   "gross_margin": 0.65,
    #   "opex_growth_rate": 0.10,
    #   "staff_cost_increase": 0.15,
    #   "churn_rate": 0.05,
    #   ...
    # }

    line_items = Column(JSON, nullable=True)
    # {
    #   "revenue": {"2024-01": 100000, "2024-02": 105000, ...},
    #   "cogs": {"2024-01": 35000, ...},
    #   ...
    # }

    formulas = Column(JSON, nullable=True)
    # {
    #   "gross_profit": "revenue - cogs",
    #   "ebitda": "gross_profit - operating_expenses",
    #   ...
    # }

    metadata_ = Column("metadata", JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    parent_scenario_id = Column(Integer, nullable=True)   # for scenario branching
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "scenario": self.scenario,
            "time_config": self.time_config,
            "assumptions": self.assumptions,
            "line_items": self.line_items,
            "formulas": self.formulas,
            "is_active": self.is_active,
            "parent_scenario_id": self.parent_scenario_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class CommandHistory(Base):
    """Log of all natural-language commands issued by the user."""
    __tablename__ = "command_history"

    id = Column(Integer, primary_key=True, index=True)
    command = Column(Text, nullable=False)
    parsed_intent = Column(JSON, nullable=True)   # structured interpretation
    result_summary = Column(Text, nullable=True)
    status = Column(String, default="success")    # success | failed | partial
    model_state_id = Column(Integer, nullable=True)
    scenario = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "command": self.command,
            "parsed_intent": self.parsed_intent,
            "result_summary": self.result_summary,
            "status": self.status,
            "model_state_id": self.model_state_id,
            "scenario": self.scenario,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
