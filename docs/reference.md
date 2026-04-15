# Reference Guide

## Command Reference

### Environment Setup

```powershell
# Activate virtual environment (PowerShell)
& .venv\Scripts\Activate.ps1

# Activate virtual environment (Command Prompt)
.venv\Scripts\activate.bat

# Install dependencies
python -m pip install -r requirements.txt

# Upgrade pip
python -m pip install --upgrade pip
```

### Application Commands

```powershell
# Run the application
python -m inventory_app.main

# Run with custom database path
set DB_PATH=C:\path\to\inventory.db
python -m inventory_app.main
```

### Testing Commands

```powershell
# Run all tests
python -m pytest -q

# Run tests with verbose output
python -m pytest -v

# Run specific test file
python -m pytest tests/test_item_service.py -v

# Run tests and show coverage
python -m pytest --cov=inventory_app
```

### Population Scripts (Manual QA)

```powershell
# Populate sample items
python tests/populate-items.py

# Populate sample requesters
python tests/populate-requesters.py

# Populate sample requisitions
python tests/populate-requisitions.py

# Alternative: Use sample_data.py for comprehensive test data
python scripts/sample_data.py
```

### Build and Packaging

```powershell
# Build executable with PyInstaller
pyinstaller --onefile lim.spec

# Build with console window (for debugging)
pyinstaller --onefile --console lim.spec

# Output location: dist/ folder
```

### Maintenance Scripts

```powershell
# Run maintenance (dry-run first)
python scripts/maintenance.py --days-to-keep 90 --max-activities 20 --dry-run

# Execute maintenance (actual cleanup)
python scripts/maintenance.py --days-to-keep 90 --max-activities 20

# Custom database path
python scripts/maintenance.py --db-path C:\path\to\inventory.db --days-to-keep 90
```

## Database Reference

### File Location

- **Default**: `inventory.db` in the application working directory
- **Custom**: Set `db.db_path` before running scripts or set `DB_PATH` environment variable

### Database Behavior

**Connection Settings:**

- `PRAGMA journal_mode = WAL` - Write-Ahead Logging for better performance
- `PRAGMA synchronous = FULL` - Full durability for data integrity
- `PRAGMA foreign_keys = ON` - Enforce referential integrity

**File Structure:**

- Main database: `inventory.db`
- WAL files: `inventory.db-wal` (Write-Ahead Log)
- SHM file: `inventory.db-shm` (Shared memory)

**Important:** Keep database on local disk. WAL mode does not work reliably on network shares.

### Database Schema

**Core Tables:**

- `Items` - Core inventory items
- `Item_Batches` - Receipt batches with quantities
- `Stock_Movements` - Ledger of all stock changes
- `Categories` - Fixed item categories
- `Suppliers` - Supplier reference data
- `Sizes` - Size reference data
- `Brands` - Brand reference data
- `Requesters` - Personnel who can make requisitions
- `Requisitions` - Requisition records with lifecycle
- `Requisition_Items` - Items in each requisition
- `Update_History` - Item edit audit trail
- `Requisition_History` - Requisition create/edit/status audit trail (including automatic status transitions)
- `Disposal_History` - Disposed items records
- `Activity_Log` - Activity events for dashboard and audit reporting (unlimited retention)
- `Defective_Items` - Defective/broken items from returns

`Update_History` includes field-level old/new values for item edits and batch synchronization changes (batch create, batch remove, and per-field batch deltas).

**Views:**

- `Item_Start_Dates` - Helper for alert calculations
- `Item_Usage` - Aggregated usage data
- `Defective_Items_Summary` - Defective items for reporting

**Triggers:**

- `trg_stock_movement_batch_before_insert/update` - Prevent batch oversubscription
- `trg_stock_movement_item_before_insert/update` - Prevent item oversubscription
- Activity log pruning triggers were removed; retention is managed as unlimited history.

### Database API

```python
from inventory_app.database.connection import db
from inventory_app.database.query_cache import cached_query

# Context-managed connection
with db.get_connection() as conn:
    cursor = conn.execute("SELECT * FROM Items LIMIT 10")
    results = cursor.fetchall()

# Transaction (atomic operations)
with db.transaction(immediate=False):
    item.save()
    batch.save()

# Immediate transaction (reserved stock) - uses BEGIN IMMEDIATE to obtain a write lock early
with db.transaction(immediate=True):
    requisition.create()

# Query execution
rows = db.execute_query("SELECT * FROM Items WHERE id = ?", (item_id,))

# Update execution
affected, last_id = db.execute_update(
    "INSERT INTO Items (name, category_id) VALUES (?, ?)",
    (name, category_id),
    return_last_id=True
)

# Cache control (QueryCache)
# Clear entire cache
db.clear_query_cache()

# Invalidate cache entries related to a particular table (returns number invalidated)
db.invalidate_cache_for_table("Items")

# Decorator usage for expensive queries
@cached_query(ttl=60)
def get_expensive_report(query=None, params=()):
    return db.execute_query(query, params)
```

### Database Backups

**Manual Backup:**

1. Stop the application
2. Copy `inventory.db` to backup location
3. Restart application

**Automated Backup (Windows Task Scheduler):**

```batch
@echo off
set BACKUP_DIR=C:\backups\inventory
set DATE=%date:~-4,4%-%date:~-10,2%-%date:~-7,2%
set TIME=%time:~0,2%-%time:~3,2%
set FILENAME=inventory_%DATE%_%TIME%.db

if not exist %BACKUP_DIR% mkdir %BACKUP_DIR%
copy inventory.db %BACKUP_DIR%\%FILENAME%
```

**Restore from Backup:**

1. Stop the application
2. Rename or delete current `inventory.db`
3. Copy backup file to `inventory.db`
4. Restart application

## Logging Reference

### Log File Location

- **Default**: `logs/logs.txt` in application directory
- **Rotation**: Logs are rotated by size to prevent uncontrolled growth

### Log Contents

**Logged Events:**

- Application startup/shutdown
- Database connections and schema initialization
- Item CRUD operations
- Requisition lifecycle events
- Stock movements
- Import operations
- Report generation
- Errors and exceptions

**PII Protection:**
The logger uses a `SanitizeFilter` to redact:

- Email addresses
- Phone numbers
- Social Security Numbers
- Credit card numbers

Long messages are truncated to prevent leaking large free-form text.

### Log Levels

- **DEBUG**: Detailed information for debugging
- **INFO**: General operational information
- **WARNING**: Non-critical issues
- **ERROR**: Errors and exceptions
- **CRITICAL**: Severe errors requiring attention

### Viewing Logs

```powershell
# View recent logs (PowerShell)
Get-Content logs/logs.txt -Tail 50

# View logs with filtering
Select-String "ERROR" logs/logs.txt

# Watch logs in real-time
Get-Content logs/logs.txt -Wait
```

## Troubleshooting Guide

### Application Won't Start

#### Error: "ModuleNotFoundError: No module named 'PyQt6'"

```powershell
# Ensure virtual environment is activated
& .venv\Scripts\Activate.ps1

# Reinstall dependencies
python -m pip install -r requirements.txt
```

#### Error: "database is locked"

- Another instance of the application is running
- Close all application windows and try again
- Check for orphaned processes in Task Manager

#### Error: "SQLite objects created in another thread"

- Database connection used across threads incorrectly
- This is an application bug; restart the application

### Data Load Errors

#### Error: "Data Load Error" on any page

1. Click Refresh to retry
2. Check database file integrity
3. Review logs for specific error messages
4. Restart application

#### Error: "No data found" in reports

- Expand date range
- Remove category/supplier filters
- Verify data exists in the database

### Import Failures

#### Error: "Required columns missing"

- Check that file contains: `name`, `stocks`, `item type`
- Verify header row is present
- Check for extra spaces in column names

#### Error: "Import aborted"

- Review logs for specific row errors
- Check that Excel file is not open in another program
- Verify file is valid `.xlsx` format

### Report Generation Failures

#### Error: "Permission denied" writing file

- Check application has write permission to working directory
- Close any open Excel files
- Choose different output location

#### Error: "No data found"

- Widen date range
- Remove filters
- Verifyrequisitions have activity dates in range

### Performance Issues

#### Slow page loads

- Large datasets load asynchronously with progress indicator
- Background processing may take time for thousands of items
- Consider using filters to reduce visible data

#### Slow reports

- Large date ranges with fine granularity generate large SQL
- Use Auto granularity for wide date ranges
- Consider running reports during off-peak hours

### Database Issues

**Database file missing:**

- First run: application creates database automatically
- Check working directory is correct
- Verify `inventory_app/database/schema.sql` exists

**Schema out of sync:**

- Update application to latest version
- Manually run schema migrations if provided
- Restore from backup if necessary

## Frequently Asked Questions

**Q: How do I add a new category?**
A: Categories are fixed and cannot be added. They are defined in `inventory_app/services/category_config.py` and `docs/settings.md`.

**Q: Can I change an item from consumable to non-consumable?**
A: Yes, edit the item and change the Item Type. Note: stock calculations differ between types.

**Q: What happens if I delete an item with requisitions?**
A: Deletion is blocked for items with requisition history. Remove requisitions first or mark item as disposed.

**Q: How are expiration/disposal dates calculated?**
A: See `docs/settings.md` for category thresholds. Dates auto-calculate when acquiring items.

**Q: Can I recover deleted data?**
A: Only from backups. Deleted items, requisitions, and requesters are permanently removed.

**Q: How do I export data for another system?**
A: Use Reports page to generate Excel exports. For raw data, use SQLite tools on `inventory.db`.

**Q: Can multiple users use the application simultaneously?**
A: The application is designed for single-user desktop use. Concurrent access may cause locking issues.

**Q: How do I reset the application to initial state?**
A: Delete `inventory.db` and restart the application. All data will be lost.
