from inventory_app.database.connection import db
from inventory_app.database.models import Item, Requester, Requisition, RequisitionItem
import importlib.util
from pathlib import Path as _P

_root = _P(__file__).parent
_rp_path = str(
    _root
    / ".."
    / "inventory_app"
    / "gui"
    / "requisitions"
    / "requisition_management"
    / "return_processor.py"
)
spec = importlib.util.spec_from_file_location("return_processor", _rp_path)
assert spec is not None and spec.loader is not None
rp_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rp_mod)
ReturnProcessor = rp_mod.ReturnProcessor
ReturnItem = rp_mod.ReturnItem


def setup_temp_db(tmp_path):
    tmp_db_path = tmp_path / "test_inventory.db"
    tmp_db_path.parent.mkdir(parents=True, exist_ok=True)
    if tmp_db_path.exists():
        tmp_db_path.unlink()
    db.db_path = tmp_db_path
    assert db.create_database() is True
    return tmp_db_path


def test_return_processing_rollback_on_movement_failure(tmp_path):
    setup_temp_db(tmp_path)

    # Create requester, requisition, item and batch
    requester = Requester(name="ReturnUser")
    assert requester.save() is True
    assert requester.id is not None

    req = Requisition()
    req.requester_id = int(requester.id)
    assert req.save("tester") is True
    assert req.id is not None

    item = Item(name="ReturnItem", category_id=1)
    assert item.save(editor_name="tester", batch_quantity=1)
    assert item.id

    batch_rows = db.execute_query(
        "SELECT id FROM Item_Batches WHERE item_id = ?", (int(item.id),)
    )
    batch_id = batch_rows[0]["id"]

    # Add RequisitionItem and a RESERVATION movement
    assert req.id is not None
    assert item.id is not None
    ri = RequisitionItem(
        requisition_id=int(req.id), item_id=int(item.id), quantity_requested=1
    )
    assert ri.save() is True

    insert_query = "INSERT INTO Stock_Movements (item_id, batch_id, movement_type, quantity, movement_date, source_id) VALUES (?, ?, ?, ?, ?, ?)"
    db.execute_update(
        insert_query,
        (int(item.id), batch_id, "RESERVATION", 1, "2021-01-01", int(req.id)),
    )

    rp = ReturnProcessor()
    return_items = [
        ReturnItem(
            item_id=int(item.id),
            batch_id=batch_id,
            quantity_requested=1,
            quantity_returned=0,
            is_consumable=True,
        )
    ]

    # Patch db.execute_update to raise when inserting CONSUMPTION movement
    orig = db.execute_update

    from typing import Any

    def patched_execute_update(
        query: str, params: tuple = (), *, return_last_id: bool = False
    ) -> Any:
        if "Stock_Movements" in query and "CONSUMP" in str(params):
            raise Exception("Simulated movement insert failure")
        return orig(query, params, return_last_id=return_last_id)

    # Assigning a patched callable to the instance method is safe for this test but
    # Pylance's overload-aware typing may complain; silence it explicitly here.
    db.execute_update = patched_execute_update  # type: ignore[assignment]

    # Process returns should fail and rollback
    import warnings

    # Ensure a DeprecationWarning isn't triggered unexpectedly during this operation
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        success = rp.process_returns(int(req.id), return_items, "tester")
        # Validate there were no unexpected deprecation warnings here (the test isn't about deprecations)
        assert not any(isinstance(x.message, DeprecationWarning) for x in w)
    assert success is False

    # Ensure RESERVATION movement still exists (was not deleted)
    rows = db.execute_query(
        "SELECT * FROM Stock_Movements WHERE source_id = ?", (int(req.id),)
    )
    assert rows

    # Ensure requisition status is not 'returned'
    status_row = db.execute_query(
        "SELECT status FROM Requisitions WHERE id = ?", (int(req.id),)
    )
    assert status_row[0]["status"] != "returned"

    db.execute_update = orig


def test_consumable_return_replaces_reservation_successfully(tmp_path):
    setup_temp_db(tmp_path)

    # Create requester, requisition, item and batch
    requester = Requester(name="ReturnUser2")
    assert requester.save() is True
    assert requester.id is not None

    req = Requisition()
    req.requester_id = int(requester.id)
    assert req.save("tester") is True
    assert req.id is not None

    item = Item(name="ReturnItem2", category_id=1)
    assert item.save(editor_name="tester", batch_quantity=1)
    assert item.id

    batch_rows = db.execute_query(
        "SELECT id FROM Item_Batches WHERE item_id = ?", (int(item.id),)
    )
    batch_id = batch_rows[0]["id"]

    # Add RequisitionItem and a RESERVATION movement
    assert req.id is not None
    assert item.id is not None
    ri = RequisitionItem(
        requisition_id=int(req.id), item_id=int(item.id), quantity_requested=1
    )
    assert ri.save() is True

    insert_query = "INSERT INTO Stock_Movements (item_id, batch_id, movement_type, quantity, movement_date, source_id) VALUES (?, ?, ?, ?, ?, ?)"
    db.execute_update(
        insert_query,
        (int(item.id), batch_id, "RESERVATION", 1, "2021-01-01", int(req.id)),
    )

    rp = ReturnProcessor()
    return_items = [
        ReturnItem(
            item_id=int(item.id),
            batch_id=batch_id,
            quantity_requested=1,
            quantity_returned=0,
            is_consumable=True,
        )
    ]

    # Process returns should succeed and replace RESERVATION with CONSUMPTION
    success = rp.process_returns(int(req.id), return_items, "tester")
    assert success is True

    # Ensure there is a CONSUMPTION movement and no RESERVATION movement for this requisition
    rows = db.execute_query(
        "SELECT movement_type, quantity FROM Stock_Movements WHERE source_id = ?",
        (int(req.id),),
    )
    types = [r["movement_type"] for r in rows]
    assert "CONSUMPTION" in types
    assert "RESERVATION" not in types

    # Ensure requisition status updated to 'returned'
    status_row = db.execute_query(
        "SELECT status FROM Requisitions WHERE id = ?", (int(req.id),)
    )
    assert status_row[0]["status"] == "returned"
