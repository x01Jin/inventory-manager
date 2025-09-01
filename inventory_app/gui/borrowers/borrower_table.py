"""
Borrower table - displays borrower data in a table format.
Provides table widget for showing borrowers with selection capabilities.
Uses composition pattern with BorrowerModel.
"""

from typing import List, Optional
from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from inventory_app.gui.borrowers.borrower_model import BorrowerRow
from inventory_app.utils.logger import logger


class BorrowerTable(QTableWidget):
    """
    Table widget for displaying borrower information.
    Shows borrower details with selection capabilities.
    """

    # Signals
    borrower_selected = pyqtSignal(int)  # Emitted when a borrower is selected (borrower_id)
    borrower_double_clicked = pyqtSignal(int)  # Emitted on double-click (borrower_id)

    def __init__(self, parent=None):
        """Initialize the borrower table."""
        super().__init__(parent)

        # Configure table properties
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels([
            "Name",
            "Affiliation",
            "Group",
            "Created"
        ])

        # Configure table appearance and behavior
        self._configure_table()

        logger.info("Borrower table initialized")

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
        self.setColumnWidth(0, 200)  # Name
        self.setColumnWidth(1, 150)  # Affiliation
        self.setColumnWidth(2, 150)  # Group
        self.setColumnWidth(3, 100)  # Created

        # Connect signals
        self.itemSelectionChanged.connect(self._on_selection_changed)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)

    def populate_table(self, borrowers: List[BorrowerRow]) -> None:
        """
        Populate the table with borrower data.

        Args:
            borrowers: List of BorrowerRow objects to display
        """
        try:
            # Clear existing data
            self.setRowCount(0)

            # Add rows
            for row_data in borrowers:
                row_position = self.rowCount()
                self.insertRow(row_position)

                # Name
                name_item = QTableWidgetItem(row_data.name)
                name_item.setData(Qt.ItemDataRole.UserRole, row_data.id)  # Store ID for selection
                self.setItem(row_position, 0, name_item)

                # Affiliation
                self.setItem(row_position, 1, QTableWidgetItem(row_data.affiliation))

                # Group
                self.setItem(row_position, 2, QTableWidgetItem(row_data.group_name))

                # Created date
                created_str = row_data.created_date.strftime("%Y-%m-%d") if row_data.created_date else ""
                self.setItem(row_position, 3, QTableWidgetItem(created_str))

            logger.info(f"Populated table with {len(borrowers)} borrowers")

        except Exception as e:
            logger.error(f"Failed to populate borrowers table: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load borrower data: {str(e)}")

    def get_selected_borrower_id(self) -> Optional[int]:
        """
        Get the ID of the currently selected borrower.

        Returns:
            Borrower ID or None if no selection
        """
        current_row = self.currentRow()
        if current_row >= 0:
            name_item = self.item(current_row, 0)  # Name column has the ID
            if name_item:
                return name_item.data(Qt.ItemDataRole.UserRole)
        return None

    def select_borrower_by_id(self, borrower_id: int) -> bool:
        """
        Select a borrower by its ID.

        Args:
            borrower_id: ID of the borrower to select

        Returns:
            bool: True if found and selected, False otherwise
        """
        for row in range(self.rowCount()):
            name_item = self.item(row, 0)
            if name_item and name_item.data(Qt.ItemDataRole.UserRole) == borrower_id:
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
            name_item = self.item(row, 0)
            affiliation_item = self.item(row, 1)
            group_item = self.item(row, 2)
            created_item = self.item(row, 3)

            row_data = {
                'name': name_item.text() if name_item else "",
                'affiliation': affiliation_item.text() if affiliation_item else "",
                'group': group_item.text() if group_item else "",
                'created': created_item.text() if created_item else ""
            }
            data.append(row_data)
        return data

    def _on_selection_changed(self) -> None:
        """Handle selection changes."""
        borrower_id = self.get_selected_borrower_id()
        if borrower_id is not None:
            self.borrower_selected.emit(borrower_id)

    def _on_item_double_clicked(self, item) -> None:
        """Handle double-click events."""
        borrower_id = self.get_selected_borrower_id()
        if borrower_id is not None:
            self.borrower_double_clicked.emit(borrower_id)

    def resize_columns_to_contents(self) -> None:
        """Resize columns to fit their contents."""
        for column in range(self.columnCount()):
            self.resizeColumnToContents(column)

        # Ensure some columns have reasonable minimum widths
        self.setColumnWidth(0, max(self.columnWidth(0), 200))  # Name
        self.setColumnWidth(1, max(self.columnWidth(1), 150))  # Affiliation
        self.setColumnWidth(2, max(self.columnWidth(2), 150))  # Group
