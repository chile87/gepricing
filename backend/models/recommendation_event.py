from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlmodel import Field, SQLModel


class RecommendationEvent(SQLModel, table=True):
    """Event log for recommendation state changes."""

    id: UUID = Field(default=None, primary_key=True)
    recommendation_id: UUID = Field(foreign_key="pricerecommendation.id")
    event_type: str = Field(max_length=64)
    actor: Optional[str] = Field(None, max_length=128)
    notes: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict, sa_type="JSONB")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RecommendationEventCreate(SQLModel):
    """RecommendationEvent creation schema."""

    recommendation_id: UUID
    event_type: str
    actor: Optional[str] = None
    notes: Optional[str] = None
    payload: Dict[str, Any] = {}


class RecommendationEventRead(SQLModel):
    """RecommendationEvent read schema."""

    id: UUID
    recommendation_id: UUID
    event_type: str
    actor: Optional[str]
    notes: Optional[str]
    payload: Dict[str, Any]
    created_at: datetime
