from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlmodel import Field, SQLModel


class PriceRecommendation(SQLModel, table=True):
    """Price recommendation from the pricing engine."""

    id: UUID = Field(default=None, primary_key=True)
    strategy_run_id: Optional[UUID] = Field(None, foreign_key="strategyrun.id")
    strategy_id: Optional[UUID] = Field(None, foreign_key="strategy.id")
    sku_id: UUID = Field(foreign_key="sku.id")
    recommendation_type: str = Field(max_length=32)  # raise, lower, promo, stop, hold
    current_price: float = Field(ge=0.0)
    recommended_price: float = Field(ge=0.0)
    margin_pct: Optional[float] = None
    expected_revenue_impact: Optional[float] = None
    expected_margin_impact: Optional[float] = None
    expected_inventory_impact: Optional[float] = None
    confidence_score: Optional[float] = None
    confidence_label: Optional[str] = Field(None, max_length=16)  # Low, Medium, High
    rule_details: Dict[str, Any] = Field(default_factory=dict, sa_type="JSONB")
    rationale: Dict[str, Any] = Field(default_factory=dict, sa_type="JSONB")
    status: str = Field(default="pending", max_length=32)  # pending, approved, rejected, applied, expired
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PriceRecommendationCreate(SQLModel):
    """PriceRecommendation creation schema."""

    strategy_run_id: Optional[UUID] = None
    strategy_id: Optional[UUID] = None
    sku_id: UUID
    recommendation_type: str
    current_price: float
    recommended_price: float
    margin_pct: Optional[float] = None
    expected_revenue_impact: Optional[float] = None
    expected_margin_impact: Optional[float] = None
    expected_inventory_impact: Optional[float] = None
    confidence_score: Optional[float] = None
    confidence_label: Optional[str] = None
    rule_details: Dict[str, Any] = {}
    rationale: Dict[str, Any] = {}
    status: str = "pending"


class PriceRecommendationRead(SQLModel):
    """PriceRecommendation read schema."""

    id: UUID
    strategy_run_id: Optional[UUID]
    strategy_id: Optional[UUID]
    sku_id: UUID
    recommendation_type: str
    current_price: float
    recommended_price: float
    margin_pct: Optional[float]
    expected_revenue_impact: Optional[float]
    expected_margin_impact: Optional[float]
    expected_inventory_impact: Optional[float]
    confidence_score: Optional[float]
    confidence_label: Optional[str]
    rule_details: Dict[str, Any]
    rationale: Dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime


class PriceRecommendationUpdate(SQLModel):
    """PriceRecommendation update schema."""

    recommendation_type: Optional[str] = None
    recommended_price: Optional[float] = None
    confidence_score: Optional[float] = None
    confidence_label: Optional[str] = None
    status: Optional[str] = None
    rationale: Optional[Dict[str, Any]] = None
