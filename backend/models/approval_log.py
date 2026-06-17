from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel


class ApprovalLog(SQLModel, table=True):
    """Approval history for recommendations."""

    id: UUID = Field(default=None, primary_key=True)
    recommendation_id: UUID = Field(foreign_key="pricerecommendation.id")
    action: str = Field(max_length=32)  # approved, rejected, reopened
    actor: Optional[str] = Field(None, max_length=128)
    notes: Optional[str] = None
    acted_at: datetime = Field(default_factory=datetime.utcnow)


class ApprovalLogCreate(SQLModel):
    """ApprovalLog creation schema."""

    recommendation_id: UUID
    action: str
    actor: Optional[str] = None
    notes: Optional[str] = None


class ApprovalLogRead(SQLModel):
    """ApprovalLog read schema."""

    id: UUID
    recommendation_id: UUID
    action: str
    actor: Optional[str]
    notes: Optional[str]
    acted_at: datetime
