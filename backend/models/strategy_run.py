from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlmodel import Field, SQLModel


class StrategyRun(SQLModel, table=True):
    """Execution of a pricing strategy."""

    id: UUID = Field(default=None, primary_key=True)
    strategy_id: Optional[UUID] = Field(None, foreign_key="strategy.id")
    triggered_by: str = Field(max_length=64)
    status: str = Field(max_length=32)  # queued, running, completed, failed, cancelled
    run_started_at: datetime = Field(default_factory=datetime.utcnow)
    run_finished_at: Optional[datetime] = None
    input_snapshot: Dict[str, Any] = Field(default_factory=dict, sa_type="JSONB")
    output_summary: Dict[str, Any] = Field(default_factory=dict, sa_type="JSONB")


class StrategyRunCreate(SQLModel):
    """StrategyRun creation schema."""

    strategy_id: Optional[UUID] = None
    triggered_by: str
    status: str
    input_snapshot: Dict[str, Any] = {}
    output_summary: Dict[str, Any] = {}


class StrategyRunRead(SQLModel):
    """StrategyRun read schema."""

    id: UUID
    strategy_id: Optional[UUID]
    triggered_by: str
    status: str
    run_started_at: datetime
    run_finished_at: Optional[datetime]
    input_snapshot: Dict[str, Any]
    output_summary: Dict[str, Any]


class StrategyRunUpdate(SQLModel):
    """StrategyRun update schema."""

    status: Optional[str] = None
    run_finished_at: Optional[datetime] = None
    output_summary: Optional[Dict[str, Any]] = None
