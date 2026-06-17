from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel


class SalesMetricsHourly(SQLModel, table=True):
    """Hourly sales metrics for a SKU."""

    id: UUID = Field(default=None, primary_key=True)
    sku_id: UUID = Field(foreign_key="sku.id")
    period_start: datetime
    units_sold: int = Field(default=0, ge=0)
    revenue: float = Field(default=0.0, ge=0.0)
    margin_value: float = Field(default=0.0, ge=0.0)
    promo_spend: float = Field(default=0.0, ge=0.0)
    conversion_rate: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SalesMetricsHourlyCreate(SQLModel):
    """SalesMetricsHourly creation schema."""

    sku_id: UUID
    period_start: datetime
    units_sold: int = 0
    revenue: float = 0.0
    margin_value: float = 0.0
    promo_spend: float = 0.0
    conversion_rate: Optional[float] = None


class SalesMetricsHourlyRead(SQLModel):
    """SalesMetricsHourly read schema."""

    id: UUID
    sku_id: UUID
    period_start: datetime
    units_sold: int
    revenue: float
    margin_value: float
    promo_spend: float
    conversion_rate: Optional[float]
    created_at: datetime
