from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel


class CompetitorListing(SQLModel, table=True):
    """Competitor product listing."""

    id: UUID = Field(default=None, primary_key=True)
    sku_id: UUID = Field(foreign_key="sku.id")
    competitor_source_id: UUID = Field(foreign_key="competitorsource.id")
    competitor_sku: Optional[str] = Field(None, max_length=128)
    competitor_product_name: Optional[str] = None
    product_url: str
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CompetitorListingCreate(SQLModel):
    """CompetitorListing creation schema."""

    sku_id: UUID
    competitor_source_id: UUID
    competitor_sku: Optional[str] = None
    competitor_product_name: Optional[str] = None
    product_url: str
    is_active: bool = True


class CompetitorListingRead(SQLModel):
    """CompetitorListing read schema."""

    id: UUID
    sku_id: UUID
    competitor_source_id: UUID
    competitor_sku: Optional[str]
    competitor_product_name: Optional[str]
    product_url: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
