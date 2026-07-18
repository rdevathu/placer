"""Shared router helpers: lookup-or-404, raw_fhir stripping, age computation."""

from __future__ import annotations

from datetime import date
from typing import Any, Optional, Type, TypeVar

from fastapi import HTTPException
from sqlmodel import SQLModel

T = TypeVar("T", bound=SQLModel)

# Bulky/agent-noisy fields dropped from responses unless include_raw is set.
_HEAVY_FIELDS = {"raw_fhir"}


def get_or_404(session, model: Type[T], obj_id: str, name: Optional[str] = None) -> T:
    obj = session.get(model, obj_id)
    if obj is None:
        label = name or model.__name__
        raise HTTPException(status_code=404, detail=f"{label} '{obj_id}' not found")
    return obj


def age_years(birth_date: Optional[date], as_of: Optional[date] = None) -> Optional[int]:
    """Compute age from birth date at read time (never stored — avoids drift)."""
    if not birth_date:
        return None
    ref = as_of or date.today()
    return ref.year - birth_date.year - ((ref.month, ref.day) < (birth_date.month, birth_date.day))


def serialize(obj: SQLModel, include_raw: bool = False) -> dict[str, Any]:
    """Serialize a table row to a dict, dropping heavy fields by default."""
    data = obj.model_dump()
    if not include_raw:
        for field in _HEAVY_FIELDS:
            data.pop(field, None)
    return data


def serialize_many(objs, include_raw: bool = False) -> list[dict[str, Any]]:
    return [serialize(o, include_raw) for o in objs]
