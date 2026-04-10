from inventory_app.gui.settings.settings_page import SettingsPage, MergeReferenceDialog
from inventory_app.database.models import Size, Brand, Supplier
from PyQt6.QtWidgets import QLabel, QTableWidget, QPushButton
from PyQt6.QtCore import Qt


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


def test_settings_brands_and_suppliers_have_merge_buttons(qtbot, monkeypatch):
    """Brands and Suppliers tabs should expose merge actions for duplicate cleanup."""
    _patch_reference_data(monkeypatch)

    page = SettingsPage()
    qtbot.addWidget(page)

    brand_widget = page.tab_widget.widget(2)
    assert brand_widget is not None
    brand_buttons = [button.text() for button in brand_widget.findChildren(QPushButton)]
    supplier_widget = page.tab_widget.widget(3)
    assert supplier_widget is not None
    supplier_buttons = [
        button.text() for button in supplier_widget.findChildren(QPushButton)
    ]

    assert "Merge Brands" in brand_buttons
    assert "Merge Suppliers" in supplier_buttons


def test_merge_reference_dialog_excludes_target_and_collects_sources(qtbot):
    """Merge dialog should exclude target from source list and collect checked source IDs."""
    entries = [
        {"id": 1, "name": "ATR", "usage_count": 4},
        {"id": 2, "name": "ATR Trading", "usage_count": 2},
        {"id": 3, "name": "ATR Trading System", "usage_count": 1},
    ]

    dialog = MergeReferenceDialog("Supplier", entries)
    qtbot.addWidget(dialog)

    dialog.target_combo.setCurrentIndex(1)  # target id 2
    target_id = dialog.target_combo.currentData()
    assert target_id == 2

    # Ensure target is not present in sources
    source_ids = []
    for row in range(dialog.sources_list.count()):
        item = dialog.sources_list.item(row)
        data = item.data(Qt.ItemDataRole.UserRole) if item else None
        if data and isinstance(data.get("id"), int):
            source_ids.append(data["id"])
    assert 2 not in source_ids

    first_source = dialog.sources_list.item(0)
    assert first_source is not None
    first_source.setCheckState(Qt.CheckState.Checked)

    third_source = dialog.sources_list.item(1)
    assert third_source is not None
    third_source.setCheckState(Qt.CheckState.Checked)
    dialog.editor_input.setText("Jin")

    dialog._on_accept()
    chosen_target, source_ids, estimated_usage, editor_name = dialog.get_selection()

    assert chosen_target == 2
    assert sorted(source_ids) == [1, 3]
    assert estimated_usage == 5
    assert editor_name == "Jin"
