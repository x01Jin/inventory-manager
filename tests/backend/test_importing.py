import pytest
from openpyxl import Workbook
from inventory_app.database.connection import db
from inventory_app.services.item_importer import import_items_from_excel
from inventory_app.utils.stock_parser import parse_stock_value, parse_stock_quantity


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for each test and ensure schema is applied."""
    db_file = tmp_path / "test_inventory.db"
    db.db_path = db_file
    assert db.create_database() is True
    yield db_file


def test_stock_string_parsing():
    """Verify parsing logic for stock quantities and sizes from strings."""
    # Simple numeric
    assert parse_stock_quantity(10) == 10
    assert parse_stock_quantity("5") == 5

    # Combined quantity and size
    info = parse_stock_value("900ml")
    assert info["quantity"] == 900
    assert info["size"] == "900ml"

    info = parse_stock_value("10 boxes")
    assert info["quantity"] == 10
    assert info["size"] is None

    info = parse_stock_value("1 box (100pcs)")
    assert info["quantity"] == 100
    assert info["size"] is None
    assert info["notes"] == "(100pcs)"

    info = parse_stock_value("2 packs of 50 pcs")
    assert info["quantity"] == 100
    assert info["size"] is None

    # Invalid strings
    with pytest.raises(ValueError):
        parse_stock_value("just text")


def test_excel_importer_logic(temp_db, tmp_path):
    """Verify that importing from Excel correctly populates the database."""
    # Create temp excel file
    excel_path = tmp_path / "test_import.xlsx"
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.append(["name", "stocks", "item type", "category"])
    ws.append(["Item A", "1", "Consumables", "Chemicals-Solid"])
    ws.append(["Item B", "500ml", "TA, Consumables", "Chemicals-Liquid"])
    ws.append(["Item C", "5", "Equipment", "Equipment"])
    ws.append(["Item D", "1 box (100pcs)", "Consumables", "Consumables"])
    wb.save(excel_path)

    # Run import
    imported_count, messages = import_items_from_excel(
        str(excel_path), editor_name="tester"
    )

    assert imported_count == 4

    # Verify DB state
    rows = db.execute_query("SELECT name, is_consumable, size FROM Items ORDER BY name")
    assert len(rows) == 4

    # Item A: Consumable = 1
    assert rows[0]["name"] == "Item A"
    assert rows[0]["is_consumable"] == 1

    # Item B: Size extracted from stocks string
    assert rows[1]["name"] == "Item B"
    assert "500ml" in rows[1]["size"]

    # Item B: Batch quantity should use the numeric part from stocks (500ml -> 500)
    item_b_qty = db.execute_query(
        """
        SELECT ib.quantity_received
        FROM Item_Batches ib
        JOIN Items i ON i.id = ib.item_id
        WHERE i.name = ?
        ORDER BY ib.id DESC
        LIMIT 1
        """,
        ("Item B",),
    )
    assert item_b_qty
    assert item_b_qty[0]["quantity_received"] == 500

    # Item C: Equipment (Not consumable)
    assert rows[2]["name"] == "Item C"
    assert rows[2]["is_consumable"] == 0

    # Item D: Boxed piece count converts to usable quantity.
    item_d_qty = db.execute_query(
        """
        SELECT ib.quantity_received
        FROM Item_Batches ib
        JOIN Items i ON i.id = ib.item_id
        WHERE i.name = ?
        ORDER BY ib.id DESC
        LIMIT 1
        """,
        ("Item D",),
    )
    assert item_d_qty
    assert item_d_qty[0]["quantity_received"] == 100

    item_d_specs = db.execute_query(
        "SELECT other_specifications FROM Items WHERE name = ?",
        ("Item D",),
    )
    assert item_d_specs
    assert "(100pcs)" in (item_d_specs[0]["other_specifications"] or "")


def test_importer_edge_cases(temp_db, tmp_path):
    """Verify importer behavior with duplicate items and missing categories."""
    excel_path = tmp_path / "edge_cases.xlsx"
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.append(["name", "stocks", "item type", "category"])

    # Duplicate items: Should be imported as separate batches or update existing?
    # Based on current implementation, it likely creates separate items if names are exactly same
    # or fails if there is a unique constraint (which there isn't in schema).
    ws.append(["Duplicate", "10", "Consumables", "Consumables"])
    ws.append(["Duplicate", "20", "Consumables", "Consumables"])

    # Missing category: Should default to 'Uncategorized'
    ws.append(["NoCat", "5", "Consumables", ""])

    wb.save(excel_path)

    imported_count, messages = import_items_from_excel(
        str(excel_path), editor_name="tester"
    )
    assert imported_count == 3

    # Verify Uncategorized
    nocat = db.execute_query("SELECT category_id FROM Items WHERE name = 'NoCat'")
    assert len(nocat) == 1

    # Get Uncategorized ID
    uncat_id = db.execute_query(
        "SELECT id FROM Categories WHERE name = 'Uncategorized'"
    )[0]["id"]
    assert nocat[0]["category_id"] == uncat_id
