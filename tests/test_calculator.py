"""Unit tests for the DriveLegal India challan calculator.

Covers:
- calculate_fine arithmetic (base, vehicle multiplier, state surcharge, repeat)
- Data integrity: complete 28 states + 8 UTs, valid sections, non-negative fines
"""
import pathlib
import json

import pytest

# Make the project importable when tests run from the repo root or tests/ dir
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

# Import from app.py: it loads data from JSON files via pathlib,
# streamlit.st calls are guarded by st.tabs only at render time.
from app import (  # noqa: E402
    NATIONAL_FINES, VEHICLE_TYPES, STATE_DATA, ALL_STATES,
    calculate_fine, get_violation_options,
)

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "data"


def test_national_fines_structure():
    for key, v in NATIONAL_FINES.items():
        assert "description" in v and isinstance(v["description"], str)
        assert "fine" in v and isinstance(v["fine"], (int, float)) and v["fine"] >= 0
        assert "section" in v and v["section"]
        assert "imprisonment" in v  # None when not applicable


def test_vehicle_types_structure():
    for key, mult in VEHICLE_TYPES.items():
        assert isinstance(mult, (int, float))
        assert 0 < mult <= 2.0, f"Multiplier out of documented range for {key}: {mult}"


def test_state_data_structure():
    for state, info in STATE_DATA.items():
        for required in ("surcharge", "notes", "helmet_law", "speed_city", "speed_highway"):
            assert required in info, f"{state} missing key {required}"
        assert 0 <= info["surcharge"] < 1
        assert 0 < info["speed_city"] < info["speed_highway"] < 300
        assert isinstance(info["notes"], list) and info["notes"]


def test_all_states_and_uts_present():
    """Project claims coverage of all 28 states and 8 Union Territories."""
    assert len(STATE_DATA) == 36
    assert len(ALL_STATES) == 36
    assert ALL_STATES == sorted(STATE_DATA.keys())
    # Spot-check a few well-known states/UTs
    for name in ("Delhi", "Maharashtra", "Telangana", "Goa", "Ladakh", "Puducherry"):
        assert name in STATE_DATA


def test_data_files_load_identically():
    """Ensure the JSON files are the actual source of truth used by the app."""
    for name, expected in (
        ("national_fines.json", NATIONAL_FINES),
        ("vehicle_types.json", VEHICLE_TYPES),
        ("state_data.json", STATE_DATA),
    ):
        loaded = json.loads((DATA_DIR / name).read_text())
        assert loaded == expected, f"{name} differs from in-app data"


# ── Calculator arithmetic ─────────────────────────────────────────────

def _expected(violation_key, vehicle_key, state, repeat):
    base = NATIONAL_FINES[violation_key]["fine"]
    mult = VEHICLE_TYPES[vehicle_key]
    surcharge = STATE_DATA[state]["surcharge"]
    adjusted = base * mult
    return {
        "base_fine": base,
        "vehicle_adjustment": adjusted - base,
        "state_surcharge": adjusted * surcharge,
        "repeat_penalty": adjusted if repeat else 0.0,
        "total": adjusted * (2.0 if repeat else 1.0) + adjusted * surcharge,
    }


@pytest.mark.parametrize("repeat", [False, True])
def test_calculate_fine_no_surcharge(repeat):
    r = calculate_fine("no_helmet", "Two-Wheeler (> 50cc)", "Bihar", repeat)
    e = _expected("no_helmet", "Two-Wheeler (> 50cc)", "Bihar", repeat)
    for key in ("base_fine", "vehicle_adjustment", "state_surcharge",
                "repeat_penalty", "total"):
        assert r[key] == pytest.approx(e[key])
    assert r["total"] == 2000.0 if repeat else 1000.0


def test_calculate_fine_with_surcharge():
    # Kerala has a 5% surcharge; car base ₹1,000 → ₹1,000 + ₹50 = ₹1,050
    r = calculate_fine("no_helmet", "Two-Wheeler (> 50cc)", "Kerala", False)
    assert r["base_fine"] == 1000
    assert r["state_surcharge"] == 50
    assert r["total"] == 1050


def test_calculate_fine_vehicle_multiplier():
    # Heavy Motor Vehicle multiplier 2.0: base 10,000 → 20,000
    r = calculate_fine("drunk_driving", "Heavy Motor Vehicle", "Delhi", False)
    assert r["base_fine"] == 10000
    assert r["vehicle_adjustment"] == 10000
    assert r["total"] == 20000


def test_calculate_fine_repeat_doubles():
    r = calculate_fine("signal_jump", "Light Motor Vehicle (Car)", "Goa", True)
    assert r["repeat_penalty"] == r["base_fine"]
    # 1000 * 1.0 + 10% surcharge (100) + 100% repeat (1000) = 2100
    assert r["total"] == 2100


def test_calculate_fine_low_cc_two_wheeler():
    # <=50cc multiplier 0.5: base 1000 → 500
    r = calculate_fine("no_seatbelt", "Two-Wheeler (≤ 50cc)", "Rajasthan", False)
    assert r["total"] == 500


def test_calculate_fine_imprisonment_passed_through():
    r = calculate_fine("drunk_driving_repeat", "Light Motor Vehicle (Car)", "Delhi", False)
    assert r["imprisonment"] == "2 years"
    assert r["section"] == "185"


def test_calculate_fine_all_combinations_sane():
    """Smoke test: every violation x vehicle x state combination computes a positive total."""
    for v in NATIONAL_FINES:
        for vt in VEHICLE_TYPES:
            for s in STATE_DATA:
                for repeat in (False, True):
                    r = calculate_fine(v, vt, s, repeat)
                    assert r["total"] > 0
                    assert r["base_fine"] >= 0
                    assert r["state_surcharge"] >= 0
                    assert r["repeat_penalty"] >= 0


def test_get_violation_options_roundtrip():
    opts = get_violation_options()
    assert set(opts.values()) == set(NATIONAL_FINES.keys())
    assert len(opts) == len(NATIONAL_FINES)
