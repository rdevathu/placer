"""Pydantic schemas for the brain's structured LLM calls.

These are the ``output_format`` contracts passed to ``placer.llm.structured``.
Keep them small and strictly typed — the model fills them, the pipeline trusts
them (with guardrails: medical/decision barriers are never auto-cleared no
matter what the model says; see pipeline._reconcile_barriers).
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

try:  # Python 3.9: Literal lives in typing (3.8+), keep the import explicit
    from typing import Literal
except ImportError:  # pragma: no cover
    from typing_extensions import Literal  # type: ignore


class PathwayScore(BaseModel):
    """One entry in the pathway confidence distribution."""

    pathway_id: int
    confidence: float = Field(ge=0.0, le=1.0)


class BarrierOp(BaseModel):
    """A barrier mutation proposed by the GPS: upsert (create/update by the
    (dimension, btype) key) or clear (mark cleared — ignored for the
    medical/decision dimensions, which only humans clear)."""

    op: Literal["upsert", "clear"]
    dimension: Literal[
        "medical",
        "clinical_docs",
        "decision",
        "payer",
        "destination",
        "home_logistics",
        "transport",
    ]
    btype: str
    description: str = ""
    evidence: str = ""
    pathway_ids: List[int] = Field(default_factory=list)
    status: Optional[str] = None


class GpsAssessment(BaseModel):
    """Full output of one Discharge-GPS assessment pass."""

    distribution: List[PathwayScore] = Field(
        description="Pathways with confidence >= 0.05 only; confidences sum to <= 1.0"
    )
    rationale: str
    review_horizon: Literal["imminent", "days", "week_plus"]
    brief: str = Field(description="Updated ~10-sentence running case brief")
    barriers: List[BarrierOp] = Field(default_factory=list)


class WatchmanVerdict(BaseModel):
    """Is this EHR event material to the discharge picture?"""

    material: bool
    reason: str
