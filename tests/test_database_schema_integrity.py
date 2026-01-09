import sqlite3
from inventory_app.database.connection import DatabaseConnection


def test_schema_contains_expected_tables(tmp_path, monkeypatch):
    # Create a temporary DB file and ensure schema is applied on initialization
    db_file = tmp_path / "test_inventory.db"
    db = DatabaseConnection(str(db_file))
    # Create the database and apply schema
    assert db.create_database() is True

    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cur.fetchall()}

    expected_tables = {
        "Items",
        "Requisitions",
        "Stock_Movements",
        "Suppliers",
        "Update_History",
        "Disposal_History",
    }

    missing = expected_tables - tables
    assert not missing, f"Missing expected schema tables: {missing}"

    conn.close()
