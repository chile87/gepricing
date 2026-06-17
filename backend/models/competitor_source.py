from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel


class CompetitorSource(SQLModel, table=True):
    """Competitor source reference data."""

    id: UUID = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True, max_length=64)
    name: str = Field(max_length=128)
    base_url: Optional[str] = None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CompetitorSourceCreate(SQLModel):
    """CompetitorSource creation schema."""

    code: str
    name: str
    base_url: Optional[str] = None
    is_active: bool = True


class CompetitorSourceRead(SQLModel):
    """CompetitorSource read schema."""

    id: UUID
    code: str
    name: str
    base_url: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
