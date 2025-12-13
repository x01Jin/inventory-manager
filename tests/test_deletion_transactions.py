from inventory_app.database.connection import db
from inventory_app.database.models import Item, Requisition, RequisitionItem, Requester


def setup_temp_db(tmp_path):
    tmp_db_path = tmp_path / "test_inventory.db"
    tmp_db_path.parent.mkdir(parents=True, exist_ok=True)
    if tmp_db_path.exists():
        tmp_db_path.unlink()
    db.db_path = tmp_db_path
    assert db.create_database() is True
    return tmp_db_path


def test_item_delete_rolls_back_on_failure(tmp_path):
    setup_temp_db(tmp_path)

    # Create an item with a batch
    item = Item(name="DelItem", category_id=1)
    assert item.save(editor_name="tester", batch_quantity=2)
    assert item.id

    # Insert an extra related record to ensure we're deleting
    # (disposal history already inserted by delete path)

    # Patch db.execute_update to raise when deleting Item_Batches
    orig = db.execute_update

    def patched_execute_update(query, params=(), return_last_id=False):
        if "DELETE FROM Item_Batches" in query:
            raise Exception("Simulated delete failure")
        return orig(query, params, return_last_id)

    db.execute_update = patched_execute_update

    success = item.delete(editor_name="tester", reason="test")
    assert success is False

    # Ensure item still exists because transaction should have rolled back
    rows = db.execute_query("SELECT * FROM Items WHERE id = ?", (item.id,))
    assert rows

    # Restore
    db.execute_update = orig


def test_requisition_delete_rolls_back_on_failure(tmp_path):
    setup_temp_db(tmp_path)

    requester = Requester(name="ReqDeleteUser")
    assert requester.save() is True
    assert requester.id is not None

    req = Requisition()
    req.requester_id = int(requester.id)
    assert req.save("tester") is True
    assert req.id is not None

    # Create an item to attach to the requisition item
    item = Item(name="ReqItem", category_id=1)
    assert item.save(editor_name="tester", batch_quantity=1)
    assert item.id is not None

    # Add a requisition item
    assert req.id is not None
    assert item.id is not None
    ri = RequisitionItem(
        requisition_id=int(req.id), item_id=int(item.id), quantity_requested=1
    )
    assert ri.save() is True

    # Patch db.execute_update to raise when deleting Requisition_Items
    orig = db.execute_update

    def patched_execute_update(query, params=(), return_last_id=False):
        if "DELETE FROM Requisition_Items" in query:
            raise Exception("Simulated requisition delete failure")
        return orig(query, params, return_last_id)

    db.execute_update = patched_execute_update

    success = req.delete(editor_name="tester")
    assert success is False

    # Requisition should still exist
    rows = db.execute_query("SELECT * FROM Requisitions WHERE id = ?", (int(req.id),))
    assert rows

    # Restore
    db.execute_update = orig
