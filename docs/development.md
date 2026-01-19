# Development Guide

Running Tests

- Tests are run with `pytest`. Ensure you have the project's virtual environment active and run:

```powershell
python -m pytest -q
```

- The test suite includes GUI tests (`pytest-qt`) and DB-related tests. Many tests create temporary DBs or use fixtures to avoid altering your working database.

Seeding sample data for manual QA

- Use `scripts/sample_data.py` to generate a realistic dataset useful for manual QA and demonstrations:

```powershell
python scripts/sample_data.py
```

- This script creates the database (if absent) and populates items, requesters, requisitions and activity logs over a simulated timeline.

Contributing

- Follow the repository style. Open a PR with a description of changes, update docs and add tests for features where appropriate. Run the full test suite before submitting a PR and ensure new tests cover added functionality.

Debugging

- Use the logger in `inventory_app/utils/logger.py` and run with a console to capture the output.

Packaging

- Use `PyInstaller` to package the GUI into an executable. The existing `build/` folder contains artifacts and references to build processes.

Notes on Schema Changes

- For schema updates, update `inventory_app/database/schema.sql` and add migrations to populate or alter fields if required.
- Constraints and indices improve integrity and performance: a `CHECK` constraint on `Stock_Movements(movement_type)` (driven by the `MovementType` enum), `ON DELETE CASCADE` for several foreign keys, and `idx_movements_source` to speed up lookup and deletes by `source_id`.

- Use `DatabaseConnection.transaction()` for multi-step flows to ensure atomic behavior and rollback on error; unit tests validate commit/rollback semantics.
- Use `execute_update(..., return_last_id=True)` to reliably obtain last insert ids for new records and avoid cross-connection `last_insert_rowid()` usage.
- Unit tests cover concurrency, transaction handling, and the movement type enum.

Background Processing Guidelines

When adding new data-intensive features, use the background processing utilities in `inventory_app/gui/utils/`:

```python
from inventory_app.gui.utils.worker import run_in_background, Worker

# Simple background task
worker = run_in_background(
    heavy_function,
    arg1, arg2,
    on_result=self._on_data_loaded,
    on_error=self._on_error,
    on_finished=self._on_finished,
)

# For batch data loading
from inventory_app.gui.utils.worker import load_data_in_background

worker = load_data_in_background(
    load_function,
    batch_size=50,
    on_batch=self._on_batch_ready,
    on_complete=self._on_complete,
)
```

Threading rules:

- Use `QThreadPool` and `QRunnable` (via the `Worker` class), not Python's `threading` module
- Never use `time.sleep()` or blocking calls in the main thread
- Emit signals with data to update UI; never modify Qt widgets from worker threads
- Use `beginInsertRows`/`endInsertRows` pattern when updating table models
- Keep worker thread count limited for older hardware compatibility
