import sqlite3
import threading
import pytest
from inventory_app.database.connection import db
from inventory_app.database.models import Item, Requisition, Requester


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for each test and ensure schema is applied."""
    db_file = tmp_path / "test_inventory.db"
    db.db_path = db_file
    assert db.create_database() is True
    yield db_file
    # Cleanup is handle by tmp_path but explicit closure might be needed
    # if we had persistent connections open.


def test_schema_integrity(temp_db):
    """Verify that the database schema contains all expected tables."""
    conn = sqlite3.connect(str(temp_db))
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cur.fetchall()}
    conn.close()

    expected_tables = {
        "Items",
        "Requisitions",
        "Stock_Movements",
        "Suppliers",
        "Update_History",
        "Disposal_History",
        "Categories",
        "Item_Batches",
        "Requesters",
    }
    missing = expected_tables - tables
    assert not missing, f"Missing expected schema tables: {missing}"


def test_indexes_exist(temp_db):
    """Ensure critical indexes exist for performance."""
    # Stock_Movements index on source_id
    idxs = db.execute_query("PRAGMA index_list('Stock_Movements')")
    names = [r["name"] for r in idxs]
    assert "idx_movements_source" in names

    # Verify index is defined on `source_id`
    info = db.execute_query("PRAGMA index_info('idx_movements_source')")
    assert info and info[0]["name"] == "source_id"


def test_execute_update_behavior(temp_db):
    """Verify execute_update returns affected rows and last insert ID."""
    rows_affected, last_id = db.execute_update(
        "INSERT INTO Categories (name) VALUES (?)", ("TestCat",), return_last_id=True
    )
    assert rows_affected == 1
    assert isinstance(last_id, int) and last_id > 0

    # Verify row exists
    rows = db.execute_query("SELECT name FROM Categories WHERE id = ?", (last_id,))
    assert rows and rows[0]["name"] == "TestCat"


def test_transaction_rollback_on_failure(temp_db, monkeypatch):
    """Verify that transactions roll back completely on failure."""
    item = Item(name="FailingItem", category_id=1)

    # Monkeypatch batch creation to fail
    def fail_create_batches(self, qty):
        raise Exception("batch creation failed")

    monkeypatch.setattr(Item, "_create_batches", fail_create_batches)

    # Item.save() uses a transaction internally
    saved = item.save(editor_name="tester", batch_quantity=1)
    assert saved is False

    # Ensure no item was created due to rollback
    rows = db.execute_query("SELECT * FROM Items WHERE name = ?", (item.name,))
    assert not rows


def test_nested_transaction_behavior(temp_db):
    """Verify manual transaction control and rollback for complex flows."""
    requester = Requester(name="ReqUser")
    assert requester.save() is True

    try:
        with db.transaction():
            req = Requisition()
            assert requester.id is not None
            req.requester_id = requester.id
            req.status = "requested"
            assert req.save("tester") is True
            # Trigger failure after partial success
            raise Exception("Force rollback")
    except Exception:
        pass

    # No requisitions should exist
    assert requester.id is not None
    rows = db.execute_query(
        "SELECT * FROM Requisitions WHERE requester_id = ?", (requester.id,)
    )
    assert not rows


def test_concurrent_access_immediate_transaction(temp_db):
    """Ensure IMMEDIATE transactions prevent over-subscription under load."""

    # Setup initial stock
    rows_affected, item_id = db.execute_update(
        "INSERT INTO Items (name, category_id) VALUES (?, ?)",
        ("ConcurrentItem", 1),
        return_last_id=True,
    )
    db.execute_update(
        "INSERT INTO Item_Batches (item_id, batch_number, quantity_received, date_received) VALUES (?, ?, ?, ?)",
        (item_id, "B1", 5, "2025-01-01"),
    )

    results = []

    def attempt_reservation():
        try:
            with db.transaction(immediate=True):
                # Check stock
                stock = db.execute_query(
                    "SELECT quantity_received FROM Item_Batches WHERE item_id = ?",
                    (item_id,),
                )[0]["quantity_received"]

                if stock >= 3:
                    # Deduct stock (simulating reservation)
                    db.execute_update(
                        "UPDATE Item_Batches SET quantity_received = quantity_received - 3 WHERE item_id = ?",
                        (item_id,),
                    )
                    results.append(True)
                else:
                    results.append(False)
        except Exception:
            results.append(False)

    t1 = threading.Thread(target=attempt_reservation)
    t2 = threading.Thread(target=attempt_reservation)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Only one should have succeeded (5 - 3 = 2, next 2 < 3)
    assert results.count(True) == 1

    final_stock = db.execute_query(
        "SELECT quantity_received FROM Item_Batches WHERE item_id = ?", (item_id,)
    )[0]["quantity_received"]
    assert final_stock == 2
