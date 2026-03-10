# Development Guide

## Local Setup

```powershell
python -m venv .venv
& .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Run app:

```powershell
python -m inventory_app.main
```

## Run Tests

```powershell
python -m pytest -q
```

Tests include backend and GUI flows (`pytest-qt`).

## Project Layout for Contributors

- `inventory_app/gui`: UI pages and widgets
- `inventory_app/services`: business logic
- `inventory_app/database`: schema, models, connection, migrations
- `tests`: unit/integration tests
- `docs`: project documentation

## Contributor Rules

- Put business rules in `services`, not in UI widgets.
- Keep data writes wrapped in transactions when a flow has multiple steps.
- Update docs when behavior changes.
- Add or update tests for changed logic.

## Database Changes

If you add or change fields:

1. Update `inventory_app/database/schema.sql`.
2. Add a numbered migration in `inventory_app/database/migrations` as needed.
3. Keep `001_baseline_schema.py` as the baseline marker; new migrations should start at `002_*`.
4. Update affected models/services/tests.
5. Update docs that describe the changed behavior.

## Debugging

- Use `inventory_app/utils/logger.py` output first.
- Reproduce with small datasets, then test with `scripts/sample_data.py`.

## Packaging

PyInstaller is used for desktop builds.
Build outputs are under `build/`.
