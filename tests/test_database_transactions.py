"""Comprehensive tests for database transaction behavior.

Tests cover save/delete transaction rollbacks and concurrent access patterns
to ensure data consistency during operations on items, requisitions, and stock movements.
"""

import importlib.util
import threading
import sqlite3
import time
from pathlib import Path as _P
from typing import cast

import pytest

from inventory_app.database.connection import db
from inventory_app.database.models import (
    Item,
    Requisition,
    Requester,
    RequisitionItem,
)
from inventory_app.services.item_service import ItemService
from inventory_app.services.stock_movement_service import StockMovementService


# Dynamically load GUI modules for testing
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

_rp_path = str(
    _root
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


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for each test."""
    tmp_db_path = tmp_path / "test_inventory.db"
    tmp_db_path.parent.mkdir(parents=True, exist_ok=True)
    if tmp_db_path.exists():
        tmp_db_path.unlink()
    db.db_path = tmp_db_path
    assert db.create_database() is True
    yield tmp_db_path
    # Cleanup
    if tmp_db_path.exists():
        tmp_db_path.unlink()


# ============================================================================
# ITEM SAVE TRANSACTION TESTS
# ============================================================================


class TestItemSaveTransactions:
    """Test transaction rollback behavior for Item.save()."""

    def test_item_save_commits_with_batch(self, temp_db):
        """Item.save() should commit and create batch when successful."""
        item = Item(name="CommittableItem", category_id=1)
        saved = item.save(editor_name="tester", batch_quantity=5)
        assert saved is True
        assert item.id is not None and item.id > 0

        # Verify batch created
        batches = db.execute_query(
            "SELECT * FROM Item_Batches WHERE item_id = ?", (item.id,)
        )
        assert batches and batches[0]["quantity_received"] == 5

    def test_item_save_rolls_back_on_batch_failure(self, temp_db, monkeypatch):
        """Item.save() should rollback if batch creation fails."""
        item = Item(name="FailingItem", category_id=1)

        def fail_create_batches(self, qty):
            raise Exception("batch creation failed")

        monkeypatch.setattr(Item, "_create_batches", fail_create_batches)

        saved = item.save(editor_name="tester", batch_quantity=1)
        assert saved is False

        # Ensure no item was created in the database due to rollback
        rows = db.execute_query("SELECT * FROM Items WHERE name = ?", (item.name,))
        assert not rows


# ============================================================================
# REQUISITION SAVE TRANSACTION TESTS
# ============================================================================


class TestRequisitionSaveTransactions:
    """Test transaction rollback behavior for Requisition.save()."""

    def test_requisition_save_rolls_back_on_movement_failure(self, temp_db):
        """Requisition.save() should rollback if nested transaction fails."""
        # Create a requester first
        requester = Requester(name="ReqUser")
        assert requester.save() is True
        assert requester.id is not None

        # Attempt to create a requisition but raise an exception inside the transaction
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


# ============================================================================
# ITEM DELETE TRANSACTION TESTS
# ============================================================================


class TestItemDeleteTransactions:
    """Test transaction rollback behavior for Item.delete()."""

    def test_item_delete_rolls_back_on_failure(self, temp_db, monkeypatch):
        """Item.delete() should rollback if batch deletion fails."""
        # Create an item with a batch
        item = Item(name="DelItem", category_id=1)
        assert item.save(editor_name="tester", batch_quantity=2)
        assert item.id

        # Patch db.execute_update to raise when deleting Item_Batches
        orig = db.execute_update

        def patched_execute_update(query, params=(), return_last_id=False):
            if "DELETE FROM Item_Batches" in query:
                raise Exception("Simulated delete failure")
            return orig(query, params, return_last_id=return_last_id)

        db.execute_update = patched_execute_update  # type: ignore[method-assign]

        success = item.delete(editor_name="tester", reason="test")
        assert success is False

        # Ensure item still exists because transaction should have rolled back
        rows = db.execute_query("SELECT * FROM Items WHERE id = ?", (item.id,))
        assert rows

        # Restore
        db.execute_update = orig


# ============================================================================
# REQUISITION DELETE TRANSACTION TESTS
# ============================================================================


class TestRequisitionDeleteTransactions:
    """Test transaction rollback behavior for Requisition.delete()."""

    def test_requisition_delete_rolls_back_on_failure(self, temp_db, monkeypatch):
        """Requisition.delete() should rollback if item deletion fails."""
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
            return orig(query, params, return_last_id=return_last_id)

        db.execute_update = patched_execute_update  # type: ignore[method-assign]

        success = req.delete(editor_name="tester")
        assert success is False

        # Requisition should still exist
        rows = db.execute_query(
            "SELECT * FROM Requisitions WHERE id = ?", (int(req.id),)
        )
        assert rows

        # Restore
        db.execute_update = orig


# ============================================================================
# STOCK MOVEMENT TRANSACTION TESTS
# ============================================================================


class TestStockMovementTransactions:
    """Test transaction behavior for stock movements and reservations."""

    def test_create_stock_movements_insufficient_stock(self, temp_db):
        """Creating stock movement with insufficient stock should fail."""
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

        rows = db.execute_query(
            "SELECT * FROM Stock_Movements WHERE source_id = ?", (1,)
        )
        assert not rows

    def test_create_stock_movements_success(self, temp_db):
        """Creating stock movement with sufficient stock should succeed."""
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

    def test_concurrent_reservations_do_not_oversubscribe(self, temp_db):
        """Concurrent reservations should not exceed available stock."""
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


# ============================================================================
# RETURN PROCESSING TRANSACTION TESTS
# ============================================================================


class TestReturnProcessingTransactions:
    """Test transaction behavior for return processing."""

    def test_return_processing_rollback_on_movement_failure(self, temp_db, monkeypatch):
        """Return processing should rollback if movement insertion fails."""
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

        def patched_execute_update(
            query: str, params: tuple = (), *, return_last_id: bool = False
        ):
            if "Stock_Movements" in query and "CONSUMP" in str(params):
                raise Exception("Simulated movement insert failure")
            return orig(query, params, return_last_id=return_last_id)

        db.execute_update = patched_execute_update  # type: ignore[assignment]

        # Process returns should fail and rollback
        import warnings

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            success = rp.process_returns(int(req.id), return_items, "tester")
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

    def test_consumable_return_replaces_reservation_successfully(self, temp_db):
        """Consumable return should successfully replace RESERVATION with CONSUMPTION."""
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


# ============================================================================
# STOCK MOVEMENT SERVICE RETURN TESTS
# ============================================================================


class TestStockMovementServiceReturns:
    """Test transaction behavior in StockMovementService.process_return()."""

    def test_process_return_commits(self, temp_db):
        """process_return should commit and record RETURN movement when successful."""
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

    def test_process_return_rolls_back_on_failure(self, temp_db, monkeypatch):
        """process_return should rollback if any movement insertion fails."""
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
