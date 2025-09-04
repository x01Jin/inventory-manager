"""
Requisitions table - displays requisition data in a table format.
Provides table widget for showing requisitions with requester and item information.
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
    Shows requester details, activity info, requested items, and returned info.
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
            "Requester",             # 2. Requester name
            "Requested Date"         # 3. Date when items were requested (or "Reserved")
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

        # Enable word wrapping for better content display
        self.setWordWrap(True)

        # Header properties - Responsive design with constraints
        header = self.horizontalHeader()
        if header:
            header.setStretchLastSection(False)  # Don't stretch last section
            # Set column sizing modes
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)  # Status - allow resize but constrain
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)  # Requester - allow resize but constrain
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)        # Date - fixed width

        # Set column widths with constraints for word wrapping
        self.setColumnWidth(0, 200)  # Status - wider to accommodate multiple statuses
        self.setColumnWidth(1, 240)  # Requester - reasonable width for names
        self.setColumnWidth(2, 150)  # Requested Date - fixed width for consistency

        # Enable automatic row height adjustment for wrapped content
        vertical_header = self.verticalHeader()
        if vertical_header:
            vertical_header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

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

                # Requester (Column 1)
                requester_item = QTableWidgetItem(row_data.requester_name)
                requester_item.setData(Qt.ItemDataRole.UserRole, row_data.id)  # Store ID for selection
                self.setItem(row_position, 1, requester_item)

                # Requested Date (Column 2) - Show actual date or "Reserved"
                if row_data.datetime_requested:
                    requested_date_str = row_data.datetime_requested.strftime("%Y-%m-%d %H:%M")
                else:
                    requested_date_str = "Reserved"
                requested_item = QTableWidgetItem(requested_date_str)
                self.setItem(row_position, 2, requested_item)

            # After populating all data, resize columns to fit content with constraints
            self.resize_columns_to_contents()

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
            requester_item = self.item(current_row, 1)  # Requester is in column 1
            if requester_item:
                return requester_item.data(Qt.ItemDataRole.UserRole)
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
            requester_item = self.item(row, 1)  # Requester is in column 1
            if requester_item and requester_item.data(Qt.ItemDataRole.UserRole) == requisition_id:
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
            requester_item = self.item(row, 1)
            requested_date_item = self.item(row, 2)

            row_data = {
                'status': status_item.text() if status_item else "",
                'requester': requester_item.text() if requester_item else "",
                'requested_date': requested_date_item.text() if requested_date_item else ""
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
        """Resize columns to fit their contents with word wrapping constraints."""
        # Temporarily disable word wrap to get accurate content width measurements
        original_word_wrap = self.wordWrap()
        self.setWordWrap(False)

        # Resize columns to contents
        for column in range(self.columnCount()):
            self.resizeColumnToContents(column)

        # Restore word wrap
        self.setWordWrap(original_word_wrap)

        # Apply constraints to prevent excessive width while allowing word wrapping
        current_width_0 = self.columnWidth(0)
        current_width_1 = self.columnWidth(1)

        # Constrain status column (allow some growth but not excessive)
        if current_width_0 > 250:
            self.setColumnWidth(0, 250)
        elif current_width_0 < 180:
            self.setColumnWidth(0, 180)

        # Constrain requester column (allow some growth but not excessive)
        if current_width_1 > 280:
            self.setColumnWidth(1, 280)
        elif current_width_1 < 200:
            self.setColumnWidth(1, 200)

        # Keep date column fixed
        self.setColumnWidth(2, 150)
