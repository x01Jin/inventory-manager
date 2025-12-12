# API & Services

This section documents the primary services and interfaces used throughout the Inventory Manager.

Database

- `inventory_app.database.connection.DatabaseConnection` — context-managed SQLite connection with query helpers: `execute_query`, `execute_update`, `execute_script`. Use `execute_update(..., return_last_id=True)` to obtain `lastrowid` from the same connection used for the INSERT.
- `DatabaseConnection.transaction()` — context manager for atomic multi-step DB operations (used in `Item.save()`, requisition creation and deletion flows).

Services

- `inventory_app.services.item_service` — operations related to item creation, editing, searching and stock aggregation.
- `inventory_app.services.movement_types.MovementType` — the canonical enum of movement types (CONSUMPTION, RESERVATION, RETURN, DISPOSAL, REQUEST, LOST). Services, GUI and models should use this enum to avoid divergent string values and the DB schema enforces valid values via a `CHECK` constraint.
- `inventory_app.services.stock_movement_service` — creates/updates `Stock_Movements` records and reconciles item quantities.
- `inventory_app.services.requesters_activity` — logs and manages requester activities and audit trail.
- `inventory_app.services.requisition_activity` — handles requisition lifecycle (request, active, return) and related stock reservations.
- `inventory_app.services.alert_engine` — computes expiration, low stock, and calibration alerts for dashboard viewing.

GUI Interfaces

- GUI modules primarily live under `inventory_app.gui.*` and expose controllers and models which call into the `services` layer.

Best Practices

- All data operations are handled through service layers rather than direct DB calls from GUI modules.
- Editor names must be provided for operations that modify persistent data for auditability.
