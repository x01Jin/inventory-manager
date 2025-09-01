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

        # Configure table properties
        self.setColumnCount(9)
        self.setHorizontalHeaderLabels([
            "Borrower",
            "Affiliation",
            "Activity",
            "Activity Date",
            "Students",
            "Groups",
            "Items",
            "Status",
            "Borrowed Date"
        ])

        # Configure table appearance and behavior
        self._configure_table()

        logger.info("Requisitions table initialized")

    def _configure_table(self):
        """Configure table appearance and behavior."""
        # Table properties
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setSortingEnabled(True)

        # Header properties
        header = self.horizontalHeader()
        if header:
            header.setStretchLastSection(True)
            header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

        # Set column widths
        self.setColumnWidth(0, 150)  # Borrower
        self.setColumnWidth(1, 120)  # Affiliation
        self.setColumnWidth(2, 200)  # Activity
        self.setColumnWidth(3, 100)  # Activity Date
        self.setColumnWidth(4, 80)   # Students
        self.setColumnWidth(5, 80)   # Groups
        self.setColumnWidth(6, 250)  # Items
        self.setColumnWidth(7, 80)   # Status
        self.setColumnWidth(8, 100)  # Borrowed Date

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

                # Borrower name
                borrower_item = QTableWidgetItem(row_data.borrower_name)
                borrower_item.setData(Qt.ItemDataRole.UserRole, row_data.id)  # Store ID for selection
                self.setItem(row_position, 0, borrower_item)

                # Affiliation
                self.setItem(row_position, 1, QTableWidgetItem(row_data.borrower_affiliation))

                # Activity name
                self.setItem(row_position, 2, QTableWidgetItem(row_data.lab_activity_name))

                # Activity date
                activity_date_str = row_data.lab_activity_date.strftime("%Y-%m-%d") if row_data.lab_activity_date else ""
                activity_date_item = QTableWidgetItem(activity_date_str)
                self.setItem(row_position, 3, activity_date_item)

                # Students
                students_str = str(row_data.num_students) if row_data.num_students else ""
                self.setItem(row_position, 4, QTableWidgetItem(students_str))

                # Groups
                groups_str = str(row_data.num_groups) if row_data.num_groups else ""
                self.setItem(row_position, 5, QTableWidgetItem(groups_str))

                # Items list
                items_item = QTableWidgetItem(row_data.items_list)
                items_item.setToolTip(row_data.items_list)  # Show full list on hover
                self.setItem(row_position, 6, items_item)

                # Status
                status_item = QTableWidgetItem(row_data.status)
                self.setItem(row_position, 7, status_item)

                # Color-code status
                self._color_status_item(status_item, row_data.status)

                # Borrowed date
                borrowed_date_str = row_data.date_borrowed.strftime("%Y-%m-%d") if row_data.date_borrowed else ""
                self.setItem(row_position, 8, QTableWidgetItem(borrowed_date_str))

            logger.info(f"Populated table with {len(requisitions)} requisitions")

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
            borrower_item = self.item(current_row, 0)  # Borrower column has the ID
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
            borrower_item = self.item(row, 0)
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
            # Get items for each column (to avoid multiple calls)
            borrower_item = self.item(row, 0)
            affiliation_item = self.item(row, 1)
            activity_item = self.item(row, 2)
            activity_date_item = self.item(row, 3)
            students_item = self.item(row, 4)
            groups_item = self.item(row, 5)
            items_item = self.item(row, 6)
            status_item = self.item(row, 7)
            borrowed_date_item = self.item(row, 8)

            row_data = {
                'borrower': borrower_item.text() if borrower_item else "",
                'affiliation': affiliation_item.text() if affiliation_item else "",
                'activity': activity_item.text() if activity_item else "",
                'activity_date': activity_date_item.text() if activity_date_item else "",
                'students': students_item.text() if students_item else "",
                'groups': groups_item.text() if groups_item else "",
                'items': items_item.text() if items_item else "",
                'status': status_item.text() if status_item else "",
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
        if status == "Active":
            item.setBackground(QColor("#FFF3CD"))  # Light yellow
            item.setForeground(QColor("#856404"))  # Dark yellow
        elif status == "Returned":
            item.setBackground(QColor("#D1ECF1"))  # Light blue
            item.setForeground(QColor("#0C5460"))  # Dark blue
        elif status == "Overdue":
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
        self.setColumnWidth(0, max(self.columnWidth(0), 150))  # Borrower
        self.setColumnWidth(2, max(self.columnWidth(2), 200))  # Activity
        self.setColumnWidth(6, max(self.columnWidth(6), 250))  # Items
