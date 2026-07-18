"""All Placer Engine tables in one module, grouped by concern.

Kept in a single file (unlike the backend's ``models/`` package) so the whole
engine schema is navigable at a glance. Same idioms as the backend: no ORM
``relationship()``s, string ids, JSON columns for lists/dicts, enum vocabulary
lives in ``state.py`` / docstrings rather than DB constraints. Cross-table
references are soft (no FK) — engine rows also point at EHR ids (patients,
facilities) that live in a different database entirely.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import JSON, Column, Text
from sqlmodel import Field, SQLModel


def new_id() -> str:
    """Random string id, matching the backend's convention."""
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.utcnow()


class TimestampMixin(SQLModel):
    """created_at / updated_at shared by mutable tables. ``updated_at`` is
    refreshed explicitly by write paths (no SQLAlchemy onupdate hooks)."""

    created_at: datetime = Field(default_factory=utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=utcnow, nullable=False)


# ---------------------------------------------------------------------------
# Case — one per tracked admission; the engine's unit of work
# ---------------------------------------------------------------------------


class Case(TimestampMixin, table=True):
    """The engine's view of one admitted patient's journey to discharge.

    ``state`` follows the DispoState machine in ``state.py``:
    tracking | predicted | committed | green | transition | discharged.
    """

    __tablename__ = "cases"

    id: str = Field(default_factory=new_id, primary_key=True)
    patient_id: str = Field(index=True, description="EHR patient id")
    encounter_id: Optional[str] = Field(default=None, index=True, description="EHR encounter id")

    state: str = Field(default="tracking", index=True)

    brief: Optional[str] = Field(default=None, sa_column=Column(Text), description="Running case summary maintained by the agent")
    facts: Optional[dict] = Field(default=None, sa_column=Column(JSON), description="Structured extracted facts (insurance, mobility, home setup, ...)")

    cursor: int = Field(default=0, description="Last EHR event seq processed for this case")
    next_review_at: Optional[datetime] = Field(default=None, description="Heartbeat: when to re-review even without new events")

    active_pathways: Optional[list] = Field(default=None, sa_column=Column(JSON), description="[{pathway_id, confidence}] currently being worked in parallel")
    dirty: bool = Field(default=False, index=True, description="New events arrived; case needs re-review after debounce")


# ---------------------------------------------------------------------------
# Barrier — a blocker on one or more pathways, bucketed by readiness dimension
# ---------------------------------------------------------------------------


class Barrier(TimestampMixin, table=True):
    """Something standing between the patient and a discharge pathway.

    ``dimension`` is one of the seven readiness dimensions:
    medical | clinical_docs | decision | payer | destination | home_logistics | transport.
    Medical readiness itself is represented as a barrier of dimension 'medical'
    that must exist and be cleared (see state.derive_readiness).
    """

    __tablename__ = "barriers"

    id: str = Field(default_factory=new_id, primary_key=True)
    case_id: str = Field(index=True)
    pathway_ids: Optional[list] = Field(default=None, sa_column=Column(JSON), description="Pathway ids this blocks; empty/None = blocks all (shared)")

    dimension: str = Field(index=True)
    btype: str = Field(description="Short machine key, e.g. 'iv_abx_course', 'auth_pending'")
    status: str = Field(default="open", index=True, description="open | in_progress | cleared | blocked")

    description: Optional[str] = None
    evidence: Optional[str] = Field(default=None, sa_column=Column(Text), description="Chart citations / call outcomes backing this barrier")


# ---------------------------------------------------------------------------
# DispoTask — an engine work item (distinct from EHR care_tasks)
# ---------------------------------------------------------------------------


class DispoTask(TimestampMixin, table=True):
    """A unit of agent work, usually aimed at clearing a Barrier.

    ``mode``: auto (agent just does it) | approval (needs human sign-off) |
    team (a human must do it). Lifecycle: suggested | pending | approved |
    in_progress | waiting | done | failed | cancelled. ``idempotency_key`` is
    unique so replayed event processing never double-creates work.
    """

    __tablename__ = "dispo_tasks"

    id: str = Field(default_factory=new_id, primary_key=True)
    case_id: str = Field(index=True)
    barrier_id: Optional[str] = Field(default=None, index=True)
    referral_id: Optional[str] = Field(default=None, index=True)

    action_id: Optional[str] = Field(default=None, description="Action-catalog ref, e.g. 'FPR-004'")
    task_type: str = Field(index=True)
    mode: str = Field(default="auto", description="auto | approval | team")
    channel: Optional[str] = Field(default=None, description="phone | fax | ehr_order | chat | ...")

    status: str = Field(default="suggested", index=True)
    pathway_ids: Optional[list] = Field(default=None, sa_column=Column(JSON), description="Pathways this serves; empty/None = shared")

    idempotency_key: Optional[str] = Field(default=None, unique=True, index=True)

    title: str
    detail: Optional[str] = Field(default=None, sa_column=Column(Text))
    result: Optional[dict] = Field(default=None, sa_column=Column(JSON))


# ---------------------------------------------------------------------------
# Referral — one facility being pursued for one pathway
# ---------------------------------------------------------------------------


class Referral(TimestampMixin, table=True):
    """A placement attempt at a specific facility.

    Lifecycle: shortlisted | intake_verified | screened | submitted | pending |
    accepted | conditional | declined | waitlisted.
    """

    __tablename__ = "referrals"

    id: str = Field(default_factory=new_id, primary_key=True)
    case_id: str = Field(index=True)
    pathway_id: int = Field(index=True)
    facility_id: str = Field(index=True, description="EHR facility id")
    facility_name: str

    status: str = Field(default="shortlisted", index=True)
    denial_reason: Optional[str] = None
    conditions: Optional[list] = Field(default=None, sa_column=Column(JSON), description="Conditions on a 'conditional' acceptance")
    bed_hold_expires: Optional[datetime] = None
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))


# ---------------------------------------------------------------------------
# Approval — a human decision point surfaced to the care team
# ---------------------------------------------------------------------------


class Approval(SQLModel, table=True):
    """Groups one or more DispoTasks behind a human yes/no.

    ``kind``: suggested (opt-in nudge) | batch (approve a plan) | per_action.
    Status: pending | approved | rejected | expired.
    """

    __tablename__ = "approvals"

    id: str = Field(default_factory=new_id, primary_key=True)
    case_id: str = Field(index=True)
    kind: str = Field(default="per_action")
    task_ids: Optional[list] = Field(default=None, sa_column=Column(JSON))

    status: str = Field(default="pending", index=True)
    prompt: Optional[str] = Field(default=None, sa_column=Column(Text))
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utcnow, nullable=False)


# ---------------------------------------------------------------------------
# ChatMessage — the team-facing conversation surface
# ---------------------------------------------------------------------------


class ChatMessage(SQLModel, table=True):
    """One message in a case thread (or the general thread when case_id is null).

    ``kind``: text | approval_card | notification | readiness_board — the
    frontend renders non-text kinds as rich cards.
    """

    __tablename__ = "chat_messages"

    id: str = Field(default_factory=new_id, primary_key=True)
    case_id: Optional[str] = Field(default=None, index=True, description="Null = general (non-case) thread")
    author: str = Field(description="'placer' or 'team:<name>'")
    kind: str = Field(default="text")
    content: Optional[str] = Field(default=None, sa_column=Column(Text))
    approval_id: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=utcnow, nullable=False)


# ---------------------------------------------------------------------------
# Run — audit trail of agent invocations
# ---------------------------------------------------------------------------


class Run(SQLModel, table=True):
    """One agent invocation: what triggered it, what it did, how it ended.

    Append-mostly; ``status`` moves running -> done | error.
    """

    __tablename__ = "runs"

    id: str = Field(default_factory=new_id, primary_key=True)
    agent: str = Field(index=True, description="e.g. 'reviewer', 'caller', 'referral_worker'")
    case_id: Optional[str] = Field(default=None, index=True)
    trigger: str = Field(description="e.g. 'event:order.created', 'heartbeat', 'chat'")

    status: str = Field(default="running", index=True, description="running | done | error")
    log: Optional[list] = Field(default=None, sa_column=Column(JSON), description="Step-by-step tool/decision log")
    outcome: Optional[str] = Field(default=None, sa_column=Column(Text))

    created_at: datetime = Field(default_factory=utcnow, nullable=False)
    finished_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# EngineMeta — tiny key-value store for engine-global state (e.g. EHR cursor)
# ---------------------------------------------------------------------------


class EngineMeta(SQLModel, table=True):
    """Engine-global scalars keyed by name. Currently: 'ehr_cursor' — the last
    EHR event ``seq`` the brain loop has processed (stored as str)."""

    __tablename__ = "engine_meta"

    key: str = Field(primary_key=True)
    value: str


# ---------------------------------------------------------------------------
# FacilityIntel — engine-side memory about facilities, layered over EHR data
# ---------------------------------------------------------------------------


class FacilityIntel(SQLModel, table=True):
    """What the engine has learned about a facility across cases (bed counts
    from calls, decline patterns) — knowledge the EHR facility record lacks."""

    __tablename__ = "facility_intel"

    id: str = Field(default_factory=new_id, primary_key=True)
    facility_id: str = Field(unique=True, index=True, description="EHR facility id")
    beds_available: Optional[int] = None
    last_verified_at: Optional[datetime] = None
    decline_history: Optional[list] = Field(default=None, sa_column=Column(JSON), description="[{case_id, reason, at}] past declines")
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))
