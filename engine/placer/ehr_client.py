"""Thin synchronous client for the dummy EHR (backend/).

Methods map 1:1 onto the backend routers (read them, don't guess): patients,
observations, dispo, orders, care-tasks, communications, facilities, and the
append-only /events feed the engine polls. Writes send an ``X-Actor`` header so
the EHR's event log attributes mutations to this agent. Every method returns
parsed JSON dicts and raises ``httpx.HTTPStatusError`` on non-2xx — callers
(the engine loop) decide how to recover.
"""

from __future__ import annotations

from typing import Any, Optional

import httpx

from . import config


class EHRClient:
    """Sync httpx wrapper around the dummy EHR REST API."""

    def __init__(self, base_url: Optional[str] = None, actor: str = "agent:placer", timeout: float = 10.0) -> None:
        self.actor = actor
        self._client = httpx.Client(base_url=base_url or config.EHR_BASE_URL, timeout=timeout)

    def close(self) -> None:
        self._client.close()

    # -- low-level helpers ---------------------------------------------------

    def _get(self, path: str, params: Optional[dict] = None) -> Any:
        resp = self._client.get(path, params=params)
        resp.raise_for_status()
        return resp.json()

    def _write(self, method: str, path: str, body: dict) -> Any:
        # X-Actor only on writes: it exists to attribute mutations in /events.
        resp = self._client.request(method, path, json=body, headers={"X-Actor": self.actor})
        resp.raise_for_status()
        return resp.json()

    # -- event feed (the engine's trigger primitive) -------------------------

    def list_events(self, since: int = 0, limit: int = 100) -> list:
        """Events with seq > since, oldest first. ``GET /events``."""
        return self._get("/events", params={"since": since, "limit": limit})

    # -- patients / chart ----------------------------------------------------

    def list_admitted_patients(self) -> list:
        """The inpatient worklist: patients with an in-progress encounter."""
        return self._get("/patients", params={"admitted": True})

    def get_patient(self, patient_id: str) -> dict:
        """One patient with computed age. ``GET /patients/{id}``."""
        return self._get(f"/patients/{patient_id}")

    def get_chart(self, patient_id: str) -> dict:
        """One-call chart snapshot (demographics, problems, meds, labs, dispo...)."""
        return self._get(f"/patients/{patient_id}/chart")

    def list_labs(self, patient_id: str, status: Optional[str] = None) -> list:
        params: dict = {}
        if status:
            params["status"] = status
        return self._get(f"/patients/{patient_id}/labs", params=params)

    def list_notes(self, patient_id: str, note_type: Optional[str] = None) -> list:
        params: dict = {}
        if note_type:
            params["note_type"] = note_type
        return self._get(f"/patients/{patient_id}/notes", params=params)

    # -- disposition ---------------------------------------------------------

    def post_dispo_assessment(
        self,
        patient_id: str,
        encounter_id: Optional[str],
        predicted_disposition: str,
        confidence: Optional[float] = None,
        rationale: Optional[str] = None,
        barriers: Optional[list] = None,
        alternatives: Optional[list] = None,
        assessed_by: Optional[str] = None,
    ) -> dict:
        """POST /dispo-assessments — supersedes the prior current assessment."""
        return self._write("POST", "/dispo-assessments", {
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "predicted_disposition": predicted_disposition,
            "confidence": confidence,
            "rationale": rationale,
            "barriers": barriers,
            "alternatives": alternatives,
            "assessed_by": assessed_by or self.actor,
        })

    # -- orders --------------------------------------------------------------

    def create_order(
        self,
        patient_id: str,
        encounter_id: Optional[str],
        order_type: str,
        display: str,
        detail: Optional[str] = None,
        priority: str = "routine",
        status: str = "draft",
        ordered_by: Optional[str] = None,
    ) -> dict:
        """POST /orders. Defaults to draft (pended) — the agent proposes,
        a clinician signs. Field names match backend ``OrderCreate``."""
        return self._write("POST", "/orders", {
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "order_type": order_type,
            "display": display,
            "detail": detail,
            "priority": priority,
            "status": status,
            "ordered_by": ordered_by or self.actor,
        })

    # -- care tasks ----------------------------------------------------------

    def create_care_task(
        self,
        patient_id: str,
        task_type: str,
        title: str,
        encounter_id: Optional[str] = None,
        description: Optional[str] = None,
        priority: str = "medium",
        assigned_to: Optional[str] = None,
        related_facility_id: Optional[str] = None,
        related_order_id: Optional[str] = None,
    ) -> dict:
        return self._write("POST", "/care-tasks", {
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "task_type": task_type,
            "title": title,
            "description": description,
            "priority": priority,
            "assigned_to": assigned_to or self.actor,
            "related_facility_id": related_facility_id,
            "related_order_id": related_order_id,
        })

    def update_care_task(self, task_id: str, **fields: Any) -> dict:
        """PATCH /care-tasks/{id} — status moves and result_summary
        (fields per backend ``CareTaskUpdate``)."""
        return self._write("PATCH", f"/care-tasks/{task_id}", fields)

    # -- communications ------------------------------------------------------

    def create_communication(
        self,
        patient_id: str,
        summary: str,
        party_type: Optional[str] = None,
        party_name: Optional[str] = None,
        outcome: Optional[str] = None,
        transcript: Optional[str] = None,
        care_task_id: Optional[str] = None,
        facility_id: Optional[str] = None,
        modality: str = "phone",
        direction: str = "outbound",
    ) -> dict:
        return self._write("POST", "/communications", {
            "patient_id": patient_id,
            "care_task_id": care_task_id,
            "facility_id": facility_id,
            "direction": direction,
            "modality": modality,
            "party_type": party_type,
            "party_name": party_name,
            "summary": summary,
            "transcript": transcript,
            "outcome": outcome,
        })

    def place_call(
        self,
        patient_id: str,
        task: str,
        party_type: str = "snf",
        party_name: Optional[str] = None,
        facility_id: Optional[str] = None,
        care_task_id: Optional[str] = None,
    ) -> dict:
        """Place a REAL outbound call via the Iliad ``/calls`` endpoint (Bland).

        The backend gate allows autonomous calls only to a SNF; it dials through
        Bland (force-numbered for the demo) and logs the matching Communication,
        so the engine must NOT also write one. Returns the backend response
        (``call_id``, dialed number, logged communication)."""
        return self._write("POST", "/calls", {
            "patient_id": patient_id,
            "task": task,
            "party_type": party_type,
            "party_name": party_name,
            "facility_id": facility_id,
            "care_task_id": care_task_id,
        })

    # -- placer chat (provider <-> Placer thread rendered in the Iliad UI) ----

    def list_placer_messages(self, patient_id: str) -> list:
        """Chronological provider<->Placer thread. ``GET /patients/{id}/placer/messages``."""
        return self._get(f"/patients/{patient_id}/placer/messages")

    def create_placer_message(
        self,
        patient_id: str,
        text: str,
        sender: str = "placer",
        sender_name: str = "Placer",
    ) -> dict:
        """POST /patients/{id}/placer/messages — no auto-reply is generated.
        Field names match backend ``PlacerMessageCreate``."""
        return self._write("POST", f"/patients/{patient_id}/placer/messages", {
            "sender": sender,
            "sender_name": sender_name,
            "text": text,
        })

    # -- facilities ----------------------------------------------------------

    def list_facilities(
        self,
        facility_type: Optional[str] = None,
        has_available_beds: Optional[bool] = None,
    ) -> list:
        params: dict = {}
        if facility_type:
            params["facility_type"] = facility_type
        if has_available_beds is not None:
            params["has_available_beds"] = has_available_beds
        return self._get("/facilities", params=params)

    def update_facility(self, facility_id: str, **fields: Any) -> dict:
        """PATCH /facilities/{id} — e.g. available_beds/notes after a call
        (fields per backend ``FacilityUpdate``)."""
        return self._write("PATCH", f"/facilities/{facility_id}", fields)
