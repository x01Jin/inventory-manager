import importlib.util
from pathlib import Path as _P
from inventory_app.database.connection import db
from inventory_app.database.models import (
    Item,
    Requisition,
    Requester,
    RequisitionItem,
)
import threading
import sqlite3
import time
from inventory_app.services.item_service import ItemService

_root = _P(__file__).parent.parent
_item_selection_path = str(
    _root
    / "inventory_app"
    / "gui"
    / "requisitions"
    / "requisition_management"
    / "item_selection_manager.py"
)
spec = importlib.util.spec_from_file_location(
    "item_selection_manager", _item_selection_path
)
assert spec is not None and spec.loader is not None
item_selection_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(item_selection_mod)
ItemSelectionManager = item_selection_mod.ItemSelectionManager


def setup_temp_db(tmp_path):
    tmp_db_path = tmp_path / "test_inventory.db"
    tmp_db_path.parent.mkdir(parents=True, exist_ok=True)
    if tmp_db_path.exists():
        tmp_db_path.unlink()
    db.db_path = tmp_db_path
    assert db.create_database() is True
    return tmp_db_path


def test_create_stock_movements_insufficient_stock(tmp_path):
    setup_temp_db(tmp_path)

    # Create an item and a single batch with quantity 2
    item = Item(name="ReserveItem", category_id=1)
    assert item.save(editor_name="tester", batch_quantity=2)
    assert item.id is not None
    item_id = int(item.id)

    # Prepare selection requesting 3 units (more than available)
    selected = [
        {
            "item_id": item_id,
            "batch_id": 1,
            "quantity": 3,
            "item_name": item.name,
            "batch_number": 1,
        }
    ]

    # Create a requisition record so FK on Stock_Movements.source_id can reference it
    requester = Requester(name="ResUser")
    assert requester.save() is True
    assert requester.id is not None
    req = Requisition()
    req.requester_id = int(requester.id)
    assert req.save("tester") is True
    assert req.id is not None
    req_id = int(req.id)

    service = ItemService()
    manager = ItemSelectionManager(service)

    success = manager.create_stock_movements_for_requisition(req_id, selected)
    assert success is False

    rows = db.execute_query("SELECT * FROM Stock_Movements WHERE source_id = ?", (1,))
    assert not rows


def test_create_stock_movements_success(tmp_path):
    setup_temp_db(tmp_path)

    item = Item(name="ReserveItem2", category_id=1)
    assert item.save(editor_name="tester", batch_quantity=5)
    assert item.id is not None
    item_id = int(item.id)

    selected = [
        {
            "item_id": item_id,
            "batch_id": 1,
            "quantity": 3,
            "item_name": item.name,
            "batch_number": 1,
        }
    ]

    # Create requisition record for FK reference
    requester = Requester(name="ResUser2")
    assert requester.save() is True
    assert requester.id is not None
    req = Requisition()
    req.requester_id = int(requester.id)
    assert req.save("tester") is True
    assert req.id is not None
    req_id = int(req.id)

    service = ItemService()
    manager = ItemSelectionManager(service)

    success = manager.create_stock_movements_for_requisition(req_id, selected)
    assert success is True

    rows = db.execute_query(
        "SELECT * FROM Stock_Movements WHERE source_id = ?", (req_id,)
    )
    assert rows and rows[0]["quantity"] == 3


def test_concurrent_reservations_do_not_oversubscribe(tmp_path):
    """Simulate two concurrent reservation attempts against the same batch.

    Both threads will request 3 units from a batch with total 5 units.
    The concurrency control should prevent oversubscription so only one
    request succeeds and total reserved quantity <= 5.
    """
    setup_temp_db(tmp_path)

    item = Item(name="ConcurrentItem", category_id=1)
    assert item.save(editor_name="tester", batch_quantity=5)
    assert item.id is not None
    item_id = int(item.id)

    # Prepare selection template
    selected_template = {
        "item_id": item_id,
        "batch_id": 1,
        "item_name": item.name,
        "batch_number": 1,
    }

    requester1 = Requester(name="ConcurrentUser1")
    requester2 = Requester(name="ConcurrentUser2")
    assert requester1.save() is True
    assert requester2.save() is True
    assert requester1.id is not None
    assert requester2.id is not None
    r1_id = int(requester1.id)
    r2_id = int(requester2.id)

    service = ItemService()
    manager = ItemSelectionManager(service)

    results: list[bool] = [False, False]

    def attempt_reservation(requester_id: int, qty: int, idx: int):
        # Try to acquire an IMMEDIATE transaction and create a requisition
        attempts = 0
        while True:
            try:
                from datetime import datetime

                with db.transaction(immediate=True):
                    # Create requisition and item inside the transaction
                    req = Requisition()
                    req.requester_id = requester_id
                    req.expected_request = datetime.now()
                    req.expected_return = datetime.now()
                    req.status = "requested"
                    assert req.save("tester") is True
                    assert req.id is not None

                    ri = RequisitionItem()
                    assert req.id is not None
                    req_id = int(req.id)
                    ri.requisition_id = req_id
                    ri.item_id = item_id
                    ri.quantity_requested = qty
                    assert ri.save() is True

                    selected = [dict(selected_template, quantity=qty)]

                    # This will re-check availability inside the IMMEDIATE transaction
                    ok = manager.create_stock_movements_for_requisition(
                        req_id, selected
                    )
                    if not ok:
                        # Simulate caller treating a movement failure as transaction failure
                        raise Exception("movement_failed")

                results[idx] = True
                return
            except sqlite3.OperationalError as e:
                # database locked may occur when two IMMEDIATE transactions race; retry briefly
                if "database is locked" in str(e).lower() and attempts < 10:
                    attempts += 1
                    time.sleep(0.05)
                    continue
                results[idx] = False
                return
            except Exception:
                results[idx] = False
                return

    t1 = threading.Thread(target=attempt_reservation, args=(r1_id, 3, 0))
    t2 = threading.Thread(target=attempt_reservation, args=(r2_id, 3, 1))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Exactly one should succeed (or at least the total reserved should not exceed 5)
    reserved_rows = db.execute_query(
        "SELECT SUM(quantity) as total_reserved FROM Stock_Movements WHERE batch_id = ?",
        (1,),
    )
    total_reserved = (
        reserved_rows[0]["total_reserved"]
        if reserved_rows and reserved_rows[0]["total_reserved"]
        else 0
    )
    assert total_reserved <= 5
    assert (results.count(True) == 1) or (
        results.count(True) == 2 and total_reserved <= 5
    )
