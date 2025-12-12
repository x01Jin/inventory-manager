# Architecture & Code Overview

Project Layout

- `inventory_app/`: Application source code
  - `main.py`: Entry script for the GUI and initialization
  - `database/`: Schema, connection logic, and models
  - `gui/`: GUI components and pages by feature
  - `services/`: Business logic including stock movements, alerts, and validation
  - `utils/`: Logging, time utilities, and helpers

Database

- Uses SQLite with `schema.sql` containing tables: Items, Item_Batches, Stock_Movements, Requisitions, Requesters, Activity_Log and history tables. The schema can be inspected and extended at `inventory_app/database/schema.sql`.

Key Modules

- `inventory_app.database.connection`: Database connection, query execution, and schema initialization
- `inventory_app.gui.main_window`: The main GUI startup
- `inventory_app.services.*`: Business logic for items, requisitions, requests, and movement

Initialization

- `main.py` calls `DatabaseConnection.create_database()` when the DB does not exist. It then verifies services and launches the GUI using PyQt6.

Database features

- `DatabaseConnection.transaction(immediate=False)` — context manager for atomic multi-statement transactions used by core flows (e.g., `Item.save()`, requisition creation, deletion) to ensure atomicity and rollback on error.
- `execute_update(..., return_last_id=True)` — returns `(affected_rows, last_insert_id)` for INSERTs so models can obtain the inserted row id from the same connection that performed the insert.
- `MovementType` enum (`inventory_app/services/movement_types.py`) defines allowed stock movement types (CONSUMPTION, RESERVATION, RETURN, DISPOSAL, REQUEST, LOST); the schema enforces allowed values via a `CHECK` constraint on `Stock_Movements(movement_type)`.
- Schema constraints: `ON DELETE CASCADE` is used on relevant foreign keys (e.g., batches, movements, requisition items) and indexes such as `idx_movements_item_date` and `idx_movements_source` are present to improve query performance and referential integrity.
