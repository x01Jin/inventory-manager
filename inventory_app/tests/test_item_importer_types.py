import pytest
from openpyxl import Workbook
from inventory_app.services.item_importer import import_items_from_excel
from inventory_app.database.connection import db


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for each test."""
    tmp_db_path = tmp_path / "test_inventory.db"
    if tmp_db_path.exists():
        tmp_db_path.unlink()
    # Save original path to restore later
    old_path = db.db_path
    db.db_path = tmp_db_path
    db.create_database()
    yield tmp_db_path
    # Restore original path
    db.db_path = old_path
    if tmp_db_path.exists():
        try:
            tmp_db_path.unlink()
        except PermissionError:
            pass


def _write_workbook(path):
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.append(["name", "stocks", "item type"])  # header
    ws.append(["Item A", "1", "Consumables"])
    ws.append(["Item B", "2", "TA, non consumable"])
    ws.append(["Item C", "500ml", "TA, Consumables"])
    wb.save(path)


def test_importer_item_type_variants(tmp_path, temp_db):
    p = tmp_path / "types.xlsx"
    _write_workbook(str(p))

    imported, messages = import_items_from_excel(str(p), editor_name="tester")
    assert imported == 3

    # Ensure the messages include the size for the 500ml row
    assert any("size=500ml" in (m.lower()) for m in messages)

    # Verify DB entries and is_consumable flags
    rows = db.execute_query(
        "SELECT name, is_consumable, size FROM Items WHERE name IN ('Item A','Item B','Item C')"
    )
    assert rows and len(rows) == 3
    mapping = {r["name"]: r for r in rows}
    assert int(mapping["Item A"]["is_consumable"]) == 1
    assert int(mapping["Item B"]["is_consumable"]) == 0
    assert int(mapping["Item C"]["is_consumable"]) == 1
    # size propagated from stocks
    assert mapping["Item C"]["size"] is not None and str(
        mapping["Item C"]["size"]
    ).lower().startswith("500")
