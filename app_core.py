"""Import-safe application core for DriveLegal India.

The Streamlit UI lives in app.py. This module owns data loading, validation,
and calculator behavior so it can be tested without rendering a Streamlit page.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"


class DataValidationError(ValueError):
    """Raised when the bundled offline data does not satisfy the schema."""


class CalculatorInputError(ValueError):
    """Raised when a calculator selection or quantity is invalid."""


def _read_json(filename: str) -> Any:
    path = DATA_DIR / filename
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise DataValidationError(f"Required offline data file is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DataValidationError(f"Offline data file is invalid JSON: {path}: {exc}") from exc


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise DataValidationError(message)


def validate_data(
    national_fines: dict[str, dict[str, Any]],
    vehicle_types: dict[str, float],
    state_data: dict[str, dict[str, Any]],
    metadata: dict[str, Any],
) -> None:
    """Validate the complete offline data package before the app renders."""
    required_fine_fields = {
        "description", "fine", "imprisonment", "rule_section", "penalty_section",
        "allowed_vehicle_types", "repeat_policy", "fine_basis", "apply_vehicle_multiplier",
        "source_status", "source_ids",
    }
    allowed_repeat_policies = {"toggle", "explicit", "not_applicable"}
    allowed_fine_bases = {"fixed", "per_excess_passenger", "base_plus_excess_tonne"}
    source_ids = {item.get("id") for item in metadata.get("sources", []) if isinstance(item, dict)}

    _require(isinstance(national_fines, dict) and national_fines, "national_fines must be a non-empty object")
    _require(isinstance(vehicle_types, dict) and vehicle_types, "vehicle_types must be a non-empty object")
    _require(isinstance(state_data, dict) and len(state_data) == 36, "state_data must contain 28 states and 8 Union Territories")
    _require(metadata.get("schema_version") == 2, "metadata schema_version must be 2")
    _require(bool(metadata.get("last_reviewed")), "metadata must include last_reviewed")
    _require(bool(source_ids), "metadata must contain at least one source")

    for vehicle, multiplier in vehicle_types.items():
        _require(isinstance(vehicle, str) and vehicle.strip(), "vehicle type names must be non-empty strings")
        _require(isinstance(multiplier, (int, float)) and 0 < multiplier <= 2, f"invalid multiplier for {vehicle}")

    for key, record in national_fines.items():
        _require(isinstance(record, dict), f"fine record {key} must be an object")
        missing = required_fine_fields - record.keys()
        _require(not missing, f"fine record {key} is missing fields: {sorted(missing)}")
        _require(isinstance(record["description"], str) and record["description"].strip(), f"fine description missing for {key}")
        _require(isinstance(record["fine"], (int, float)) and record["fine"] >= 0, f"invalid fine for {key}")
        _require(record["repeat_policy"] in allowed_repeat_policies, f"invalid repeat policy for {key}")
        _require(record["fine_basis"] in allowed_fine_bases, f"invalid fine basis for {key}")
        _require(isinstance(record["allowed_vehicle_types"], list) and record["allowed_vehicle_types"], f"vehicle applicability missing for {key}")
        _require(set(record["allowed_vehicle_types"]).issubset(vehicle_types), f"unknown vehicle type in {key}")
        _require(isinstance(record["source_ids"], list) and set(record["source_ids"]).issubset(source_ids), f"invalid source IDs for {key}")
        if record["repeat_policy"] == "explicit":
            _require("repeat_fine" in record and record["repeat_fine"] >= 0, f"explicit repeat fine missing for {key}")
        if record["fine_basis"] == "per_excess_passenger":
            _require(record.get("quantity_field") == "excess_passengers", f"passenger quantity field missing for {key}")
        if record["fine_basis"] == "base_plus_excess_tonne":
            _require(record.get("quantity_field") == "excess_tonnes", f"tonnage quantity field missing for {key}")
            _require(record.get("extra_unit_fine", 0) > 0, f"extra-tonne fine missing for {key}")

    required_state_fields = {"surcharge", "notes", "helmet_law", "speed_city", "speed_highway", "source_status", "source_ids", "legal_note"}
    for state, record in state_data.items():
        missing = required_state_fields - record.keys()
        _require(not missing, f"state record {state} is missing fields: {sorted(missing)}")
        _require(0 <= record["surcharge"] < 1, f"invalid surcharge for {state}")
        _require(0 < record["speed_city"] < record["speed_highway"] < 300, f"invalid speed limits for {state}")
        _require(isinstance(record["notes"], list) and record["notes"], f"notes missing for {state}")
        _require(set(record["source_ids"]).issubset(source_ids), f"invalid source IDs for {state}")

    descriptions = [record["description"] for record in national_fines.values()]
    _require(len(descriptions) == len(set(descriptions)), "violation descriptions must be unique for the selector")


def load_data() -> tuple[dict[str, Any], dict[str, float], dict[str, Any], dict[str, Any]]:
    national_fines = _read_json("national_fines.json")
    vehicle_types = _read_json("vehicle_types.json")
    state_data = _read_json("state_data.json")
    metadata = _read_json("metadata.json")
    validate_data(national_fines, vehicle_types, state_data, metadata)
    return national_fines, vehicle_types, state_data, metadata


NATIONAL_FINES, VEHICLE_TYPES, STATE_DATA, METADATA = load_data()
ALL_STATES = sorted(STATE_DATA)


def get_violation_options() -> dict[str, str]:
    return {record["description"]: key for key, record in NATIONAL_FINES.items()}


def get_allowed_vehicle_types(violation_key: str) -> list[str]:
    try:
        return NATIONAL_FINES[violation_key]["allowed_vehicle_types"]
    except KeyError as exc:
        raise CalculatorInputError(f"Unknown violation: {violation_key}") from exc


def _validate_quantity(record: dict[str, Any], quantity: float | int | None) -> float:
    basis = record["fine_basis"]
    if basis == "fixed":
        return 0.0
    if quantity is None:
        raise CalculatorInputError(f"{record['description']} requires a quantity")
    try:
        numeric = float(quantity)
    except (TypeError, ValueError) as exc:
        raise CalculatorInputError("Quantity must be numeric") from exc
    if numeric < 0:
        raise CalculatorInputError("Quantity cannot be negative")
    if basis == "per_excess_passenger" and not numeric.is_integer():
        raise CalculatorInputError("Excess passengers must be a whole number")
    if basis == "per_excess_passenger" and numeric < 1:
        raise CalculatorInputError("At least one excess passenger is required")
    if basis == "base_plus_excess_tonne" and numeric < 0:
        raise CalculatorInputError("Excess tonnes cannot be negative")
    return numeric


def calculate_fine(
    violation_key: str,
    vehicle_key: str,
    state: str,
    repeat: bool = False,
    quantity: float | int | None = None,
) -> dict[str, Any]:
    """Calculate a reference amount with explicit legal-data semantics.

    The bundled legal fine is not multiplied by vehicle type unless the data
    record explicitly opts in. Current legal records use vehicle type to filter
    applicability, not to invent a different statutory fine.
    """
    if violation_key not in NATIONAL_FINES:
        raise CalculatorInputError(f"Unknown violation: {violation_key}")
    if vehicle_key not in VEHICLE_TYPES:
        raise CalculatorInputError(f"Unknown vehicle type: {vehicle_key}")
    if state not in STATE_DATA:
        raise CalculatorInputError(f"Unknown state or Union Territory: {state}")

    record = NATIONAL_FINES[violation_key]
    allowed = record["allowed_vehicle_types"]
    if vehicle_key not in allowed:
        raise CalculatorInputError(f"{record['description']} is not applicable to {vehicle_key}")
    if record["repeat_policy"] == "not_applicable" and repeat:
        raise CalculatorInputError(f"Repeat-offence calculation is not available for {record['description']}")

    numeric_quantity = _validate_quantity(record, quantity)
    if record["fine_basis"] == "per_excess_passenger":
        reference_fine = record["fine"] * numeric_quantity
    elif record["fine_basis"] == "base_plus_excess_tonne":
        reference_fine = record["fine"] + record["extra_unit_fine"] * numeric_quantity
    else:
        reference_fine = record["fine"]

    repeat_penalty = 0.0
    applied_repeat_fine = None
    if repeat and record["repeat_policy"] == "explicit":
        applied_repeat_fine = record["repeat_fine"]
        reference_fine = applied_repeat_fine

    multiplier = VEHICLE_TYPES[vehicle_key] if record["apply_vehicle_multiplier"] else 1.0
    adjusted = reference_fine * multiplier
    if repeat and record["repeat_policy"] == "toggle":
        repeat_penalty = adjusted
    state_surcharge = adjusted * STATE_DATA[state]["surcharge"]
    total = round(adjusted + state_surcharge + repeat_penalty, 2)

    return {
        "base_fine": round(reference_fine, 2),
        "vehicle_adjustment": round(adjusted - reference_fine, 2),
        "vehicle_multiplier": multiplier,
        "vehicle_multiplier_applied": record["apply_vehicle_multiplier"],
        "state_surcharge": round(state_surcharge, 2),
        "repeat_penalty": round(repeat_penalty, 2),
        "total": total,
        "rule_section": record["rule_section"],
        "penalty_section": record["penalty_section"],
        "imprisonment": record["imprisonment"],
        "quantity": numeric_quantity,
        "repeat_applied": bool(repeat),
        "explicit_repeat_fine": applied_repeat_fine,
        "legal_note": record.get("legal_note"),
        "source_status": record["source_status"],
        "fine_basis": record["fine_basis"],
    }
