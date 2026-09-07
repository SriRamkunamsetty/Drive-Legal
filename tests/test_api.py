"""Comprehensive test suite for the DriveLegal India FastAPI microservice."""

import sys
from pathlib import Path

ROOT_DIR = str(Path(__file__).resolve().parent.parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import pytest
from fastapi.testclient import TestClient
from api import app

client = TestClient(app)


def test_api_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "2.0.0"
    assert data["metrics"]["national_violations"] == 19
    assert data["metrics"]["jurisdictions_covered"] == 36
    assert data["metrics"]["verified_compounding_states"] == 8

    v1_resp = client.get("/api/v1/health")
    assert v1_resp.status_code == 200
    assert v1_resp.json() == data


def test_api_get_violations():
    response = client.get("/api/v1/violations")
    assert response.status_code == 200
    violations = response.json()
    assert len(violations) == 19

    # Filter by vehicle
    bike_resp = client.get("/api/v1/violations", params={"vehicle_type": "Two-Wheeler (> 50cc)"})
    assert bike_resp.status_code == 200
    assert all("Two-Wheeler (> 50cc)" in v["allowed_vehicle_types"] for v in bike_resp.json())

    # Filter by search
    search_resp = client.get("/api/v1/violations", params={"search": "helmet"})
    assert search_resp.status_code == 200
    assert any("helmet" in v["description"].lower() for v in search_resp.json())


def test_api_get_states():
    response = client.get("/api/v1/states")
    assert response.status_code == 200
    states = response.json()
    assert len(states) == 36

    compounding_resp = client.get("/api/v1/states", params={"compounding_only": True})
    assert compounding_resp.status_code == 200
    compounding_states = compounding_resp.json()
    assert len(compounding_states) == 8
    assert all(s["has_compounding_schedule"] for s in compounding_states)


def test_api_calculate_single_fine():
    payload = {
        "violation_key": "no_helmet",
        "vehicle_type": "Two-Wheeler (> 50cc)",
        "state": "Karnataka",
        "quantity": None,
        "is_repeat": False
    }
    response = client.post("/api/v1/calculate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["violation_key"] == "no_helmet"
    assert data["base_fine"] == 1000.0
    assert data["calculated_fine"] == 1000.0
    assert data["state_compounding_applied"] is True
    assert data["compounded_fine"] == 500
    assert data["effective_fine"] == 500.0
    assert data["savings_from_compounding"] == 500.0
    assert data["notification_id"] == "TD 132 TMR 2019"


def test_api_calculate_single_fine_invalid_vehicle():
    payload = {
        "violation_key": "no_helmet",
        "vehicle_type": "Light Motor Vehicle (Car)",
        "state": "Delhi"
    }
    response = client.post("/api/v1/calculate", json=payload)
    assert response.status_code == 400
    assert "not applicable to" in response.json()["detail"]


def test_api_calculate_multi_fine():
    payload = {
        "state": "Maharashtra",
        "items": [
            {
                "violation_key": "no_helmet",
                "vehicle_type": "Two-Wheeler (> 50cc)",
                "quantity": None,
                "is_repeat": False
            },
            {
                "violation_key": "no_seatbelt",
                "vehicle_type": "Light Motor Vehicle (Car)",
                "quantity": None,
                "is_repeat": False
            }
        ]
    }
    response = client.post("/api/v1/calculate-multi", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "Maharashtra"
    assert data["item_count"] == 2
    assert data["grand_total"] == 2000.0
    assert data["total_compounding_fee"] == 700.0  # 500 helmet + 200 seatbelt
    assert data["has_compounding_items"] is True


def test_api_compounding_matrix():
    response = client.get("/api/v1/compounding-matrix")
    assert response.status_code == 200
    data = response.json()
    assert len(data["states"]) == 8
    assert len(data["rows"]) > 0

    # Filter matrix
    filtered = client.get("/api/v1/compounding-matrix", params={"violations": ["no_helmet", "signal_jump"]})
    assert filtered.status_code == 200
    assert len(filtered.json()["rows"]) == 2


def test_api_laws_catalogue():
    response = client.get("/api/v1/laws")
    assert response.status_code == 200
    assert len(response.json()) == 18

    search_resp = client.get("/api/v1/laws", params={"q": "185"})
    assert search_resp.status_code == 200
    laws = search_resp.json()
    assert len(laws) >= 1
    assert any("185" in l["section"] for l in laws)


def test_api_citizen_rights():
    response = client.get("/api/v1/citizen-rights")
    assert response.status_code == 200
    assert len(response.json()) == 5

    single_resp = client.get("/api/v1/citizen-rights", params={"id": "digilocker_validity"})
    assert single_resp.status_code == 200
    assert single_resp.json()[0]["id"] == "digilocker_validity"

    not_found = client.get("/api/v1/citizen-rights", params={"id": "non_existent"})
    assert not_found.status_code == 404
