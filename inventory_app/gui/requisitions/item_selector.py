"""
Item selector dialog for choosing items in laboratory requisitions.
Provides searchable interface for selecting items using row highlighting.
"""

from typing import List, Dict, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QGroupBox, QMessageBox, QHeaderView,
    QAbstractItemView
)
from PyQt6.QtCore import Qt

from inventory_app.gui.requisitions.requisitions_controller import RequisitionsController
from inventory_app.utils.logger import logger


class ItemSelector(QDialog):
    """Dialog for selecting items and quantities for requisitions."""

    def __init__(self, parent=None, pre_selected_items: Optional[List[Dict]] = None,
                 current_requisition_id: Optional[int] = None):
        super().__init__(parent)
        self.controller = RequisitionsController()
        self.selected_items: List[Dict] = pre_selected_items or []
        self.all_items: List[Dict] = []
        self.current_requisition_id = current_requisition_id

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
        self.items_table.setColumnCount(4)
        self.items_table.setHorizontalHeaderLabels([
            "Item Name", "Category", "Size", "Brand"
        ])

        # Configure table
        header = self.items_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.items_table.setAlternatingRowColors(True)
        self.items_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.items_table.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)

        # Connect selection change signal
        self.items_table.itemSelectionChanged.connect(self._on_selection_changed)

        # Block signals initially to prevent unwanted updates during setup
        self.items_table.blockSignals(True)

        # Set column widths
        self.items_table.setColumnWidth(0, 250)  # Item Name (with LAB code)
        self.items_table.setColumnWidth(1, 120)  # Category
        self.items_table.setColumnWidth(2, 80)   # Size
        self.items_table.setColumnWidth(3, 100)  # Brand

        table_layout.addWidget(self.items_table)
        layout.addWidget(table_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.clear_button = QPushButton("🗑️ Clear All")
        self.clear_button.clicked.connect(self.clear_selection)
        button_layout.addWidget(self.clear_button)

        button_layout.addStretch()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        self.done_button = QPushButton("✅ Done")
        self.done_button.clicked.connect(self.confirm_selection)
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
            if self.current_requisition_id is not None:
                # Editing mode: include items borrowed by current requisition
                self.all_items = self.controller.get_inventory_items_for_editing(self.current_requisition_id)
                logger.info(f"Loaded {len(self.all_items)} inventory items for editing requisition {self.current_requisition_id}")
            else:
                # New requisition mode: exclude all borrowed items
                self.all_items = self.controller.get_inventory_items()
                logger.info(f"Loaded {len(self.all_items)} inventory items for new requisition")

            self.populate_table(self.all_items)
            # Unblock signals after initial setup
            self.items_table.blockSignals(False)
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

                # Item Name with LAB code
                unique_code = item.get('unique_code', 'NO-CODE')
                item_name = item.get('name', '')
                display_name = f"{unique_code}: {item_name}"
                name_item = QTableWidgetItem(display_name)
                name_item.setData(Qt.ItemDataRole.UserRole, item.get('id'))
                self.items_table.setItem(row_position, 0, name_item)

                # Category
                self.items_table.setItem(row_position, 1, QTableWidgetItem(item.get('category_name', '')))

                # Size
                self.items_table.setItem(row_position, 2, QTableWidgetItem(item.get('size') or ''))

                # Brand
                self.items_table.setItem(row_position, 3, QTableWidgetItem(item.get('brand') or ''))

                # Select row if item is already selected
                if self._is_item_selected(item.get('id')):
                    self.items_table.selectRow(row_position)

            logger.debug(f"Populated table with {len(items)} items")

        except Exception as e:
            logger.error(f"Failed to populate table: {e}")

    def _is_item_selected(self, item_id: Optional[int]) -> bool:
        """Check if an item is already selected."""
        if item_id is None:
            return False
        return any(item['item_id'] == item_id for item in self.selected_items)

    def _on_selection_changed(self):
        """Handle table selection changes."""
        try:
            # Get currently selected rows
            selected_rows = set()
            for item in self.items_table.selectedItems():
                selected_rows.add(item.row())

            # Update selected_items based on current selection
            new_selected_items = []

            for row in selected_rows:
                name_item = self.items_table.item(row, 0)
                if name_item:
                    item_id = name_item.data(Qt.ItemDataRole.UserRole)
                    item_name = name_item.text()

                    if item_id is not None:
                        selected_item = {
                            'item_id': item_id,
                            'name': item_name,
                            'quantity_borrowed': 1
                        }
                        new_selected_items.append(selected_item)

            # Update the selection list
            self.selected_items = new_selected_items
            logger.debug(f"Updated selection to {len(self.selected_items)} items")

        except Exception as e:
            logger.error(f"Failed to handle selection change: {e}")

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

            # Block signals while populating to prevent unwanted selection updates
            self.items_table.blockSignals(True)
            self.populate_table(filtered_items)
            self.items_table.blockSignals(False)
            logger.debug(f"Filtered to {len(filtered_items)} items matching '{search_term}'")

        except Exception as e:
            logger.error(f"Failed to filter items: {e}")

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
            self.items_table.clearSelection()  # Clear table selection
            logger.info("Cleared all selected items")

    def confirm_selection(self):
        """Show confirmation dialog with selected items before finalizing."""
        if not self.selected_items:
            QMessageBox.warning(self, "No Items Selected", "Please select at least one item before proceeding.")
            return

        try:
            # Create summary message
            summary_lines = []

            for item in self.selected_items:
                name = item.get('name', 'Unknown')
                summary_lines.append(f"• {name}")

            summary_text = "\n".join(summary_lines)

            reply = QMessageBox.question(
                self, "Confirm Selection",
                f"You have selected the following items:\n\n{summary_text}\n\nDo you want to finalize this selection?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.accept()
                logger.info("Selection confirmed and dialog accepted")

        except Exception as e:
            logger.error(f"Failed to confirm selection: {e}")

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
