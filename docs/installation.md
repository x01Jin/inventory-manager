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

Scheduling maintenance

- **Cron (Linux/macOS):** Add a cron job to run daily (example at 2am) using the installed Python environment:

```bash
# Run maintenance daily at 02:00
0 2 * * * /path/to/venv/bin/python /path/to/repo/scripts/maintenance.py --db-path /path/to/repo/inventory.db --days-to-keep 90 --max-activities 20
```

- **Windows Task Scheduler:** Create a basic task that runs daily and use the following command as the action (Program/Script + Arguments):

Program/script: `python.exe`
Arguments: `C:\path\to\repo\scripts\maintenance.py --db-path C:\path\to\repo\inventory.db --days-to-keep 90 --max-activities 20`

The maintenance script will call into the app's `ActivityLogger` to delete old items and maintain a maximum number of recent activities. This provides a reliable cross-platform way to ensure the database does not grow unchecked even when the GUI application does not run.
