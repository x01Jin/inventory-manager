import pytest
import time
from datetime import date
from inventory_app.gui.inventory.inventory_page import InventoryPage
from inventory_app.gui.inventory.inventory_controller import InventoryController
from inventory_app.gui.inventory.inventory_model import ItemRow


@pytest.fixture
def mock_inventory_data(monkeypatch):
    """Fixture to mock inventory data loading for UI tests."""
    data = [
        {
            "id": 1,
            "name": "Test Item 1",
            "category_name": "Equipment",
            "size": "L",
            "brand": "Brand A",
            "total_stock": 100,
            "available_stock": 90,
            "is_consumable": 0,
        },
        {
            "id": 2,
            "name": "Consumable 2",
            "category_name": "Consumables",
            "size": "M",
            "brand": "Brand B",
            "total_stock": 50,
            "available_stock": 50,
            "is_consumable": 1,
        },
    ]
    monkeypatch.setattr(
        "inventory_app.gui.inventory.inventory_controller.InventoryController.load_inventory_data",
        lambda *a, **kw: data,
    )
    return data


def test_inventory_page_load(qtbot, mock_inventory_data):
    """Verify that the inventory page loads and displays data."""
    page = InventoryPage()
    qtbot.addWidget(page)

    # Trigger refresh
    page.refresh_data()

    # Wait for parallel loader to complete (polling because it's async)
    import time

    timeout = 5  # 5 seconds max
    start = time.time()
    while page._is_loading and time.time() - start < timeout:
        # Process events to allow async tasks to progress
        from PyQt6.QtWidgets import QApplication

        QApplication.processEvents()
        time.sleep(0.1)

    assert not page._is_loading, "Inventory page timed out loading data"

    # Verify table data
    # The table has a populate_table method that adds rows.
    # We check if the row count matches our mock data.
    assert page.table.rowCount() == len(mock_inventory_data)

    # Check first row name (Column 1 is name, Column 0 is stock)
    name_item = page.table.item(0, 1)
    assert name_item is not None
    assert name_item.text() == mock_inventory_data[0]["name"]


def test_inventory_search_responsiveness(qtbot, mock_inventory_data):
    """Verify that searching/filtering responds within reasonable time."""
    page = InventoryPage()
    qtbot.addWidget(page)
    page.refresh_data()

    start_time = time.perf_counter()
    page._on_search_changed("Test")
    duration = time.perf_counter() - start_time

    # Should be very fast (under 100ms for small sets)
    assert duration < 0.1


def test_inventory_controller_query_integrity(monkeypatch):
    """Verify that the inventory controller generates safe queries."""
    captured = {"query": None}

    def fake_execute_query(query, params=None):
        captured["query"] = query
        return []

    import inventory_app.database.connection as conn

    monkeypatch.setattr(conn.db, "execute_query", fake_execute_query)

    controller = InventoryController()
    controller.load_inventory_data()

    assert captured["query"] is not None
    assert "%s" not in captured["query"]  # Ensure parameterization
    assert "Items" in captured["query"]


def test_task12_inventory_page_filters_compose(qtbot, monkeypatch):
    """Task 12: page-level filters should compose instead of overwriting each other."""

    def skip_initial_refresh(self):
        return None

    monkeypatch.setattr(InventoryPage, "refresh_data", skip_initial_refresh)

    page = InventoryPage()
    qtbot.addWidget(page)

    page.model.set_items(
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
        ]
    )

    page.filters.set_categories(["Apparatus"])
    page.filters.set_suppliers(["ATR Trading System", "Malcor Chemicals"])
    page.filters.set_item_types(["Non-consumable"])

    page.filters.search_input.setText("Beaker")
    page.filters.category_combo.setCurrentIndex(
        page.filters.category_combo.findData("Apparatus")
    )
    page.filters.supplier_combo.setCurrentIndex(
        page.filters.supplier_combo.findData("ATR Trading System")
    )
    page.filters.item_type_combo.setCurrentIndex(
        page.filters.item_type_combo.findData("Non-consumable")
    )
    page._apply_current_filters()

    filtered = page.model.get_filtered_items()
    assert len(filtered) == 1
    assert filtered[0].id == 1


def test_task12_double_click_opens_item_history_dialog(qtbot, monkeypatch):
    """Task 12: table interaction should open item usage history dialog."""

    def skip_initial_refresh(self):
        return None

    monkeypatch.setattr(InventoryPage, "refresh_data", skip_initial_refresh)

    opened = {"value": False}

    class FakeDialog:
        def __init__(self, *args, **kwargs):
            pass

        def exec(self):
            opened["value"] = True
            return 0

    monkeypatch.setattr(
        "inventory_app.gui.inventory.inventory_page.ItemHistoryDialog",
        FakeDialog,
    )

    page = InventoryPage()
    qtbot.addWidget(page)

    page.model.set_items(
        [
            ItemRow(
                id=99,
                name="History Item",
                category_name="Equipment",
                item_type="Non-consumable",
                size=None,
                brand=None,
                supplier_name=None,
                other_specifications=None,
                po_number=None,
                expiration_date=None,
                calibration_date=None,
                is_consumable=False,
                acquisition_date=date(2024, 1, 1),
                last_modified=None,
                total_stock=5,
                available_stock=5,
            )
        ]
    )
    page._update_filtered_table()

    page.table.selectRow(0)
    page._on_table_double_click(None)
    assert opened["value"] is True
