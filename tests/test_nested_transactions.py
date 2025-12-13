from inventory_app.database.connection import db
from inventory_app.database.models import Item, Requester, Requisition, RequisitionItem
from inventory_app.services.item_service import ItemService
import importlib.util
from pathlib import Path as _P

_root = _P(__file__).parent
_item_selection_path = str(
    _root
    / ".."
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


def test_create_stock_movements_nested_transaction_rolls_back_on_failure(tmp_path):
    setup_temp_db(tmp_path)

    # Set up requester, requisition, item
    requester = Requester(name="NestedUser")
    assert requester.save() is True
    assert requester.id is not None
    req = Requisition()
    req.requester_id = int(requester.id)
    assert req.save("tester") is True

    item = Item(name="NestedItem", category_id=1)
    assert item.save(editor_name="tester", batch_quantity=1)

    # Create a RequisitionItem and a pre-existing RESERVATION movement
    assert req.id is not None
    assert item.id is not None
    ri = RequisitionItem(
        requisition_id=int(req.id), item_id=int(item.id), quantity_requested=1
    )
    assert ri.save() is True

    batch_rows = db.execute_query(
        "SELECT id FROM Item_Batches WHERE item_id = ?", (int(item.id),)
    )
    batch_id = batch_rows[0]["id"]

    insert_query = "INSERT INTO Stock_Movements (item_id, batch_id, movement_type, quantity, movement_date, source_id) VALUES (?, ?, ?, ?, ?, ?)"
    db.execute_update(
        insert_query,
        (int(item.id), batch_id, "RESERVATION", 1, "2021-01-01", int(req.id)),
    )

    manager = ItemSelectionManager(ItemService())
    selected = [
        {
            "item_id": int(item.id),
            "batch_id": batch_id,
            "item_name": item.name,
            "batch_number": "B1",
            "quantity": 1,
            "category_name": "Cat",
        }
    ]

    orig = db.execute_update

    def patched_execute_update(query, params=(), return_last_id=False):
        # Simulate a failure when attempting to insert new Stock_Movements
        if "Stock_Movements" in query and "VALUES" in query:
            raise Exception("Simulated insert failure")
        return orig(query, params, return_last_id)

    db.execute_update = patched_execute_update

    # Perform deletion and movement creation inside a transaction; ensure it rolls back
    from inventory_app.database.connection import db as global_db

    try:
        with global_db.transaction(immediate=True):
            # Delete existing movements for reorder
            db.execute_update(
                "DELETE FROM Stock_Movements WHERE source_id = ?", (int(req.id),)
            )
            # This should raise and bubble up (no nested transaction)
            manager.create_stock_movements_for_requisition(int(req.id), selected)
    except Exception:
        pass

    # After rollback, the original RESERVATION movement should still exist
    rows = db.execute_query(
        "SELECT * FROM Stock_Movements WHERE source_id = ?", (int(req.id),)
    )
    assert rows

    db.execute_update = orig
