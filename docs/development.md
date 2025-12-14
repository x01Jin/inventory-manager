# Development Guide

Running Tests

- Test helper scripts are available in the `tests/` folder. They help populate sample items, requesters and requisitions for test and profiling.

Contributing

- Follow the repository style. Open a PR with a description of changes, update docs and add tests for features where appropriate.

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
