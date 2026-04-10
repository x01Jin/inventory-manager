"""
Inventory filters widget for search and filtering functionality.
Provides search input and filter dropdowns.
"""

from typing import List, Optional, Tuple
from datetime import date
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QGroupBox,
    QDateEdit,
    QCheckBox,
    QSizePolicy,
)
from PyQt6.QtCore import pyqtSignal, QDate
from inventory_app.utils.logger import logger


class InventoryFilters(QWidget):
    """Widget for inventory search and filtering controls."""

    # Signals
    search_changed = pyqtSignal(str)  # Search term changed
    category_filter_changed = pyqtSignal(str)  # Category filter changed
    supplier_filter_changed = pyqtSignal(str)  # Supplier filter changed
    item_type_filter_changed = pyqtSignal(str)  # Item type filter changed
    date_range_filter_changed = pyqtSignal(object, object)  # Acquisition date range
    clear_filters_requested = pyqtSignal()  # Clear all filters

    def __init__(self, parent=None):
        super().__init__(parent)
        self.categories: List[str] = []
        self.suppliers: List[str] = []
        self.item_types: List[str] = []
        self.setup_ui()

    def setup_ui(self):
        """Setup the filter controls UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Search group
        search_group = QGroupBox("Search & Filters")
        search_layout = QVBoxLayout(search_group)
        search_layout.setContentsMargins(8, 8, 8, 8)

        # Search row
        search_row = QHBoxLayout()
        search_row.setSpacing(8)

        # Search input
        search_label = QLabel("🔍 Search:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name, category, or supplier...")
        self.search_input.setMinimumWidth(260)
        self.search_input.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.search_input.textChanged.connect(self._on_search_changed)

        search_row.addWidget(search_label)
        search_row.addWidget(self.search_input)
        search_row.setStretch(1, 1)

        search_layout.addLayout(search_row)

        # Primary filters row
        primary_filters_row = QHBoxLayout()
        primary_filters_row.setSpacing(10)

        # Category filter
        category_label = QLabel("📂 Category:")
        self.category_combo = QComboBox()
        self.category_combo.addItem("All Categories", "")
        self.category_combo.currentTextChanged.connect(self._on_category_changed)
        self.category_combo.setMinimumWidth(150)
        self.category_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        # Supplier filter
        supplier_label = QLabel("🏢 Supplier:")
        self.supplier_combo = QComboBox()
        self.supplier_combo.addItem("All Suppliers", "")
        self.supplier_combo.currentTextChanged.connect(self._on_supplier_changed)
        self.supplier_combo.setMinimumWidth(150)
        self.supplier_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        # Item type filter
        item_type_label = QLabel("🧪 Item Type:")
        self.item_type_combo = QComboBox()
        self.item_type_combo.addItem("All Item Types", "")
        self.item_type_combo.currentTextChanged.connect(self._on_item_type_changed)
        self.item_type_combo.setMinimumWidth(160)
        self.item_type_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        # Acquisition date-range filter
        self.use_date_range_checkbox = QCheckBox("Filter by acquisition date")
        self.use_date_range_checkbox.toggled.connect(self._on_date_range_toggled)

        date_from_label = QLabel("From:")
        self.date_from_edit = QDateEdit()
        self.date_from_edit.setCalendarPopup(True)
        self.date_from_edit.setDisplayFormat("MM/dd/yyyy")
        self.date_from_edit.setDate(QDate.currentDate().addDays(-30))
        self.date_from_edit.setEnabled(False)
        self.date_from_edit.setMinimumWidth(130)
        self.date_from_edit.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.date_from_edit.dateChanged.connect(self._on_date_range_changed)

        date_to_label = QLabel("To:")
        self.date_to_edit = QDateEdit()
        self.date_to_edit.setCalendarPopup(True)
        self.date_to_edit.setDisplayFormat("MM/dd/yyyy")
        self.date_to_edit.setDate(QDate.currentDate())
        self.date_to_edit.setEnabled(False)
        self.date_to_edit.setMinimumWidth(130)
        self.date_to_edit.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.date_to_edit.dateChanged.connect(self._on_date_range_changed)

        primary_filters_row.addWidget(category_label)
        primary_filters_row.addWidget(self.category_combo)
        primary_filters_row.addWidget(supplier_label)
        primary_filters_row.addWidget(self.supplier_combo)
        primary_filters_row.addWidget(item_type_label)
        primary_filters_row.addWidget(self.item_type_combo)
        primary_filters_row.setStretch(1, 1)
        primary_filters_row.setStretch(3, 1)
        primary_filters_row.setStretch(5, 1)

        # Secondary filters row
        secondary_filters_row = QHBoxLayout()
        secondary_filters_row.setSpacing(10)

        # Clear filters button
        self.clear_button = QPushButton("🗑️ Clear Filters")
        self.clear_button.clicked.connect(self._on_clear_filters)

        secondary_filters_row.addWidget(self.use_date_range_checkbox)
        secondary_filters_row.addWidget(date_from_label)
        secondary_filters_row.addWidget(self.date_from_edit)
        secondary_filters_row.addWidget(date_to_label)
        secondary_filters_row.addWidget(self.date_to_edit)
        secondary_filters_row.addWidget(self.clear_button)
        secondary_filters_row.setStretch(2, 1)
        secondary_filters_row.setStretch(4, 1)

        search_layout.addLayout(primary_filters_row)
        search_layout.addLayout(secondary_filters_row)
        layout.addWidget(search_group)

    def set_categories(self, categories: List[str]):
        """Set available categories for filtering."""
        self.categories = categories.copy()
        selected = self.get_selected_category()

        # Clear existing items except "All Categories"
        while self.category_combo.count() > 1:
            self.category_combo.removeItem(1)

        # Add categories in canonical order
        for category in categories:
            self.category_combo.addItem(category, category)

        if selected:
            index = self.category_combo.findData(selected)
            if index >= 0:
                self.category_combo.setCurrentIndex(index)

        logger.debug(f"Set {len(categories)} categories for filtering")

    def set_suppliers(self, suppliers: List[str]):
        """Set available suppliers for filtering."""
        self.suppliers = suppliers.copy()
        selected = self.get_selected_supplier()

        # Clear existing items except "All Suppliers"
        while self.supplier_combo.count() > 1:
            self.supplier_combo.removeItem(1)

        # Add suppliers
        for supplier in sorted(suppliers):
            self.supplier_combo.addItem(supplier, supplier)

        if selected:
            index = self.supplier_combo.findData(selected)
            if index >= 0:
                self.supplier_combo.setCurrentIndex(index)

        logger.debug(f"Set {len(suppliers)} suppliers for filtering")

    def set_item_types(self, item_types: List[str]):
        """Set available item types for filtering."""
        self.item_types = item_types.copy()
        selected = self.get_selected_item_type()

        while self.item_type_combo.count() > 1:
            self.item_type_combo.removeItem(1)

        for item_type in sorted(item_types):
            self.item_type_combo.addItem(item_type, item_type)

        if selected:
            index = self.item_type_combo.findData(selected)
            if index >= 0:
                self.item_type_combo.setCurrentIndex(index)

        logger.debug(f"Set {len(item_types)} item types for filtering")

    def get_search_text(self) -> str:
        """Get current search text."""
        return self.search_input.text().strip()

    def get_selected_category(self) -> str:
        """Get currently selected category filter."""
        return self.category_combo.currentData() or ""

    def get_selected_supplier(self) -> str:
        """Get currently selected supplier filter."""
        return self.supplier_combo.currentData() or ""

    def get_selected_item_type(self) -> str:
        """Get currently selected item type filter."""
        return self.item_type_combo.currentData() or ""

    def get_date_range(self) -> Tuple[Optional[date], Optional[date]]:
        """Get selected acquisition date range filter."""
        if not self.use_date_range_checkbox.isChecked():
            return None, None
        return (
            self.date_from_edit.date().toPyDate(),
            self.date_to_edit.date().toPyDate(),
        )

    def clear_filters(self):
        """Clear all filter controls."""
        self.search_input.clear()
        self.category_combo.setCurrentIndex(0)
        self.supplier_combo.setCurrentIndex(0)
        self.item_type_combo.setCurrentIndex(0)
        self.use_date_range_checkbox.setChecked(False)
        self.date_from_edit.setDate(QDate.currentDate().addDays(-30))
        self.date_to_edit.setDate(QDate.currentDate())
        logger.debug("Filters cleared")

    def _on_search_changed(self, text: str):
        """Handle search text change."""
        self.search_changed.emit(text.strip())

    def _on_category_changed(self, text: str):
        """Handle category filter change."""
        category = self.category_combo.currentData() or ""
        self.category_filter_changed.emit(category)

    def _on_supplier_changed(self, text: str):
        """Handle supplier filter change."""
        supplier = self.supplier_combo.currentData() or ""
        self.supplier_filter_changed.emit(supplier)

    def _on_item_type_changed(self, text: str):
        """Handle item type filter change."""
        item_type = self.item_type_combo.currentData() or ""
        self.item_type_filter_changed.emit(item_type)

    def _on_date_range_toggled(self, checked: bool):
        """Enable or disable acquisition date range filtering."""
        self.date_from_edit.setEnabled(checked)
        self.date_to_edit.setEnabled(checked)
        self._emit_date_range()

    def _on_date_range_changed(self, _date: QDate):
        """Handle acquisition date range changes."""
        self._emit_date_range()

    def _emit_date_range(self):
        """Emit current date range values."""
        start_date, end_date = self.get_date_range()
        self.date_range_filter_changed.emit(start_date, end_date)

    def _on_clear_filters(self):
        """Handle clear filters button click."""
        self.clear_filters()
        self.clear_filters_requested.emit()
