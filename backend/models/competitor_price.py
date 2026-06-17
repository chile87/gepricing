from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel


class CompetitorPrice(SQLModel, table=True):
    """Competitor price observation (time-series)."""

    id: UUID = Field(default=None, primary_key=True)
    sku_id: UUID = Field(foreign_key="sku.id")
    competitor_source_id: Optional[UUID] = Field(None, foreign_key="competitorsource.id")
    competitor_listing_id: Optional[UUID] = Field(None, foreign_key="competitorlisting.id")
    crawler_run_id: Optional[UUID] = Field(None, foreign_key="crawlerrun.id")
    source: str = Field(max_length=64)
    price: float = Field(ge=0.0)
    original_price: Optional[float] = None
    promo_price: Optional[float] = None
    currency: str = Field(default="USD", max_length=8)
    availability: Optional[str] = Field(None, max_length=32)
    stock_status: Optional[str] = Field(None, max_length=32)
    url: Optional[str] = None
    crawled_at: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CompetitorPriceCreate(SQLModel):
    """CompetitorPrice creation schema."""

    sku_id: UUID
    competitor_source_id: Optional[UUID] = None
    competitor_listing_id: Optional[UUID] = None
    crawler_run_id: Optional[UUID] = None
    source: str
    price: float
    original_price: Optional[float] = None
    promo_price: Optional[float] = None
    currency: str = "USD"
    availability: Optional[str] = None
    stock_status: Optional[str] = None
    url: Optional[str] = None
    crawled_at: Optional[datetime] = None


class CompetitorPriceRead(SQLModel):
    """CompetitorPrice read schema."""

    id: UUID
    sku_id: UUID
    competitor_source_id: Optional[UUID]
    competitor_listing_id: Optional[UUID]
    crawler_run_id: Optional[UUID]
    source: str
    price: float
    original_price: Optional[float]
    promo_price: Optional[float]
    currency: str
    availability: Optional[str]
    stock_status: Optional[str]
    url: Optional[str]
    crawled_at: datetime
    created_at: datetime
