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
