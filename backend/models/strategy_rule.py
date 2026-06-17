from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlmodel import Field, SQLModel


class StrategyRule(SQLModel, table=True):
    """Rule within a strategy."""

    id: UUID = Field(default=None, primary_key=True)
    strategy_id: UUID = Field(foreign_key="strategy.id")
    rule_type: str = Field(max_length=64)
    rule_name: str = Field(max_length=128)
    priority: int = Field(default=100)
    config: Dict[str, Any] = Field(default_factory=dict, sa_type="JSONB")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class StrategyRuleCreate(SQLModel):
    """StrategyRule creation schema."""

    strategy_id: UUID
    rule_type: str
    rule_name: str
    priority: int = 100
    config: Dict[str, Any] = {}
    is_active: bool = True


class StrategyRuleRead(SQLModel):
    """StrategyRule read schema."""

    id: UUID
    strategy_id: UUID
    rule_type: str
    rule_name: str
    priority: int
    config: Dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class StrategyRuleUpdate(SQLModel):
    """StrategyRule update schema."""

    rule_type: Optional[str] = None
    rule_name: Optional[str] = None
    priority: Optional[int] = None
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
