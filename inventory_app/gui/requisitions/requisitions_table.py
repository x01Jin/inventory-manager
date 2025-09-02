"""
Requisitions table - displays requisition data in a table format.
Provides table widget for showing requisitions with borrower and item information.
Uses composition pattern with RequisitionsModel.
"""

from typing import List, Optional, Dict, Any
from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from inventory_app.gui.requisitions.requisitions_model import RequisitionRow
from inventory_app.utils.logger import logger


class RequisitionsTable(QTableWidget):
    """
    Table widget for displaying requisition information.
    Shows borrower details, activity info, and borrowed items.
    """

    # Signals
    requisition_selected = pyqtSignal(int)  # Emitted when a requisition is selected (requisition_id)
    requisition_double_clicked = pyqtSignal(int)  # Emitted on double-click (requisition_id)

    def __init__(self, parent=None):
        """Initialize the requisitions table."""
        super().__init__(parent)

        # Configure table properties - Simplified to 3 columns
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels([
            "Status",               # 1. Status (Active/Returned)
            "Borrower",             # 2. Borrower name
            "Borrowed Date"         # 3. Date when items were borrowed (or "Reserved")
        ])

        # Configure table appearance and behavior
        self._configure_table()

        logger.info("Requisitions table initialized with datetime support")

    def _configure_table(self):
        """Configure table appearance and behavior."""
        # Table properties
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setSortingEnabled(True)

        # Disable cell editing on double-click
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        # Header properties - Responsive design
        header = self.horizontalHeader()
        if header:
            header.setStretchLastSection(True)
            # Set responsive column sizing
            for col in range(self.columnCount()):
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

        # Set minimum widths for readability
        self.setColumnWidth(0, 80)   # Status
        self.setColumnWidth(1, 200)  # Borrower (more space for names)
        self.setColumnWidth(2, 150)  # Borrowed Date

        # Connect signals
        self.itemSelectionChanged.connect(self._on_selection_changed)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)

    def populate_table(self, requisitions: List[RequisitionRow]) -> None:
        """
        Populate the table with requisition data.

        Args:
            requisitions: List of RequisitionRow objects to display
        """
        try:
            # Clear existing data
            self.setRowCount(0)

            # Add rows
            for row_data in requisitions:
                row_position = self.rowCount()
                self.insertRow(row_position)

                # Status (Column 0)
                display_status = row_data.status.capitalize() if row_data.status else "Unknown"
                status_item = QTableWidgetItem(display_status)
                self.setItem(row_position, 0, status_item)
                self._color_status_item(status_item, row_data.status)

                # Borrower (Column 1)
                borrower_item = QTableWidgetItem(row_data.borrower_name)
                borrower_item.setData(Qt.ItemDataRole.UserRole, row_data.id)  # Store ID for selection
                self.setItem(row_position, 1, borrower_item)

                # Borrowed Date (Column 2) - Show actual date or "Reserved"
                if row_data.datetime_borrowed:
                    borrowed_date_str = row_data.datetime_borrowed.strftime("%Y-%m-%d %H:%M")
                else:
                    borrowed_date_str = "Reserved"
                borrowed_item = QTableWidgetItem(borrowed_date_str)
                self.setItem(row_position, 2, borrowed_item)

        except Exception as e:
            logger.error(f"Failed to populate requisitions table: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load requisition data: {str(e)}")

    def get_selected_requisition_id(self) -> Optional[int]:
        """
        Get the ID of the currently selected requisition.

        Returns:
            Requisition ID or None if no selection
        """
        current_row = self.currentRow()
        if current_row >= 0:
            borrower_item = self.item(current_row, 1)  # Borrower is in column 1
            if borrower_item:
                return borrower_item.data(Qt.ItemDataRole.UserRole)
        return None

    def select_requisition_by_id(self, requisition_id: int) -> bool:
        """
        Select a requisition by its ID.

        Args:
            requisition_id: ID of the requisition to select

        Returns:
            bool: True if found and selected, False otherwise
        """
        for row in range(self.rowCount()):
            borrower_item = self.item(row, 1)  # Borrower is in column 1
            if borrower_item and borrower_item.data(Qt.ItemDataRole.UserRole) == requisition_id:
                self.selectRow(row)
                return True
        return False

    def clear_selection(self) -> None:
        """Clear the current selection."""
        self.clearSelection()

    def get_table_data_for_export(self) -> List[Dict[str, Any]]:
        """
        Get table data in a format suitable for export.

        Returns:
            List of dictionaries with column data
        """
        data = []
        for row in range(self.rowCount()):
            # Get items for each column (3 columns only)
            status_item = self.item(row, 0)
            borrower_item = self.item(row, 1)
            borrowed_date_item = self.item(row, 2)

            row_data = {
                'status': status_item.text() if status_item else "",
                'borrower': borrower_item.text() if borrower_item else "",
                'borrowed_date': borrowed_date_item.text() if borrowed_date_item else ""
            }
            data.append(row_data)
        return data

    def _color_status_item(self, item: QTableWidgetItem, status: str) -> None:
        """
        Color-code the status item based on status value.

        Args:
            item: The table item to color
            status: The status string
        """
        if status == "active":
            item.setBackground(QColor("#FFF3CD"))  # Light yellow
            item.setForeground(QColor("#856404"))  # Dark yellow
        elif status == "returned":
            item.setBackground(QColor("#D1ECF1"))  # Light blue
            item.setForeground(QColor("#0C5460"))  # Dark blue
        elif status == "overdue":
            item.setBackground(QColor("#F8D7DA"))  # Light red
            item.setForeground(QColor("#721C24"))  # Dark red
        else:
            # Default colors
            item.setBackground(QColor("#FFFFFF"))  # White
            item.setForeground(QColor("#000000"))  # Black

    def _on_selection_changed(self) -> None:
        """Handle selection changes."""
        requisition_id = self.get_selected_requisition_id()
        if requisition_id is not None:
            self.requisition_selected.emit(requisition_id)

    def _on_item_double_clicked(self, item) -> None:
        """Handle double-click events."""
        requisition_id = self.get_selected_requisition_id()
        if requisition_id is not None:
            self.requisition_double_clicked.emit(requisition_id)

    def resize_columns_to_contents(self) -> None:
        """Resize columns to fit their contents."""
        for column in range(self.columnCount()):
            self.resizeColumnToContents(column)

        # Ensure some columns have reasonable minimum widths
        self.setColumnWidth(0, max(self.columnWidth(0), 80))    # Status (column 0)
        self.setColumnWidth(1, max(self.columnWidth(1), 200))   # Borrower (column 1)
        self.setColumnWidth(2, max(self.columnWidth(2), 150))   # Borrowed Date (column 2)
