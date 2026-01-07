from inventory_app.database.connection import db
from inventory_app.database.models import Supplier


def setup_temp_db(tmp_path):
    tmp_db_path = tmp_path / "test_inventory.db"
    tmp_db_path.parent.mkdir(parents=True, exist_ok=True)
    if tmp_db_path.exists():
        tmp_db_path.unlink()
    db.db_path = tmp_db_path
    created = db.create_database()
    assert created is True
    return tmp_db_path


def test_execute_update_returns_last_id(tmp_path):
    setup_temp_db(tmp_path)

    # Use execute_update directly to insert
    rows_affected, last_id = db.execute_update(
        "INSERT INTO Categories (name) VALUES (?)", ("TestCat",), return_last_id=True
    )
    assert rows_affected == 1
    assert isinstance(last_id, int) and last_id > 0

    # Verify row exists in DB
    rows = db.execute_query("SELECT * FROM Categories WHERE id = ?", (last_id,))
    assert rows and rows[0]["name"] == "TestCat"


def test_model_save_sets_id(tmp_path):
    setup_temp_db(tmp_path)

    # Categories are now fixed (v0.7.0b patch) and don't have save() method
    # Test with Supplier instead which still has save()
    sup = Supplier(name="TestSupplier")
    success, message = sup.save()
    assert success is True
    assert sup.id is not None and sup.id > 0

    rows = db.execute_query("SELECT * FROM Suppliers WHERE id = ?", (sup.id,))
    assert rows and rows[0]["name"] == "TestSupplier"
