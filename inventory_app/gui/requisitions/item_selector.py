"""
Item selector dialog for choosing items in laboratory requisitions.
Provides searchable interface for selecting items and quantities.
"""

from typing import List, Dict, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QSpinBox, QGroupBox, QMessageBox, QHeaderView,
    QAbstractItemView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from inventory_app.gui.requisitions.requisitions_controller import RequisitionsController
from inventory_app.utils.logger import logger


class ItemSelector(QDialog):
    """Dialog for selecting items and quantities for requisitions."""

    def __init__(self, parent=None, pre_selected_items: Optional[List[Dict]] = None):
        super().__init__(parent)
        self.controller = RequisitionsController()
        self.selected_items: List[Dict] = pre_selected_items or []
        self.all_items: List[Dict] = []

        self.setWindowTitle("Select Items for Requisition")
        self.setup_ui()
        self.load_items()

    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Search and filter section
        search_group = QGroupBox("Search Items")
        search_layout = QHBoxLayout(search_group)

        search_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by item name...")
        self.search_input.textChanged.connect(self.filter_items)
        search_layout.addWidget(self.search_input)

        self.search_button = QPushButton("🔍 Search")
        self.search_button.clicked.connect(self.filter_items)
        search_layout.addWidget(self.search_button)

        layout.addWidget(search_group)

        # Items table
        table_group = QGroupBox("Available Items")
        table_layout = QVBoxLayout(table_group)

        self.items_table = QTableWidget()
        self.items_table.setColumnCount(6)
        self.items_table.setHorizontalHeaderLabels([
            "Item Name", "Category", "Size", "Brand", "Available", "Quantity"
        ])

        # Configure table
        header = self.items_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.items_table.setAlternatingRowColors(True)
        self.items_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        # Set column widths
        self.items_table.setColumnWidth(0, 200)  # Item Name
        self.items_table.setColumnWidth(1, 120)  # Category
        self.items_table.setColumnWidth(2, 80)   # Size
        self.items_table.setColumnWidth(3, 100)  # Brand
        self.items_table.setColumnWidth(4, 80)   # Available
        self.items_table.setColumnWidth(5, 80)   # Quantity

        table_layout.addWidget(self.items_table)
        layout.addWidget(table_group)

        # Selected items summary
        summary_group = QGroupBox("Selected Items")
        summary_layout = QVBoxLayout(summary_group)

        self.summary_label = QLabel("No items selected")
        self.summary_label.setStyleSheet("font-weight: bold;")
        summary_layout.addWidget(self.summary_label)

        layout.addWidget(summary_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.add_selected_button = QPushButton("➕ Add Selected Item")
        self.add_selected_button.clicked.connect(self.add_selected_item)
        button_layout.addWidget(self.add_selected_button)

        self.view_selected_button = QPushButton("📋 View Selected")
        self.view_selected_button.clicked.connect(self.view_selected_items)
        button_layout.addWidget(self.view_selected_button)

        self.clear_button = QPushButton("🗑️ Clear All")
        self.clear_button.clicked.connect(self.clear_selection)
        button_layout.addWidget(self.clear_button)

        button_layout.addStretch()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        self.done_button = QPushButton("✅ Done")
        self.done_button.clicked.connect(self.accept)
        self.done_button.setDefault(True)
        button_layout.addWidget(self.done_button)

        layout.addLayout(button_layout)

        # Set dialog properties
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        self.setModal(True)

    def load_items(self):
        """Load all available inventory items."""
        try:
            self.all_items = self.controller.get_inventory_items()
            self.populate_table(self.all_items)
            logger.info(f"Loaded {len(self.all_items)} inventory items")
        except Exception as e:
            logger.error(f"Failed to load items: {e}")
            QMessageBox.critical(self, "Error", "Failed to load inventory items.")

    def populate_table(self, items: List[Dict]):
        """Populate the items table with data."""
        try:
            self.items_table.setRowCount(0)

            for item in items:
                row_position = self.items_table.rowCount()
                self.items_table.insertRow(row_position)

                # Item Name
                name_item = QTableWidgetItem(item.get('name', ''))
                name_item.setData(Qt.ItemDataRole.UserRole, item.get('id'))
                self.items_table.setItem(row_position, 0, name_item)

                # Category
                self.items_table.setItem(row_position, 1, QTableWidgetItem(item.get('category_name', '')))

                # Size
                self.items_table.setItem(row_position, 2, QTableWidgetItem(item.get('size') or ''))

                # Brand
                self.items_table.setItem(row_position, 3, QTableWidgetItem(item.get('brand') or ''))

                # Available Quantity
                available = item.get('available_quantity', 0)
                available_item = QTableWidgetItem(str(available))
                if available <= 0:
                    available_item.setBackground(QColor("#F8D7DA"))  # Light red for unavailable
                elif available <= 5:
                    available_item.setBackground(QColor("#FFF3CD"))  # Light yellow for low stock
                self.items_table.setItem(row_position, 4, available_item)

                # Quantity SpinBox
                quantity_spin = QSpinBox()
                quantity_spin.setMinimum(0)
                quantity_spin.setMaximum(available)
                quantity_spin.setValue(0)
                self.items_table.setCellWidget(row_position, 5, quantity_spin)

            logger.debug(f"Populated table with {len(items)} items")

        except Exception as e:
            logger.error(f"Failed to populate table: {e}")

    def filter_items(self):
        """Filter items based on search term."""
        search_term = self.search_input.text().strip().lower()

        if not search_term:
            self.populate_table(self.all_items)
            return

        try:
            # Search in item names
            filtered_items = [
                item for item in self.all_items
                if search_term in item.get('name', '').lower()
            ]

            # If no results, try searching in inventory
            if not filtered_items:
                filtered_items = self.controller.search_items(search_term)

            self.populate_table(filtered_items)
            logger.debug(f"Filtered to {len(filtered_items)} items matching '{search_term}'")

        except Exception as e:
            logger.error(f"Failed to filter items: {e}")

    def add_selected_item(self):
        """Add the currently selected item to the selection."""
        current_row = self.items_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select an item to add.")
            return

        try:
            # Get item data
            name_item = self.items_table.item(current_row, 0)
            if not name_item:
                return

            item_id = name_item.data(Qt.ItemDataRole.UserRole)
            item_name = name_item.text()

            # Get quantity
            quantity_widget = self.items_table.cellWidget(current_row, 5)
            if not isinstance(quantity_widget, QSpinBox):
                return

            quantity = quantity_widget.value()
            if quantity <= 0:
                QMessageBox.warning(self, "Invalid Quantity", "Please enter a quantity greater than 0.")
                return

            # Check if item already selected
            existing_index = None
            for i, selected in enumerate(self.selected_items):
                if selected['item_id'] == item_id:
                    existing_index = i
                    break

            if existing_index is not None:
                # Update existing quantity
                self.selected_items[existing_index]['quantity_borrowed'] += quantity
                QMessageBox.information(self, "Updated",
                                      f"Updated quantity for {item_name} to {self.selected_items[existing_index]['quantity_borrowed']}.")
            else:
                # Add new item
                selected_item = {
                    'item_id': item_id,
                    'name': item_name,
                    'quantity_borrowed': quantity
                }
                self.selected_items.append(selected_item)
                QMessageBox.information(self, "Added", f"Added {item_name} (x{quantity}) to selection.")

            # Update summary
            self.update_summary()
            logger.info(f"Added item {item_id} with quantity {quantity}")

        except Exception as e:
            logger.error(f"Failed to add selected item: {e}")
            QMessageBox.critical(self, "Error", "Failed to add item to selection.")

    def view_selected_items(self):
        """Show dialog with currently selected items."""
        if not self.selected_items:
            QMessageBox.information(self, "No Items", "No items have been selected yet.")
            return

        try:
            # Create summary message
            summary_lines = []
            total_items = 0

            for item in self.selected_items:
                name = item.get('name', 'Unknown')
                quantity = item.get('quantity_borrowed', 0)
                summary_lines.append(f"• {name}: {quantity}")
                total_items += quantity

            summary_text = "\n".join(summary_lines)
            summary_text += f"\n\nTotal Items: {total_items}"

            QMessageBox.information(self, "Selected Items", summary_text)

        except Exception as e:
            logger.error(f"Failed to show selected items: {e}")

    def clear_selection(self):
        """Clear all selected items."""
        if not self.selected_items:
            QMessageBox.information(self, "No Items", "No items to clear.")
            return

        reply = QMessageBox.question(
            self, "Clear Selection",
            "Are you sure you want to clear all selected items?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.selected_items.clear()
            self.update_summary()
            logger.info("Cleared all selected items")

    def update_summary(self):
        """Update the summary label with selected items count."""
        try:
            if not self.selected_items:
                self.summary_label.setText("No items selected")
                return

            total_items = sum(item.get('quantity_borrowed', 0) for item in self.selected_items)
            item_count = len(self.selected_items)

            if item_count == 1:
                self.summary_label.setText(f"1 item selected ({total_items} total units)")
            else:
                self.summary_label.setText(f"{item_count} items selected ({total_items} total units)")

        except Exception as e:
            logger.error(f"Failed to update summary: {e}")
            self.summary_label.setText("Error updating summary")

    def get_selected_items(self) -> List[Dict]:
        """Get the list of selected items."""
        return self.selected_items.copy()

    @staticmethod
    def select_items(parent=None, pre_selected: Optional[List[Dict]] = None) -> Optional[List[Dict]]:
        """
        Static method to select items using the dialog.
        Returns the selected items list or None if cancelled.
        """
        dialog = ItemSelector(parent, pre_selected)
        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            return dialog.get_selected_items()

        return None
