from pathlib import Path

import pytest

from inventory_app.database.connection import db
from inventory_app.database.migrations.migration_manager import MigrationManager


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for migration tests."""
    original_db_path = db.db_path
    db.db_path = tmp_path / "test_migrations.db"
    assert db.create_database() is True
    yield db.db_path
    db.db_path = original_db_path


def _migrations_dir() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "inventory_app"
        / "database"
        / "migrations"
    )


def test_migration_manager_accepts_file_path_for_discovery():
    """Migration manager should resolve a file path to its parent directory."""
    migrations_init = _migrations_dir() / "__init__.py"
    manager = MigrationManager(str(migrations_init))

    discovered = manager._discover_migrations()
    discovered_ids = {migration["id"] for migration in discovered}

    assert 1 in discovered_ids


def test_baseline_migration_is_applied_and_recorded(temp_db):
    """Baseline migration should run once and be recorded in Schema_Versions."""
    manager = MigrationManager(str(_migrations_dir()))

    pending_before = manager.get_pending_migrations()
    assert any(migration["id"] == 1 for migration in pending_before)

    assert manager.run_pending_migrations() is True

    rows = db.execute_query(
        "SELECT migration_id FROM Schema_Versions WHERE migration_id = '001'"
    )
    assert len(rows) == 1

    pending_after = manager.get_pending_migrations()
    assert pending_after == []
