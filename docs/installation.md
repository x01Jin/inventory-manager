# Installation

## Requirements

- Python 3.10 or newer
- `venv` (built into Python)
- Local file system access for creating `inventory.db`

## Setup

1. Open a terminal in the project root.
2. Create a virtual environment.
3. Install dependencies.

```powershell
python -m venv .venv
& .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run the App

```powershell
python -m inventory_app.main
```

On first run, the app creates `inventory.db` automatically if it does not exist.

## Optional: Seed Sample Data

```powershell
python scripts/sample_data.py
```

This creates realistic test data for manual QA and demos.

## Optional: Maintenance Script

Use this when you want to prune old activity logs.

Dry run:

```powershell
python scripts/maintenance.py --days-to-keep 90 --max-activities 20 --dry-run
```

Apply changes:

```powershell
python scripts/maintenance.py --days-to-keep 90 --max-activities 20
```

## Practical Notes

- SQLite is configured for durability and integrity (`WAL`, `synchronous=FULL`, `foreign_keys=ON`).
- Keep the database on a local disk for best reliability.
- Schema source of truth: `inventory_app/database/schema.sql`.
