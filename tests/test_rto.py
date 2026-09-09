"""Test suite for RTO directory parsing, Bharat-series resolution, and RTO REST API."""

import sys
from pathlib import Path

ROOT_DIR = str(Path(__file__).resolve().parent.parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import pytest
from fastapi.testclient import TestClient

import app_core
from api import app

client = TestClient(app)


def test_rto_directory_loaded():
    """Verify RTO directory is loaded with 38 State/UT codes and detailed divisions."""
    assert len(app_core.RTO_DIRECTORY["state_codes"]) >= 36
    assert "DL" in app_core.RTO_DIRECTORY["state_codes"]
    assert "KA" in app_core.RTO_DIRECTORY["state_codes"]
    assert "MH" in app_core.RTO_DIRECTORY["state_codes"]
    assert "TN" in app_core.RTO_DIRECTORY["state_codes"]
    assert "bh_series" in app_core.RTO_DIRECTORY


def test_standard_vehicle_registration_parsing():
    """Verify parsing of standard state registration numbers with hyphens and spaces."""
    # Delhi
    delhi_res = app_core.parse_vehicle_registration("DL-01-AB-1234")
    assert delhi_res["is_valid"] is True
    assert delhi_res["is_bh_series"] is False
    assert delhi_res["state_code"] == "DL"
    assert delhi_res["state_name"] == "Delhi"
    assert delhi_res["rto_code"] == "01"
    assert delhi_res["rto_name"] == "Mall Road (Civil Lines)"
    assert delhi_res["vehicle_unique_number"] == "1234"
    assert delhi_res["jurisdiction_type"] == "state"

    # Maharashtra (without hyphens)
    mh_res = app_core.parse_vehicle_registration("MH02CD5678")
    assert mh_res["is_valid"] is True
    assert mh_res["state_code"] == "MH"
    assert mh_res["state_name"] == "Maharashtra"
    assert mh_res["rto_code"] == "02"
    assert mh_res["rto_name"] == "Mumbai (West) - Andheri"

    # Karnataka
    ka_res = app_core.parse_vehicle_registration("KA-05-XY-9999")
    assert ka_res["is_valid"] is True
    assert ka_res["state_code"] == "KA"
    assert ka_res["state_name"] == "Karnataka"
    assert ka_res["rto_code"] == "05"
    assert ka_res["rto_name"] == "Bangalore South (Jayanagar)"


def test_bharat_series_registration_parsing():
    """Verify parsing of MoRTH Central Bharat-series (BH) vehicle registrations."""
    bh1 = app_core.parse_vehicle_registration("21BH1234AA")
    assert bh1["is_valid"] is True
    assert bh1["is_bh_series"] is True
    assert bh1["registration_year"] == "2021"
    assert bh1["series_code"] == "AA"
    assert bh1["vehicle_unique_number"] == "1234"
    assert "Notification G.S.R. 594(E)" in bh1["statutory_note"]
    assert bh1["jurisdiction_type"] == "central_bh"

    # Lowercase and spacing handling
    bh2 = app_core.parse_vehicle_registration("  23 bh 9999 z  ")
    assert bh2["is_valid"] is True
    assert bh2["is_bh_series"] is True
    assert bh2["registration_year"] == "2023"
    assert bh2["series_code"] == "Z"
    assert bh2["vehicle_unique_number"] == "9999"


def test_invalid_vehicle_registrations():
    """Verify robust handling of invalid, malformed, or unrecognized registration numbers."""
    assert app_core.parse_vehicle_registration("")[ "is_valid"] is False
    assert app_core.parse_vehicle_registration("NOT_A_REG")[ "is_valid"] is False
    assert app_core.parse_vehicle_registration("XX-99-ZZ-0000")[ "is_valid"] is False  # Non-existent state XX
    
    with pytest.raises(app_core.CalculatorInputError):
        app_core.parse_vehicle_registration(12345)


def test_api_rto_resolve_endpoint():
    """Verify REST API endpoint GET /api/v1/rto/resolve/{reg_number}."""
    resp_standard = client.get("/api/v1/rto/resolve/KA-01-AB-1234")
    assert resp_standard.status_code == 200
    data_std = resp_standard.json()
    assert data_std["is_valid"] is True
    assert data_std["state_name"] == "Karnataka"
    assert data_std["rto_code"] == "01"
    assert data_std["rto_name"] == "Bangalore Central (Koramangala)"

    resp_bh = client.get("/api/v1/rto/resolve/22BH1234AB")
    assert resp_bh.status_code == 200
    data_bh = resp_bh.json()
    assert data_bh["is_valid"] is True
    assert data_bh["is_bh_series"] is True
    assert data_bh["registration_year"] == "2022"

    resp_invalid = client.get("/api/v1/rto/resolve/INVALID_NUM")
    assert resp_invalid.status_code == 200
    assert resp_invalid.json()["is_valid"] is False
