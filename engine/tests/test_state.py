"""Unit tests for the pure state logic in placer.state."""

from __future__ import annotations

import pytest

from placer.state import (
    ALLOWED_TRANSITIONS,
    DispoState,
    IllegalTransition,
    apply_transition,
    derive_readiness,
    select_active_pathways,
    trump,
)


# --- transitions ------------------------------------------------------------


def test_happy_path_to_discharge():
    s = "tracking"
    for event, expected in [
        ("predict", "predicted"),
        ("commit", "committed"),
        ("clear", "green"),
        ("depart", "transition"),
        ("discharge", "discharged"),
    ]:
        s = apply_transition(s, event)
        assert s == expected


def test_regressions_and_revocations():
    assert apply_transition("green", "regress") == "committed"
    assert apply_transition("green", "revoke") == "predicted"
    assert apply_transition("committed", "revoke") == "predicted"
    assert apply_transition("transition", "regress") == "committed"


def test_illegal_transitions_raise_with_context():
    with pytest.raises(IllegalTransition) as exc:
        apply_transition("tracking", "commit")
    assert "tracking" in str(exc.value)
    assert "predict" in str(exc.value)  # names what IS allowed

    with pytest.raises(IllegalTransition):
        apply_transition("discharged", "predict")  # terminal
    with pytest.raises(IllegalTransition):
        apply_transition("predicted", "clear")  # can't skip commit
    with pytest.raises(IllegalTransition):
        apply_transition("nonsense-state", "predict")


def test_every_state_in_transition_map():
    assert set(ALLOWED_TRANSITIONS) == {s.value for s in DispoState}


# --- select_active_pathways -------------------------------------------------


def test_fifty_fifty_selects_both():
    dist = [
        {"pathway_id": 11, "confidence": 0.5},
        {"pathway_id": 12, "confidence": 0.5},
    ]
    selected = select_active_pathways(dist, floor=0.25, max_k=3)
    assert {d["pathway_id"] for d in selected} == {11, 12}


def test_floor_filters_low_confidence():
    dist = [
        {"pathway_id": 1, "confidence": 0.7},
        {"pathway_id": 11, "confidence": 0.2},
        {"pathway_id": 14, "confidence": 0.1},
    ]
    selected = select_active_pathways(dist, floor=0.25, max_k=3)
    assert [d["pathway_id"] for d in selected] == [1]


def test_max_k_caps_and_sorts_desc():
    dist = [
        {"pathway_id": 1, "confidence": 0.3},
        {"pathway_id": 2, "confidence": 0.9},
        {"pathway_id": 4, "confidence": 0.5},
        {"pathway_id": 8, "confidence": 0.4},
    ]
    selected = select_active_pathways(dist, floor=0.25, max_k=3)
    assert [d["pathway_id"] for d in selected] == [2, 4, 8]


def test_below_floor_keeps_leader():
    dist = [
        {"pathway_id": 11, "confidence": 0.2},
        {"pathway_id": 12, "confidence": 0.15},
    ]
    selected = select_active_pathways(dist, floor=0.25, max_k=3)
    assert [d["pathway_id"] for d in selected] == [11]


def test_no_signal_selects_nothing():
    assert select_active_pathways([], floor=0.25, max_k=3) == []
    dist = [{"pathway_id": 1, "confidence": 0.01}]
    assert select_active_pathways(dist, floor=0.25, max_k=3) == []


# --- derive_readiness -------------------------------------------------------


def _cleared_strict_barriers():
    """Explicitly cleared medical + decision barriers (the strict dims)."""
    return [
        {"dimension": "medical", "status": "cleared"},
        {"dimension": "decision", "status": "cleared"},
    ]


def test_green_when_committed_and_all_clear():
    result = derive_readiness(_cleared_strict_barriers(), state="committed")
    assert result["green"] is True
    assert all(d["clear"] for d in result["dimensions"].values())


def test_not_green_when_not_committed():
    result = derive_readiness(_cleared_strict_barriers(), state="predicted")
    assert result["green"] is False  # dims clear, but no team commitment


def test_medical_requires_explicit_cleared_barrier():
    # No barriers at all: lenient dims clear, medical/decision do not.
    result = derive_readiness([], state="committed")
    assert result["dimensions"]["medical"]["clear"] is False
    assert result["dimensions"]["decision"]["clear"] is False
    assert result["dimensions"]["transport"]["clear"] is True
    assert result["green"] is False


def test_open_barrier_blocks_dimension():
    barriers = _cleared_strict_barriers() + [
        {"dimension": "payer", "status": "open"},
        {"dimension": "payer", "status": "in_progress"},
    ]
    result = derive_readiness(barriers, state="committed")
    payer = result["dimensions"]["payer"]
    assert payer == {"clear": False, "open_count": 2}
    assert result["green"] is False


def test_open_medical_barrier_beats_cleared_one():
    barriers = _cleared_strict_barriers() + [
        {"dimension": "medical", "status": "blocked"},
    ]
    result = derive_readiness(barriers, state="committed")
    assert result["dimensions"]["medical"]["clear"] is False
    assert result["green"] is False


# --- trump ------------------------------------------------------------------


def test_trump_cancels_exclusive_keeps_shared():
    tasks = [
        {"id": "t1", "pathway_ids": [11]},        # decided pathway -> keep
        {"id": "t2", "pathway_ids": [12]},        # losing pathway -> cancel
        {"id": "t3", "pathway_ids": None},        # shared -> keep
        {"id": "t4", "pathway_ids": []},          # shared -> keep
        {"id": "t5", "pathway_ids": [11, 12]},    # includes winner -> keep
    ]
    referrals = [
        {"id": "r1", "pathway_ids": [11]},
        {"id": "r2", "pathway_ids": [12]},
    ]
    barriers = [
        {"id": "b1", "pathway_ids": [12, 14]},
        {"id": "b2", "pathway_ids": None},
    ]
    keep, cancel = trump(tasks, referrals, barriers, decided_pathway_id=11)
    assert set(keep) == {"t1", "t3", "t4", "t5", "r1", "b2"}
    assert set(cancel) == {"t2", "r2", "b1"}
