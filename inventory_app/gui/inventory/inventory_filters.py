"""
Inventory filters widget for search and filtering functionality.
Provides search input and filter dropdowns.
"""

from typing import List
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QLineEdit, QComboBox, QPushButton, QGroupBox
)
from PyQt6.QtCore import pyqtSignal
from inventory_app.utils.logger import logger


class InventoryFilters(QWidget):
    """Widget for inventory search and filtering controls."""

    # Signals
    search_changed = pyqtSignal(str)          # Search term changed
    category_filter_changed = pyqtSignal(str) # Category filter changed
    supplier_filter_changed = pyqtSignal(str) # Supplier filter changed
    clear_filters_requested = pyqtSignal()    # Clear all filters

    def __init__(self, parent=None):
        super().__init__(parent)
        self.categories: List[str] = []
        self.suppliers: List[str] = []
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
        self.search_input.setMinimumWidth(300)
        self.search_input.textChanged.connect(self._on_search_changed)

        search_row.addWidget(search_label)
        search_row.addWidget(self.search_input)
        search_row.addStretch()

        search_layout.addLayout(search_row)

        # Filters row
        filters_row = QHBoxLayout()
        filters_row.setSpacing(10)

        # Category filter
        category_label = QLabel("📂 Category:")
        self.category_combo = QComboBox()
        self.category_combo.addItem("All Categories", "")
        self.category_combo.currentTextChanged.connect(self._on_category_changed)
        self.category_combo.setMinimumWidth(150)

        # Supplier filter
        supplier_label = QLabel("🏢 Supplier:")
        self.supplier_combo = QComboBox()
        self.supplier_combo.addItem("All Suppliers", "")
        self.supplier_combo.currentTextChanged.connect(self._on_supplier_changed)
        self.supplier_combo.setMinimumWidth(150)

        # Clear filters button
        self.clear_button = QPushButton("🗑️ Clear Filters")
        self.clear_button.clicked.connect(self._on_clear_filters)

        filters_row.addWidget(category_label)
        filters_row.addWidget(self.category_combo)
        filters_row.addWidget(supplier_label)
        filters_row.addWidget(self.supplier_combo)
        filters_row.addWidget(self.clear_button)
        filters_row.addStretch()

        search_layout.addLayout(filters_row)
        layout.addWidget(search_group)

    def set_categories(self, categories: List[str]):
        """Set available categories for filtering."""
        self.categories = categories.copy()

        # Clear existing items except "All Categories"
        while self.category_combo.count() > 1:
            self.category_combo.removeItem(1)

        # Add categories
        for category in sorted(categories):
            self.category_combo.addItem(category, category)

        logger.debug(f"Set {len(categories)} categories for filtering")

    def set_suppliers(self, suppliers: List[str]):
        """Set available suppliers for filtering."""
        self.suppliers = suppliers.copy()

        # Clear existing items except "All Suppliers"
        while self.supplier_combo.count() > 1:
            self.supplier_combo.removeItem(1)

        # Add suppliers
        for supplier in sorted(suppliers):
            self.supplier_combo.addItem(supplier, supplier)

        logger.debug(f"Set {len(suppliers)} suppliers for filtering")

    def get_search_text(self) -> str:
        """Get current search text."""
        return self.search_input.text().strip()

    def get_selected_category(self) -> str:
        """Get currently selected category filter."""
        return self.category_combo.currentData() or ""

    def get_selected_supplier(self) -> str:
        """Get currently selected supplier filter."""
        return self.supplier_combo.currentData() or ""

    def clear_filters(self):
        """Clear all filter controls."""
        self.search_input.clear()
        self.category_combo.setCurrentIndex(0)
        self.supplier_combo.setCurrentIndex(0)
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

    def _on_clear_filters(self):
        """Handle clear filters button click."""
        self.clear_filters()
        self.clear_filters_requested.emit()
