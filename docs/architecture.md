# Architecture & Code Overview

Project Layout

- `inventory_app/`: Application source code
  - `main.py`: Entry script for the GUI and initialization
  - `database/`: Schema, connection logic, and models
  - `gui/`: GUI components and pages by feature
    - `utils/`: Background processing utilities (workers, async table models)
  - `services/`: Business logic including stock movements, alerts, and validation
  - `utils/`: Logging, time utilities, and helpers

Database

- Uses SQLite with `schema.sql` containing tables: Items, Item_Batches, Stock_Movements, Requisitions, Requesters, Activity_Log and history tables. The schema can be inspected and extended at `inventory_app/database/schema.sql`.

Key Modules

- `inventory_app.database.connection`: Database connection, query execution, and schema initialization
- `inventory_app.gui.main_window`: The main GUI startup
- `inventory_app.gui.utils.worker`: Background threading utilities using QThreadPool
- `inventory_app.services.*`: Business logic for items, requisitions, requests, and movement

Initialization

- `main.py` calls `DatabaseConnection.create_database()` when the DB does not exist. It then verifies services and launches the GUI using PyQt6.

Background Processing

The application uses Qt's QThreadPool and QRunnable for background data loading to prevent UI freezes on slower hardware. Key components:

- `Worker`: General-purpose QRunnable for executing functions in background threads
- `DataLoadWorker`: Specialized worker for loading large datasets with batch emissions
- `WorkerPool`: Singleton manager for the global thread pool with configurable thread limits

Background processing is used in:

- Dashboard metrics loading (`metrics_worker.py`)
- Dashboard activity loading
- Dashboard alerts loading
- Inventory table data loading
- Requisition table data loading
- Requester table data loading
- Excel import operations
- Available items loading in requisition dialogs

The threading model follows Qt best practices:

- Workers emit signals with data to update the UI
- Main thread handles all GUI updates
- No blocking calls or `time.sleep()` in the main thread
- Thread count is capped (default: 4) to support older/weaker CPUs

Database features

- `DatabaseConnection.transaction(immediate=False)` — context manager for atomic multi-statement transactions used by core flows (e.g., `Item.save()`, requisition creation, deletion) to ensure atomicity and rollback on error. The `immediate=True` option will open an immediate transaction (`BEGIN IMMEDIATE`) which obtains a write lock early and is used in reservation flows to prevent concurrent oversubscription.
- `execute_update(..., return_last_id=True)` — returns `(affected_rows, last_insert_id)` for INSERTs so models can obtain the inserted row id from the same connection that performed the insert.
- `inventory_app.services.stock_calculation_service` — provides `stock_calculation_service`, a centralized service that exposes consistent SQL subqueries and helper methods for stock calculations (`get_stock_calculation_subquery`, `get_requisition_calculation_subquery`, `calculate_total_stock`, `calculate_batch_stock`). Use this service instead of duplicating stock SQL logic across modules to ensure consistency and correctness.
- `inventory_app.database.query_cache` — introduces a TTL-based `QueryCache` and `cached_query(ttl=..., query_name="")` decorator for caching expensive database queries. The global `db` instance exposes `clear_query_cache()` and `invalidate_cache_for_table(table_name)` to control cache state after writes that affect query results.
- `MovementType` enum (`inventory_app/services/movement_types.py`) defines allowed stock movement types (CONSUMPTION, RESERVATION, RETURN, DISPOSAL, REQUEST); the schema enforces allowed values via a `CHECK` constraint on `Stock_Movements(movement_type)`.
- Schema constraints: `ON DELETE CASCADE` is used on relevant foreign keys (e.g., batches, movements, requisition items) and indexes such as `idx_movements_item_date` and `idx_movements_source` are present to improve query performance and referential integrity.
