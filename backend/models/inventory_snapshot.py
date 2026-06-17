from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel


class InventorySnapshot(SQLModel, table=True):
    """Inventory snapshot at a point in time."""

    id: UUID = Field(default=None, primary_key=True)
    sku_id: UUID = Field(foreign_key="sku.id")
    on_hand_qty: int = Field(ge=0)
    reserved_qty: int = Field(default=0, ge=0)
    inbound_qty: int = Field(default=0, ge=0)
    snapshot_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)


class InventorySnapshotCreate(SQLModel):
    """InventorySnapshot creation schema."""

    sku_id: UUID
    on_hand_qty: int
    reserved_qty: int = 0
    inbound_qty: int = 0
    snapshot_at: datetime


class InventorySnapshotRead(SQLModel):
    """InventorySnapshot read schema."""

    id: UUID
    sku_id: UUID
    on_hand_qty: int
    reserved_qty: int
    inbound_qty: int
    snapshot_at: datetime
    created_at: datetime
