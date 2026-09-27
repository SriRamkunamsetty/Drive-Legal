"""Tests for Section 200 compounding schedule expansion — Haryana, Punjab, West Bengal, Odisha, Andhra Pradesh.

Fixes Issue #51.
"""
import pytest
import app_core


NEW_COMPOUNDING_STATES = ["Haryana", "Punjab", "West Bengal", "Odisha", "Andhra Pradesh"]

EXPECTED_NOTIFICATIONS = {
    "Haryana":         "10/104/2019-3HB-II",
    "Punjab":          "1/5/2019-5TP1/8050",
    "West Bengal":     "2090-WT/O/M",
    "Odisha":          "9817/T",
    "Andhra Pradesh":  "G.O.Ms.No.92-TR.I",
}

EXPECTED_EFFECTIVE_DATES = {
    "Haryana":         "2019-09-19",
    "Punjab":          "2019-10-22",
    "West Bengal":     "2019-09-27",
    "Odisha":          "2019-09-30",
    "Andhra Pradesh":  "2019-09-21",
}


class TestNewStateCompoundingSchedules:
    def test_all_new_states_have_compounding_schedule(self):
        for state in NEW_COMPOUNDING_STATES:
            data = app_core.STATE_DATA[state]
            assert data.get("compounding_schedule"), f"{state} has no compounding_schedule"
            assert len(data["compounding_schedule"]) >= 5, (
                f"{state} compounding_schedule has fewer than 5 entries"
            )

    def test_notification_ids_correct(self):
        for state, expected_notif in EXPECTED_NOTIFICATIONS.items():
            actual = app_core.STATE_DATA[state].get("notification_id")
            assert actual == expected_notif, (
                f"{state}: expected notification_id={expected_notif!r}, got {actual!r}"
            )

    def test_effective_dates_correct(self):
        for state, expected_date in EXPECTED_EFFECTIVE_DATES.items():
            actual = app_core.STATE_DATA[state].get("effective_date")
            assert actual == expected_date, (
                f"{state}: expected effective_date={expected_date!r}, got {actual!r}"
            )

    def test_source_status_is_state_notification(self):
        for state in NEW_COMPOUNDING_STATES:
            status = app_core.STATE_DATA[state].get("source_status")
            assert status == "state_notification", (
                f"{state}: source_status should be 'state_notification', got {status!r}"
            )

    def test_compounding_violations_exist_in_national_fines(self):
        for state in NEW_COMPOUNDING_STATES:
            sched = app_core.STATE_DATA[state].get("compounding_schedule", {})
            for v_key in sched:
                assert v_key in app_core.NATIONAL_FINES, (
                    f"{state} compounding_schedule references unknown violation {v_key!r}"
                )

    def test_compounding_amounts_are_positive_integers(self):
        for state in NEW_COMPOUNDING_STATES:
            sched = app_core.STATE_DATA[state].get("compounding_schedule", {})
            for v_key, amount in sched.items():
                assert isinstance(amount, int) and amount > 0, (
                    f"{state}.{v_key}: amount must be positive int, got {amount!r}"
                )

    def test_validate_data_passes(self):
        """Full validate_data() must succeed after expansion."""
        app_core.validate_data(
            app_core.NATIONAL_FINES,
            app_core.VEHICLE_TYPES,
            app_core.STATE_DATA,
            app_core.METADATA,
        )

    def test_total_compounding_states_is_thirteen(self):
        states_with = [s for s, d in app_core.STATE_DATA.items() if d.get("compounding_schedule")]
        assert len(states_with) == 13, (
            f"Expected 13 states with compounding, got {len(states_with)}: {states_with}"
        )


class TestCompoundingResolutionNewStates:
    def test_haryana_no_helmet_compounding(self):
        result = app_core.calculate_fine(
            violation_key="no_helmet",
            vehicle_key="Two-Wheeler (> 50cc)",
            state="Haryana",
            repeat=False,
        )
        assert result.get("compounding_fee") == 500
        assert result.get("compounding_notification_id") == "10/104/2019-3HB-II"

    def test_punjab_no_dl_compounding(self):
        result = app_core.calculate_fine(
            violation_key="no_dl",
            vehicle_key="Light Motor Vehicle (Car)",
            state="Punjab",
            repeat=False,
        )
        assert result.get("compounding_fee") == 2000
        assert result.get("compounding_notification_id") == "1/5/2019-5TP1/8050"

    def test_west_bengal_no_insurance_compounding(self):
        result = app_core.calculate_fine(
            violation_key="no_insurance",
            vehicle_key="Light Motor Vehicle (Car)",
            state="West Bengal",
            repeat=False,
        )
        assert result.get("compounding_fee") == 1000

    def test_odisha_no_rc_compounding(self):
        result = app_core.calculate_fine(
            violation_key="no_rc",
            vehicle_key="Light Motor Vehicle (Car)",
            state="Odisha",
            repeat=False,
        )
        assert result.get("compounding_fee") == 1000

    def test_andhra_pradesh_overspeeding_compounding(self):
        result = app_core.calculate_fine(
            violation_key="overspeeding_lmv",
            vehicle_key="Light Motor Vehicle (Car)",
            state="Andhra Pradesh",
            repeat=False,
        )
        assert result.get("compounding_fee") == 1000
        assert result.get("compounding_notification_id") == "G.O.Ms.No.92-TR.I"

    def test_haryana_seatbelt_compounding_savings(self):
        result = app_core.calculate_fine(
            violation_key="no_seatbelt",
            vehicle_key="Light Motor Vehicle (Car)",
            state="Haryana",
            repeat=False,
        )
        # Central fine is 1000, compounded is 500 — savings = 500
        assert result.get("compounding_fee") == 500
        central_fine = result["total"]
        assert central_fine > result["compounding_fee"]

    def test_state_without_compounding_still_works(self):
        """States not in expansion (e.g. Assam) must still return no compounding."""
        result = app_core.calculate_fine(
            violation_key="no_helmet",
            vehicle_key="Two-Wheeler (> 50cc)",
            state="Assam",
            repeat=False,
        )
        assert result.get("compounding_fee") is None


class TestCompoundingMatrixNewStates:
    def test_new_states_in_matrix(self):
        matrix = app_core.get_compounding_comparison_matrix()
        matrix_states = matrix.get("states", [])
        for state in NEW_COMPOUNDING_STATES:
            assert state in matrix_states, f"{state} not found in compounding matrix"

    def test_matrix_has_more_states_than_before(self):
        """Matrix should now have 13 states (was 8 before PR-B)."""
        matrix = app_core.get_compounding_comparison_matrix()
        assert len(matrix.get("states", [])) == 13

    def test_haryana_fee_in_no_helmet_row(self):
        matrix = app_core.get_compounding_comparison_matrix(violation_keys=["no_helmet"])
        rows = matrix.get("rows", [])
        assert rows, "no_helmet row missing from matrix"
        row = rows[0]
        assert row["state_fees"].get("Haryana") == 500

    def test_andhra_pradesh_in_matrix(self):
        matrix = app_core.get_compounding_comparison_matrix(violation_keys=["no_seatbelt"])
        rows = matrix.get("rows", [])
        row = next((r for r in rows if r["violation_key"] == "no_seatbelt"), None)
        assert row is not None
        assert "Andhra Pradesh" in row["state_fees"]
        assert row["state_fees"]["Andhra Pradesh"] == 500
