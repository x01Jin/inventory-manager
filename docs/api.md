# Services Reference

This project does not expose a public HTTP API.
When this document says "API", it means internal Python services used by the GUI.

## Database Layer

- `inventory_app.database.connection.DatabaseConnection`
- Main helper methods: `execute_query`, `execute_update`, `execute_script`, `transaction`
- Default DB file: `inventory.db`

Use `transaction()` for multi-step writes so changes commit together or roll back together.

## Main Services

- `inventory_app.services.item_service`
Purpose: item lookup and stock-related item operations.

- `inventory_app.services.requisition_service.RequisitionService`
Purpose: create requisitions, update status, and process returns.

- `inventory_app.services.stock_movement_service.StockMovementService`
Purpose: maintain stock movement records (consume, reserve, return, dispose, request).

- `inventory_app.services.alert_engine`
Purpose: compute dashboard alerts (low stock, expiry, calibration).

- `inventory_app.services.summary_tables`
Purpose: maintain denormalized summary tables for fast dashboard/report reads.

- `inventory_app.services.validation_service`
Purpose: centralized payload validation helpers.

## Shared Domain Enum

- `inventory_app.services.movement_types.MovementType`
Valid movement types:

- `CONSUMPTION`
- `RESERVATION`
- `RETURN`
- `DISPOSAL`
- `REQUEST`

The schema enforces valid movement values through a `CHECK` constraint.

## GUI to Service Contract

GUI modules should call services for business actions instead of writing SQL directly.
This keeps business behavior in one place and reduces duplicated logic.

## Maintenance Utility

- `scripts/maintenance.py`
Purpose: prune old activity records and keep activity table size bounded.
