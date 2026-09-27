"""Tests for Driving Licence Suspension Risk Engine — Fixes #52."""
import pytest
from fastapi.testclient import TestClient
from api import app
import app_core

client = TestClient(app)


class TestDLSuspensionRiskData:
    def test_all_violations_have_dl_risk_field(self):
        for key, rec in app_core.NATIONAL_FINES.items():
            assert "dl_suspension_risk" in rec, f"{key} missing dl_suspension_risk"
            assert rec["dl_suspension_risk"] in ("none", "caution", "high", "automatic"), (
                f"{key}: invalid dl_suspension_risk value {rec['dl_suspension_risk']!r}"
            )

    def test_drunk_driving_is_automatic(self):
        assert app_core.NATIONAL_FINES["drunk_driving"]["dl_suspension_risk"] == "automatic"

    def test_minor_driving_is_automatic(self):
        assert app_core.NATIONAL_FINES["minor_driving"]["dl_suspension_risk"] == "automatic"

    def test_signal_jump_is_high(self):
        assert app_core.NATIONAL_FINES["signal_jump"]["dl_suspension_risk"] == "high"

    def test_mobile_driving_is_high(self):
        assert app_core.NATIONAL_FINES["mobile_driving"]["dl_suspension_risk"] == "high"

    def test_dangerous_driving_is_high(self):
        assert app_core.NATIONAL_FINES["dangerous_driving"]["dl_suspension_risk"] == "high"

    def test_overspeeding_is_caution(self):
        assert app_core.NATIONAL_FINES["overspeeding_lmv"]["dl_suspension_risk"] == "caution"
        assert app_core.NATIONAL_FINES["overspeeding_mmv"]["dl_suspension_risk"] == "caution"

    def test_no_helmet_is_none(self):
        assert app_core.NATIONAL_FINES["no_helmet"]["dl_suspension_risk"] == "none"

    def test_no_parking_is_none(self):
        assert app_core.NATIONAL_FINES["no_parking"]["dl_suspension_risk"] == "none"


class TestGetDLSuspensionRisk:
    def test_drunk_driving_automatic_full_response(self):
        result = app_core.get_dl_suspension_risk("drunk_driving")
        assert result["violation_key"] == "drunk_driving"
        assert result["risk_level"] == "automatic"
        assert result["is_automatic"] is True
        assert result["statutory_basis"]
        assert result["citizen_action"]
        assert result["description"]

    def test_no_helmet_none_risk(self):
        result = app_core.get_dl_suspension_risk("no_helmet")
        assert result["risk_level"] == "none"
        assert result["is_automatic"] is False

    def test_signal_jump_high_risk(self):
        result = app_core.get_dl_suspension_risk("signal_jump")
        assert result["risk_level"] == "high"
        assert result["is_automatic"] is False

    def test_wrong_side_caution(self):
        result = app_core.get_dl_suspension_risk("wrong_side")
        assert result["risk_level"] == "caution"

    def test_invalid_violation_key_raises(self):
        with pytest.raises(app_core.CalculatorInputError, match="Unknown violation key"):
            app_core.get_dl_suspension_risk("not_a_real_violation")

    def test_result_has_all_expected_fields(self):
        result = app_core.get_dl_suspension_risk("mobile_driving")
        for field in ("violation_key", "description", "risk_level", "statutory_basis",
                      "citizen_action", "is_automatic", "legal_note"):
            assert field in result

    def test_automatic_citizen_action_mentions_lawyer(self):
        result = app_core.get_dl_suspension_risk("drunk_driving")
        assert "lawyer" in result["citizen_action"].lower() or "advocate" in result["citizen_action"].lower()


class TestGetOffenceRiskProfile:
    def test_single_automatic_offence(self):
        result = app_core.get_offence_risk_profile(["drunk_driving"])
        assert result["highest_risk_level"] == "automatic"
        assert "drunk_driving" in result["automatic_offences"]
        assert result["is_habitual_offender_risk"] is False  # only 1 offence

    def test_three_offences_triggers_habitual(self):
        result = app_core.get_offence_risk_profile(["no_helmet", "no_parking", "no_seatbelt"])
        assert result["is_habitual_offender_risk"] is True
        assert result["offence_count"] == 3

    def test_two_offences_not_habitual(self):
        result = app_core.get_offence_risk_profile(["no_helmet", "no_parking"])
        assert result["is_habitual_offender_risk"] is False

    def test_highest_risk_detection(self):
        result = app_core.get_offence_risk_profile(["no_helmet", "signal_jump", "no_parking"])
        assert result["highest_risk_level"] == "high"
        assert "signal_jump" in result["high_risk_offences"]

    def test_automatic_in_mixed_list(self):
        result = app_core.get_offence_risk_profile([
            "no_helmet", "no_seatbelt", "drunk_driving", "overspeeding_lmv"
        ])
        assert result["highest_risk_level"] == "automatic"
        assert "drunk_driving" in result["automatic_offences"]
        assert result["is_habitual_offender_risk"] is True

    def test_duplicate_violations_counted(self):
        # 3 speeding tickets = habitual
        result = app_core.get_offence_risk_profile([
            "overspeeding_lmv", "overspeeding_lmv", "overspeeding_lmv"
        ])
        assert result["offence_count"] == 3
        assert result["is_habitual_offender_risk"] is True

    def test_empty_list_raises(self):
        with pytest.raises(app_core.CalculatorInputError):
            app_core.get_offence_risk_profile([])

    def test_invalid_key_raises(self):
        with pytest.raises(app_core.CalculatorInputError, match="Unknown violation keys"):
            app_core.get_offence_risk_profile(["no_helmet", "invalid_key"])

    def test_result_has_all_fields(self):
        result = app_core.get_offence_risk_profile(["no_helmet"])
        for field in ("offence_count", "highest_risk_level", "automatic_offences",
                      "high_risk_offences", "caution_offences", "is_habitual_offender_risk",
                      "habitual_offender_threshold", "statutory_basis", "recommendation"):
            assert field in result

    def test_threshold_is_three(self):
        result = app_core.get_offence_risk_profile(["no_helmet"])
        assert result["habitual_offender_threshold"] == 3

    def test_recommendation_present_and_non_empty(self):
        result = app_core.get_offence_risk_profile(["drunk_driving"])
        assert result["recommendation"]


class TestDLRiskAPI:
    def test_get_dl_risk_drunk_driving(self):
        response = client.get("/api/v1/violations/drunk_driving/dl-risk")
        assert response.status_code == 200
        data = response.json()
        assert data["risk_level"] == "automatic"
        assert data["is_automatic"] is True

    def test_get_dl_risk_no_helmet(self):
        response = client.get("/api/v1/violations/no_helmet/dl-risk")
        assert response.status_code == 200
        data = response.json()
        assert data["risk_level"] == "none"

    def test_get_dl_risk_invalid_violation(self):
        response = client.get("/api/v1/violations/not_a_violation/dl-risk")
        assert response.status_code == 400

    def test_post_offence_risk_profile_basic(self):
        response = client.post(
            "/api/v1/offence-risk-profile",
            json={"violation_keys": ["no_helmet", "mobile_driving"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["highest_risk_level"] == "high"
        assert data["is_habitual_offender_risk"] is False

    def test_post_offence_risk_profile_habitual(self):
        response = client.post(
            "/api/v1/offence-risk-profile",
            json={"violation_keys": ["no_helmet", "no_seatbelt", "no_parking"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_habitual_offender_risk"] is True

    def test_post_offence_risk_profile_empty_list(self):
        response = client.post(
            "/api/v1/offence-risk-profile",
            json={"violation_keys": []},
        )
        assert response.status_code == 422  # Pydantic min_length=1 validation

    def test_health_includes_dl_risk_metric(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "dl_risk_violations" in data["metrics"]
        # 13 violations have non-none risk across expanded catalogue
        assert data["metrics"]["dl_risk_violations"] == 13
