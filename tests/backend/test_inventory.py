import sqlite3
import pytest
from datetime import date, datetime, timedelta
from inventory_app.database.connection import db
from inventory_app.database.models import (
    Supplier,
    check_case_insensitive_duplicate,
)
from inventory_app.services.category_config import (
    get_category_config,
    get_all_category_names,
)
from inventory_app.services.item_status_service import item_status_service
from inventory_app.services.validation_service import ValidationService


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

    for item_id in (apparatus_id, models_id):
        db.execute_update(
            "INSERT INTO Item_Batches (item_id, batch_number, quantity_received, date_received) VALUES (?, ?, ?, ?)",
            (item_id, 1, 1, today.isoformat()),
        )

    apparatus_status = item_status_service.get_item_status(apparatus_id)
    models_status = item_status_service.get_item_status(models_id)

    assert apparatus_status is not None
    assert models_status is not None
    assert "EXPIRING" in apparatus_status.status
    assert models_status.status == "OK"


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
