# Contributing to DriveLegal India

Thank you for contributing to DriveLegal India. The project is an offline informational reference, so correctness, provenance, and clear limitations are more important than adding unsupported data quickly.

## Workflow

Start by checking the open issues. For a new defect or data request, create an issue describing the observed behavior, the expected behavior, and the source or notification that supports the change. Create a focused branch such as `fix/section-mapping` or `feat/state-source-metadata`.

Keep runtime behavior offline. Do not add remote images, API calls, telemetry, or data downloads. If an asset is needed, include it in the repository and test the application with network access disabled.

## Legal-data changes

Use the central Act text and the applicable state or local notification. Record both `rule_section` and `penalty_section` when they differ. Add source identifiers, a review date or effective date where available, and mark values `reference_only` when they require state-notification verification. Do not turn a maximum or reference amount into an “exact challan” claim.

For quantity-based offences, use the supported `fine_basis` values and add the required quantity field. Do not use vehicle multipliers to invent a statutory amount. Vehicle multipliers are permitted only when a data record explicitly opts in and has a supporting source.

## Tests and checks

Install development dependencies and run the checks before opening a pull request:

```bash
pip install -r requirements-dev.txt
pytest -q
python -m py_compile app.py app_core.py
python -m json.tool data/national_fines.json >/dev/null
python -m json.tool data/vehicle_types.json >/dev/null
python -m json.tool data/state_data.json >/dev/null
python -m json.tool data/metadata.json >/dev/null
```

Add tests for new calculator behavior, invalid inputs, rounding, and schema fields. The core module must remain import-safe without starting a Streamlit server.

## Pull requests

Explain the user-visible and data-model changes, list the verification commands, link the issue with a closing keyword when appropriate, and call out any legal or notification uncertainty. Keep unrelated refactors out of focused fixes.
