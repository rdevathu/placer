"""The Watchman: cheap materiality triage for EHR events.

Rules first, LLM last. Almost every event type has a deterministic answer; only
free-text notes need model judgment. The rule table lives at module top as data
so the routing policy is inspectable without reading the code.
"""

from __future__ import annotations

import logging

from placer import llm

from .schemas import WatchmanVerdict

logger = logging.getLogger(__name__)

# event_type -> True (always material), False (never), or "llm" (classify).
# Any event whose actor starts with "agent" bypasses this table entirely — those
# are our own workers' outcomes and always route straight through as material.
# `care_task.updated` by a clinician is material (a human moved the worklist);
# other care_task/communication/facility churn by non-agents is ambient noise.
RULES: dict = {
    "patient.admitted": True,
    "order.completed": True,
    "order.resulted": True,
    "order.created": True,  # routine clinician orders shift the clinical picture
    "care_task.updated": True,
    "care_task.created": False,
    "care_task.deleted": False,
    "communication.created": False,
    "facility.updated": False,
    "note.created": "llm",
}

_WATCHMAN_SYSTEM = (
    "You are Placer's Watchman. Given a new EHR event and the running case "
    "brief for a hospitalized patient, decide whether the event is MATERIAL to "
    "the patient's discharge disposition (pathway choice, barriers, readiness, "
    "timing). Routine vitals, hygiene notes, and administrative chatter are not "
    "material. New clinical developments, goals-of-care changes, family input, "
    "placement information, and functional-status changes are. Be decisive."
)


def is_material(event: dict, case_brief: str) -> WatchmanVerdict:
    """Classify one EHR event. Never raises: LLM failure degrades to material
    (better one spurious reassessment than a missed signal)."""
    actor = event.get("actor") or ""
    event_type = event.get("event_type") or ""

    if actor.startswith("agent"):
        return WatchmanVerdict(material=True, reason="agent-actor event: internal outcome, route through")

    rule = RULES.get(event_type)
    if rule is True:
        return WatchmanVerdict(material=True, reason=f"rule: {event_type} is always material")
    if rule is False:
        return WatchmanVerdict(material=False, reason=f"rule: {event_type} by non-agent is ambient")

    if rule == "llm":
        prompt = (
            f"EHR event:\n{event}\n\n"
            f"Current case brief:\n{case_brief or '(no brief yet)'}\n\n"
            "Is this event material to discharge planning?"
        )
        try:
            return llm.structured(prompt, WatchmanVerdict, system=_WATCHMAN_SYSTEM)
        except Exception as exc:  # degrade safe: don't drop signal on model error
            logger.warning("watchman LLM classify failed (%s); defaulting material", exc)
            return WatchmanVerdict(material=True, reason=f"llm error, defaulted material: {exc}")

    return WatchmanVerdict(material=False, reason=f"rule: unknown event_type '{event_type}' defaults immaterial")
