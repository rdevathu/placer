"""Shared model plumbing: timestamp mixin and id helpers."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlmodel import Field, SQLModel


def new_id() -> str:
    """Generate a random string id for natively-created (non-imported) rows."""
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.utcnow()


class TimestampMixin(SQLModel):
    """created_at / updated_at columns shared by every table.

    ``updated_at`` is refreshed explicitly in write handlers (kept simple and
    predictable rather than relying on SQLAlchemy onupdate hooks).
    """

    created_at: datetime = Field(default_factory=utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=utcnow, nullable=False)
