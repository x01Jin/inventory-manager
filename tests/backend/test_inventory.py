import sqlite3
import pytest
from datetime import date, datetime, timedelta
from inventory_app.database.connection import db
from inventory_app.database.models import (
    Item,
    Supplier,
    check_case_insensitive_duplicate,
)
from inventory_app.services.category_config import (
    get_category_config,
    get_all_category_names,
)
from inventory_app.services.category_sync_service import sync_development_categories
from inventory_app.services.item_status_service import item_status_service
from inventory_app.services.validation_service import ValidationService
from inventory_app.gui.inventory.inventory_model import InventoryModel, ItemRow
from inventory_app.gui.inventory.inventory_controller import InventoryController


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for each test and ensure schema is applied."""
    db_file = tmp_path / "test_inventory.db"
    db.db_path = db_file
    assert db.create_database() is True
    yield db_file


def test_category_config_and_dates(temp_db):
    """Verify category configuration and automatic date calculations."""
    categories = get_all_category_names()
    assert "Chemicals-Solid" in categories
    assert "Equipment" in categories
    assert "Others" in categories
    assert "Uncategorized" in categories

    # Chemicals-Solid: 24 months
    config = get_category_config("Chemicals-Solid")
    assert config is not None
    acq_date = date(2025, 1, 1)
    exp_date = config.calculate_expiration_date(acq_date)
    assert exp_date == date(2027, 1, 1)

    # Equipment: 5 years disposal, 1 year calibration
    eq_config = get_category_config("Equipment")
    assert eq_config is not None
    disp_date = eq_config.calculate_expiration_date(acq_date)
    assert disp_date == date(2030, 1, 1)
    cal_date = eq_config.calculate_calibration_date(acq_date)
    assert cal_date == date(2026, 1, 1)

    # Others and Uncategorized: no auto lifecycle date
    others_config = get_category_config("Others")
    assert others_config is not None
    assert others_config.calculate_expiration_date(acq_date) is None

    uncategorized_config = get_category_config("Uncategorized")
    assert uncategorized_config is not None
    assert uncategorized_config.calculate_expiration_date(acq_date) is None


def test_duplicate_prevention(temp_db):
    """Verify case-insensitive duplicate prevention for suppliers and items."""
    # Supplier duplicate
    s1 = Supplier(name="Test supplier")
    s1.save()

    s2 = Supplier(name="TEST SUPPLIER")
    success, msg = s2.save()
    assert success is False
    assert "already exists" in msg.lower()

    # Size/Brand case-insensitive check
    # (Checking if the utility function used by models works)
    db.execute_update("INSERT INTO Sizes (name) VALUES (?)", ("10ml",))
    db.execute_update("INSERT INTO Brands (name) VALUES (?)", ("Pyrex",))

    has_dup, _ = check_case_insensitive_duplicate("Sizes", "10mL")
    assert has_dup is True

    has_dup, _ = check_case_insensitive_duplicate("Brands", "PYREX")
    assert has_dup is True


def test_item_likely_duplicate_lookup_is_category_scoped(temp_db):
    """Likely duplicates should match by normalized name within same category only."""
    same_category = Item(name="Beaker", category_id=1)
    assert same_category.save(editor_name="tester") is True

    other_category = Item(name="beaker", category_id=2)
    assert other_category.save(editor_name="tester") is True

    matches = Item.find_likely_duplicates("  BEAKER  ", 1)
    assert len(matches) == 1
    assert matches[0]["id"] == same_category.id

    excluded_matches = Item.find_likely_duplicates(
        "beaker", 1, exclude_id=same_category.id
    )
    assert excluded_matches == []


def test_stock_movement_logic(temp_db):
    """Verify stock movement types and service parameterization."""
    from inventory_app.services.stock_movement_service import StockMovementService

    svc = StockMovementService()

    # Create item and batch
    item_id = db.execute_update(
        "INSERT INTO Items (name, category_id) VALUES (?, ?)",
        ("StockItem", 1),
        return_last_id=True,
    )[1]
    assert isinstance(item_id, int)
    db.execute_update(
        "INSERT INTO Item_Batches (item_id, batch_number, quantity_received, date_received) VALUES (?, ?, ?, ?)",
        (item_id, 1, 100, "2025-01-01"),
    )

    # Record consumption
    svc.record_consumption(item_id, 20, None, "test")

    # Verify stock calculation
    # (Assuming query_total_stock exists in connection or we check movements directly)
    movements = db.execute_query(
        "SELECT SUM(quantity) as total FROM Stock_Movements WHERE item_id = ? AND movement_type = 'CONSUMPTION'",
        (item_id,),
    )
    assert movements[0]["total"] == 20

    # Verify invalid movement type is rejected by DB
    with pytest.raises(sqlite3.IntegrityError):
        db.execute_update(
            "INSERT INTO Stock_Movements (item_id, movement_type, quantity, movement_date) VALUES (?, ?, ?, ?)",
            (item_id, "INVALID", 1, "2025-01-01"),
        )


def test_validation_service_logic(temp_db):
    """Verify requisition and return validation logic."""
    svc = ValidationService()

    # Valid requisition
    start = datetime.now()
    end = start + timedelta(hours=2)
    requisition_data = {
        "expected_request": start.isoformat(),
        "expected_return": end.isoformat(),
        "lab_activity_name": "Test",
        "lab_activity_date": date.today().isoformat(),
    }
    items_data = [{"item_id": 1, "quantity_requested": 5}]
    assert svc.validate_requisition_creation(1, requisition_data, items_data) is True

    # Invalid: return before request
    requisition_data["expected_return"] = (start - timedelta(hours=1)).isoformat()
    assert svc.validate_requisition_creation(1, requisition_data, items_data) is False
    error = svc.get_last_error()
    assert error is not None and "after" in error

    # Invalid: required expected_return missing
    requisition_data["expected_return"] = ""
    assert svc.validate_requisition_creation(1, requisition_data, items_data) is False
    error = svc.get_last_error()
    assert error is not None and "expected_return" in error


def test_validation_service_accepts_legacy_requisition_date_keys(temp_db):
    """Legacy date_requested/date_return keys should still validate for compatibility."""
    svc = ValidationService()

    start = datetime.now()
    end = start + timedelta(hours=2)
    requisition_data = {
        "date_requested": start.isoformat(),
        "date_return": end.isoformat(),
        "lab_activity_name": "Compatibility Test",
        "lab_activity_date": date.today().isoformat(),
    }
    items_data = [{"item_id": 1, "quantity_requested": 1}]

    assert svc.validate_requisition_creation(1, requisition_data, items_data) is True


def test_cascade_delete_integrity(temp_db):
    """Verify that deleting an item removes all associated batches and movements."""
    # Item + Batch
    item_id = db.execute_update(
        "INSERT INTO Items (name, category_id) VALUES (?, ?)",
        ("DelItem", 1),
        return_last_id=True,
    )[1]
    db.execute_update(
        "INSERT INTO Item_Batches (item_id, batch_number, quantity_received, date_received) VALUES (?, ?, ?, ?)",
        (item_id, "B1", 10, "2025-01-01"),
    )
    db.execute_update(
        "INSERT INTO Stock_Movements (item_id, movement_type, quantity, movement_date) VALUES (?, ?, ?, ?)",
        (item_id, "CONSUMPTION", 2, "2025-01-01"),
    )

    # Delete item
    db.execute_update("DELETE FROM Items WHERE id = ?", (item_id,))

    # Check dependencies
    assert not db.execute_query(
        "SELECT * FROM Item_Batches WHERE item_id = ?", (item_id,)
    )
    assert not db.execute_query(
        "SELECT * FROM Stock_Movements WHERE item_id = ?", (item_id,)
    )


def test_varied_stock_movements(temp_db):
    """Verify all types of stock movements in StockMovementService."""
    from inventory_app.services.stock_movement_service import StockMovementService
    from inventory_app.services.movement_types import MovementType

    svc = StockMovementService()

    # Setup item and batch
    item_id = db.execute_update(
        "INSERT INTO Items (name, category_id) VALUES (?, ?)",
        ("MultiMoveItem", 1),
        return_last_id=True,
    )[1]
    assert item_id is not None
    db.execute_update(
        "INSERT INTO Item_Batches (item_id, batch_number, quantity_received, date_received) VALUES (?, ?, ?, ?)",
        (item_id, 1, 100, "2025-01-01"),
    )

    # Create requester and requisition for FK satisfaction
    reqr_id = db.execute_update(
        "INSERT INTO Requesters (name) VALUES (?)", ("MoveTester",), return_last_id=True
    )[1]
    req_id = db.execute_update(
        "INSERT INTO Requisitions (requester_id, expected_request, expected_return, status, lab_activity_name, lab_activity_date) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            reqr_id,
            "2025-01-01 00:00:00",
            "2025-01-01 00:00:00",
            "active",
            "Testing",
            "2025-01-01",
        ),
        return_last_id=True,
    )[1]
    assert req_id is not None

    # 1. RESERVATION
    svc.record_reservation(item_id, 10, source_id=req_id, note="tester")

    # 2. RETURN
    svc.record_return(item_id, 5, source_id=req_id, note="tester")

    # 3. DISPOSAL
    svc.record_disposal(item_id, 2, source_id=None, note="tester")

    # 4. REQUEST
    # Create another requisition for request if needed, or use the same one
    svc.record_request(item_id, 3, source_id=req_id, note="tester")

    # Verify records exist with correct types
    rows = db.execute_query(
        "SELECT movement_type, quantity FROM Stock_Movements WHERE item_id = ? ORDER BY id",
        (item_id,),
    )

    expected = [
        (MovementType.RESERVATION.value, 10),
        (MovementType.RETURN.value, 5),
        (MovementType.DISPOSAL.value, 2),
        (MovementType.REQUEST.value, 3),
    ]

    for i, (m_type, qty) in enumerate(expected):
        assert rows[i]["movement_type"] == m_type
        assert rows[i]["quantity"] == qty


def test_task10_stock_calculation_service_behavior(temp_db):
    """Task 10: consumables deplete permanently; non-consumables only lose stock on disposal."""
    from inventory_app.services.stock_calculation_service import (
        stock_calculation_service,
    )

    consumable_id = db.execute_update(
        "INSERT INTO Items (name, category_id, is_consumable) VALUES (?, ?, ?)",
        ("Task10 Consumable", 1, 1),
        return_last_id=True,
    )[1]
    assert consumable_id is not None
    consumable_batch_id = db.execute_update(
        "INSERT INTO Item_Batches (item_id, batch_number, quantity_received, date_received) VALUES (?, ?, ?, ?)",
        (consumable_id, 1, 100, "2025-01-01"),
        return_last_id=True,
    )[1]
    assert consumable_batch_id is not None

    non_consumable_id = db.execute_update(
        "INSERT INTO Items (name, category_id, is_consumable) VALUES (?, ?, ?)",
        ("Task10 NonConsumable", 1, 0),
        return_last_id=True,
    )[1]
    assert non_consumable_id is not None
    non_consumable_batch_id = db.execute_update(
        "INSERT INTO Item_Batches (item_id, batch_number, quantity_received, date_received) VALUES (?, ?, ?, ?)",
        (non_consumable_id, 1, 10, "2025-01-01"),
        return_last_id=True,
    )[1]
    assert non_consumable_batch_id is not None

    # Consumable: reservation does not affect stock, but consumption/disposal do.
    db.execute_update(
        "INSERT INTO Stock_Movements (item_id, batch_id, movement_type, quantity, movement_date) VALUES (?, ?, ?, ?, ?)",
        (consumable_id, consumable_batch_id, "RESERVATION", 15, "2025-01-02"),
    )
    db.execute_update(
        "INSERT INTO Stock_Movements (item_id, batch_id, movement_type, quantity, movement_date) VALUES (?, ?, ?, ?, ?)",
        (consumable_id, consumable_batch_id, "CONSUMPTION", 25, "2025-01-03"),
    )
    db.execute_update(
        "INSERT INTO Stock_Movements (item_id, batch_id, movement_type, quantity, movement_date) VALUES (?, ?, ?, ?, ?)",
        (consumable_id, consumable_batch_id, "RETURN", 5, "2025-01-04"),
    )
    db.execute_update(
        "INSERT INTO Stock_Movements (item_id, batch_id, movement_type, quantity, movement_date) VALUES (?, ?, ?, ?, ?)",
        (consumable_id, consumable_batch_id, "DISPOSAL", 3, "2025-01-05"),
    )

    # Non-consumable: request/return are temporary, disposal is permanent.
    db.execute_update(
        "INSERT INTO Stock_Movements (item_id, batch_id, movement_type, quantity, movement_date) VALUES (?, ?, ?, ?, ?)",
        (non_consumable_id, non_consumable_batch_id, "REQUEST", 4, "2025-01-02"),
    )
    db.execute_update(
        "INSERT INTO Stock_Movements (item_id, batch_id, movement_type, quantity, movement_date) VALUES (?, ?, ?, ?, ?)",
        (non_consumable_id, non_consumable_batch_id, "RETURN", 4, "2025-01-03"),
    )
    db.execute_update(
        "INSERT INTO Stock_Movements (item_id, batch_id, movement_type, quantity, movement_date) VALUES (?, ?, ?, ?, ?)",
        (non_consumable_id, non_consumable_batch_id, "DISPOSAL", 2, "2025-01-04"),
    )

    assert stock_calculation_service.calculate_total_stock(consumable_id) == 77
    assert stock_calculation_service.calculate_batch_stock(consumable_batch_id) == 77

    assert stock_calculation_service.calculate_total_stock(non_consumable_id) == 8
    assert stock_calculation_service.calculate_batch_stock(non_consumable_batch_id) == 8


def test_task12_inventory_filters_compose_correctly(temp_db):
    """Task 12: search/category/supplier/item-type/date filters must compose as intersection."""
    model = InventoryModel()
    model.set_items(
        [
            ItemRow(
                id=1,
                name="Beaker 500ml",
                category_name="Apparatus",
                item_type="Non-consumable",
                size="500ml",
                brand="Pyrex",
                supplier_name="ATR Trading System",
                other_specifications=None,
                po_number=None,
                expiration_date=None,
                calibration_date=None,
                is_consumable=False,
                acquisition_date=date(2024, 1, 10),
                last_modified=None,
                total_stock=10,
                available_stock=8,
            ),
            ItemRow(
                id=2,
                name="Beaker 250ml",
                category_name="Apparatus",
                item_type="Non-consumable",
                size="250ml",
                brand="Pyrex",
                supplier_name="Malcor Chemicals",
                other_specifications=None,
                po_number=None,
                expiration_date=None,
                calibration_date=None,
                is_consumable=False,
                acquisition_date=date(2024, 1, 10),
                last_modified=None,
                total_stock=12,
                available_stock=12,
            ),
            ItemRow(
                id=3,
                name="Hydrochloric Acid",
                category_name="Chemicals-Liquid",
                item_type="Consumable",
                size="1000ml",
                brand="Dalkem",
                supplier_name="ATR Trading System",
                other_specifications=None,
                po_number=None,
                expiration_date=date(2026, 1, 1),
                calibration_date=None,
                is_consumable=True,
                acquisition_date=date(2025, 1, 10),
                last_modified=None,
                total_stock=1000,
                available_stock=900,
            ),
        ]
    )

    model.apply_current_filters(
        search_term="beaker",
        category="Apparatus",
        supplier="ATR Trading System",
        item_type="Non-consumable",
        date_from=date(2024, 1, 1),
        date_to=date(2024, 12, 31),
    )

    filtered = model.get_filtered_items()
    assert len(filtered) == 1
    assert filtered[0].id == 1


def test_task12_item_usage_history_includes_defective_and_date_range(temp_db):
    """Task 12: item history includes usage + defective rows and respects date range."""
    item_id = db.execute_update(
        "INSERT INTO Items (name, category_id) VALUES (?, ?)",
        ("Task12 Item", 1),
        return_last_id=True,
    )[1]
    assert item_id is not None
    requester_id = db.execute_update(
        "INSERT INTO Requesters (name, grade_level, section) VALUES (?, ?, ?)",
        ("Student A", "Grade 8", "A"),
        return_last_id=True,
    )[1]
    assert requester_id is not None

    req_id = db.execute_update(
        "INSERT INTO Requisitions (requester_id, expected_request, expected_return, status, lab_activity_name, lab_activity_date) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            requester_id,
            "2025-01-05 09:00:00",
            "2025-01-05 11:00:00",
            "returned",
            "Acid-Base Lab",
            "2025-01-05",
        ),
        return_last_id=True,
    )[1]
    assert req_id is not None

    db.execute_update(
        "INSERT INTO Requisition_Items (requisition_id, item_id, quantity_requested) VALUES (?, ?, ?)",
        (req_id, item_id, 4),
    )
    db.execute_update(
        "INSERT INTO Defective_Items (item_id, requisition_id, quantity, notes, reported_by, reported_date) VALUES (?, ?, ?, ?, ?, ?)",
        (item_id, req_id, 1, "Cracked after use", "Custodian", "2025-01-06"),
    )

    controller = InventoryController()
    all_rows = controller.get_item_usage_history(item_id)
    assert len(all_rows) == 2
    assert {row["event_type"] for row in all_rows} == {"Usage", "Defective"}

    usage_only_rows = controller.get_item_usage_history(
        item_id,
        start_date=date(2025, 1, 5),
        end_date=date(2025, 1, 5),
    )
    assert len(usage_only_rows) == 1
    assert usage_only_rows[0]["event_type"] == "Usage"


def test_inventory_data_includes_defective_indicator_fields(temp_db):
    """Inventory data should expose defective flags and counts for row indicators."""
    item_id = db.execute_update(
        "INSERT INTO Items (name, category_id, is_consumable) VALUES (?, ?, ?)",
        ("Indicator Item", 1, 0),
        return_last_id=True,
    )[1]
    assert item_id is not None

    db.execute_update(
        "INSERT INTO Item_Batches (item_id, batch_number, quantity_received, date_received) VALUES (?, ?, ?, ?)",
        (item_id, 1, 2, "2026-01-01"),
    )

    requester_id = db.execute_update(
        "INSERT INTO Requesters (name) VALUES (?)",
        ("Indicator Requester",),
        return_last_id=True,
    )[1]
    assert requester_id is not None

    requisition_id = db.execute_update(
        "INSERT INTO Requisitions (requester_id, expected_request, expected_return, status, lab_activity_name, lab_activity_date) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            requester_id,
            "2026-01-02 09:00:00",
            "2026-01-02 10:00:00",
            "returned",
            "Indicator Lab",
            "2026-01-02",
        ),
        return_last_id=True,
    )[1]
    assert requisition_id is not None

    db.execute_update(
        "INSERT INTO Defective_Items (item_id, requisition_id, quantity, notes, reported_by, reported_date) VALUES (?, ?, ?, ?, ?, ?)",
        (
            item_id,
            requisition_id,
            2,
            "Broken handle",
            "custodian",
            "2026-01-02",
        ),
    )

    rows = InventoryController().load_inventory_data()
    target = next((row for row in rows if row["id"] == item_id), None)
    assert target is not None
    assert target["has_defective"] == 1
    assert target["defective_count"] == 2
    assert target["total_stock"] == 2
    assert target["available_stock"] == 0

    status = item_status_service.get_item_status(item_id)
    assert status is not None
    assert status.has_defective is True
    assert status.defective_count == 2

    # Aggregate total stock metric remains based on stock movements policy,
    # and only disposed confirmations permanently reduce total stock.
    batch_stats = InventoryController().get_batch_statistics()
    assert batch_stats["total_stock"] == 2


def test_inventory_controller_returns_defective_details(temp_db):
    """Defective details query should return descriptions and context for item rows."""
    item_id = db.execute_update(
        "INSERT INTO Items (name, category_id, is_consumable) VALUES (?, ?, ?)",
        ("Defective Detail Item", 1, 0),
        return_last_id=True,
    )[1]
    assert item_id is not None

    requester_id = db.execute_update(
        "INSERT INTO Requesters (name) VALUES (?)",
        ("Defective Detail Requester",),
        return_last_id=True,
    )[1]
    requisition_id = db.execute_update(
        "INSERT INTO Requisitions (requester_id, expected_request, expected_return, status, lab_activity_name, lab_activity_date) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            requester_id,
            "2026-01-03 09:00:00",
            "2026-01-03 11:00:00",
            "returned",
            "Glassware Activity",
            "2026-01-03",
        ),
        return_last_id=True,
    )[1]

    db.execute_update(
        "INSERT INTO Defective_Items (item_id, requisition_id, quantity, notes, reported_by, editor_name, reported_date) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            item_id,
            requisition_id,
            1,
            "Hairline crack on base",
            "custodian-a",
            "custodian-a",
            "2026-01-03",
        ),
    )

    rows = InventoryController().get_item_defective_details(item_id)
    assert len(rows) == 1
    assert rows[0]["quantity"] == 1
    assert rows[0]["notes"] == "Hairline crack on base"
    assert rows[0]["lab_activity"] == "Glassware Activity"
    assert rows[0]["requester_name"] == "Defective Detail Requester"


def test_defective_confirmation_actions_update_history_and_stock(temp_db):
    """Disposed/not-defective confirmations should be recorded and affect stock behavior correctly."""
    item_id = db.execute_update(
        "INSERT INTO Items (name, category_id, is_consumable) VALUES (?, ?, ?)",
        ("Defective Confirm Item", 1, 0),
        return_last_id=True,
    )[1]
    assert item_id is not None
    db.execute_update(
        "INSERT INTO Item_Batches (item_id, batch_number, quantity_received, date_received) VALUES (?, ?, ?, ?)",
        (item_id, 1, 5, "2026-01-01"),
    )
    requester_id = db.execute_update(
        "INSERT INTO Requesters (name) VALUES (?)",
        ("Confirm User",),
        return_last_id=True,
    )[1]
    assert requester_id is not None
    requisition_id = db.execute_update(
        "INSERT INTO Requisitions (requester_id, expected_request, expected_return, status, lab_activity_name, lab_activity_date) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            requester_id,
            "2026-01-02 09:00:00",
            "2026-01-02 10:00:00",
            "returned",
            "Confirm Activity",
            "2026-01-02",
        ),
        return_last_id=True,
    )[1]
    assert requisition_id is not None
    defective_id = db.execute_update(
        "INSERT INTO Defective_Items (item_id, requisition_id, quantity, notes, reported_by, editor_name, reported_date) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            item_id,
            requisition_id,
            3,
            "Potential crack",
            "custodian",
            "custodian",
            "2026-01-02",
        ),
        return_last_id=True,
    )[1]
    assert defective_id is not None

    controller = InventoryController()
    assert controller.apply_defective_action(
        defective_item_id=defective_id,
        action_type="NOT_DEFECTIVE",
        quantity=1,
        acted_by="reviewer-1",
        notes="Passed re-check",
    )
    assert controller.apply_defective_action(
        defective_item_id=defective_id,
        action_type="DISPOSED",
        quantity=2,
        acted_by="reviewer-1",
        notes="Confirmed cracked",
    )

    rows = controller.load_inventory_data()
    target = next((row for row in rows if row["id"] == item_id), None)
    assert target is not None
    assert target["defective_count"] == 0
    assert target["total_stock"] == 3

    history_rows = controller.get_item_usage_history(item_id)
    event_types = {row.get("event_type") for row in history_rows}
    assert "Disposed" in event_types
    assert "Not Defective" in event_types

    disposal_movements = db.execute_query(
        "SELECT quantity FROM Stock_Movements WHERE item_id = ? AND movement_type = ?",
        (item_id, "DISPOSAL"),
    )
    assert disposal_movements
    assert sum(int(row["quantity"]) for row in disposal_movements) == 2

    batch_stats = controller.get_batch_statistics()
    assert batch_stats["total_stock"] == 3

    activity_rows = db.execute_query(
        "SELECT activity_type, user_name, description FROM Activity_Log WHERE activity_type IN (?, ?) ORDER BY id ASC",
        ("DEFECTIVE_NOT_DEFECTIVE", "DEFECTIVE_DISPOSED"),
    )
    assert len(activity_rows) == 2
    assert activity_rows[0]["activity_type"] == "DEFECTIVE_NOT_DEFECTIVE"
    assert activity_rows[1]["activity_type"] == "DEFECTIVE_DISPOSED"
    assert all(row["user_name"] == "reviewer-1" for row in activity_rows)


def test_non_consumable_usage_history_includes_borrow_and_return_events(temp_db):
    """Non-consumables should include borrow/return/lost movement timeline in item history."""
    item_id = db.execute_update(
        "INSERT INTO Items (name, category_id, is_consumable) VALUES (?, ?, ?)",
        ("History Asset", 1, 0),
        return_last_id=True,
    )[1]
    assert item_id is not None
    requester_id = db.execute_update(
        "INSERT INTO Requesters (name, grade_level, section) VALUES (?, ?, ?)",
        ("Borrower", "Grade 9", "B"),
        return_last_id=True,
    )[1]
    assert requester_id is not None
    requisition_id = db.execute_update(
        "INSERT INTO Requisitions (requester_id, expected_request, expected_return, status, lab_activity_name, lab_activity_date) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            requester_id,
            "2026-01-04 09:00:00",
            "2026-01-04 11:00:00",
            "returned",
            "Asset Lab",
            "2026-01-04",
        ),
        return_last_id=True,
    )[1]
    assert requisition_id is not None
    db.execute_update(
        "INSERT INTO Requisition_Items (requisition_id, item_id, quantity_requested) VALUES (?, ?, ?)",
        (requisition_id, item_id, 3),
    )
    db.execute_update(
        "INSERT INTO Stock_Movements (item_id, movement_type, quantity, movement_date, source_id, note) VALUES (?, ?, ?, ?, ?, ?)",
        (item_id, "REQUEST", 3, "2026-01-04", requisition_id, "Borrowed for class"),
    )
    db.execute_update(
        "INSERT INTO Stock_Movements (item_id, movement_type, quantity, movement_date, source_id, note) VALUES (?, ?, ?, ?, ?, ?)",
        (item_id, "RETURN", 2, "2026-01-05", requisition_id, "Returned after class"),
    )

    rows = InventoryController().get_item_usage_history(item_id)
    event_types = {row["event_type"] for row in rows}
    assert "Usage" in event_types
    assert "Borrowed" in event_types
    assert "Returned" in event_types


def test_task10_inventory_stats_total_stock_deducts_finalized_usage(temp_db):
    """Inventory quick stats total stock should permanently deduct finalized consumable usage."""
    from inventory_app.gui.inventory.inventory_controller import InventoryController
    from inventory_app.gui.requisitions.requisition_management.return_processor import (
        ReturnItem,
        ReturnProcessor,
    )

    requester_id = db.execute_update(
        "INSERT INTO Requesters (name) VALUES (?)",
        ("Stats Tester",),
        return_last_id=True,
    )[1]
    assert requester_id is not None
    item_id = db.execute_update(
        "INSERT INTO Items (name, category_id, is_consumable) VALUES (?, ?, ?)",
        ("Stats Consumable", 1, 1),
        return_last_id=True,
    )[1]
    assert item_id is not None
    batch_id = db.execute_update(
        "INSERT INTO Item_Batches (item_id, batch_number, quantity_received, date_received) VALUES (?, ?, ?, ?)",
        (item_id, 1, 100, "2026-01-01"),
        return_last_id=True,
    )[1]
    assert batch_id is not None

    requisition_id = db.execute_update(
        "INSERT INTO Requisitions (requester_id, expected_request, expected_return, status, lab_activity_name, lab_activity_date) VALUES (?, ?, ?, ?, ?, ?)",
        (
            requester_id,
            "2026-01-02 09:00:00",
            "2026-01-02 12:00:00",
            "active",
            "Stats Lab",
            "2026-01-02",
        ),
        return_last_id=True,
    )[1]
    assert requisition_id is not None
    db.execute_update(
        "INSERT INTO Requisition_Items (requisition_id, item_id, quantity_requested) VALUES (?, ?, ?)",
        (requisition_id, item_id, 10),
    )
    db.execute_update(
        "INSERT INTO Stock_Movements (item_id, batch_id, movement_type, quantity, movement_date, source_id) VALUES (?, ?, ?, ?, ?, ?)",
        (item_id, batch_id, "RESERVATION", 10, "2026-01-02", requisition_id),
    )

    processor = ReturnProcessor()
    ok = processor.process_returns(
        requisition_id,
        [
            ReturnItem(
                item_id=item_id,
                batch_id=batch_id,
                quantity_requested=10,
                quantity_returned=0,
                is_consumable=True,
            )
        ],
        editor_name="tester",
    )
    assert ok is True

    stats = InventoryController().get_batch_statistics()
    assert stats["total_stock"] == 90


def test_non_consumable_disposal_uses_category_config(temp_db):
    """Status fallback disposal date must follow category_config policy per category."""
    today = date.today()

    categories = db.execute_query("SELECT id, name FROM Categories")
    cat_ids = {row["name"]: row["id"] for row in categories}

    apparatus_acq = (today - timedelta(days=(3 * 365) - 30)).isoformat()
    models_acq = (today - timedelta(days=(3 * 365) - 30)).isoformat()

    apparatus_id = db.execute_update(
        "INSERT INTO Items (name, category_id, is_consumable, acquisition_date) VALUES (?, ?, ?, ?)",
        ("Apparatus Policy Item", cat_ids["Apparatus"], 0, apparatus_acq),
        return_last_id=True,
    )[1]
    models_id = db.execute_update(
        "INSERT INTO Items (name, category_id, is_consumable, acquisition_date) VALUES (?, ?, ?, ?)",
        ("Model Policy Item", cat_ids["Lab Models"], 0, models_acq),
        return_last_id=True,
    )[1]

    assert isinstance(apparatus_id, int)
    assert isinstance(models_id, int)

    db.execute_update(
        "INSERT INTO Item_Batches (item_id, batch_number, quantity_received, date_received) VALUES (?, ?, ?, ?)",
        (apparatus_id, 1, 1, apparatus_acq),
    )
    db.execute_update(
        "INSERT INTO Item_Batches (item_id, batch_number, quantity_received, date_received) VALUES (?, ?, ?, ?)",
        (models_id, 1, 1, models_acq),
    )

    apparatus_status = item_status_service.get_item_status(apparatus_id)
    models_status = item_status_service.get_item_status(models_id)

    assert apparatus_status is not None
    assert models_status is not None
    assert "EXPIRING" in apparatus_status.status
    assert models_status.status == "OK"


def test_task7_per_batch_disposal_uses_oldest_risk_batch(temp_db):
    """Per-batch fallback should flag older risky batches even when item acquisition is newer."""
    today = date.today()

    categories = db.execute_query("SELECT id, name FROM Categories")
    cat_ids = {row["name"]: row["id"] for row in categories}

    # Keep item-level acquisition recent to prove batch-level fallback drives disposal status.
    item_id = db.execute_update(
        "INSERT INTO Items (name, category_id, is_consumable, acquisition_date) VALUES (?, ?, ?, ?)",
        ("Task7 Batch Apparatus", cat_ids["Apparatus"], 0, today.isoformat()),
        return_last_id=True,
    )[1]
    assert isinstance(item_id, int)

    old_batch_date = (today - timedelta(days=(3 * 365) - 20)).isoformat()
    recent_batch_date = (today - timedelta(days=30)).isoformat()

    db.execute_update(
        "INSERT INTO Item_Batches (item_id, batch_number, quantity_received, date_received) VALUES (?, ?, ?, ?)",
        (item_id, 1, 1, old_batch_date),
    )
    db.execute_update(
        "INSERT INTO Item_Batches (item_id, batch_number, quantity_received, date_received) VALUES (?, ?, ?, ?)",
        (item_id, 2, 1, recent_batch_date),
    )

    status = item_status_service.get_item_status(item_id)
    assert status is not None
    assert "EXPIRING" in status.status
    assert status.batch_label == "B1"


def test_non_calibration_category_ignores_calibration_alerts(temp_db):
    """Calibration status should only apply to categories configured for calibration."""
    today = date.today()

    categories = db.execute_query("SELECT id, name FROM Categories")
    cat_ids = {row["name"]: row["id"] for row in categories}

    item_id = db.execute_update(
        """
        INSERT INTO Items (name, category_id, is_consumable, calibration_date, acquisition_date)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "Apparatus Calibration Should Be Ignored",
            cat_ids["Apparatus"],
            0,
            (today - timedelta(days=330)).isoformat(),
            today.isoformat(),
        ),
        return_last_id=True,
    )[1]

    assert isinstance(item_id, int)

    db.execute_update(
        "INSERT INTO Item_Batches (item_id, batch_number, quantity_received, date_received) VALUES (?, ?, ?, ?)",
        (item_id, 1, 1, today.isoformat()),
    )

    status = item_status_service.get_item_status(item_id)
    assert status is not None
    assert "CAL_WARNING" not in status.status
    assert "CAL_DUE" not in status.status


def test_category_sync_remaps_legacy_labels(temp_db):
    """Legacy category labels should be remapped to canonical categories."""
    result = db.execute_update(
        "INSERT INTO Categories (name) VALUES (?)",
        ("Chemicals - Solid",),
        return_last_id=True,
    )
    assert isinstance(result, tuple)
    _, legacy_category_id = result
    assert legacy_category_id is not None

    item_result = db.execute_update(
        "INSERT INTO Items (name, category_id, is_consumable) VALUES (?, ?, ?)",
        ("Legacy Cat Item", legacy_category_id, 1),
        return_last_id=True,
    )
    assert isinstance(item_result, tuple)
    _, item_id = item_result
    assert item_id is not None

    assert sync_development_categories() is True

    legacy_rows = db.execute_query(
        "SELECT id FROM Categories WHERE name = ?",
        ("Chemicals - Solid",),
    )
    assert not legacy_rows

    canonical_rows = db.execute_query(
        "SELECT id FROM Categories WHERE name = ?",
        ("Chemicals-Solid",),
    )
    assert canonical_rows
    canonical_id = canonical_rows[0]["id"]

    item_rows = db.execute_query(
        "SELECT category_id FROM Items WHERE id = ?",
        (item_id,),
    )
    assert item_rows
    assert item_rows[0]["category_id"] == canonical_id
