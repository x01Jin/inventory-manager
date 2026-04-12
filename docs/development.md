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
- Run heavy GUI-triggered work (report generation, export, large refreshes) in background workers to keep the main window responsive.

## Database Changes

If you add or change fields:

1. Update `inventory_app/database/schema.sql`.
2. Add a numbered migration in `inventory_app/database/migrations` as needed.
3. Keep `001_baseline_schema.py` as the baseline marker; new migrations should start at `002_*`.
4. Update affected models/services/tests.
5. Update docs that describe the changed behavior.

## Debugging

- Use `inventory_app/utils/logger.py` output first.
- Reproduce with small datasets, then run deterministic procedural dataset generation with `python scripts/sample_data.py --start 4/12/2023 --end 4/12/2026`.
- Startup summary backfill runs asynchronously after summary service initialization; check logs for `Background summary backfill` if startup feels slow.
- Reference normalization runs asynchronously at startup; check logs for `reference-normalization` if startup verification is needed.

## GUI Performance Rules

- Keep startup interactive: only dashboard is created eagerly in `MainWindow`; other pages are lazily instantiated on first navigation.
- Do not query database from filter widgets directly. Load data in page-level background tasks, then apply UI updates in callbacks.
- Requisition dialog item loading is two-stage: fetch in background, preprocess availability in background, then batch-render on UI thread.
- Requisitions table refresh uses incremental append batches; avoid full-table rebuild in each progress step.
- Dashboard schedule data is fetched in a worker thread; UI thread should only render already-loaded rows.
- For large list filtering in dialogs, batch updates and minimize repaint frequency (`setUpdatesEnabled(False/True)` around batch updates).

## Packaging

PyInstaller is used for desktop builds.
Build outputs are under `build/`.
