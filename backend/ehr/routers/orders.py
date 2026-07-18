"""Orders — the live, agent-writable action surface.

Lifecycle: draft (pended) -> signed -> completed | cancelled. Signing a lab
order materializes a pending Observation; completing that order results it.
Illegal transitions return 409 with the allowed states so agents can recover.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from ..db import get_session
from ..models import Medication, Observation, Order
from ..models.base import new_id, utcnow
from ..schemas import OrderCreate, OrderSign, OrderUpdate
from ._common import get_or_404, serialize, serialize_many

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get(
    "",
    summary="List orders",
    description="Filter by patient, status, and type. Use `status=draft` to find pended orders awaiting signature, `status=signed` for active orders.",
)
def list_orders(
    session: Session = Depends(get_session),
    patient_id: Optional[str] = None,
    status: Optional[str] = Query(None, description="draft | signed | completed | cancelled"),
    order_type: Optional[str] = Query(None, description="lab | medication | imaging | consult | nursing | dispo | referral"),
    limit: int = Query(100, le=500),
    offset: int = 0,
) -> list[dict]:
    stmt = select(Order)
    if patient_id:
        stmt = stmt.where(Order.patient_id == patient_id)
    if status:
        stmt = stmt.where(Order.status == status)
    if order_type:
        stmt = stmt.where(Order.order_type == order_type)
    orders = session.exec(stmt.order_by(Order.created_at.desc()).offset(offset).limit(limit)).all()
    return serialize_many(orders)


@router.get("/{order_id}", summary="Get one order")
def get_order(order_id: str, session: Session = Depends(get_session)) -> dict:
    return serialize(get_or_404(session, Order, order_id, "Order"))


@router.post(
    "",
    status_code=201,
    summary="Place an order (pend or sign)",
    description=(
        "Creates an order. Defaults to `status=draft` (pended, awaiting a "
        "clinician's signature) — this is how an agent proposes an order. Pass "
        "`status=signed` to sign immediately. If `order_type=lab` and the order "
        "is signed, a pending Observation is created automatically and linked."
    ),
)
def create_order(body: OrderCreate, session: Session = Depends(get_session)) -> dict:
    now = utcnow()
    order = Order(
        id=new_id(),
        patient_id=body.patient_id,
        encounter_id=body.encounter_id,
        order_type=body.order_type.value,
        status=body.status.value,
        display=body.display,
        detail=body.detail,
        priority=body.priority,
        ordered_by=body.ordered_by,
        authored_at=now,
    )
    if order.status == "signed":
        order.signed_by = body.ordered_by
        order.signed_at = now
        _materialize_lab(session, order)
    session.add(order)
    session.commit()
    session.refresh(order)
    return serialize(order)


@router.patch("/{order_id}", summary="Edit a draft order")
def update_order(order_id: str, body: OrderUpdate, session: Session = Depends(get_session)) -> dict:
    order = get_or_404(session, Order, order_id, "Order")
    if order.status != "draft":
        raise HTTPException(status_code=409, detail=f"Only draft orders can be edited; order is '{order.status}'")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(order, key, value)
    order.updated_at = utcnow()
    session.add(order)
    session.commit()
    session.refresh(order)
    return serialize(order)


@router.post(
    "/{order_id}/sign",
    summary="Sign a pended order",
    description="Moves a draft order to `signed` (active). For lab orders this creates the pending result.",
)
def sign_order(order_id: str, body: OrderSign, session: Session = Depends(get_session)) -> dict:
    order = get_or_404(session, Order, order_id, "Order")
    if order.status not in ("draft",):
        raise HTTPException(status_code=409, detail=f"Only draft orders can be signed; order is '{order.status}'")
    now = utcnow()
    order.status = "signed"
    order.signed_by = body.signed_by
    order.signed_at = now
    order.updated_at = now
    _materialize_lab(session, order)
    session.add(order)
    session.commit()
    session.refresh(order)
    return serialize(order)


@router.post(
    "/{order_id}/complete",
    summary="Complete / fulfill a signed order",
    description="Marks a signed order completed. If it is a lab order with a linked pending Observation, that result is marked final.",
)
def complete_order(order_id: str, session: Session = Depends(get_session)) -> dict:
    order = get_or_404(session, Order, order_id, "Order")
    if order.status != "signed":
        raise HTTPException(status_code=409, detail=f"Only signed orders can be completed; order is '{order.status}'")
    now = utcnow()
    order.status = "completed"
    order.completed_at = now
    order.updated_at = now
    if order.result_observation_id:
        obs = session.get(Observation, order.result_observation_id)
        if obs and obs.status == "pending":
            obs.status = "final"
            obs.issued_time = now
            obs.updated_at = now
            session.add(obs)
    session.add(order)
    session.commit()
    session.refresh(order)
    return serialize(order)


@router.post("/{order_id}/cancel", summary="Cancel an order")
def cancel_order(order_id: str, session: Session = Depends(get_session)) -> dict:
    order = get_or_404(session, Order, order_id, "Order")
    if order.status in ("completed", "cancelled"):
        raise HTTPException(status_code=409, detail=f"Cannot cancel a '{order.status}' order")
    order.status = "cancelled"
    order.updated_at = utcnow()
    # Cancel a linked pending lab result too.
    if order.result_observation_id:
        obs = session.get(Observation, order.result_observation_id)
        if obs and obs.status == "pending":
            obs.status = "cancelled"
            session.add(obs)
    session.add(order)
    session.commit()
    session.refresh(order)
    return serialize(order)


def _materialize_lab(session: Session, order: Order) -> None:
    """When a lab order is signed, create the pending Observation it will result into."""
    if order.order_type != "lab" or order.result_observation_id:
        return
    obs = Observation(
        id=new_id(),
        patient_id=order.patient_id,
        encounter_id=order.encounter_id,
        category="laboratory",
        loinc_code=order.code,
        display=order.display,
        status="pending",
        effective_time=order.signed_at or utcnow(),
    )
    session.add(obs)
    session.flush()  # obtain obs.id (FK enforcement is fine here — parent exists)
    order.result_observation_id = obs.id
