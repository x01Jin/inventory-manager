"""Baseline migration for schema-tracked databases."""

from pathlib import Path

from inventory_app.database.connection import db


description = "Establish baseline schema version for migration tracking"


def _table_exists(table_name: str) -> bool:
    rows = db.execute_query(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
        use_cache=False,
    )
    return bool(rows)


def _ensure_schema_versions_table() -> None:
    db.execute_update(
        """
        CREATE TABLE IF NOT EXISTS Schema_Versions (
            migration_id TEXT PRIMARY KEY,
            applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            description TEXT
        )
        """
    )
    db.execute_update(
        "CREATE INDEX IF NOT EXISTS idx_schema_versions_id ON Schema_Versions(migration_id)"
    )


def _bootstrap_schema_if_missing() -> None:
    # If core tables already exist, this is an existing database and we only
    # need to make sure schema version tracking is present.
    if _table_exists("Items"):
        return

    schema_path = Path(__file__).resolve().parents[1] / "schema.sql"
    schema_sql = schema_path.read_text(encoding="utf-8")
    db.execute_script(schema_sql)


def up() -> None:
    _ensure_schema_versions_table()
    _bootstrap_schema_if_missing()
