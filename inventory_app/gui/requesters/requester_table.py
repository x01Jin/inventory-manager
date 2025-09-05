"""
Requester table - displays requester data in a table format.
Provides table widget for showing requesters with selection capabilities.
Uses composition pattern with RequesterModel.
"""

from typing import List, Optional
from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from inventory_app.gui.requesters.requester_model import RequesterRow
from inventory_app.utils.logger import logger


class RequesterTable(QTableWidget):
    """
    Table widget for displaying requester information.
    Shows requester details with selection capabilities.
    """

    # Signals
    requester_selected = pyqtSignal(int)  # Emitted when a requester is selected (requester_id)
    requester_double_clicked = pyqtSignal(int)  # Emitted on double-click (requester_id)

    def __init__(self, parent=None):
        """Initialize the requester table."""
        super().__init__(parent)

        # Configure table properties
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels([
            "Requisitions",
            "Name",
            "Affiliation",
            "Group",
            "Created"
        ])

        # Configure table appearance and behavior
        self._configure_table()

        logger.info("Requester table initialized")

    def _configure_table(self):
        """Configure table appearance and behavior."""
        # Table properties
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setSortingEnabled(True)

        # Disable cell editing on double-click
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        # Header properties
        header = self.horizontalHeader()
        if header:
            header.setStretchLastSection(True)
            header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

        # Set column widths
        self.setColumnWidth(0, 100)  # Requisitions
        self.setColumnWidth(1, 200)  # Name
        self.setColumnWidth(2, 250)  # Affiliation
        self.setColumnWidth(3, 250)  # Group
        self.setColumnWidth(4, 100)  # Created

        # Connect signals
        self.itemSelectionChanged.connect(self._on_selection_changed)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)

    def populate_table(self, requesters: List[RequesterRow]) -> None:
        """
        Populate the table with requester data.

        Args:
            requesters: List of RequesterRow objects to display
        """
        try:
            # Clear existing data
            self.setRowCount(0)

            # Add rows
            for row_data in requesters:
                row_position = self.rowCount()
                self.insertRow(row_position)

                # Requisitions count
                requisitions_item = QTableWidgetItem(str(row_data.requisitions_count))
                self.setItem(row_position, 0, requisitions_item)

                # Name
                name_item = QTableWidgetItem(row_data.name)
                name_item.setData(Qt.ItemDataRole.UserRole, row_data.id)  # Store ID for selection
                self.setItem(row_position, 1, name_item)

                # Affiliation
                self.setItem(row_position, 2, QTableWidgetItem(row_data.affiliation))

                # Group
                self.setItem(row_position, 3, QTableWidgetItem(row_data.group_name))

                # Created date
                created_str = ""
                if row_data.created_datetime:
                    from inventory_app.utils.date_utils import format_date_short, format_time_12h
                    date_str = format_date_short(row_data.created_datetime)
                    time_str = format_time_12h(row_data.created_datetime.time())
                    created_str = f"{date_str} at {time_str}"
                self.setItem(row_position, 4, QTableWidgetItem(created_str))

            logger.info(f"Populated table with {len(requesters)} requesters")

        except Exception as e:
            logger.error(f"Failed to populate requesters table: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load requester data: {str(e)}")

    def get_selected_requester_id(self) -> Optional[int]:
        """
        Get the ID of the currently selected requester.

        Returns:
            Requester ID or None if no selection
        """
        current_row = self.currentRow()
        if current_row >= 0:
            name_item = self.item(current_row, 1)  # Name column has the ID (column 1)
            if name_item:
                return name_item.data(Qt.ItemDataRole.UserRole)
        return None

    def select_requester_by_id(self, requester_id: int) -> bool:
        """
        Select a requester by its ID.

        Args:
            requester_id: ID of the requester to select

        Returns:
            bool: True if found and selected, False otherwise
        """
        for row in range(self.rowCount()):
            name_item = self.item(row, 1)  # Name is in column 1
            if name_item and name_item.data(Qt.ItemDataRole.UserRole) == requester_id:
                self.selectRow(row)
                return True
        return False

    def clear_selection(self) -> None:
        """Clear the current selection."""
        self.clearSelection()

    def get_table_data_for_export(self) -> List[dict]:
        """
        Get table data in a format suitable for export.

        Returns:
            List of dictionaries with column data
        """
        data = []
        for row in range(self.rowCount()):
            # Get items for each column
            requisitions_item = self.item(row, 0)
            name_item = self.item(row, 1)
            affiliation_item = self.item(row, 2)
            group_item = self.item(row, 3)
            created_item = self.item(row, 4)

            row_data = {
                'requisitions': requisitions_item.text() if requisitions_item else "",
                'name': name_item.text() if name_item else "",
                'affiliation': affiliation_item.text() if affiliation_item else "",
                'group': group_item.text() if group_item else "",
                'created': created_item.text() if created_item else ""
            }
            data.append(row_data)
        return data

    def _on_selection_changed(self) -> None:
        """Handle selection changes."""
        requester_id = self.get_selected_requester_id()
        if requester_id is not None:
            self.requester_selected.emit(requester_id)

    def _on_item_double_clicked(self, item) -> None:
        """Handle double-click events."""
        requester_id = self.get_selected_requester_id()
        if requester_id is not None:
            self.requester_double_clicked.emit(requester_id)

    def resize_columns_to_contents(self) -> None:
        """Resize columns to fit their contents."""
        for column in range(self.columnCount()):
            self.resizeColumnToContents(column)

        # Ensure some columns have reasonable minimum widths
        self.setColumnWidth(0, max(self.columnWidth(0), 100))  # Requisitions
        self.setColumnWidth(1, max(self.columnWidth(1), 200))  # Name
        self.setColumnWidth(2, max(self.columnWidth(2), 200))  # Affiliation
        self.setColumnWidth(3, max(self.columnWidth(3), 200))  # Group
