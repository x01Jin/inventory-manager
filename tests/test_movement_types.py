import sqlite3
from inventory_app.database.connection import db
from inventory_app.database.models import Item, Requisition, Requester


def setup_temp_db(tmp_path):
    tmp_db_path = tmp_path / "test_inventory.db"
    tmp_db_path.parent.mkdir(parents=True, exist_ok=True)
    if tmp_db_path.exists():
        tmp_db_path.unlink()
    db.db_path = tmp_db_path
    assert db.create_database() is True
    return tmp_db_path


def test_invalid_movement_type_insert_rejected(tmp_path):
    setup_temp_db(tmp_path)

    # Create an item and requisition to satisfy foreign keys
    item = Item(name="InvalidMoveItem", category_id=1)
    assert item.save(editor_name="tester", batch_quantity=1)
    assert item.id is not None
    requester = Requester(name="RequestX")
    assert requester.save() is True
    assert requester.id is not None
    req = Requisition()
    req.requester_id = int(requester.id)
    assert req.save("tester") is True
    assert req.id is not None

    # Attempt to insert a Stock_Movements row with an invalid movement_type
    query = "INSERT INTO Stock_Movements (item_id, movement_type, quantity, movement_date, source_id) VALUES (?, ?, ?, ?, ?)"
    params = (int(item.id), "INVALID", 1, "2020-01-01", int(req.id))

    import pytest

    with pytest.raises(sqlite3.IntegrityError):
        db.execute_update(query, params)
