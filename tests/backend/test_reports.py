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
