import pytest
import time
from datetime import date
from PyQt6.QtWidgets import QApplication, QWidget
from inventory_app.gui.inventory.inventory_page import InventoryPage
from inventory_app.gui.inventory.inventory_controller import InventoryController
from inventory_app.gui.inventory.inventory_model import ItemRow
from inventory_app.gui.inventory.inventory_table import InventoryTable
from inventory_app.services.item_status_service import item_status_service


class _FakeStatus:
    def __init__(self, status: str):
        self.status = status


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


def test_inventory_table_displays_po_number_column(qtbot):
    """Inventory table should show PO Number as its own visible column."""
    table = InventoryTable()
    qtbot.addWidget(table)

    assert "PO Number" in table.COLUMNS

    table.populate_table(
        [
            {
                "id": 1,
                "name": "PO Tracked Item",
                "category_name": "Equipment",
                "size": "N/A",
                "brand": "Brand A",
                "supplier_name": "Supplier A",
                "po_number": "PO-1001",
                "other_specifications": "N/A",
                "expiration_date": None,
                "calibration_date": None,
                "acquisition_date": None,
                "last_modified": None,
                "has_sds": 0,
                "is_consumable": False,
                "total_stock": 10,
                "available_stock": 10,
            }
        ],
        statuses={},
        skip_styling=True,
    )

    po_item = table.item(0, 6)
    assert po_item is not None
    assert po_item.text() == "PO-1001"


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


def test_inventory_status_filter_targets_alert_state(qtbot, monkeypatch):
    """Status filter should return only rows matching requested status token."""

    def skip_initial_refresh(self):
        return None

    monkeypatch.setattr(InventoryPage, "refresh_data", skip_initial_refresh)

    page = InventoryPage()
    qtbot.addWidget(page)

    page.model.set_items(
        [
            ItemRow(
                id=1,
                name="Expired Chemical",
                category_name="Chemicals-Liquid",
                item_type="Consumable",
                size=None,
                brand=None,
                supplier_name=None,
                other_specifications=None,
                po_number=None,
                expiration_date=None,
                calibration_date=None,
                is_consumable=True,
                acquisition_date=date(2024, 1, 10),
                last_modified=None,
                total_stock=10,
                available_stock=8,
            ),
            ItemRow(
                id=2,
                name="Calibration Soon",
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
                acquisition_date=date(2024, 1, 10),
                last_modified=None,
                total_stock=12,
                available_stock=12,
            ),
        ]
    )
    page.model.set_status_lookup(
        {
            1: _FakeStatus("EXPIRED"),
            2: _FakeStatus("CAL_WARNING"),
        }
    )

    page.filters.status_combo.setCurrentIndex(
        page.filters.status_combo.findData("CAL_WARNING")
    )
    page._apply_current_filters()

    filtered = page.model.get_filtered_items()
    assert len(filtered) == 1
    assert filtered[0].id == 2


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


def test_sds_button_only_for_chemical_rows(qtbot, monkeypatch):
    """SDS row action appears only for Chemicals-Solid/Liquid rows."""

    def skip_initial_refresh(self):
        return None

    monkeypatch.setattr(InventoryPage, "refresh_data", skip_initial_refresh)

    page = InventoryPage()
    qtbot.addWidget(page)

    page.model.set_items(
        [
            ItemRow(
                id=1,
                name="Acetone",
                category_name="Chemicals-Liquid",
                item_type="Consumable",
                size="500mL",
                brand="LabCorp",
                supplier_name="Malcor Chemicals",
                other_specifications=None,
                po_number=None,
                expiration_date=None,
                calibration_date=None,
                is_consumable=True,
                acquisition_date=date(2025, 1, 1),
                last_modified=None,
                has_sds=False,
                total_stock=10,
                available_stock=10,
            ),
            ItemRow(
                id=2,
                name="Beaker",
                category_name="Apparatus",
                item_type="Non-consumable",
                size="250mL",
                brand="Pyrex",
                supplier_name="ATR Trading System",
                other_specifications=None,
                po_number=None,
                expiration_date=None,
                calibration_date=None,
                is_consumable=False,
                acquisition_date=date(2024, 1, 1),
                last_modified=None,
                has_sds=False,
                total_stock=10,
                available_stock=10,
            ),
        ]
    )
    page._update_filtered_table()

    assert page.table.cellWidget(0, 1) is not None
    assert page.table.cellWidget(1, 1) is None


def test_sds_row_action_opens_external_file_when_entry_exists(qtbot, monkeypatch):
    """Row SDS action should open the existing SDS file externally."""

    def skip_initial_refresh(self):
        return None

    monkeypatch.setattr(InventoryPage, "refresh_data", skip_initial_refresh)

    opened = {"value": False}

    class FakeSDS:
        def __init__(self):
            self.file_path = "C:/tmp/acid.pdf"

    monkeypatch.setattr(
        "inventory_app.gui.inventory.inventory_page.ItemSDS.get_by_item_id",
        lambda _item_id: FakeSDS(),
    )
    monkeypatch.setattr(
        "inventory_app.gui.inventory.inventory_page.QDesktopServices.openUrl",
        lambda _url: opened.__setitem__("value", True) or True,
    )

    page = InventoryPage()
    qtbot.addWidget(page)

    page.model.set_items(
        [
            ItemRow(
                id=10,
                name="Sulfuric Acid",
                category_name="Chemicals-Liquid",
                item_type="Consumable",
                size="1L",
                brand="Merck",
                supplier_name="Malcor Chemicals",
                other_specifications=None,
                po_number=None,
                expiration_date=None,
                calibration_date=None,
                is_consumable=True,
                acquisition_date=date(2025, 1, 1),
                last_modified=None,
                has_sds=True,
                total_stock=5,
                available_stock=5,
            )
        ]
    )
    page._update_filtered_table()

    page.table.sds_requested.emit(10)
    assert opened["value"] is True


def test_sds_row_action_warns_when_entry_missing(qtbot, monkeypatch):
    """Row SDS action should warn when chemical has no SDS entry yet."""

    def skip_initial_refresh(self):
        return None

    monkeypatch.setattr(InventoryPage, "refresh_data", skip_initial_refresh)
    monkeypatch.setattr(
        "inventory_app.gui.inventory.inventory_page.ItemSDS.get_by_item_id",
        lambda _item_id: None,
    )

    warned = {"value": False}
    monkeypatch.setattr(
        "inventory_app.gui.inventory.inventory_page.QMessageBox.information",
        lambda *args, **kwargs: warned.__setitem__("value", True),
    )

    page = InventoryPage()
    qtbot.addWidget(page)

    page.model.set_items(
        [
            ItemRow(
                id=12,
                name="Ammonia",
                category_name="Chemicals-Liquid",
                item_type="Consumable",
                size="500mL",
                brand="Merck",
                supplier_name="Malcor Chemicals",
                other_specifications=None,
                po_number=None,
                expiration_date=None,
                calibration_date=None,
                is_consumable=True,
                acquisition_date=date(2025, 1, 1),
                last_modified=None,
                has_sds=False,
                total_stock=5,
                available_stock=5,
            )
        ]
    )
    page._update_filtered_table()

    page.table.sds_requested.emit(12)
    assert warned["value"] is True


def test_sds_settings_toolbar_button_visible_for_selected_chemical(qtbot, monkeypatch):
    """Toolbar SDS settings button should appear only when a chemical row is selected."""

    def skip_initial_refresh(self):
        return None

    monkeypatch.setattr(InventoryPage, "refresh_data", skip_initial_refresh)

    page = InventoryPage()
    qtbot.addWidget(page)

    page.model.set_items(
        [
            ItemRow(
                id=21,
                name="Ethanol",
                category_name="Chemicals-Liquid",
                item_type="Consumable",
                size="1L",
                brand="Merck",
                supplier_name="Malcor Chemicals",
                other_specifications=None,
                po_number=None,
                expiration_date=None,
                calibration_date=None,
                is_consumable=True,
                acquisition_date=date(2025, 1, 1),
                last_modified=None,
                has_sds=False,
                total_stock=5,
                available_stock=5,
            ),
            ItemRow(
                id=22,
                name="Clamp",
                category_name="Apparatus",
                item_type="Non-consumable",
                size=None,
                brand=None,
                supplier_name="ATR Trading System",
                other_specifications=None,
                po_number=None,
                expiration_date=None,
                calibration_date=None,
                is_consumable=False,
                acquisition_date=date(2025, 1, 1),
                last_modified=None,
                has_sds=False,
                total_stock=5,
                available_stock=5,
            ),
        ]
    )
    page._update_filtered_table()

    page.table.selectRow(0)
    page._on_table_selection_changed()
    assert page.sds_settings_button.isHidden() is False

    page.table.selectRow(1)
    page._on_table_selection_changed()
    assert page.sds_settings_button.isHidden() is True


def test_sds_inline_widgets_do_not_overlay_after_repopulate(qtbot):
    """Repopulating rows should not leave stale SDS inline widgets behind."""
    table = InventoryTable()
    qtbot.addWidget(table)

    first_data = [
        {
            "id": 1,
            "name": "Dishwashing liquid",
            "category_name": "Chemicals-Liquid",
            "size": "250mL",
            "brand": "N/A",
            "supplier_name": "N/A",
            "other_specifications": None,
            "expiration_date": None,
            "calibration_date": None,
            "acquisition_date": None,
            "last_modified": None,
            "has_sds": 0,
            "is_consumable": True,
            "total_stock": 10,
            "available_stock": 10,
        }
    ]
    table.populate_table(first_data, statuses={}, skip_styling=True)
    QApplication.processEvents()

    assert table.cellWidget(0, 1) is not None
    assert len(table.findChildren(QWidget, "sdsInlineWrapper")) == 1

    second_data = [
        {
            "id": 2,
            "name": "Acetone",
            "category_name": "Apparatus",
            "size": "500mL",
            "brand": "N/A",
            "supplier_name": "N/A",
            "other_specifications": None,
            "expiration_date": None,
            "calibration_date": None,
            "acquisition_date": None,
            "last_modified": None,
            "has_sds": 0,
            "is_consumable": False,
            "total_stock": 10,
            "available_stock": 10,
        }
    ]
    table.populate_table(second_data, statuses={}, skip_styling=True)
    QApplication.processEvents()

    name_item = table.item(0, 1)
    assert table.cellWidget(0, 1) is None
    assert name_item is not None
    assert name_item.text() == "Acetone"
    assert len(table.findChildren(QWidget, "sdsInlineWrapper")) == 0


def test_inventory_table_uses_batched_population_for_large_sets(qtbot, monkeypatch):
    """Large datasets should populate over multiple UI batches instead of one long loop."""
    batch_calls = {"count": 0}
    original_batch = InventoryTable._populate_table_batch

    def wrapped_batch(self, token):
        batch_calls["count"] += 1
        return original_batch(self, token)

    monkeypatch.setattr(InventoryTable, "_populate_table_batch", wrapped_batch)

    table = InventoryTable()
    qtbot.addWidget(table)

    large_data = []
    for idx in range(220):
        large_data.append(
            {
                "id": idx + 1,
                "name": f"Item {idx + 1}",
                "category_name": "Equipment",
                "size": "N/A",
                "brand": "Brand",
                "supplier_name": "Supplier",
                "other_specifications": None,
                "expiration_date": None,
                "calibration_date": None,
                "acquisition_date": None,
                "last_modified": None,
                "has_sds": 0,
                "is_consumable": False,
                "total_stock": 10,
                "available_stock": 10,
            }
        )

    table.populate_table(large_data, statuses={}, skip_styling=True)

    qtbot.waitUntil(
        lambda: table.item(len(large_data) - 1, 1) is not None, timeout=5000
    )

    assert batch_calls["count"] > 1
    assert table.rowCount() == len(large_data)


def test_filtered_table_reuses_cached_statuses(qtbot, monkeypatch):
    """Filtering should reuse already-prefetched statuses and avoid extra bulk lookups."""

    def skip_initial_refresh(self):
        return None

    monkeypatch.setattr(InventoryPage, "refresh_data", skip_initial_refresh)

    page = InventoryPage()
    qtbot.addWidget(page)

    page.model.set_items(
        [
            ItemRow(
                id=101,
                name="Cached Item 1",
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
            ),
            ItemRow(
                id=102,
                name="Cached Item 2",
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
                total_stock=8,
                available_stock=8,
            ),
        ]
    )

    cached_lookup = {
        101: _FakeStatus("CAL_WARNING"),
        102: _FakeStatus("EXPIRED"),
    }
    page.model.set_status_lookup(cached_lookup)

    called_with = []

    def track_bulk_status_fetch(item_ids):
        called_with.append(list(item_ids))
        return {}

    monkeypatch.setattr(
        item_status_service, "get_statuses_for_items", track_bulk_status_fetch
    )

    page._update_filtered_table()

    assert called_with == []


def test_inventory_progressive_styling_receives_prefetched_statuses(qtbot, monkeypatch):
    """Progressive styling should receive non-None statuses from prefetched cache."""
    table = InventoryTable()
    qtbot.addWidget(table)

    items = []
    statuses = {}
    for idx in range(190):
        item_id = idx + 1
        items.append(
            {
                "id": item_id,
                "name": f"Status Item {item_id}",
                "category_name": "Equipment",
                "size": None,
                "brand": None,
                "supplier_name": None,
                "other_specifications": None,
                "expiration_date": None,
                "calibration_date": None,
                "acquisition_date": None,
                "last_modified": None,
                "has_sds": 0,
                "is_consumable": False,
                "total_stock": 5,
                "available_stock": 5,
            }
        )
        statuses[item_id] = _FakeStatus("EXPIRED")

    seen_statuses = []
    original_apply = table._apply_row_styling

    def wrapped_apply(row, item_status):
        seen_statuses.append(item_status)
        return original_apply(row, item_status)

    monkeypatch.setattr(table, "_apply_row_styling", wrapped_apply)

    table.populate_table(items, statuses=statuses, skip_styling=False)

    qtbot.waitUntil(lambda: len(seen_statuses) > 0, timeout=5000)

    assert any(status is not None for status in seen_statuses)
