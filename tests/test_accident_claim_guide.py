"""Tests for Motor Accident Claim Guide and Compensation Estimator — Fixes #53."""
import pytest
from fastapi.testclient import TestClient
from api import app
import app_core

client = TestClient(app)

GUIDE_IDS = [
    "hit_and_run_compensation",
    "no_fault_compensation",
    "mact_petition",
    "insurance_claim_own_damage",
    "victim_rights_at_accident_scene",
]


class TestAccidentClaimGuideData:
    def test_guide_returns_five_entries(self):
        guide = app_core.get_accident_claim_guide()
        assert len(guide) == 5

    def test_all_required_fields_present(self):
        guide = app_core.get_accident_claim_guide()
        required = {"id", "category", "statutory_basis", "title", "summary",
                    "eligibility", "procedure", "key_provisions", "documents_required", "time_limit"}
        for entry in guide:
            missing = required - entry.keys()
            assert not missing, f"Entry {entry.get('id')} missing fields: {missing}"

    def test_all_expected_ids_present(self):
        guide = app_core.get_accident_claim_guide()
        ids = {e["id"] for e in guide}
        for expected_id in GUIDE_IDS:
            assert expected_id in ids, f"Missing guide entry: {expected_id}"

    def test_hit_and_run_compensation_amounts(self):
        guide = app_core.get_accident_claim_guide()
        entry = next(e for e in guide if e["id"] == "hit_and_run_compensation")
        comp = entry.get("compensation", {})
        assert comp.get("death") == 200000, "Hit-and-run death compensation should be Rs 2 lakh"
        assert comp.get("grievous_hurt") == 50000, "Hit-and-run grievous hurt should be Rs 50,000"

    def test_no_fault_compensation_amounts(self):
        guide = app_core.get_accident_claim_guide()
        entry = next(e for e in guide if e["id"] == "no_fault_compensation")
        comp = entry.get("compensation", {})
        assert comp.get("death") == 500000, "Sec 164 death floor should be Rs 5 lakh"
        assert comp.get("grievous_hurt") == 250000, "Sec 164 grievous hurt floor should be Rs 2.5 lakh"

    def test_all_ids_unique(self):
        guide = app_core.get_accident_claim_guide()
        ids = [e["id"] for e in guide]
        assert len(ids) == len(set(ids)), "Guide entry IDs must be unique"

    def test_procedures_are_lists(self):
        guide = app_core.get_accident_claim_guide()
        for entry in guide:
            assert isinstance(entry["procedure"], list) and len(entry["procedure"]) >= 1
            assert isinstance(entry["eligibility"], list) and len(entry["eligibility"]) >= 1
            assert isinstance(entry["key_provisions"], list) and len(entry["key_provisions"]) >= 1


class TestAccidentCompensationEstimate:
    def test_hit_and_run_death_fixed(self):
        result = app_core.get_accident_compensation_estimate("hit_and_run_death")
        assert result["statutory_minimum_inr"] == 200000.0
        assert result["estimated_compensation_inr"] == 200000.0
        assert "solatium_death" in result["components"]

    def test_hit_and_run_grievous_fixed(self):
        result = app_core.get_accident_compensation_estimate("hit_and_run_grievous")
        assert result["statutory_minimum_inr"] == 50000.0
        assert result["estimated_compensation_inr"] == 50000.0

    def test_fatal_without_income_uses_floor(self):
        result = app_core.get_accident_compensation_estimate("fatal")
        assert result["statutory_minimum_inr"] == 500000.0
        assert result["estimated_compensation_inr"] == 500000.0

    def test_fatal_with_income_and_age_exceeds_floor(self):
        # 30-year-old earning Rs 50,000/month: dependency = 50000*12*0.67 = 4,02,000
        # multiplier for 30 = 16, dependency_total = 64,32,000
        result = app_core.get_accident_compensation_estimate("fatal", monthly_income=50000, age=30)
        assert result["estimated_compensation_inr"] > 500000
        assert "loss_of_dependency" in result["components"]
        assert result["components"]["multiplier"] == 16.0

    def test_fatal_age_boundary_multiplier(self):
        # Age 65+ should give multiplier 5
        result = app_core.get_accident_compensation_estimate("fatal", monthly_income=20000, age=70)
        assert result["components"]["multiplier"] == 4.0

    def test_grievous_hurt_without_income_uses_floor(self):
        result = app_core.get_accident_compensation_estimate("grievous_hurt")
        assert result["statutory_minimum_inr"] == 250000.0
        assert result["estimated_compensation_inr"] == 250000.0

    def test_grievous_hurt_with_income(self):
        result = app_core.get_accident_compensation_estimate("grievous_hurt", monthly_income=30000, age=25)
        assert "lost_earnings_3_months" in result["components"]
        assert result["components"]["lost_earnings_3_months"] == pytest.approx(90000.0, rel=1e-3)

    def test_simple_hurt_no_floor(self):
        result = app_core.get_accident_compensation_estimate("simple_hurt")
        assert result["statutory_minimum_inr"] == 0.0
        assert result["estimated_compensation_inr"] == 0.0

    def test_invalid_type_raises(self):
        with pytest.raises(app_core.CalculatorInputError, match="Invalid accident_type"):
            app_core.get_accident_compensation_estimate("unknown_type")

    def test_result_has_all_fields(self):
        result = app_core.get_accident_compensation_estimate("fatal")
        for field in ("accident_type", "statutory_minimum_inr", "estimated_compensation_inr",
                      "methodology", "components", "statutory_basis", "disclaimer"):
            assert field in result

    def test_disclaimer_present(self):
        result = app_core.get_accident_compensation_estimate("grievous_hurt")
        assert result["disclaimer"]


class TestAccidentClaimGuideAPI:
    def test_get_all_guide_entries(self):
        response = client.get("/api/v1/accident-claim-guide")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

    def test_get_single_guide_entry_by_id(self):
        response = client.get("/api/v1/accident-claim-guide", params={"id": "hit_and_run_compensation"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "hit_and_run_compensation"

    def test_get_guide_entry_not_found(self):
        response = client.get("/api/v1/accident-claim-guide", params={"id": "nonexistent"})
        assert response.status_code == 404

    def test_post_compensation_estimate_hit_and_run_death(self):
        response = client.post(
            "/api/v1/accident-compensation-estimate",
            json={"accident_type": "hit_and_run_death"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["statutory_minimum_inr"] == 200000.0
        assert data["estimated_compensation_inr"] == 200000.0

    def test_post_compensation_estimate_fatal_with_income(self):
        response = client.post(
            "/api/v1/accident-compensation-estimate",
            json={"accident_type": "fatal", "monthly_income": 40000, "age": 35},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["estimated_compensation_inr"] > 500000

    def test_post_compensation_estimate_invalid_type(self):
        response = client.post(
            "/api/v1/accident-compensation-estimate",
            json={"accident_type": "not_valid"},
        )
        assert response.status_code == 422  # Pydantic validation failure
