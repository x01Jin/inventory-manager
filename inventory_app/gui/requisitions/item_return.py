"""
Item return dialog for processing laboratory equipment returns.
Provides interface for selecting items and quantities to return.
"""

from typing import List, Dict, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QGroupBox, QMessageBox, QHeaderView,
    QAbstractItemView, QLineEdit, QFormLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from inventory_app.gui.requisitions.requisitions_controller import RequisitionsController
from inventory_app.services.validation_service import ValidationService
from inventory_app.utils.logger import logger


class ItemReturnDialog(QDialog):
    """
    Dialog for processing item returns from requisitions.
    Allows selection of items and quantities to return.
    """

    # Signal emitted when return is successfully processed
    return_completed = pyqtSignal()

    def __init__(self, parent=None, requisition_id: Optional[int] = None):
        super().__init__(parent)
        self.requisition_id = requisition_id
        self.controller = RequisitionsController()
        self.validation_service = ValidationService()
        self.borrowed_items: List[Dict] = []
        self.return_quantities: Dict[int, int] = {}  # item_id -> return_quantity

        self.setWindowTitle("Return Items")
        self.setModal(True)
        self.setup_ui()
        self.load_borrowed_items()

    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header with requisition info
        header_group = QGroupBox("Return Items")
        header_layout = QVBoxLayout(header_group)

        self.requisition_info_label = QLabel("Loading requisition details...")
        self.requisition_info_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(self.requisition_info_label)

        layout.addWidget(header_group)

        # Items table
        table_group = QGroupBox("Items to Return")
        table_layout = QVBoxLayout(table_group)

        self.items_table = QTableWidget()
        self.items_table.setColumnCount(2)
        self.items_table.setHorizontalHeaderLabels([
            "Item Name", "Status"
        ])

        # Configure table
        header = self.items_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.items_table.setAlternatingRowColors(True)
        self.items_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.items_table.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.items_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        # Connect selection change signal
        self.items_table.itemSelectionChanged.connect(self._on_selection_changed)

        # Set column widths
        self.items_table.setColumnWidth(0, 400)  # Item Name
        self.items_table.setColumnWidth(1, 120)  # Status

        table_layout.addWidget(self.items_table)
        layout.addWidget(table_group)

        # Editor information (Spec #14)
        editor_group = QGroupBox("Editor Information")
        editor_layout = QFormLayout(editor_group)

        self.editor_name_input = QLineEdit()
        self.editor_name_input.setPlaceholderText("Enter your name/initials (required)")
        self.editor_name_input.textChanged.connect(self._update_button_state)
        editor_layout.addRow("Editor Name:", self.editor_name_input)

        layout.addWidget(editor_group)

        # Summary
        summary_group = QGroupBox("Return Summary")
        summary_layout = QVBoxLayout(summary_group)

        self.summary_label = QLabel("No items selected for return")
        self.summary_label.setStyleSheet("color: #666;")
        summary_layout.addWidget(self.summary_label)

        layout.addWidget(summary_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        self.return_button = QPushButton("✅ Process Return")
        self.return_button.clicked.connect(self.process_return)
        self.return_button.setDefault(True)
        self.return_button.setEnabled(False)
        button_layout.addWidget(self.return_button)

        layout.addLayout(button_layout)

        # Set dialog properties
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)

    def load_borrowed_items(self):
        """Load items that are currently borrowed for this requisition."""
        if not self.requisition_id:
            QMessageBox.warning(self, "Error", "No requisition selected.")
            self.reject()
            return

        try:
            # Get requisition details
            requisition_summary = self.controller.get_all_requisitions()
            current_req = None

            for req in requisition_summary:
                if req.requisition.id == self.requisition_id:
                    current_req = req
                    break

            if not current_req:
                QMessageBox.warning(self, "Error", "Requisition not found.")
                self.reject()
                return

            # Update header info
            borrower_name = current_req.borrower.name
            activity_name = current_req.requisition.lab_activity_name
            activity_date = current_req.requisition.lab_activity_date

            self.requisition_info_label.setText(
                f"Requisition #{self.requisition_id} - {borrower_name}\n"
                f"Activity: {activity_name} ({activity_date})"
            )

            # Get borrowed items that haven't been fully returned
            self.borrowed_items = self._get_borrowed_items_for_return(self.requisition_id)

            if not self.borrowed_items:
                QMessageBox.information(self, "No Items",
                                      "All items for this requisition have already been returned.")
                self.reject()
                return

            self.populate_table()
            logger.info(f"Loaded {len(self.borrowed_items)} borrowed items for return")

        except Exception as e:
            logger.error(f"Failed to load borrowed items: {e}")
            QMessageBox.critical(self, "Error", "Failed to load requisition items.")
            self.reject()

    def _get_borrowed_items_for_return(self, requisition_id: int) -> List[Dict]:
        """Get items that are still outstanding for return."""
        try:
            # Get all items in the requisition
            requisition_items = self.controller.item_service.get_requisition_items_with_details(requisition_id)

            # Filter out items that have been fully returned
            outstanding_items = []

            for item in requisition_items:
                item_id = item['item_id']
                borrowed_qty = item['quantity_borrowed']

                # Calculate returned quantity
                returned_qty = self._get_returned_quantity(item_id, requisition_id)

                if returned_qty < borrowed_qty:
                    outstanding_qty = borrowed_qty - returned_qty
                    item_copy = item.copy()
                    item_copy['outstanding_quantity'] = outstanding_qty
                    item_copy['returned_quantity'] = returned_qty
                    outstanding_items.append(item_copy)

            return outstanding_items

        except Exception as e:
            logger.error(f"Failed to get borrowed items for return: {e}")
            return []

    def _get_returned_quantity(self, item_id: int, requisition_id: int) -> int:
        """Get the quantity of an item that has been returned for this requisition."""
        try:
            from inventory_app.database.connection import db
            query = """
            SELECT COALESCE(SUM(quantity), 0) as returned_qty
            FROM Stock_Movements
            WHERE item_id = ? AND source_id = ? AND movement_type = 'RETURN'
            """
            rows = db.execute_query(query, (item_id, requisition_id))
            return rows[0]['returned_qty'] if rows else 0
        except Exception as e:
            logger.error(f"Failed to get returned quantity: {e}")
            return 0

    def populate_table(self):
        """Populate the items table with borrowed items."""
        try:
            self.items_table.setRowCount(0)

            for item in self.borrowed_items:
                row_position = self.items_table.rowCount()
                self.items_table.insertRow(row_position)

                # Item Name with LAB code
                unique_code = item.get('unique_code', 'NO-CODE')
                item_name = item.get('name', '')
                display_name = f"{unique_code}: {item_name}"
                name_item = QTableWidgetItem(display_name)
                name_item.setData(Qt.ItemDataRole.UserRole, item.get('item_id'))
                self.items_table.setItem(row_position, 0, name_item)

                # Status
                status_item = QTableWidgetItem("Ready for Return")
                status_item.setForeground(QColor(0, 123, 255))  # Blue color
                self.items_table.setItem(row_position, 1, status_item)

            logger.debug(f"Populated table with {len(self.borrowed_items)} items for return")

        except Exception as e:
            logger.error(f"Failed to populate table: {e}")

    def _on_selection_changed(self):
        """Handle table selection changes."""
        try:
            # Clear previous selections
            self.return_quantities.clear()

            # Get currently selected rows
            selected_rows = set()
            for item in self.items_table.selectedItems():
                selected_rows.add(item.row())

            # Update return quantities for selected items
            for row in selected_rows:
                name_item = self.items_table.item(row, 0)
                if name_item:
                    item_id = name_item.data(Qt.ItemDataRole.UserRole)
                    if item_id is not None:
                        # Since items are unique, return quantity is always 1
                        self.return_quantities[item_id] = 1

                        # Update status to selected
                        status_item = self.items_table.item(row, 1)
                        if status_item:
                            status_item.setText("Selected for Return")
                            status_item.setForeground(QColor(40, 167, 69))  # Green

            # Reset status for unselected items
            for row in range(self.items_table.rowCount()):
                if row not in selected_rows:
                    status_item = self.items_table.item(row, 1)
                    if status_item:
                        status_item.setText("Ready for Return")
                        status_item.setForeground(QColor(0, 123, 255))  # Blue

            # Update summary and button state
            self._update_summary()
            self._update_button_state()

            logger.debug(f"Updated selection to {len(self.return_quantities)} items")

        except Exception as e:
            logger.error(f"Failed to handle selection change: {e}")

    def _update_summary(self):
        """Update the return summary display."""
        try:
            total_items = len([q for q in self.return_quantities.values() if q > 0])
            total_quantity = sum(self.return_quantities.values())

            if total_items == 0:
                self.summary_label.setText("No items selected for return")
                self.summary_label.setStyleSheet("color: #666;")
            else:
                self.summary_label.setText(
                    f"Returning {total_quantity} units from {total_items} item type(s)"
                )
                self.summary_label.setStyleSheet("color: #27ae60; font-weight: bold;")

        except Exception as e:
            logger.error(f"Failed to update summary: {e}")

    def _update_button_state(self):
        """Update the return button enabled state."""
        has_items_to_return = any(q > 0 for q in self.return_quantities.values())
        editor_name_valid = bool(self.editor_name_input.text().strip())
        self.return_button.setEnabled(has_items_to_return and editor_name_valid)

    def process_return(self):
        """Process the return of selected items."""
        try:
            # Validate inputs
            if not self.return_quantities:
                QMessageBox.warning(self, "No Items", "Please select at least one item to return.")
                return

            editor_name = self.editor_name_input.text().strip()
            if not editor_name:
                QMessageBox.warning(self, "Editor Required", "Editor name is required (Spec #14).")
                self.editor_name_input.setFocus()
                return

            # Prepare return data
            return_data = []
            for item_id, quantity in self.return_quantities.items():
                if quantity > 0:
                    return_data.append({
                        'item_id': item_id,
                        'quantity_returned': quantity
                    })

            # Validate return data
            if not self.validation_service.validate_return_data(return_data):
                QMessageBox.warning(self, "Validation Error", "Invalid return data.")
                return

            # Show confirmation
            summary_lines = []
            for item in self.borrowed_items:
                item_id = item.get('item_id')
                if item_id in self.return_quantities:
                    return_qty = self.return_quantities[item_id]
                    if return_qty > 0:
                        name = f"{item.get('unique_code', '')}: {item.get('name', '')}"
                        summary_lines.append(f"• {name} - returning {return_qty}")

            summary_text = "\n".join(summary_lines)

            reply = QMessageBox.question(
                self, "Confirm Return",
                f"Are you sure you want to process these returns?\n\n{summary_text}\n\n"
                f"Editor: {editor_name}\n\nThis action cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )

            if reply != QMessageBox.StandardButton.Yes:
                return

            # Process the return
            if self.requisition_id is None:
                QMessageBox.critical(self, "Error", "Invalid requisition ID.")
                return

            logger.info(f"Processing return for requisition {self.requisition_id}")
            success = self.controller.return_items(self.requisition_id, return_data, editor_name)

            if success:
                logger.info(f"Return processed successfully for requisition {self.requisition_id}")
                QMessageBox.information(self, "Success",
                                      "Items returned successfully!\n\n"
                                      "The requisition has been updated and stock levels adjusted.")
                self.return_completed.emit()
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to process return.")

        except Exception as e:
            logger.error(f"Failed to process return: {e}")
            QMessageBox.critical(self, "Error", f"Failed to process return: {str(e)}")

    def get_return_data(self) -> Dict:
        """Get the return data for processing."""
        return {
            'requisition_id': self.requisition_id,
            'return_quantities': self.return_quantities.copy(),
            'editor_name': self.editor_name_input.text().strip()
        }
