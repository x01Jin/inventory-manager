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
- For stock logic, prefer `inventory_app.services.stock_calculation_service.StockCalculationService` (`stock_calculation_service`) to produce consistent SQL fragments and helper methods (e.g., `get_stock_calculation_subquery`, `get_requisition_calculation_subquery`, `calculate_total_stock`) rather than duplicating SQL across modules. This improves maintainability and reduces the risk of subtle calculation differences.
- For expensive or frequently-run queries (e.g., selection lists, metrics), consider using the `cached_query` decorator or `QueryCache` directly to improve UI responsiveness. When writing cache-affecting changes (inserts/updates/deletes), call `db.invalidate_cache_for_table(table_name)` or `db.clear_query_cache()` to ensure cached results are up-to-date.
- Unit tests cover concurrency, transaction handling, the `StockCalculationService`, and caching behavior; add tests when introducing logic that affects stock calculations or cache invalidation.

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
