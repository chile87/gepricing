from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel


class Category(SQLModel, table=True):
    """Product category reference data."""

    id: UUID = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True, max_length=64)
    name: str = Field(max_length=128)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CategoryCreate(SQLModel):
    """Category creation schema."""

    code: str
    name: str


class CategoryRead(SQLModel):
    """Category read schema."""

    id: UUID
    code: str
    name: str
    created_at: datetime
