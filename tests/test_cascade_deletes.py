from inventory_app.database.connection import db
from inventory_app.database.models import Item, Requester, Requisition, RequisitionItem


def setup_temp_db(tmp_path):
    tmp_db_path = tmp_path / "test_inventory.db"
    if tmp_db_path.exists():
        tmp_db_path.unlink()
    db.db_path = tmp_db_path
    assert db.create_database() is True
    return tmp_db_path


def test_item_delete_cascades(tmp_path):
    setup_temp_db(tmp_path)

    item = Item(name="CascadeItem", category_id=1)
    assert item.save(editor_name="tester", batch_quantity=2) is True

    # Create a requester and requisition with this item
    requester = Requester(name="CascadeUser")
    assert requester.save() is True
    assert requester.id is not None

    req = Requisition()
    req.requester_id = int(requester.id)
    assert req.save("tester") is True

    assert req.id is not None
    assert item.id is not None
    req_item = RequisitionItem()
    req_item.requisition_id = int(req.id)
    req_item.item_id = int(item.id)
    req_item.quantity_requested = 1
    assert req_item.save() is True

    # Manually insert a stock movement and update history
    db.execute_update(
        "INSERT INTO Stock_Movements (item_id, movement_type, quantity, movement_date, source_id) VALUES (?, 'CONSUMPTION', 1, date('now'), NULL)",
        (int(item.id),),
    )
    db.execute_update(
        "INSERT INTO Update_History (item_id, editor_name, reason) VALUES (?, ?, ?)",
        (int(item.id), "tester", "initial"),
    )

    # Delete main item (should cascade delete dependent records due to schema)
    db.execute_update("DELETE FROM Items WHERE id = ?", (int(item.id),))

    # Assert batches, movements, and history are gone
    batches = db.execute_query(
        "SELECT * FROM Item_Batches WHERE item_id = ?", (int(item.id),)
    )
    assert not batches
    movements = db.execute_query(
        "SELECT * FROM Stock_Movements WHERE item_id = ?", (int(item.id),)
    )
    assert not movements
    history = db.execute_query(
        "SELECT * FROM Update_History WHERE item_id = ?", (int(item.id),)
    )
    assert not history
    req_items = db.execute_query(
        "SELECT * FROM Requisition_Items WHERE item_id = ?", (int(item.id),)
    )
    assert not req_items
