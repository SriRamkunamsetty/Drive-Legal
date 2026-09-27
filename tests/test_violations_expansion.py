"""Tests for the expanded violations catalogue (PR A — Fixes #50)."""
import pytest
import app_core

NEW_VIOLATIONS = [
    "without_fastag",
    "no_puc",
    "tinted_windows",
    "no_lane_discipline",
    "driving_unfit_vehicle",
    "racing_on_road",
    "no_reflective_tape",
    "reverse_on_highway",
    "without_fire_extinguisher",
]

DL_RISK_LEVELS = {
    "without_fastag": "none",
    "no_puc": "none",
    "tinted_windows": "none",
    "no_lane_discipline": "caution",
    "driving_unfit_vehicle": "caution",
    "racing_on_road": "high",
    "no_reflective_tape": "none",
    "reverse_on_highway": "none",
    "without_fire_extinguisher": "none",
}


class TestNewViolationsPresent:
    def test_all_new_violations_in_national_fines(self):
        for v in NEW_VIOLATIONS:
            assert v in app_core.NATIONAL_FINES, f"{v} missing from NATIONAL_FINES"

    def test_new_violations_have_required_fields(self):
        required = {"description", "fine", "rule_section", "penalty_section",
                    "allowed_vehicle_types", "repeat_policy", "fine_basis",
                    "apply_vehicle_multiplier", "source_status", "source_ids", "legal_note"}
        for v in NEW_VIOLATIONS:
            rec = app_core.NATIONAL_FINES[v]
            for field in required:
                assert field in rec, f"{v} missing field {field}"

    def test_new_violations_have_dl_risk_field(self):
        for v in NEW_VIOLATIONS:
            rec = app_core.NATIONAL_FINES[v]
            assert "dl_suspension_risk" in rec, f"{v} missing dl_suspension_risk"
            assert rec["dl_suspension_risk"] in ("none", "caution", "high", "automatic")

    def test_validate_data_passes_with_new_violations(self):
        """validate_data() must pass cleanly after the violations expansion."""
        # Should not raise
        app_core.validate_data(
            app_core.NATIONAL_FINES,
            app_core.VEHICLE_TYPES,
            app_core.STATE_DATA,
            app_core.METADATA,
        )


class TestDLSuspensionRisk:
    def test_known_risk_levels(self):
        for v, expected_risk in DL_RISK_LEVELS.items():
            result = app_core.get_dl_suspension_risk(v)
            assert result["risk_level"] == expected_risk, f"{v}: expected {expected_risk}, got {result['risk_level']}"

    def test_drunk_driving_is_automatic(self):
        result = app_core.get_dl_suspension_risk("drunk_driving")
        assert result["risk_level"] == "automatic"
        assert result["is_automatic"] is True

    def test_no_helmet_has_none_risk(self):
        result = app_core.get_dl_suspension_risk("no_helmet")
        assert result["risk_level"] == "none"
        assert result["is_automatic"] is False

    def test_invalid_key_raises(self):
        with pytest.raises(app_core.CalculatorInputError):
            app_core.get_dl_suspension_risk("not_a_real_violation")

    def test_result_has_all_expected_fields(self):
        result = app_core.get_dl_suspension_risk("no_puc")
        for field in ("violation_key", "description", "risk_level", "statutory_basis", "citizen_action", "is_automatic", "legal_note"):
            assert field in result

    def test_racing_on_road_high_risk(self):
        result = app_core.get_dl_suspension_risk("racing_on_road")
        assert result["risk_level"] == "high"
        assert result["is_automatic"] is False


class TestNewViolationCalculations:
    def test_fastag_fine_calculation(self):
        res = app_core.calculate_fine(
            violation_key="without_fastag",
            vehicle_key="Light Motor Vehicle (Car)",
            state="Karnataka",
            repeat=False,
        )
        assert res["base_fine"] == 500

    def test_no_puc_fine_calculation(self):
        res = app_core.calculate_fine(
            violation_key="no_puc",
            vehicle_key="Two-Wheeler (> 50cc)",
            state="Maharashtra",
            repeat=False,
        )
        assert res["base_fine"] == 10000

    def test_racing_on_road_fine_calculation(self):
        res = app_core.calculate_fine(
            violation_key="racing_on_road",
            vehicle_key="Light Motor Vehicle (Car)",
            state="Delhi",
            repeat=False,
        )
        assert res["base_fine"] == 5000

    def test_tinted_windows_correct_vehicle_types(self):
        rec = app_core.NATIONAL_FINES["tinted_windows"]
        # Two-wheelers should not be in the allowed list
        assert "Two-Wheeler (> 50cc)" not in rec["allowed_vehicle_types"]
        # Cars should be in the allowed list
        assert "Light Motor Vehicle (Car)" in rec["allowed_vehicle_types"]

    def test_fire_extinguisher_transport_only(self):
        rec = app_core.NATIONAL_FINES["without_fire_extinguisher"]
        assert "Transport / Commercial" in rec["allowed_vehicle_types"]
        assert "Two-Wheeler (> 50cc)" not in rec["allowed_vehicle_types"]
