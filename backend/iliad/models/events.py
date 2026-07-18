"""Event feed table — the append-only trigger primitive for the agent engine.

Every mutating API write appends an Event row. Downstream agents poll
``GET /events?since=<seq>`` and react. The table is append-only; rows are never
updated or deleted (a demo reset drops the whole table with the rest of the DB).
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from .base import utcnow


class Event(SQLModel, table=True):
    """One row per mutation, in commit order.

    ``seq`` is a monotonically increasing integer (SQLite rowid alias), so
    ``seq > since`` is a reliable cursor. ``patient_id`` is a *soft* reference
    (no FK) so event rows never participate in FK insert-ordering.
    """

    __tablename__ = "events"

    seq: Optional[int] = Field(default=None, primary_key=True)
    event_type: str = Field(index=True, description="lowercase-dot, e.g. 'order.created'")
    patient_id: Optional[str] = Field(default=None, index=True)

    actor: str = Field(default="clinician", description="'clinician' or 'agent:<name>' (from X-Actor)")

    entity_type: Optional[str] = Field(default=None, description="e.g. 'order', 'care_task'")
    entity_id: Optional[str] = None

    payload: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=utcnow, nullable=False)
