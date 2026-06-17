from datetime import datetime
from typing import Any, Dict
from uuid import UUID

from sqlmodel import Field, SQLModel


class UIChangeFeed(SQLModel, table=True):
    """Realtime UI change notification feed (via pg_notify)."""

    id: int = Field(default=None, primary_key=True)  # BIGSERIAL
    entity_type: str = Field(max_length=64)
    entity_id: UUID
    event_type: str = Field(max_length=32)  # insert, update, delete
    payload: Dict[str, Any] = Field(default_factory=dict, sa_type="JSONB")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UIChangeFeedCreate(SQLModel):
    """UIChangeFeed creation schema."""

    entity_type: str
    entity_id: UUID
    event_type: str
    payload: Dict[str, Any] = {}


class UIChangeFeedRead(SQLModel):
    """UIChangeFeed read schema."""

    id: int
    entity_type: str
    entity_id: UUID
    event_type: str
    payload: Dict[str, Any]
    created_at: datetime
