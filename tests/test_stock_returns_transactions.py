from typing import cast
from inventory_app.database.connection import db
from inventory_app.services.stock_movement_service import StockMovementService
from inventory_app.database.models import Item, Requester, Requisition, RequisitionItem


def setup_temp_db(tmp_path):
    tmp_db_path = tmp_path / "test_inventory.db"
    if tmp_db_path.exists():
        tmp_db_path.unlink()
    db.db_path = tmp_db_path
    assert db.create_database() is True
    return tmp_db_path


def test_process_return_commits(tmp_path):
    setup_temp_db(tmp_path)

    # Create an item and a batch
    item = Item(name="Returnable", category_id=1)
    assert item.save(editor_name="tester", batch_quantity=1) is True

    # Create a requester and requisition
    requester = Requester(name="ReturnUser")
    assert requester.save() is True

    assert requester.id is not None

    req = Requisition()
    req.requester_id = cast(int, requester.id)
    assert req.save("tester") is True

    # Add a requisition item
    assert req.id is not None
    assert item.id is not None

    req_item = RequisitionItem()
    req_item.requisition_id = cast(int, req.id)
    req_item.item_id = cast(int, item.id)
    req_item.quantity_requested = 5
    assert req_item.save() is True

    svc = StockMovementService()

    # Process a simple return for this requisition
    return_data = [{"item_id": cast(int, item.id), "quantity_returned": 3}]
    assert svc.process_return(cast(int, req.id), return_data, "tester") is True

    # Verify RETURN movement was recorded
    rows = db.execute_query(
        "SELECT * FROM Stock_Movements WHERE source_id = ? AND movement_type = 'RETURN'",
        (cast(int, req.id),),
    )

    assert rows and rows[0]["quantity"] == 3


def test_process_return_rolls_back_on_failure(tmp_path, monkeypatch):
    setup_temp_db(tmp_path)

    # Create an item and requisition similarly
    item = Item(name="RollbackItem", category_id=1)
    assert item.save(editor_name="tester", batch_quantity=1) is True

    requester = Requester(name="RollbackUser")
    assert requester.save() is True
    assert requester.id is not None

    req = Requisition()
    req.requester_id = cast(int, requester.id)
    assert req.save("tester") is True

    svc = StockMovementService()

    # Monkeypatch record_return to raise an exception after first call
    calls = {"count": 0}

    def failing_record(item_id, qty, source_id, note, batch_id=None):
        calls["count"] += 1
        if calls["count"] > 1:
            raise Exception("simulated failure")
        # otherwise delegate to the real implementation
        return original_record(item_id, qty, source_id, note, batch_id)

    original_record = svc.record_return
    monkeypatch.setattr(svc, "record_return", failing_record)

    return_data = [
        {"item_id": cast(int, item.id), "quantity_returned": 1},
        {"item_id": cast(int, item.id), "quantity_returned": 1},
    ]

    assert svc.process_return(cast(int, req.id), return_data, "tester") is False

    # Ensure no RETURN movements exist due to rollback
    rows = db.execute_query(
        "SELECT * FROM Stock_Movements WHERE source_id = ? AND movement_type = 'RETURN'",
        (cast(int, req.id),),
    )
    assert not rows
