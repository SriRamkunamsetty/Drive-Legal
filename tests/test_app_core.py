"""Tests for the import-safe DriveLegal calculator core."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app_core import (
    ALL_STATES,
    METADATA,
    NATIONAL_FINES,
    STATE_DATA,
    VEHICLE_TYPES,
    CalculatorInputError,
    DataValidationError,
    calculate_fine,
    get_allowed_vehicle_types,
    get_source_details,
    get_violation_options,
    validate_data,
)


ROOT = Path(__file__).resolve().parent.parent


def test_complete_data_package_is_loaded_from_local_files():
    assert len(NATIONAL_FINES) == 19
    assert len(VEHICLE_TYPES) == 7
    assert len(STATE_DATA) == 36
    assert ALL_STATES == sorted(STATE_DATA)
    for filename, expected in (
        ("national_fines.json", NATIONAL_FINES),
        ("vehicle_types.json", VEHICLE_TYPES),
        ("state_data.json", STATE_DATA),
    ):
        assert json.loads((ROOT / "data" / filename).read_text(encoding="utf-8")) == expected


def test_every_fine_record_has_required_schema():
    for record in NATIONAL_FINES.values():
        assert record["description"]
        assert record["fine"] >= 0
        assert record["rule_section"]
        assert record["penalty_section"]
        assert record["allowed_vehicle_types"]
        assert set(record["allowed_vehicle_types"]).issubset(VEHICLE_TYPES)
        assert record["source_ids"]
        assert record["legal_note"]
        assert record["fine_basis"] in {"fixed", "per_excess_passenger", "base_plus_excess_tonne"}


def test_all_state_records_have_expected_shape():
    assert set(STATE_DATA) == set(ALL_STATES)
    for state, info in STATE_DATA.items():
        assert 0 <= info["surcharge"] < 1
        assert 0 < info["speed_city"] < info["speed_highway"] < 300
        assert info["notes"]
        assert info["source_status"] == "reference_only"


def test_source_ids_resolve_to_display_ready_metadata():
    sources = get_source_details(["mva1988", "mva2019"])
    assert [source["id"] for source in sources] == ["mva1988", "mva2019"]
    assert all(source["title"] and source["url"].startswith("https://") for source in sources)


def test_unknown_source_ids_are_rejected():
    with pytest.raises(DataValidationError, match="Unknown source IDs"):
        get_source_details(["not-in-metadata"])


def test_calculation_result_includes_resolved_sources():
    result = calculate_fine("signal_jump", "Light Motor Vehicle (Car)", "Delhi")
    assert result["source_ids"] == ["mva1988", "mva2019"]
    assert [source["id"] for source in result["sources"]] == result["source_ids"]
    assert all(source["url"].startswith("https://") for source in result["sources"])


def test_red_light_uses_rule_section_119_and_penalty_section_184():
    record = NATIONAL_FINES["signal_jump"]
    assert record["rule_section"] == "119"
    assert record["penalty_section"] == "184"
    assert record["imprisonment"] == "Up to 1 year (or fine, or both)"
    result = calculate_fine("signal_jump", "Light Motor Vehicle (Car)", "Delhi")
    assert result["rule_section"] == "119"
    assert result["penalty_section"] == "184"
    assert result["total"] == 5000


def test_all_national_records_have_record_level_legal_notes():
    assert all(record["legal_note"].strip() for record in NATIONAL_FINES.values())


def test_overloading_goods_is_quantity_based_and_not_multiplied_by_vehicle_type():
    result = calculate_fine("overloading_goods", "Heavy Motor Vehicle", "Delhi", quantity=1.5)
    assert result["base_fine"] == 23000
    assert result["total"] == 23000
    assert result["fine_basis"] == "base_plus_excess_tonne"
    assert result["vehicle_multiplier_applied"] is False


def test_overloading_passengers_is_per_excess_passenger():
    result = calculate_fine("overloading_passenger", "Transport / Commercial", "Delhi", quantity=3)
    assert result["base_fine"] == 600
    assert result["total"] == 600
    assert result["fine_basis"] == "per_excess_passenger"


def test_explicit_drunk_driving_repeat_rate_is_not_doubled_again():
    result = calculate_fine("drunk_driving", "Light Motor Vehicle (Car)", "Delhi", repeat=True)
    assert result["base_fine"] == 15000
    assert result["repeat_penalty"] == 0
    assert result["total"] == 15000
    assert result["explicit_repeat_fine"] == 15000


def test_generic_repeat_policy_doubles_reference_amount():
    first = calculate_fine("signal_jump", "Light Motor Vehicle (Car)", "Goa", repeat=False)
    repeat = calculate_fine("signal_jump", "Light Motor Vehicle (Car)", "Goa", repeat=True)
    assert first["total"] == 5500
    assert repeat["repeat_penalty"] == 5000
    assert repeat["total"] == 10500


def test_state_surcharge_is_rounded_to_two_decimal_places():
    result = calculate_fine("no_parking", "Two-Wheeler (≤ 50cc)", "Kerala")
    assert result["base_fine"] == 500
    assert result["state_surcharge"] == 25
    assert result["total"] == 525
    assert isinstance(result["total"], float)
    assert round(result["total"], 2) == result["total"]


def test_invalid_vehicle_and_violation_combinations_are_rejected():
    assert "Light Motor Vehicle (Car)" not in get_allowed_vehicle_types("no_helmet")
    with pytest.raises(CalculatorInputError, match="not applicable"):
        calculate_fine("no_helmet", "Light Motor Vehicle (Car)", "Delhi")
    with pytest.raises(CalculatorInputError, match="not applicable"):
        calculate_fine("overloading_goods", "Two-Wheeler (> 50cc)", "Delhi", quantity=1)


def test_quantity_validation_is_strict():
    with pytest.raises(CalculatorInputError, match="requires a quantity"):
        calculate_fine("overloading_goods", "Heavy Motor Vehicle", "Delhi")
    with pytest.raises(CalculatorInputError, match="whole number"):
        calculate_fine("overloading_passenger", "Transport / Commercial", "Delhi", quantity=1.5)
    with pytest.raises(CalculatorInputError, match="cannot be negative"):
        calculate_fine("overloading_goods", "Heavy Motor Vehicle", "Delhi", quantity=-1)


def test_non_finite_quantities_are_rejected():
    for quantity in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(CalculatorInputError, match="finite"):
            calculate_fine("overloading_goods", "Heavy Motor Vehicle", "Delhi", quantity=quantity)


def test_boolean_quantities_are_rejected():
    with pytest.raises(CalculatorInputError, match="not Boolean"):
        calculate_fine("overloading_passenger", "Transport / Commercial", "Delhi", quantity=True)


def test_fixed_records_reject_repeat_toggle_when_not_applicable():
    with pytest.raises(CalculatorInputError, match="not available"):
        calculate_fine("no_helmet", "Two-Wheeler (> 50cc)", "Delhi", repeat=True)


def test_violation_labels_are_unique_and_round_trip():
    options = get_violation_options()
    assert len(options) == len(NATIONAL_FINES)
    assert set(options.values()) == set(NATIONAL_FINES)


def test_validation_rejects_invalid_metadata_and_state_count():
    with pytest.raises(DataValidationError):
        validate_data(NATIONAL_FINES, VEHICLE_TYPES, {"Delhi": STATE_DATA["Delhi"]}, METADATA)


def test_validation_rejects_incomplete_source_metadata():
    metadata = {**METADATA, "sources": [{"id": "mva1988", "title": "Missing URL"}]}
    with pytest.raises(DataValidationError, match="metadata source field missing: url"):
        validate_data(NATIONAL_FINES, VEHICLE_TYPES, STATE_DATA, metadata)


def test_validation_rejects_missing_legal_notes():
    fines = {**NATIONAL_FINES, "bad": {**NATIONAL_FINES["no_parking"]}}
    del fines["bad"]["legal_note"]
    with pytest.raises(DataValidationError, match="missing fields"):
        validate_data(fines, VEHICLE_TYPES, STATE_DATA, METADATA)


def test_validation_rejects_non_finite_fines_and_boolean_multipliers():
    fines = {**NATIONAL_FINES, "bad": {**NATIONAL_FINES["no_parking"], "fine": float("inf")}}
    with pytest.raises(DataValidationError, match="invalid fine"):
        validate_data(fines, VEHICLE_TYPES, STATE_DATA, METADATA)

    vehicles = {**VEHICLE_TYPES, "Bad vehicle": True}
    with pytest.raises(DataValidationError, match="invalid multiplier"):
        validate_data(NATIONAL_FINES, vehicles, STATE_DATA, METADATA)


def test_validation_rejects_empty_sources_and_unexpected_locations():
    fines = {**NATIONAL_FINES, "bad": {**NATIONAL_FINES["no_parking"], "source_ids": []}}
    with pytest.raises(DataValidationError, match="invalid source IDs"):
        validate_data(fines, VEHICLE_TYPES, STATE_DATA, METADATA)

    states = {**STATE_DATA}
    states["Not a location"] = states.pop("Delhi")
    with pytest.raises(DataValidationError, match="expected 28 states"):
        validate_data(NATIONAL_FINES, VEHICLE_TYPES, states, METADATA)


def test_validation_rejects_malformed_state_record():
    states = {**STATE_DATA, "Delhi": None}
    with pytest.raises(DataValidationError, match="state record Delhi must be an object"):
        validate_data(NATIONAL_FINES, VEHICLE_TYPES, states, METADATA)


def test_calculator_rejects_non_boolean_repeat_and_fixed_quantities():
    with pytest.raises(CalculatorInputError, match="Repeat must be Boolean"):
        calculate_fine("signal_jump", "Light Motor Vehicle (Car)", "Delhi", repeat="false")
    with pytest.raises(CalculatorInputError, match="does not accept a quantity"):
        calculate_fine("no_parking", "Light Motor Vehicle (Car)", "Delhi", quantity=float("nan"))
