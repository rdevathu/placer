"""Engine database: SQLite engine, session dependency, schema lifecycle.

Mirrors the backend's ``ehr/db.py`` minus the FK-toggle machinery — the engine
never bulk-seeds cross-referencing rows, so plain FK-less inserts are fine.
The DB is disposable state; it can always be rebuilt by re-syncing the EHR.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from . import config

# check_same_thread=False lets the connection be shared across FastAPI's
# threadpool; SQLAlchemy still serializes access per-session.
engine = create_engine(
    config.DATABASE_URL,
    echo=config.SQL_ECHO,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    """Create all tables if they do not yet exist."""
    # Import for the side effect of registering tables on SQLModel.metadata.
    from . import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def reset_db() -> None:
    """Drop every table and recreate the empty schema."""
    from . import models  # noqa: F401

    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding a transactional session."""
    with Session(engine) as session:
        yield session
