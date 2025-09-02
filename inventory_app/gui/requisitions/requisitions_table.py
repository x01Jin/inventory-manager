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

        # Configure table properties - Updated column order
        self.setColumnCount(10)
        self.setHorizontalHeaderLabels([
            "Status",           # 1. Status (Active/Returned)
            "Borrower",         # 2. Borrower name
            "Affiliation",      # 3. Borrower affiliation
            "Activity",         # 4. Lab activity name
            "Activity Date",    # 5. When the activity occurs
            "Students",         # 6. Number of students (optional)
            "Groups",           # 7. Number of groups (optional)
            "Items",            # 8. List of borrowed items
            "Borrowed Date",    # 9. Date when items were borrowed
            "Time"              # 10. Time when items were borrowed
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

        # Header properties - Responsive design
        header = self.horizontalHeader()
        if header:
            header.setStretchLastSection(True)
            # Set responsive column sizing
            for col in range(self.columnCount()):
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

        # Set minimum widths for readability
        self.setColumnWidth(0, 80)   # Status
        self.setColumnWidth(1, 150)  # Borrower
        self.setColumnWidth(2, 120)  # Affiliation
        self.setColumnWidth(3, 200)  # Activity
        self.setColumnWidth(4, 100)  # Activity Date
        self.setColumnWidth(5, 80)   # Students
        self.setColumnWidth(6, 80)   # Groups
        self.setColumnWidth(7, 250)  # Items (needs more space for word wrap)
        self.setColumnWidth(8, 80)   # Status
        self.setColumnWidth(9, 100)  # Borrowed Date
        self.setColumnWidth(10, 80)  # Time

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
                status_item = QTableWidgetItem(row_data.status)
                self.setItem(row_position, 0, status_item)
                self._color_status_item(status_item, row_data.status)

                # Borrower (Column 1)
                borrower_item = QTableWidgetItem(row_data.borrower_name)
                borrower_item.setData(Qt.ItemDataRole.UserRole, row_data.id)  # Store ID for selection
                self.setItem(row_position, 1, borrower_item)

                # Affiliation (Column 2)
                self.setItem(row_position, 2, QTableWidgetItem(row_data.borrower_affiliation))

                # Activity (Column 3)
                self.setItem(row_position, 3, QTableWidgetItem(row_data.lab_activity_name))

                # Activity Date (Column 4)
                activity_date_str = row_data.lab_activity_date.strftime("%Y-%m-%d") if row_data.lab_activity_date else ""
                self.setItem(row_position, 4, QTableWidgetItem(activity_date_str))

                # Students (Column 5)
                students_str = str(row_data.num_students) if row_data.num_students else ""
                self.setItem(row_position, 5, QTableWidgetItem(students_str))

                # Groups (Column 6)
                groups_str = str(row_data.num_groups) if row_data.num_groups else ""
                self.setItem(row_position, 6, QTableWidgetItem(groups_str))

                # Items (Column 7)
                items_item = QTableWidgetItem(row_data.items_list)
                items_item.setToolTip(row_data.items_list)  # Show full list on hover
                self.setItem(row_position, 7, items_item)

                # Borrowed Date (Column 8)
                borrowed_date_str = row_data.datetime_borrowed.strftime("%Y-%m-%d") if row_data.datetime_borrowed else ""
                self.setItem(row_position, 8, QTableWidgetItem(borrowed_date_str))

                # Time (Column 9)
                borrowed_time_str = row_data.datetime_borrowed.strftime("%H:%M") if row_data.datetime_borrowed else ""
                self.setItem(row_position, 9, QTableWidgetItem(borrowed_time_str))

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
            # Get items for each column (updated column order)
            status_item = self.item(row, 0)
            borrower_item = self.item(row, 1)
            affiliation_item = self.item(row, 2)
            activity_item = self.item(row, 3)
            activity_date_item = self.item(row, 4)
            students_item = self.item(row, 5)
            groups_item = self.item(row, 6)
            items_item = self.item(row, 7)
            borrowed_date_item = self.item(row, 8)
            time_item = self.item(row, 9)

            row_data = {
                'status': status_item.text() if status_item else "",
                'borrower': borrower_item.text() if borrower_item else "",
                'affiliation': affiliation_item.text() if affiliation_item else "",
                'activity': activity_item.text() if activity_item else "",
                'activity_date': activity_date_item.text() if activity_date_item else "",
                'students': students_item.text() if students_item else "",
                'groups': groups_item.text() if groups_item else "",
                'items': items_item.text() if items_item else "",
                'borrowed_date': borrowed_date_item.text() if borrowed_date_item else "",
                'time': time_item.text() if time_item else ""
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

        # Ensure some columns have reasonable minimum widths (updated column indices)
        self.setColumnWidth(1, max(self.columnWidth(1), 150))  # Borrower (column 1)
        self.setColumnWidth(3, max(self.columnWidth(3), 200))  # Activity (column 3)
        self.setColumnWidth(7, max(self.columnWidth(7), 250))  # Items (column 7)
