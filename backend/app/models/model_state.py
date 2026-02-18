from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Float, DateTime, Text, JSON, ForeignKey, Boolean, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


class ModelStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class ModelState(Base):
    __tablename__ = "model_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False, default="Base Model")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[ModelStatus] = mapped_column(Enum(ModelStatus), default=ModelStatus.ACTIVE)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    unit_scale: Mapped[str] = mapped_column(String(20), default="thousands")
    forecast_start: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    forecast_end: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    forecast_frequency: Mapped[str] = mapped_column(String(20), default="annual")
    assumptions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    command_history: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    scenarios: Mapped[list["Scenario"]] = relationship(
        "Scenario", back_populates="model_state", cascade="all, delete-orphan"
    )
    variables: Mapped[list["ModelVariable"]] = relationship(
        "ModelVariable", back_populates="model_state", cascade="all, delete-orphan"
    )


class Scenario(Base):
    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    model_state_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("model_states.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_base: Mapped[bool] = mapped_column(Boolean, default=False)
    overrides: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # Full computed output for this scenario
    computed_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    model_state: Mapped["ModelState"] = relationship("ModelState", back_populates="scenarios")


class ModelVariable(Base):
    __tablename__ = "model_variables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    model_state_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("model_states.id"), nullable=False
    )
    scenario_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("scenarios.id"), nullable=True
    )
    section: Mapped[str] = mapped_column(String(100), nullable=False)  # revenue, costs, headcount, etc.
    key: Mapped[str] = mapped_column(String(200), nullable=False)
    label: Mapped[str] = mapped_column(String(500), nullable=False)
    value_type: Mapped[str] = mapped_column(String(50), default="number")  # number, percent, text, formula
    # Time-series values: {period_label: value}
    values: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    formula: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_assumption: Mapped[bool] = mapped_column(Boolean, default=False)
    is_driver: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    model_state: Mapped["ModelState"] = relationship("ModelState", back_populates="variables")
