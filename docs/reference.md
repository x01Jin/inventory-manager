# Reference

Commands

- Activate venv:

```powershell
& .venv\Scripts\Activate.ps1
```

- Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

- Run the app:

```powershell
python -m inventory_app.main
```

- Run tests: (populates DB data, used for manual QA)

```powershell
python tests/populate-items.py
python tests/populate-requesters.py
python tests/populate-requisitions.py
```

Build as executable (PyInstaller)

```powershell
pyinstaller --onefile lim.spec
```

Database

- The app uses SQLite and stores the file as `inventory.db` in the current working directory (unless otherwise configured). Schema is `inventory_app/database/schema.sql`.

- Database behavior: connections enable `PRAGMA journal_mode = WAL` (Write-Ahead Logging), `PRAGMA synchronous = FULL` for stronger durability, and `PRAGMA foreign_keys = ON` to enforce referential integrity. The schema also includes triggers that prevent stock movements which would reduce a batch's or an item's available quantity below zero; those triggers abort the offending statement and act as a defensive guard against invalid state. WAL uses auxiliary files; keep the database on a local disk for reliable operation.

Notes

- If the GUI import fails, ensure PyQt6 is installed and your virtual environment is active.
