# Installation

Prerequisites

- Python 3.10+ (3.11 recommended)
- Virtual environment tooling (venv)
- A working Python environment with file system access

Install

1. Clone the repo and change into the project root.
2. Create and activate a virtual environment:

```powershell
python -m venv .venv
& .venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Start the application to initialize the database automatically:

```powershell
python -m inventory_app.main
```

Notes

- The database schema is in `inventory_app/database/schema.sql`. The initial run will auto-create the SQLite DB at `inventory.db` if it does not exist.

- The application configures SQLite connections for stronger durability and integrity by enabling Write-Ahead Logging (`PRAGMA journal_mode = WAL`), setting `PRAGMA synchronous = FULL` and enforcing `PRAGMA foreign_keys = ON`. Because WAL uses additional files, place the database on a local disk (not a network share) for reliable operation.

Maintenance

The project includes a small maintenance helper script at `scripts/maintenance.py` that calls into the application's `ActivityLogger` utilities to prune old activity log entries and keep the activity table bounded.

- **Usage (dry-run)**:

```powershell
python scripts/maintenance.py --days-to-keep 90 --max-activities 20 --dry-run
```

- **Run now (perform deletions)**:

```powershell
python scripts/maintenance.py --days-to-keep 90 --max-activities 20
```

- **Scheduling (examples)**:
  - Cron (Linux/macOS): add a daily cron job that runs the script using your virtual environment's Python executable. Example (02:00 daily):

```bash
0 2 * * * /path/to/venv/bin/python /path/to/repo/scripts/maintenance.py --days-to-keep 90 --max-activities 20
```

- Windows Task Scheduler: create a basic daily task that runs `python.exe` with the arguments:

```path
C:\path\to\repo\scripts\maintenance.py --days-to-keep 90 --max-activities 20
```

Notes

- The maintenance script is idempotent and safe to run repeatedly. It uses parameterized queries and the `ActivityLogger` API (`cleanup_old_activities` and `maintain_activity_limit`) so no ad-hoc SQL is required.
- If you need a different database location, pass `--db-path /path/to/inventory.db`. The script sets the global `db.db_path` before running.

Seeding sample data for manual QA

- The project contains `scripts/sample_data.py` which runs a realistic timeline population to help with testing and demoing features. Run it directly:

```powershell
python scripts/sample_data.py
```

This will create the database if it does not yet exist and populate a realistic set of items, requesters and requisitions for testing and manual QA.
