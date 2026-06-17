from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel


class MarketAlert(SQLModel, table=True):
    """Market-driven alert for dashboard visibility."""

    id: UUID = Field(default=None, primary_key=True)
    sku_id: UUID = Field(foreign_key="sku.id")
    competitor_price_id: Optional[UUID] = Field(None, foreign_key="competitorprice.id")
    alert_type: str = Field(max_length=32)  # competitor_drop, competitor_rise, inventory_risk, margin_risk, new_recommendation
    severity: str = Field(max_length=16)  # low, medium, high, critical
    title: str
    message: Optional[str] = None
    is_read: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MarketAlertCreate(SQLModel):
    """MarketAlert creation schema."""

    sku_id: UUID
    competitor_price_id: Optional[UUID] = None
    alert_type: str
    severity: str
    title: str
    message: Optional[str] = None
    is_read: bool = False


class MarketAlertRead(SQLModel):
    """MarketAlert read schema."""

    id: UUID
    sku_id: UUID
    competitor_price_id: Optional[UUID]
    alert_type: str
    severity: str
    title: str
    message: Optional[str]
    is_read: bool
    created_at: datetime
