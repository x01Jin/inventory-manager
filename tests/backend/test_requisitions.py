import pytest
from datetime import datetime, date
from inventory_app.database.connection import db
from inventory_app.database.models import Requisition
from inventory_app.gui.requisitions.requisitions_model import RequisitionsModel


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for each test and ensure schema is applied."""
    db_file = tmp_path / "test_inventory.db"
    db.db_path = db_file
    assert db.create_database() is True
    yield db_file


def test_requisition_model_instantiation():
    """Verify Requisition model defaults and date handling."""
    req = Requisition()
    assert req.expected_request.tzinfo is not None
    assert isinstance(req.lab_activity_date, date)

    # Verify fresh instances get fresh times
    import time

    time.sleep(0.01)
    req2 = Requisition()
    assert req.expected_request != req2.expected_request


def test_requisition_save_and_retrieve(temp_db):
    """Verify saving and retrieving requisitions with date parsing."""
    # Setup requester
    requester_id = db.execute_update(
        "INSERT INTO Requesters (name) VALUES (?)", ("Test User",), return_last_id=True
    )[1]
    assert requester_id is not None

    # Save requisition
    req = Requisition()
    req.requester_id = requester_id
    req.status = "requested"
    req.lab_activity_name = "Chemistry 101"
    req.lab_activity_date = date(2025, 5, 20)
    assert req.save("tester") is True

    # Retrieve and check date parsing
    retrieved = Requisition.get_all()
    assert len(retrieved) == 1
    assert retrieved[0].lab_activity_name == "Chemistry 101"
    assert retrieved[0].lab_activity_date == date(2025, 5, 20)
    assert isinstance(retrieved[0].expected_request, datetime)

    # Update and verify field-level requisition history.
    req.lab_activity_name = "Chemistry 102"
    assert req.save("tester") is True
    history_rows = db.execute_query(
        "SELECT field_name, old_value, new_value FROM Requisition_History WHERE requisition_id = ? ORDER BY id DESC",
        (req.id,),
    )
    assert any(row["field_name"] == "lab_activity_name" for row in history_rows)


def test_requisition_html_generation(temp_db):
    """Verify HTML generation logic for printing requisitions."""
    from inventory_app.gui.requisitions.requisitions_page import RequisitionsPage

    # Create sample data in DB
    item_id = db.execute_update(
        "INSERT INTO Items (name, category_id) VALUES (?, ?)",
        ("Test Item", 1),
        return_last_id=True,
    )[1]
    requester_id = db.execute_update(
        "INSERT INTO Requesters (name, requester_type) VALUES (?, ?)",
        ("Bob", "teacher"),
        return_last_id=True,
    )[1]
    req_id = db.execute_update(
        "INSERT INTO Requisitions (requester_id, expected_request, expected_return, status, lab_activity_name, lab_activity_date) VALUES (?, ?, ?, ?, ?, ?)",
        (
            requester_id,
            "2025-01-01 09:00:00",
            "2025-01-01 12:00:00",
            "requested",
            "Lab Test",
            "2025-01-01",
        ),
        return_last_id=True,
    )[1]
    assert isinstance(req_id, int)
    db.execute_update(
        "INSERT INTO Requisition_Items (requisition_id, item_id, quantity_requested) VALUES (?, ?, ?)",
        (req_id, item_id, 2),
    )

    # We need a summary object as expected by RequisitionsPage._generate_requisition_html
    # Usually this comes from the model's data loading
    model = RequisitionsModel()
    model.load_data()
    req_summary = model.get_requisition_by_id(req_id)

    assert req_summary is not None
    html = RequisitionsPage._generate_requisition_html(req_summary)

    assert "Lab Test" in html
    assert "Test Item" in html
    assert "REQUESTED" in html.upper()


def test_item_po_field_persistence(temp_db):
    """Verify that the Purchase Order field is persisted in the Items table."""
    item_id = db.execute_update(
        "INSERT INTO Items (name, category_id, po_number) VALUES (?, ?, ?)",
        ("Ordered Item", 1, "PO-12345"),
        return_last_id=True,
    )[1]

    row = db.execute_query("SELECT po_number FROM Items WHERE id = ?", (item_id,))[0]
    assert row["po_number"] == "PO-12345"

    # Check optionality
    item_id2 = db.execute_update(
        "INSERT INTO Items (name, category_id) VALUES (?, ?)",
        ("No PO Item", 1),
        return_last_id=True,
    )[1]
    row2 = db.execute_query("SELECT po_number FROM Items WHERE id = ?", (item_id2,))[0]
    assert row2["po_number"] is None


def test_requisition_lifecycle(temp_db):
    """Verify requisition state transitions and stock movements."""
    from inventory_app.services.requisition_service import RequisitionService
    from inventory_app.services.movement_types import MovementType
    from inventory_app.services.item_service import ItemService
    from inventory_app.services.stock_calculation_service import (
        stock_calculation_service,
    )

    svc = RequisitionService()

    # 1. Setup Requester, Item and Batch
    reqr_id = db.execute_update(
        "INSERT INTO Requesters (name) VALUES (?)", ("Prof. X",), return_last_id=True
    )[1]
    assert reqr_id is not None
    # Retrieve existing category IDs
    cat_id = db.execute_query(
        "SELECT id FROM Categories WHERE name = 'Chemicals-Solid'"
    )[0]["id"]
    asset_cat_id = db.execute_query(
        "SELECT id FROM Categories WHERE name = 'Equipment'"
    )[0]["id"]

    # Consumable
    item_id = db.execute_update(
        "INSERT INTO Items (name, category_id, is_consumable) VALUES (?, ?, ?)",
        ("Ethanol", cat_id, 1),
        return_last_id=True,
    )[1]
    assert item_id is not None
    batch_id = db.execute_update(
        "INSERT INTO Item_Batches (item_id, batch_number, quantity_received, date_received) VALUES (?, ?, ?, ?)",
        (item_id, 1, 10, "2025-01-01"),
        return_last_id=True,
    )[1]
    assert batch_id is not None

    # Non-consumable
    asset_id = db.execute_update(
        "INSERT INTO Items (name, category_id, is_consumable) VALUES (?, ?, ?)",
        ("Beaker", asset_cat_id, 0),
        return_last_id=True,
    )[1]
    assert asset_id is not None
    asset_batch_id = db.execute_update(
        "INSERT INTO Item_Batches (item_id, batch_number, quantity_received, date_received) VALUES (?, ?, ?, ?)",
        (asset_id, 1, 5, "2025-01-01"),
        return_last_id=True,
    )[1]
    assert asset_batch_id is not None

    # 2. Create Requisition (Requested)
    items_data = [
        {"item_id": item_id, "batch_id": batch_id, "quantity": 2},
        {"item_id": asset_id, "batch_id": asset_batch_id, "quantity": 3},
    ]

    req_id = svc.create_requisition(
        requester_id=reqr_id,
        items=items_data,
        expected_request=datetime.now(),
        expected_return=datetime.now(),
        lab_activity_name="Chemistry",
        user_name="tester",
    )
    assert req_id is not None

    # Verify reservation and request movements
    movements = db.execute_query(
        "SELECT item_id, movement_type, quantity FROM Stock_Movements WHERE source_id = ?",
        (req_id,),
    )
    assert any(
        m["item_id"] == item_id
        and m["movement_type"] == MovementType.RESERVATION.value
        and m["quantity"] == 2
        for m in movements
    )
    assert any(
        m["item_id"] == asset_id
        and m["movement_type"] == MovementType.REQUEST.value
        and m["quantity"] == 3
        for m in movements
    )

    # 3. Update status to active
    assert svc.update_status(req_id, "active", user_name="tester") is True

    # Task 10: availability drops while requested/borrowed, stock baseline remains policy-based.
    item_service = ItemService()
    assert item_service._get_available_stock_for_batch(batch_id) == 8
    assert item_service._get_available_stock_for_batch(asset_batch_id) == 2

    # 4. Finalize Return (Returned)
    # Consumable: Consume 1, Return 1
    # Asset: Return 2, Lose 1
    return_items = [
        {
            "item_id": item_id,
            "batch_id": batch_id,
            "quantity_requested": 2,
            "quantity_returned": 1,
            "is_consumable": True,
        },
        {
            "item_id": asset_id,
            "batch_id": asset_batch_id,
            "quantity_requested": 3,
            "quantity_lost": 1,
            "is_consumable": False,
        },
    ]
    assert svc.process_return(req_id, return_items, user_name="tester") is True

    # Verify final state
    req_row = db.execute_query(
        "SELECT status FROM Requisitions WHERE id = ?", (req_id,)
    )[0]
    assert req_row["status"] == "returned"

    # Verify movements are replaced correctly
    movements = db.execute_query(
        "SELECT item_id, movement_type, quantity FROM Stock_Movements WHERE source_id = ?",
        (req_id,),
    )
    # No RESERVATION or REQUEST anymore
    assert not any(
        m["movement_type"]
        in [MovementType.RESERVATION.value, MovementType.REQUEST.value]
        for m in movements
    )
    # 1 CONSUMPTION for ethanol
    assert any(
        m["item_id"] == item_id
        and m["movement_type"] == MovementType.CONSUMPTION.value
        and m["quantity"] == 1
        for m in movements
    )
    # 1 DISPOSAL for beaker
    assert any(
        m["item_id"] == asset_id
        and m["movement_type"] == MovementType.DISPOSAL.value
        and m["quantity"] == 1
        for m in movements
    )

    # Task 10 stock assertions after final return processing
    assert stock_calculation_service.calculate_total_stock(item_id) == 9
    assert stock_calculation_service.calculate_total_stock(asset_id) == 4


def test_defective_return_records_activity_event(temp_db):
    """Defective return processing should create a dedicated activity entry."""
    from inventory_app.gui.requisitions.requisition_management.return_processor import (
        ReturnItem,
        ReturnProcessor,
    )

    requester_id = db.execute_update(
        "INSERT INTO Requesters (name) VALUES (?)",
        ("Defect Activity User",),
        return_last_id=True,
    )[1]
    assert requester_id is not None

    item_id = db.execute_update(
        "INSERT INTO Items (name, category_id, is_consumable) VALUES (?, ?, ?)",
        ("Defect Activity Item", 1, 0),
        return_last_id=True,
    )[1]
    assert item_id is not None

    batch_id = db.execute_update(
        "INSERT INTO Item_Batches (item_id, batch_number, quantity_received, date_received) VALUES (?, ?, ?, ?)",
        (item_id, 1, 3, "2026-01-01"),
        return_last_id=True,
    )[1]
    assert batch_id is not None

    requisition_id = db.execute_update(
        "INSERT INTO Requisitions (requester_id, expected_request, expected_return, status, lab_activity_name, lab_activity_date) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            requester_id,
            "2026-01-02 08:00:00",
            "2026-01-02 12:00:00",
            "active",
            "Defect Log Activity",
            "2026-01-02",
        ),
        return_last_id=True,
    )[1]
    assert requisition_id is not None

    db.execute_update(
        "INSERT INTO Requisition_Items (requisition_id, item_id, quantity_requested) VALUES (?, ?, ?)",
        (requisition_id, item_id, 2),
    )
    db.execute_update(
        "INSERT INTO Stock_Movements (item_id, batch_id, movement_type, quantity, movement_date, source_id) VALUES (?, ?, ?, ?, ?, ?)",
        (item_id, batch_id, "REQUEST", 2, "2026-01-02", requisition_id),
    )

    ok = ReturnProcessor().process_returns(
        requisition_id,
        [
            ReturnItem(
                item_id=item_id,
                batch_id=batch_id,
                quantity_requested=2,
                quantity_lost=0,
                quantity_defective=1,
                is_consumable=False,
                defective_notes="Chip on rim",
            )
        ],
        editor_name="qa-user",
    )
    assert ok is True

    activity_rows = db.execute_query(
        "SELECT activity_type, description, entity_id, entity_type, user_name FROM Activity_Log "
        "WHERE activity_type = ? ORDER BY id DESC LIMIT 1",
        ("ITEM_MARKED_DEFECTIVE",),
    )
    assert activity_rows
    assert activity_rows[0]["entity_id"] == item_id
    assert activity_rows[0]["entity_type"] == "item"
    assert activity_rows[0]["user_name"] == "qa-user"
