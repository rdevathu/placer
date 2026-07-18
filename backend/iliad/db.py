"""Database engine, session management, and schema lifecycle helpers.

A single SQLite file backs the whole EHR. We expose a FastAPI dependency
(``get_session``) plus ``init_db`` / ``reset_db`` used by seeding and the admin
reset endpoint.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from . import config

# check_same_thread=False lets the SQLite connection be shared across FastAPI's
# threadpool; SQLModel/SQLAlchemy still serializes access per-session.
engine = create_engine(
    config.DATABASE_URL,
    echo=config.SQL_ECHO,
    connect_args={"check_same_thread": False},
)


# Foreign-key enforcement is toggled off only during bulk seeding (see
# ``fk_enforcement``). Without ORM relationships, SQLAlchemy flushes a mixed
# batch in an order that can trip FK constraints; the seed data is trusted and
# internally consistent, so we relax enforcement just for that load.
_ENFORCE_FK = True


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # noqa: ANN001
    """Set foreign-key enforcement and WAL journaling on each new connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute(f"PRAGMA foreign_keys={'ON' if _ENFORCE_FK else 'OFF'}")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


class fk_enforcement:
    """Context manager to temporarily change FK enforcement for new connections.

    Disposes the connection pool on enter/exit so pooled connections pick up the
    new pragma value rather than serving a stale one.
    """

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def __enter__(self) -> "fk_enforcement":
        global _ENFORCE_FK
        self._previous = _ENFORCE_FK
        _ENFORCE_FK = self.enabled
        engine.dispose()
        return self

    def __exit__(self, *exc) -> None:
        global _ENFORCE_FK
        _ENFORCE_FK = self._previous
        engine.dispose()


def init_db() -> None:
    """Create all tables if they do not yet exist."""
    # Import models for their side effect of registering on SQLModel.metadata.
    from . import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def reset_db() -> None:
    """Drop every table and recreate the empty schema.

    Callers are responsible for reseeding afterwards. Used by the demo-reset
    flow so a fresh run always starts from a known state.
    """
    from . import models  # noqa: F401

    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding a transactional session."""
    with Session(engine) as session:
        yield session
