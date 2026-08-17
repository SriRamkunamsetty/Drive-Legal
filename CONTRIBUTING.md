# Contributing to DriveLegal India

Thank you for your interest in contributing to DriveLegal India — a fully
offline, location-specific traffic law and challan calculator covering all
28 states and 8 Union Territories of India. Contributions are welcome from
everyone, including first-time open-source contributors.

## How to Contribute

### 1. Find or create an issue

- Check the open [Issues](https://github.com/mudit108-code/Drive-Legal/issues)
  for something to work on.
- If you find a bug or have an idea that is not listed, open a new issue
  describing it before starting work. Discussing first avoids duplicated effort.

### 2. Fork and clone

```bash
gh repo fork mudit108-code/Drive-Legal --clone=true
cd Drive-Legal
```

### 3. Create a feature branch

Use a short, descriptive branch name:

```bash
git checkout -b fix/<short-description>
# or
git checkout -b feat/<short-description>
```

### 4. Make your changes

- Keep the project **fully offline** — no external API calls may be added.
- If you change fine amounts or sections, verify them against the
  **Motor Vehicles Act 1988** and the **Motor Vehicles (Amendment) Act 2019**
  and cite the section.
- If you change data, update the JSON files under `data/` (and the matching
  hardcoded lists in `app.py` if present), not just one of the two.
- Add or update tests under `tests/` when changing `calculate_fine` or the
  data schemas.

### 5. Test your changes

```bash
pip install -r requirements.txt pytest
python3 -m pytest tests/
```

All tests must pass before you open a pull request.

### 6. Commit and push

Write a clear commit message describing what changed and why:

```bash
git add .
git commit -m "Brief description of the change"
git push -u origin HEAD
```

### 7. Open a pull request

- Open a PR from your branch into `main` of the upstream repository.
- In the PR description, include:
  - A short summary of the work done
  - The issue number solved (e.g., `Fixes Issue #15`) — use a
    [closing keyword](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue)
    so the issue closes automatically on merge
- Wait for review; address any requested changes and keep the discussion polite.

## Project Conventions

| Area | Convention |
|------|------------|
| Language | Python 3.10+ |
| UI framework | Streamlit (`streamlit run app.py`) |
| Data format | JSON under `data/` (embedded, no network access) |
| Testing | `pytest` under `tests/` |
| Commit style | Short imperative summary, e.g. "Add Kerala school-zone speed limits" |

## Code of Conduct

Be respectful and constructive. Harassment or discriminatory behaviour will
not be tolerated.

## Questions?

Open an issue and ask — the maintainers are happy to help.
