"""
Item selector dialog for choosing items in laboratory requisitions.
Provides searchable interface for selecting items using simplified table structure.
"""

from typing import List, Dict, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QGroupBox, QMessageBox, QHeaderView,
    QAbstractItemView, QSpinBox, QWidget
)
from PyQt6.QtCore import Qt

from inventory_app.gui.requisitions.requisitions_controller import RequisitionsController
from inventory_app.gui.styles import DarkTheme
from inventory_app.utils.logger import logger


class QuantityWidget(QWidget):
    """Custom widget for quantity input showing available/requested format."""

    def __init__(self, available_stock: int, parent=None):
        super().__init__(parent)
        self.available_stock = available_stock
        self.setup_ui()

    def setup_ui(self):
        """Setup the quantity widget UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)

        # Display available stock
        self.available_label = QLabel(f"{self.available_stock}/")
        self.available_label.setStyleSheet("color: #888888; font-size: 11px;")

        # Quantity input (spinbox for easy editing)
        self.quantity_spinbox = QSpinBox()
        self.quantity_spinbox.setMinimum(0)
        self.quantity_spinbox.setMaximum(self.available_stock)
        self.quantity_spinbox.setValue(0)
        self.quantity_spinbox.setFixedWidth(60)
        self.quantity_spinbox.setStyleSheet("""
            QSpinBox {
                padding: 2px;
                border: 1px solid #555;
                border-radius: 3px;
                background-color: #2a2a2a;
                color: #ffffff;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 16px;
                height: 12px;
            }
        """)

        layout.addWidget(self.available_label)
        layout.addWidget(self.quantity_spinbox)
        layout.addStretch()

    def get_quantity(self) -> int:
        """Get the current quantity value."""
        return self.quantity_spinbox.value()

    def set_quantity(self, quantity: int):
        """Set the quantity value."""
        self.quantity_spinbox.setValue(min(quantity, self.available_stock))


class ItemSelector(QDialog):
    """Dialog for selecting items and quantities for requisitions."""

    # Column definitions
    COLUMNS = ["Quantity", "Name", "Category", "Size", "Brand", "Supplier"]

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
        self.items_table.setColumnCount(len(self.COLUMNS))
        self.items_table.setHorizontalHeaderLabels(self.COLUMNS)

        # Configure table properties
        self.items_table.setAlternatingRowColors(True)
        self.items_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.items_table.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.items_table.setSortingEnabled(True)

        # Configure header
        header = self.items_table.horizontalHeader()
        if header:
            header.setSectionsMovable(False)
            header.setStretchLastSection(True)

        # Set column widths
        self.items_table.setColumnWidth(0, 120)  # Quantity
        self.items_table.setColumnWidth(1, 200)  # Name
        self.items_table.setColumnWidth(2, 120)  # Category
        self.items_table.setColumnWidth(3, 80)   # Size
        self.items_table.setColumnWidth(4, 100)  # Brand
        self.items_table.setColumnWidth(5, 120)  # Supplier

        # Apply dark theme styling
        self.apply_styling()

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
        self.setMinimumWidth(900)
        self.setMinimumHeight(600)
        self.setModal(True)

    def apply_styling(self):
        """Apply dark theme styling to the table."""
        self.items_table.setStyleSheet(f"""
            QTableWidget {{
                gridline-color: {DarkTheme.BORDER_COLOR};
                background-color: {DarkTheme.SECONDARY_DARK};
                border: 1px solid {DarkTheme.BORDER_COLOR};
                border-radius: 6px;
                selection-background-color: {DarkTheme.ACCENT_COLOR};
            }}

            QTableWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {DarkTheme.BORDER_COLOR};
                color: {DarkTheme.TEXT_PRIMARY};
            }}

            QTableWidget::item:selected {{
                background-color: {DarkTheme.ACCENT_COLOR};
            }}

            QHeaderView::section {{
                background-color: {DarkTheme.PRIMARY_DARK};
                color: {DarkTheme.TEXT_PRIMARY};
                padding: 8px;
                border: 1px solid {DarkTheme.BORDER_COLOR};
                font-weight: bold;
            }}
        """)

    def load_items(self):
        """Load all available inventory batches."""
        try:
            if self.current_requisition_id is not None:
                # Editing mode: include batches borrowed by current requisition
                self.all_items = self.controller.get_inventory_batches_for_editing(self.current_requisition_id)
                logger.info(f"Loaded {len(self.all_items)} inventory batches for editing requisition {self.current_requisition_id}")
            else:
                # New requisition mode: show batches with available stock
                self.all_items = self.controller.get_inventory_batches_for_selection()
                logger.info(f"Loaded {len(self.all_items)} inventory batches for new requisition")

            self.populate_table(self.all_items)
            # Unblock signals after initial setup
            self.items_table.blockSignals(False)
        except Exception as e:
            logger.error(f"Failed to load batches: {e}")
            QMessageBox.critical(self, "Error", "Failed to load inventory batches.")

    def populate_table(self, batches: List[Dict]):
        """Populate the items table with batch data."""
        try:
            self.items_table.setRowCount(0)

            for batch in batches:
                row_position = self.items_table.rowCount()
                self.items_table.insertRow(row_position)

                # Quantity widget (available/requested format)
                available_stock = batch.get('available_stock', 0)
                quantity_widget = QuantityWidget(available_stock)
                quantity_widget.quantity_spinbox.valueChanged.connect(
                    lambda value, row=row_position: self._on_quantity_changed(row, value)
                )
                self.items_table.setCellWidget(row_position, 0, quantity_widget)

                # Batch display name (includes batch number)
                batch_display_name = batch.get('batch_display_name', batch.get('item_name', ''))
                name_item = QTableWidgetItem(batch_display_name)
                name_item.setData(Qt.ItemDataRole.UserRole, {
                    'batch_id': batch.get('batch_id'),
                    'item_id': batch.get('item_id'),
                    'item_name': batch.get('item_name', '')
                })
                self.items_table.setItem(row_position, 1, name_item)

                # Category
                self.items_table.setItem(row_position, 2, QTableWidgetItem(batch.get('category_name', 'N/A')))

                # Size
                self.items_table.setItem(row_position, 3, QTableWidgetItem(batch.get('size', 'N/A')))

                # Brand
                self.items_table.setItem(row_position, 4, QTableWidgetItem(batch.get('brand', 'N/A')))

                # Supplier
                self.items_table.setItem(row_position, 5, QTableWidgetItem(batch.get('supplier_name', 'N/A')))

                # Set pre-selected quantity if batch is already selected
                if self._is_batch_selected(batch.get('batch_id')):
                    selected_batch = next(
                        (sel_batch for sel_batch in self.selected_items if sel_batch.get('batch_id') == batch.get('batch_id')),
                        None
                    )
                    if selected_batch:
                        quantity_widget.set_quantity(selected_batch['quantity_borrowed'])
                        self.items_table.selectRow(row_position)

            # Resize rows to fit content
            self.items_table.resizeRowsToContents()

            logger.debug(f"Populated table with {len(batches)} batches")

        except Exception as e:
            logger.error(f"Failed to populate table: {e}")

    def _is_item_selected(self, item_id: Optional[int]) -> bool:
        """Check if an item is already selected."""
        if item_id is None:
            return False
        return any(item['item_id'] == item_id for item in self.selected_items)

    def _is_batch_selected(self, batch_id: Optional[int]) -> bool:
        """Check if a batch is already selected."""
        if batch_id is None:
            return False
        return any(item.get('batch_id') == batch_id for item in self.selected_items)

    def _on_quantity_changed(self, row: int, quantity: int):
        """Handle quantity input changes."""
        try:
            if quantity <= 0:
                return

            # Get batch information from the name column (column 1)
            name_item = self.items_table.item(row, 1)
            if not name_item:
                return

            item_data = name_item.data(Qt.ItemDataRole.UserRole)
            if not isinstance(item_data, dict):
                return

            batch_id = item_data.get('batch_id')
            item_id = item_data.get('item_id')
            item_name = item_data.get('item_name', name_item.text())

            if batch_id is not None and item_id is not None:
                # Check if batch is already in selected_items
                existing_batch = next((batch for batch in self.selected_items if batch.get('batch_id') == batch_id), None)

                if existing_batch:
                    # Update existing batch
                    existing_batch['quantity_borrowed'] = quantity
                else:
                    # Add new batch
                    selected_batch = {
                        'batch_id': batch_id,
                        'item_id': item_id,
                        'name': item_name,
                        'quantity_borrowed': quantity
                    }
                    self.selected_items.append(selected_batch)

                logger.debug(f"Updated quantity for batch {batch_id} (item {item_id}): {quantity}")

        except Exception as e:
            logger.error(f"Failed to handle quantity change: {e}")

    def _on_selection_changed(self):
        """Handle table selection changes."""
        try:
            # Get currently selected rows
            selected_rows = set()
            for item in self.items_table.selectedItems():
                selected_rows.add(item.row())

            # Update selected_items based on current selection and quantities
            new_selected_items = []

            for row in selected_rows:
                name_item = self.items_table.item(row, 1)  # Name is in column 1
                if name_item:
                    item_id = name_item.data(Qt.ItemDataRole.UserRole)
                    item_name = name_item.text()

                    if item_id is not None:
                        # Get quantity from quantity widget (column 0)
                        quantity_widget = self.items_table.cellWidget(row, 0)
                        quantity = 0  # Default to 0
                        if quantity_widget and isinstance(quantity_widget, QuantityWidget):
                            quantity = quantity_widget.get_quantity()

                        if quantity > 0:  # Only include items with quantity > 0
                            selected_item = {
                                'item_id': item_id,
                                'name': item_name,
                                'quantity_borrowed': quantity
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
        """Show confirmation dialog with selected batches before finalizing."""
        # Collect all batches with quantities from the table
        selected_batches_with_qty = []

        for row in range(self.items_table.rowCount()):
            quantity_widget = self.items_table.cellWidget(row, 0)  # Quantity is in column 0
            if quantity_widget and isinstance(quantity_widget, QuantityWidget):
                quantity = quantity_widget.get_quantity()
                if quantity > 0:
                    name_item = self.items_table.item(row, 1)  # Name is in column 1
                    if name_item:
                        item_data = name_item.data(Qt.ItemDataRole.UserRole)
                        if isinstance(item_data, dict):
                            batch_id = item_data.get('batch_id')
                            item_id = item_data.get('item_id')
                            item_name = item_data.get('item_name', name_item.text())

                            if batch_id is not None and item_id is not None:
                                selected_batches_with_qty.append({
                                    'batch_id': batch_id,
                                    'item_id': item_id,
                                    'name': item_name,
                                    'quantity_borrowed': quantity
                                })

        if not selected_batches_with_qty:
            QMessageBox.warning(self, "No Batches Selected", "Please enter quantities for at least one batch before proceeding.")
            return

        try:
            # Create summary message
            summary_lines = []

            for batch in selected_batches_with_qty:
                name = batch.get('name', 'Unknown')
                quantity = batch.get('quantity_borrowed', 0)
                summary_lines.append(f"• {name} (Quantity: {quantity})")

            summary_text = "\n".join(summary_lines)

            reply = QMessageBox.question(
                self, "Confirm Selection",
                f"You have selected the following batches:\n\n{summary_text}\n\nDo you want to finalize this selection?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.selected_items = selected_batches_with_qty
                self.accept()
                logger.info(f"Selection confirmed with {len(selected_batches_with_qty)} batches")

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
