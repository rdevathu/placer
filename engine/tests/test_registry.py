"""Tests for the pathway registry catalog."""

from __future__ import annotations

from placer.registry import load_pathways

# Must stay in sync with the backend's DispositionType enum values.
VALID_EHR_DISPOSITIONS = {
    "home",
    "home_with_services",
    "snf",
    "assisted_living",
    "inpatient_rehab",
    "ltac",
    "hospice_home",
    "hospice_facility",
    "undetermined",
}

WIRED_IDS = {1, 2, 4, 8, 11, 12, 14}


def test_all_25_pathways_load():
    pathways = load_pathways()
    assert set(pathways) == set(range(1, 26))
    for pid, p in pathways.items():
        assert p["id"] == pid
        assert p["key"] and p["name"]


def test_exactly_seven_wired():
    pathways = load_pathways()
    wired = {pid for pid, p in pathways.items() if p["wired"]}
    assert wired == WIRED_IDS


def test_ehr_dispositions_are_valid_backend_values():
    for p in load_pathways().values():
        assert p["ehr_disposition"] in VALID_EHR_DISPOSITIONS, p["key"]


def test_requirements_only_on_wired():
    for pid, p in load_pathways().items():
        if pid in WIRED_IDS:
            assert 5 <= len(p["requirements"]) <= 8, p["key"]
        else:
            assert p["requirements"] == [], p["key"]
