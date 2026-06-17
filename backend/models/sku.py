from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel


class SKU(SQLModel, table=True):
    """Product SKU."""

    id: UUID = Field(default=None, primary_key=True)
    sku_code: str = Field(unique=True, max_length=64)
    name: str
    category_id: Optional[UUID] = Field(None, foreign_key="category.id")
    category: str = Field(max_length=128)
    brand: Optional[str] = Field(None, max_length=128)
    cost_price: float = Field(ge=0.0)
    current_price: float = Field(ge=0.0)
    approval_price: Optional[float] = Field(default=None, ge=0.0)
    currency: str = Field(default="USD", max_length=8)
    inventory: int = Field(default=0, ge=0)
    reorder_point: int = Field(default=0, ge=0)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SKUCreate(SQLModel):
    """SKU creation schema."""

    sku_code: str
    name: str
    category_id: Optional[UUID] = None
    category: str
    brand: Optional[str] = None
    cost_price: float
    current_price: float
    approval_price: Optional[float] = None
    currency: str = "USD"
    inventory: int = 0
    reorder_point: int = 0
    is_active: bool = True


class SKURead(SQLModel):
    """SKU read schema."""

    id: UUID
    sku_code: str
    name: str
    category_id: Optional[UUID]
    category: str
    brand: Optional[str]
    cost_price: float
    current_price: float
    approval_price: Optional[float]
    currency: str
    inventory: int
    reorder_point: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SKUUpdate(SQLModel):
    """SKU update schema."""

    name: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    cost_price: Optional[float] = None
    current_price: Optional[float] = None
    approval_price: Optional[float] = None
    currency: Optional[str] = None
    inventory: Optional[int] = None
    reorder_point: Optional[int] = None
    is_active: Optional[bool] = None
