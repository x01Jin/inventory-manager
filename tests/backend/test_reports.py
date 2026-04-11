import pytest
from datetime import date
from pathlib import Path
from openpyxl import load_workbook
from inventory_app.database.connection import db
from inventory_app.database.models import Item
from inventory_app.gui.reports.report_generator import ReportGenerator
from inventory_app.gui.reports.query_builder import ReportQueryBuilder
from inventory_app.gui.reports.data_sources import (
    get_defective_items_data,
    get_stock_levels_data,
    get_audit_log_data,
)


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for each test and ensure schema is applied."""
    db_file = tmp_path / "test_inventory.db"
    db.db_path = db_file
    assert db.create_database() is True
    yield db_file


def test_query_builder_logic():
    """Verify that ReportQueryBuilder correctly generates SQL and parameters."""
    builder = ReportQueryBuilder()
    start = date(2025, 1, 1)
    end = date(2025, 1, 5)

    # Test periodic query building
    query, params = builder.build_dynamic_report_query(start, end, "daily")

    # Verify parameterization (no string injection)
    assert query.count("?") == len(params)
    assert "r.lab_activity_date" in query

    # Verify period key generation
    from inventory_app.gui.reports.report_utils import date_formatter

    keys = date_formatter.get_period_keys(start, end, "daily")
    assert len(keys) == 5
    for k in keys:
        assert f'"{k}"' in query


def test_usage_report_generation(temp_db, tmp_path):
    """Verify end-to-call usage report generation to Excel."""
    # Setup data
    item_id = db.execute_update(
        "INSERT INTO Items (name, category_id) VALUES (?, ?)",
        ("Pencil", 1),
        return_last_id=True,
    )[1]
    reqr_id = db.execute_update(
        "INSERT INTO Requesters (name) VALUES (?)", ("Student",), return_last_id=True
    )[1]

    # Requisition on 2025-01-01
    req_id = db.execute_update(
        "INSERT INTO Requisitions (requester_id, status, lab_activity_date, lab_activity_name, expected_request, expected_return) VALUES (?, ?, ?, ?, ?, ?)",
        (
            reqr_id,
            "requested",
            "2025-01-01",
            "Test Activity",
            "2025-01-01 09:00:00",
            "2025-01-01 12:00:00",
        ),
        return_last_id=True,
    )[1]
    db.execute_update(
        "INSERT INTO Requisition_Items (requisition_id, item_id, quantity_requested) VALUES (?, ?, ?)",
        (req_id, item_id, 5),
    )

    gen = ReportGenerator()
    out_file = tmp_path / "usage.xlsx"
    result = gen.generate_report(
        date(2025, 1, 1), date(2025, 1, 1), output_path=str(out_file)
    )

    assert isinstance(result, str)
    assert Path(result).exists()
    wb = load_workbook(result)
    ws = wb.active
    assert ws is not None

    # Find Pencil row and verify total
    found = False
    for row in range(5, ws.max_row + 1):
        if ws.cell(row=row, column=1).value == "Pencil":
            # Total is usually the last column
            assert ws.cell(row=row, column=ws.max_column).value == 5
            found = True
            break
    assert found


def test_specialized_reports_data_retrieval(temp_db):
    """Verify data retrieval for specialized reports (Disposal, Defective)."""
    # Setup defective item
    item_id = db.execute_update(
        "INSERT INTO Items (name, category_id) VALUES (?, ?)",
        ("Broken Item", 1),
        return_last_id=True,
    )[1]
    # Setup defective item linked to a requisition
    reqr_id = db.execute_update(
        "INSERT INTO Requesters (name) VALUES (?)", ("Bob",), return_last_id=True
    )[1]
    req_id = db.execute_update(
        "INSERT INTO Requisitions (requester_id, status, lab_activity_date, lab_activity_name, expected_request, expected_return) VALUES (?, ?, ?, ?, ?, ?)",
        (
            reqr_id,
            "returned",
            "2025-01-01",
            "Returned Activity",
            "2025-01-01 09:00:00",
            "2025-01-01 12:00:00",
        ),
        return_last_id=True,
    )[1]

    db.execute_update(
        "INSERT INTO Defective_Items (item_id, requisition_id, quantity, notes, reported_by, reported_date) VALUES (?, ?, ?, ?, ?, ?)",
        (item_id, req_id, 1, "Cracked", "tester", "2025-01-01"),
    )

    data = get_defective_items_data(date(2025, 1, 1), date(2025, 1, 1))
    assert len(data) == 1
    assert data[0]["Item Name"] == "Broken Item"
    assert data[0]["Notes"] == "Cracked"


def test_update_history_report_integrity(temp_db):
    """Verify that update history is correctly logged and retrieved."""
    item_id = db.execute_update(
        "INSERT INTO Items (name, category_id) VALUES (?, ?)",
        ("HistoryItem", 1),
        return_last_id=True,
    )[1]

    # Simulate update via model to trigger history logging
    assert item_id is not None
    item = Item.get_by_id(item_id)
    assert item is not None
    item.name = "UpdatedName"
    assert item.save(editor_name="RefactorTester") is True

    # Check history table
    history = db.execute_query(
        "SELECT * FROM Update_History WHERE item_id = ?", (item_id,)
    )
    assert len(history) >= 1
    assert history[0]["editor_name"] == "RefactorTester"
    assert any(row.get("field_name") == "name" for row in history)
    matching = [row for row in history if row.get("field_name") == "name"]
    assert matching[0]["old_value"] == "HistoryItem"
    assert matching[0]["new_value"] == "UpdatedName"


def test_audit_log_data_source(temp_db):
    """Unified audit log dataset should include history and activity records."""
    created_item_id = db.execute_update(
        "INSERT INTO Items (name, category_id) VALUES (?, ?)",
        ("Audit Item", 1),
        return_last_id=True,
    )[1]
    assert created_item_id is not None
    item_id = created_item_id

    item = Item.get_by_id(item_id)
    assert item is not None
    item.name = "Audit Item Updated"
    assert item.save(editor_name="AuditTester") is True

    rows = get_audit_log_data(
        start_date=date(2020, 1, 1),
        end_date=date(2100, 1, 1),
        editor_filter="AuditTester",
    )

    assert rows
    assert any(r.get("Action") == "ITEM_UPDATE" for r in rows)
    assert any(r.get("Editor") == "AuditTester" for r in rows)


def test_task10_stock_levels_data_policy(temp_db):
    """Task 10: stock report reflects consumable depletion and non-consumable disposal only."""
    consumable_id = db.execute_update(
        "INSERT INTO Items (name, category_id, is_consumable) VALUES (?, ?, ?)",
        ("Report Consumable", 1, 1),
        return_last_id=True,
    )[1]
    non_consumable_id = db.execute_update(
        "INSERT INTO Items (name, category_id, is_consumable) VALUES (?, ?, ?)",
        ("Report NonConsumable", 1, 0),
        return_last_id=True,
    )[1]

    consumable_batch_id = db.execute_update(
        "INSERT INTO Item_Batches (item_id, batch_number, quantity_received, date_received) VALUES (?, ?, ?, ?)",
        (consumable_id, 1, 50, "2025-01-01"),
        return_last_id=True,
    )[1]
    non_consumable_batch_id = db.execute_update(
        "INSERT INTO Item_Batches (item_id, batch_number, quantity_received, date_received) VALUES (?, ?, ?, ?)",
        (non_consumable_id, 1, 20, "2025-01-01"),
        return_last_id=True,
    )[1]

    # Consumable final stock: 50 - 12 - 3 + 2 = 37
    db.execute_update(
        "INSERT INTO Stock_Movements (item_id, batch_id, movement_type, quantity, movement_date) VALUES (?, ?, ?, ?, ?)",
        (consumable_id, consumable_batch_id, "CONSUMPTION", 12, "2025-01-02"),
    )
    db.execute_update(
        "INSERT INTO Stock_Movements (item_id, batch_id, movement_type, quantity, movement_date) VALUES (?, ?, ?, ?, ?)",
        (consumable_id, consumable_batch_id, "DISPOSAL", 3, "2025-01-03"),
    )
    db.execute_update(
        "INSERT INTO Stock_Movements (item_id, batch_id, movement_type, quantity, movement_date) VALUES (?, ?, ?, ?, ?)",
        (consumable_id, consumable_batch_id, "RETURN", 2, "2025-01-04"),
    )

    # Non-consumable final stock: 20 - 5 = 15 (REQUEST/RETURN must not change stock)
    db.execute_update(
        "INSERT INTO Stock_Movements (item_id, batch_id, movement_type, quantity, movement_date) VALUES (?, ?, ?, ?, ?)",
        (non_consumable_id, non_consumable_batch_id, "REQUEST", 7, "2025-01-02"),
    )
    db.execute_update(
        "INSERT INTO Stock_Movements (item_id, batch_id, movement_type, quantity, movement_date) VALUES (?, ?, ?, ?, ?)",
        (non_consumable_id, non_consumable_batch_id, "RETURN", 7, "2025-01-03"),
    )
    db.execute_update(
        "INSERT INTO Stock_Movements (item_id, batch_id, movement_type, quantity, movement_date) VALUES (?, ?, ?, ?, ?)",
        (non_consumable_id, non_consumable_batch_id, "DISPOSAL", 5, "2025-01-05"),
    )

    rows = get_stock_levels_data()
    by_name = {row["Item Name"]: row for row in rows}

    assert by_name["Report Consumable"]["Current Stock"] == 37
    assert by_name["Report NonConsumable"]["Current Stock"] == 15
