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
