# System Overview

## What This App Is

Inventory Manager is a local desktop application built with PyQt6.
It helps a laboratory team track:

- Inventory items and stock changes
- Requisitions (item requests and returns)
- Requesters (who requested what)
- Reports for auditing and planning

## High-Level Structure

Main source code is in `inventory_app/`.

- `main.py`: startup and app bootstrap
- `database/`: schema, DB connection, models, migration manager, query cache
- `gui/`: all desktop UI pages and widgets
- `services/`: business rules and stock/requisition workflows
- `utils/`: logging and utility helpers

## How Data Moves Through the App

1. User action happens in the GUI.
2. GUI calls a service function.
3. Service reads/writes SQLite through the database layer.
4. Results return to the GUI for display.

This separation makes the app easier to test and safer to evolve.

## Startup Flow

When you run `python -m inventory_app.main`:

1. The app checks whether `inventory.db` exists.
2. If missing, it creates the database from `schema.sql`.
3. Migration manager checks for pending migrations.
4. Summary table service starts and backfills aggregate tables.
5. Main window opens.

## Core Data Model (Simplified)

- `Items`: inventory records
- `Item_Batches`: received quantities by batch
- `Stock_Movements`: ledger of consumption/reservation/return/disposal/request
- `Requisitions`: request transactions and status
- `Requisition_Items`: line items per requisition
- `Requesters`: people/groups making requests
- `Activity_Log` and history tables: audit trail

## Performance and Responsiveness

- Background work uses Qt worker threads (`QThreadPool` + `QRunnable`).
- The worker pool is capped for weaker hardware (up to 4 threads).
- Query caching and summary tables are used to speed up repeated reads.
- Summary aggregates are refreshed in the background on an interval.

## Design Boundaries

The app is intentionally:

- Local-first (single SQLite database file)
- Desktop-only (no web API layer)
- Service-oriented internally (business logic in `services/`)

For current technical limitations and risks, read [Known Limitations](limitations.md).
