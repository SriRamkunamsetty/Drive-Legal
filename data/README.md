# DriveLegal India — Data Layer

This directory contains the structured, offline-embedded data for DriveLegal
India. All data files are **JSON**, load directly from disk by `app.py`, and
require **no external APIs or internet connection** at runtime.

## Files

| File | Contents |
|------|----------|
| `national_fines.json` | National fine schedule per violation — fine amount, possible imprisonment, and MV Act section (Motor Vehicles Amendment Act 2019) |
| `vehicle_types.json` | Vehicle categories and their fine multipliers (0.5 – 2.0) |
| `state_data.json` | State / UT-specific surcharges, city & highway speed limits, helmet law, and enforcement notes for all 28 states and 8 UTs |

## How the app loads the data

`app.py` reads these files at import time from `_DATA_DIR = pathlib.Path(__file__).parent / "data"` and populates `NATIONAL_FINES`, `VEHICLE_TYPES`, and `STATE_DATA`. The rest of the application logic (challan calculator, UI) is unchanged.

## Adding or editing data

1. Edit the relevant JSON file (keep the existing key structure — other files and `app.py` depend on it).
2. Keep fines consistent with the **Motor Vehicles Amendment Act 2019** and cite the section.
3. Keep states/UTs in the official naming used in `state_data.json` (36 entries: 28 states + 8 UTs).
4. Run `pytest` (or the bundled tests) to verify the calculator still produces correct totals.

## Sources

- Motor Vehicles Act, 1988
- Motor Vehicles (Amendment) Act, 2019
- MoRTH speed-limit notifications
- State Transport Department rules (surcharges, local enforcement notes)
