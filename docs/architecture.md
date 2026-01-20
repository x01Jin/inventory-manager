# Architecture & Code Overview

## Project Layout

- `inventory_app/`: Application source code
  - `main.py`: Entry script for the GUI and initialization
  - `database/`: Schema, connection logic, and models
  - `gui/`: GUI components and pages by feature
    - `utils/`: Background processing utilities (workers, async table models, virtual scrolling)
  - `services/`: Business logic including stock movements, alerts, validation, and summary tables
  - `utils/`: Logging, time utilities, and helpers

## Database

- Uses SQLite with `schema.sql` containing tables: Items, Item_Batches, Stock_Movements, Requisitions, Requesters, Activity_Log, and history tables. The schema can be inspected and extended at `inventory_app/database/schema.sql`.
- Summary tables for performance: Stock_Summary, Requisition_Summary, Statistics_Aggregate
- Database migrations in `inventory_app/database/migrations/` for schema updates

## Key Modules

- `inventory_app.database.connection`: Database connection, query execution, and schema initialization
- `inventory_app.database.migrations`: Migration manager for automatic schema updates
- `inventory_app.gui.main_window`: The main GUI startup
- `inventory_app.gui.utils.worker`: Background threading utilities using QThreadPool
- `inventory_app.services.*`: Business logic for items, requisitions, requests, movement, and summary tables
- `inventory_app.services.stock_calculation_service`: Centralized stock calculations
- `inventory_app.services.summary_tables`: Pre-computed summary tables for instant statistics

## Initialization

- `main.py` calls `DatabaseConnection.create_database()` when the DB does not exist. It then verifies services and launches the GUI using PyQt6.
- Summary tables service is initialized and backfilled on startup

## Background Processing

The application uses Qt's QThreadPool and QRunnable for background data loading to prevent UI freezes on slower hardware. Key components:

- `Worker`: General-purpose QRunnable for executing functions in background threads (`inventory_app/gui/utils/worker.py`)
- `DataLoadWorker`: Specialized worker for loading large datasets with batch emissions (`inventory_app/gui/utils/worker.py`)
- `WorkerPool`: Singleton manager for the global thread pool with configurable thread limits (`inventory_app/gui/utils/worker.py`)
- `ParallelLoader`: Concurrent loading of inventory and requisition data (`inventory_app/gui/utils/parallel_loader.py`)
- `MultiprocessingManager`: Process pool for CPU-intensive operations (Windows-compatible with 'spawn' context) (`inventory_app/gui/utils/multiprocess_manager.py`)

Background processing is used in:

- Dashboard metrics loading (`metrics_worker.py`)
- Dashboard activity loading
- Dashboard alerts loading
- Inventory table data loading (with parallel loading)
- Requisition table data loading (with parallel loading)
- Requester table data loading
- Excel import operations
- Available items loading in requisition dialogs
- Large query processing via multiprocessing

The threading model follows Qt best practices:

- Workers emit signals with data to update the UI
- Main thread handles all GUI updates
- No blocking calls or `time.sleep()` in the main thread
- Thread count is capped (default: 4) to support older/weaker CPUs

## Performance Optimizations

### Query Caching

- `inventory_app.database.query_cache` — TTL-based `QueryCache` and `cached_query(ttl=..., query_name="")` decorator for caching expensive database queries
- Multi-level TTL strategy: 10s for inventory, 60s for reference data, 30s for statistics
- Automatic cache invalidation on INSERT/UPDATE/DELETE
- Global `db` instance exposes `clear_query_cache()` and `invalidate_cache_for_table(table_name)`

### Batched Status Queries

- `item_status_service.get_statuses_for_items(item_ids)` — Batch status calculation in O(1) queries
- Eliminates N+1 query pattern during table population
- SQLite parameter chunking (500 IDs per batch)

Virtual Scrolling

- `VirtualTableModel` for handling thousands of rows with constant memory (`inventory_app/gui/utils/virtual_table_model.py`)
- LRU cache for row data (500 rows max)
- Progressive loading via `fetchMore()`
- Scroll-optimized prefetching (50 rows above, 100 rows below visible area)

Async Table Loading

- `AsyncTableModel` and `AsyncTableController` for background data loading in PyQt6 tables (`inventory_app/gui/utils/async_table.py`)
- Uses QThreadPool for thread-safe table updates
- Implements `beginInsertRows`/`endInsertRows` pattern for efficient row updates

Summary Tables

- `summary_tables_service` — Pre-computed statistics via `Stock_Summary`, `Requisition_Summary`, and `Statistics_Aggregate` tables
- Automatic updates via database triggers
- Background refresh thread (60-second interval)
- Instant dashboard statistics

Batch Processing

- Adaptive batch sizing for data loading, table population, and styling
- Strategic `processEvents()` calls for UI responsiveness
- Pre-allocation strategies for memory efficiency

Database features

- `DatabaseConnection.transaction(immediate=False)` — context manager for atomic multi-statement transactions used by core flows (e.g., `Item.save()`, requisition creation, deletion) to ensure atomicity and rollback on error. The `immediate=True` option will open an immediate transaction (`BEGIN IMMEDIATE`) which obtains a write lock early and is used in reservation flows to prevent concurrent oversubscription.
- `execute_update(..., return_last_id=True)` — returns `(affected_rows, last_insert_id)` for INSERTs so models can obtain the inserted row id from the same connection that performed the insert.
- `inventory_app.services.stock_calculation_service` — provides `stock_calculation_service`, a centralized service that exposes consistent SQL subqueries and helper methods for stock calculations (`get_stock_calculation_subquery`, `get_requisition_calculation_subquery`, `calculate_total_stock`, `calculate_batch_stock`). Use this service instead of duplicating stock SQL logic across modules to ensure consistency and correctness.
- `inventory_app.database.query_cache` — introduces a TTL-based `QueryCache` and `cached_query(ttl=..., query_name="")` decorator for caching expensive database queries. The global `db` instance exposes `clear_query_cache()` and `invalidate_cache_for_table(table_name)` to control cache state after writes that affect query results.
- `MovementType` enum (`inventory_app/services/movement_types.py`) defines allowed stock movement types (CONSUMPTION, RESERVATION, RETURN, DISPOSAL, REQUEST); the schema enforces allowed values via a `CHECK` constraint on `Stock_Movements(movement_type)`.
- Schema constraints: `ON DELETE CASCADE` is used on relevant foreign keys (e.g., batches, movements, requisition items) and indexes such as `idx_movements_item_date` and `idx_movements_source` are present to improve query performance and referential integrity.

## Database Migrations

The application uses a migration-based schema update system that runs automatically on startup.

### How Migrations Work

1. On startup, MigrationManager checks the `Schema_Versions` table
2. Compares applied migrations against available migration scripts in `inventory_app/database/migrations/`
3. Applies any pending migrations automatically
4. No user intervention required

### Migration Files

Migration scripts are located in `inventory_app/database/migrations/`:

- Named sequentially: `001_*.py`, `002_*.py`, etc.
- Each migration has an `up()` function that applies schema changes
- Migrations are idempotent - checking before applying changes
- Migration metadata stored in `Schema_Versions` table

### No Data Loss

Migrations only add columns or tables - they never delete or modify existing data. If a column already exists, the migration skips it safely.

### Troubleshooting

If a migration fails, check application logs for error details. Common issues:

- Database file locked by another process
- Insufficient file permissions
- Corrupted database file
