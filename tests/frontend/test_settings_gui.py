from inventory_app.gui.settings.settings_page import SettingsPage
from inventory_app.database.models import Size, Brand, Supplier
from PyQt6.QtWidgets import QLabel, QTableWidget, QPushButton


def _patch_reference_data(monkeypatch):
    """Patch settings reference data to deterministic test values."""

    monkeypatch.setattr(
        Size,
        "get_all",
        classmethod(lambda cls: [Size(id=1, name="500 mL"), Size(id=2, name="250 mL")]),
    )
    monkeypatch.setattr(
        Brand,
        "get_all",
        classmethod(
            lambda cls: [Brand(id=1, name="Pyrex"), Brand(id=2, name="Generic")]
        ),
    )
    monkeypatch.setattr(
        Supplier,
        "get_all",
        classmethod(
            lambda cls: [
                Supplier(id=1, name="Malcor Chemicals"),
                Supplier(id=2, name="ATR Trading System"),
            ]
        ),
    )

    monkeypatch.setattr(Size, "get_usage_count", lambda self: 3 if self.id == 1 else 0)
    monkeypatch.setattr(Brand, "get_usage_count", lambda self: 2 if self.id == 1 else 0)
    monkeypatch.setattr(
        Supplier, "get_usage_count", lambda self: 1 if self.id == 1 else 0
    )


def test_settings_delete_disabled_for_used_values(qtbot, monkeypatch):
    """Used size/brand/supplier values should be visibly tagged and non-deletable."""
    _patch_reference_data(monkeypatch)

    page = SettingsPage()
    qtbot.addWidget(page)

    page.sizes_table.selectRow(0)
    size_status = page.sizes_table.item(0, 2)
    size_usage = page.sizes_table.item(0, 1)
    assert size_status is not None
    assert size_status.text() == "NON-DELETABLE"
    assert size_usage is not None
    assert size_usage.text() == "3 item(s)"
    assert page.delete_size_btn.isEnabled() is False

    page.brands_table.selectRow(0)
    brand_status = page.brands_table.item(0, 2)
    brand_usage = page.brands_table.item(0, 1)
    assert brand_status is not None
    assert brand_status.text() == "NON-DELETABLE"
    assert brand_usage is not None
    assert brand_usage.text() == "2 item(s)"
    assert page.delete_brand_btn.isEnabled() is False

    page.suppliers_table.selectRow(0)
    supplier_status = page.suppliers_table.item(0, 2)
    supplier_usage = page.suppliers_table.item(0, 1)
    assert supplier_status is not None
    assert supplier_status.text() == "NON-DELETABLE"
    assert supplier_usage is not None
    assert supplier_usage.text() == "1 item(s)"
    assert page.delete_supplier_btn.isEnabled() is False


def test_settings_delete_enabled_for_unused_values(qtbot, monkeypatch):
    """Unused reference values should be deletable."""
    _patch_reference_data(monkeypatch)

    page = SettingsPage()
    qtbot.addWidget(page)

    page.sizes_table.selectRow(1)
    size_status = page.sizes_table.item(1, 2)
    assert size_status is not None
    assert size_status.text() == "Unused"
    assert page.delete_size_btn.isEnabled() is True

    page.brands_table.selectRow(1)
    brand_status = page.brands_table.item(1, 2)
    assert brand_status is not None
    assert brand_status.text() == "Unused"
    assert page.delete_brand_btn.isEnabled() is True

    page.suppliers_table.selectRow(1)
    supplier_status = page.suppliers_table.item(1, 2)
    assert supplier_status is not None
    assert supplier_status.text() == "Unused"
    assert page.delete_supplier_btn.isEnabled() is True


def test_settings_reference_tabs_use_tables(qtbot, monkeypatch):
    """Sizes, Brands, and Suppliers tabs should render row-select tables."""
    _patch_reference_data(monkeypatch)

    page = SettingsPage()
    qtbot.addWidget(page)

    for table in [page.sizes_table, page.brands_table, page.suppliers_table]:
        header_name = table.horizontalHeaderItem(0)
        header_usage = table.horizontalHeaderItem(1)
        header_status = table.horizontalHeaderItem(2)
        assert table.columnCount() == 3
        assert header_name is not None
        assert header_name.text() == "Name"
        assert header_usage is not None
        assert header_usage.text() == "Usage"
        assert header_status is not None
        assert header_status.text() == "Status"
        assert table.rowCount() == 2


def test_categories_tab_is_read_only_and_has_required_note(qtbot, monkeypatch):
    """Categories tab should present fixed lifecycle rules without category CRUD actions."""
    _patch_reference_data(monkeypatch)

    page = SettingsPage()
    qtbot.addWidget(page)

    tab_names = [page.tab_widget.tabText(i) for i in range(page.tab_widget.count())]
    assert "Categories" in tab_names

    categories_index = tab_names.index("Categories")
    categories_tab = page.tab_widget.widget(categories_index)

    assert categories_tab is not None
    table_widgets = categories_tab.findChildren(QTableWidget)
    assert len(table_widgets) == 1
    assert table_widgets[0].editTriggers() == QTableWidget.EditTrigger.NoEditTriggers

    labels_text = "\n".join(
        label.text().lower() for label in categories_tab.findChildren(QLabel)
    )
    assert "these categories are fixed" in labels_text

    category_buttons = [
        button.text().lower() for button in categories_tab.findChildren(QPushButton)
    ]
    assert not any("category" in text for text in category_buttons)
