from inventory_app.database.connection import db
from inventory_app.database.models import Item


def setup_temp_db(tmp_path):
    tmp_db_path = tmp_path / "test_inventory.db"
    tmp_db_path.parent.mkdir(parents=True, exist_ok=True)
    if tmp_db_path.exists():
        tmp_db_path.unlink()
    db.db_path = tmp_db_path
    created = db.create_database()
    assert created is True
    return tmp_db_path


def test_item_save_commits_with_batch(tmp_path):
    setup_temp_db(tmp_path)

    item = Item(name="CommittableItem", category_id=1)
    saved = item.save(editor_name="tester", batch_quantity=5)
    assert saved is True
    assert item.id is not None and item.id > 0

    # Verify batch created
    batches = db.execute_query(
        "SELECT * FROM Item_Batches WHERE item_id = ?", (item.id,)
    )
    assert batches and batches[0]["quantity_received"] == 5


def test_item_save_rolls_back_on_batch_failure(tmp_path, monkeypatch):
    setup_temp_db(tmp_path)

    item = Item(name="FailingItem", category_id=1)

    def fail_create_batches(self, qty):
        raise Exception("batch creation failed")

    monkeypatch.setattr(Item, "_create_batches", fail_create_batches)

    saved = item.save(editor_name="tester", batch_quantity=1)
    assert saved is False

    # Ensure no item was created in the database due to rollback
    rows = db.execute_query("SELECT * FROM Items WHERE name = ?", (item.name,))
    assert not rows


def test_requisition_save_rolls_back_on_movement_failure(tmp_path):
    setup_temp_db(tmp_path)

    from inventory_app.database.models import Requester, Requisition

    # Create a requester first
    requester = Requester(name="ReqUser")
    assert requester.save() is True
    assert requester.id is not None

    # Now attempt to create a requisition but raise an exception inside the transaction
    try:
        with db.transaction():
            req = Requisition()
            req.requester_id = int(requester.id)
            req.expected_request = req.expected_request
            req.expected_return = req.expected_return
            req.status = "requested"
            assert req.save("tester") is True

            # Simulate failure during stock movements creation
            raise Exception("Simulated stock movement failure")
    except Exception:
        pass

    # The transaction should have rolled back; no requisitions should exist
    rows = db.execute_query(
        "SELECT * FROM Requisitions WHERE requester_id = ?", (int(requester.id),)
    )
    assert not rows
