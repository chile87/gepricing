from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlmodel import Field, SQLModel


class CrawlerRun(SQLModel, table=True):
    """Crawler execution run."""

    id: UUID = Field(default=None, primary_key=True)
    source_id: Optional[UUID] = Field(None, foreign_key="competitorsource.id")
    status: str = Field(max_length=32)  # queued, running, completed, failed, partial
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None
    pages_crawled: int = Field(default=0, ge=0)
    items_found: int = Field(default=0, ge=0)
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict, sa_type="JSONB")


class CrawlerRunCreate(SQLModel):
    """CrawlerRun creation schema."""

    source_id: Optional[UUID] = None
    status: str
    pages_crawled: int = 0
    items_found: int = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = {}


class CrawlerRunRead(SQLModel):
    """CrawlerRun read schema."""

    id: UUID
    source_id: Optional[UUID]
    status: str
    started_at: datetime
    finished_at: Optional[datetime]
    pages_crawled: int
    items_found: int
    error_message: Optional[str]
    metadata: Dict[str, Any]


class CrawlerRunUpdate(SQLModel):
    """CrawlerRun update schema."""

    status: Optional[str] = None
    finished_at: Optional[datetime] = None
    pages_crawled: Optional[int] = None
    items_found: Optional[int] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
