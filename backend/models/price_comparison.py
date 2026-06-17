from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel


class PriceComparison(SQLModel, table=True):
    """Materialized competitor comparison snapshot per SKU."""

    __tablename__ = "price_comparisons"

    id: UUID = Field(default=None, primary_key=True)
    sku_id: UUID = Field(foreign_key="skus.id")
    competitor_count: int = Field(default=0, ge=0)
    lowest_competitor_price: Optional[float] = Field(default=None, ge=0.0)
    average_competitor_price: Optional[float] = Field(default=None, ge=0.0)
    highest_competitor_price: Optional[float] = Field(default=None, ge=0.0)
    price_gap_value: Optional[float] = None
    price_gap_pct: Optional[float] = None
    lowest_competitor_source: Optional[str] = Field(default=None, max_length=64)
    snapshot_at: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PriceComparisonCreate(SQLModel):
    """PriceComparison creation schema."""

    sku_id: UUID
    competitor_count: int = 0
    lowest_competitor_price: Optional[float] = None
    average_competitor_price: Optional[float] = None
    highest_competitor_price: Optional[float] = None
    price_gap_value: Optional[float] = None
    price_gap_pct: Optional[float] = None
    lowest_competitor_source: Optional[str] = None
    snapshot_at: Optional[datetime] = None


class PriceComparisonRead(SQLModel):
    """PriceComparison read schema."""

    id: UUID
    sku_id: UUID
    competitor_count: int
    lowest_competitor_price: Optional[float]
    average_competitor_price: Optional[float]
    highest_competitor_price: Optional[float]
    price_gap_value: Optional[float]
    price_gap_pct: Optional[float]
    lowest_competitor_source: Optional[str]
    snapshot_at: datetime
    created_at: datetime
    updated_at: datetime
