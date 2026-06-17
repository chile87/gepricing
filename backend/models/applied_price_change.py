from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel


class AppliedPriceChange(SQLModel, table=True):
    """Applied price change (audit trail)."""

    id: UUID = Field(default=None, primary_key=True)
    recommendation_id: UUID = Field(foreign_key="pricerecommendation.id")
    sku_id: UUID = Field(foreign_key="sku.id")
    old_price: float = Field(ge=0.0)
    new_price: float = Field(ge=0.0)
    applied_by: Optional[str] = Field(None, max_length=128)
    applied_at: datetime = Field(default_factory=datetime.utcnow)
    change_reason: Optional[str] = None


class AppliedPriceChangeCreate(SQLModel):
    """AppliedPriceChange creation schema."""

    recommendation_id: UUID
    sku_id: UUID
    old_price: float
    new_price: float
    applied_by: Optional[str] = None
    change_reason: Optional[str] = None


class AppliedPriceChangeRead(SQLModel):
    """AppliedPriceChange read schema."""

    id: UUID
    recommendation_id: UUID
    sku_id: UUID
    old_price: float
    new_price: float
    applied_by: Optional[str]
    applied_at: datetime
    change_reason: Optional[str]
