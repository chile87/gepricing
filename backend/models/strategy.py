from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel


class Strategy(SQLModel, table=True):
    """Pricing strategy."""

    id: UUID = Field(default=None, primary_key=True)
    name: str = Field(max_length=128)
    description: Optional[str] = None
    status: str = Field(default="draft", max_length=32)  # draft, active, paused, archived
    created_by: Optional[str] = Field(None, max_length=128)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class StrategyCreate(SQLModel):
    """Strategy creation schema."""

    name: str
    description: Optional[str] = None
    status: str = "draft"
    created_by: Optional[str] = None
    is_active: bool = True


class StrategyRead(SQLModel):
    """Strategy read schema."""

    id: UUID
    name: str
    description: Optional[str]
    status: str
    created_by: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class StrategyUpdate(SQLModel):
    """Strategy update schema."""

    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None
