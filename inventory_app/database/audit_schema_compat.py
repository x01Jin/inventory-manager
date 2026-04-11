"""Task 9 audit schema compatibility helpers.

Applies idempotent schema updates for development databases so Task 9
features can run without requiring a destructive reset.
"""

from inventory_app.database.connection import db
from inventory_app.utils.logger import logger


def _has_column(table_name: str, column_name: str) -> bool:
    """Return True when the target column exists in the table."""
    rows = db.execute_query(
        f"PRAGMA table_info({table_name})",
        use_cache=False,
    )
    return any(row.get("name") == column_name for row in rows)


def _drop_trigger_if_exists(trigger_name: str) -> None:
    """Drop a trigger if it exists."""
    db.execute_update(f"DROP TRIGGER IF EXISTS {trigger_name}")


def ensure_audit_schema() -> bool:
    """Ensure audit schema requirements exist.

    Returns:
        bool: True when checks/updates completed successfully.
    """
    try:
        with db.transaction():
            # Activity log retention must be unlimited.
            _drop_trigger_if_exists("trg_activity_log_cleanup_after_insert")
            _drop_trigger_if_exists("trg_activity_log_maintain_limit_after_insert")

            # Field-level audit columns for item and requisition history.
            if not _has_column("Update_History", "field_name"):
                db.execute_update(
                    "ALTER TABLE Update_History ADD COLUMN field_name TEXT"
                )
            if not _has_column("Update_History", "old_value"):
                db.execute_update(
                    "ALTER TABLE Update_History ADD COLUMN old_value TEXT"
                )
            if not _has_column("Update_History", "new_value"):
                db.execute_update(
                    "ALTER TABLE Update_History ADD COLUMN new_value TEXT"
                )

            if not _has_column("Requisition_History", "field_name"):
                db.execute_update(
                    "ALTER TABLE Requisition_History ADD COLUMN field_name TEXT"
                )
            if not _has_column("Requisition_History", "old_value"):
                db.execute_update(
                    "ALTER TABLE Requisition_History ADD COLUMN old_value TEXT"
                )
            if not _has_column("Requisition_History", "new_value"):
                db.execute_update(
                    "ALTER TABLE Requisition_History ADD COLUMN new_value TEXT"
                )

            # Standardize defective item attribution.
            if not _has_column("Defective_Items", "editor_name"):
                db.execute_update(
                    "ALTER TABLE Defective_Items ADD COLUMN editor_name TEXT"
                )

            db.execute_update(
                "UPDATE Defective_Items SET editor_name = reported_by WHERE editor_name IS NULL"
            )

        logger.info("Task 9 audit schema compatibility checks completed")
        return True
    except Exception as exc:
        logger.error(f"Task 9 schema compatibility failed: {exc}")
        return False
