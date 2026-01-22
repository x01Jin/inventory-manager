"""
Migration manager for database schema updates.
"""

from __future__ import annotations

import importlib.util
import logging
import re
from pathlib import Path
from typing import Any, Callable

from inventory_app.database.connection import db

logger = logging.getLogger(__name__)

MigrationCallback = Callable[[str, int], None]


class MigrationManager:
    """Manages database migrations."""

    MIGRATION_PATTERN = re.compile(r"^(\d+)_.*\.py$")

    def __init__(self, migrations_dir: str):
        self.migrations_dir = Path(migrations_dir)
        self._migrations_cache: list[dict[str, Any]] | None = None

    def _discover_migrations(self) -> list[dict[str, Any]]:
        """Discover available migrations in the migrations directory."""
        if self._migrations_cache is not None:
            return self._migrations_cache

        migrations = []
        for file_path in sorted(self.migrations_dir.glob("[0-9]*.py")):
            match = self.MIGRATION_PATTERN.match(file_path.name)
            if match:
                migration_id = int(match.group(1))
                spec = importlib.util.spec_from_file_location(
                    f"migration_{migration_id}", file_path
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    migrations.append(
                        {
                            "id": migration_id,
                            "description": getattr(module, "description", "No description"),
                            "up": getattr(module, "up", None),
                            "path": file_path,
                        }
                    )

        self._migrations_cache = sorted(migrations, key=lambda m: m["id"])
        return self._migrations_cache

    def _get_applied_migrations(self) -> set[int]:
        """Get list of already applied migration IDs."""
        try:
            rows = db.execute_query(
                "SELECT migration_id FROM Schema_Versions ORDER BY migration_id"
            )
            return {int(row["migration_id"]) for row in rows}
        except Exception:
            return set()

    def _record_migration(self, migration_id: int, description: str) -> None:
        """Record a migration as applied."""
        db.execute_update(
            "INSERT INTO Schema_Versions (migration_id, description, applied_at) VALUES (?, ?, datetime('now'))",
            (str(migration_id).zfill(3), description),
        )

    def get_pending_migrations(self) -> list[dict[str, Any]]:
        """Get list of pending migrations not yet applied."""
        applied = self._get_applied_migrations()
        return [m for m in self._discover_migrations() if m["id"] not in applied]

    def run_pending_migrations(
        self,
        progress_callback: MigrationCallback | None = None,
    ) -> bool:
        """Run all pending migrations.

        Args:
            progress_callback: Optional callback(status_message, percent_complete)

        Returns:
            True if all migrations succeeded, False on failure
        """
        pending = self.get_pending_migrations()
        if not pending:
            return True

        total = len(pending)
        for index, migration in enumerate(pending):
            percent = int((index / total) * 100)
            status = f"Running migration {migration['id']}: {migration['description']}"

            if progress_callback:
                progress_callback(status, percent)

            try:
                if migration["up"] is None:
                    logger.warning(
                        f"Migration {migration['id']} has no 'up' function, skipping"
                    )
                    continue

                migration["up"]()
                self._record_migration(migration["id"], migration["description"])
                logger.info(f"Successfully applied migration {migration['id']}")

            except Exception:
                logger.exception(f"Failed to apply migration {migration['id']}")
                return False

        if progress_callback:
            progress_callback("Migration complete", 100)

        return True
