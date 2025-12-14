"""
Requisitions table - displays requisition data in a table format.
Provides table widget for showing requisitions with requester and item information.
Uses composition pattern with RequisitionsModel.
"""

from typing import List, Optional, Dict, Any
from PyQt6.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QMessageBox,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QShowEvent

from inventory_app.gui.requisitions.requisitions_model import RequisitionRow
from inventory_app.utils.logger import logger
from inventory_app.utils.date_utils import format_date_short, format_time_12h
from inventory_app.gui.styles import DarkTheme

# Some PyQt6 stubs (Pylance) may not expose newer ItemDataRole attributes like SortRole.
# Use getattr with a safe fallback to avoid static analysis errors while keeping runtime
# behavior correct when the attribute exists.
SORT_ROLE = getattr(Qt.ItemDataRole, "SortRole", int(Qt.ItemDataRole.UserRole) + 1)


class RequisitionsTable(QTableWidget):
    """
    Table widget for displaying requisition information.
    Shows requester details, activity info, requested items, and returned info.
    """

    # Signals
    requisition_selected = pyqtSignal(
        int
    )  # Emitted when a requisition is selected (requisition_id)
    requisition_double_clicked = pyqtSignal(
        int
    )  # Emitted on double-click (requisition_id)

    def __init__(self, parent=None):
        """Initialize the requisitions table."""
        super().__init__(parent)

        # Configure table properties - Simplified to 3 columns
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(
            [
                "Status",  # 1. Status (Active/Returned)
                "Requester",  # 2. Requester name
                "Request Date",  # 3. Date of the request
            ]
        )

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

        # Set size policy to allow vertical expansion
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Disable cell editing on double-click
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        # Disable global word wrapping - we'll enable it per cell for requester column
        self.setWordWrap(False)

        # Header properties - Fixed widths for status and date, interactive for requester
        header = self.horizontalHeader()
        if header:
            header.setStretchLastSection(False)  # Don't stretch last section
            header.setSortIndicatorShown(False)
            header.sectionClicked.connect(self._on_header_clicked)
            # Set column sizing modes
            header.setSectionResizeMode(
                0, QHeaderView.ResizeMode.Fixed
            )  # Status - fixed width
            header.setSectionResizeMode(
                1, QHeaderView.ResizeMode.Interactive
            )  # Requester - allow resize with constraints
            header.setSectionResizeMode(
                2, QHeaderView.ResizeMode.Fixed
            )  # Date - fixed width

        # Set column widths
        self.setColumnWidth(0, 150)  # Status - fixed
        self.setColumnWidth(1, 240)  # Requester - max width with word wrap
        self.setColumnWidth(2, 220)  # Requested Date - fixed

        # Enable automatic row height adjustment for wrapped content
        vertical_header = self.verticalHeader()
        if vertical_header:
            vertical_header.setSectionResizeMode(
                QHeaderView.ResizeMode.ResizeToContents
            )

        # Connect signals
        self.itemSelectionChanged.connect(self._on_selection_changed)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)

    class SortableTableItem(QTableWidgetItem):
        """QTableWidgetItem subclass that prefers SortRole for comparisons."""

        def __lt__(self, other):
            try:
                my = self.data(SORT_ROLE)
                ot = other.data(SORT_ROLE)
                if my is not None and ot is not None:
                    return my < ot
            except Exception:
                pass
            # Fallback to case-insensitive text compare
            return (self.text() or "").lower() < (other.text() or "").lower()

    def populate_table(self, requisitions: List[RequisitionRow]) -> None:
        """
        Populate the table with requisition data.

        Args:
            requisitions: List of RequisitionRow objects to display
        """
        try:
            # Disable sorting while we repopulate to avoid mixed-state sorting/visual glitches
            prev_sorting = self.isSortingEnabled()
            self.setSortingEnabled(False)

            # Clear existing data
            self.setRowCount(0)

            # Add rows
            for row_data in requisitions:
                row_position = self.rowCount()
                self.insertRow(row_position)

                # Status (Column 0)
                display_status = (
                    row_data.status.capitalize() if row_data.status else "Unknown"
                )
                status_item = self.SortableTableItem(display_status)
                # Set sort priority for status: requested < active < overdue < returned (lower sorts first)
                status_rank = 99
                s = (row_data.status or "").lower()
                if s == "requested":
                    status_rank = 0
                elif s == "active":
                    status_rank = 1
                elif s == "overdue":
                    status_rank = 2
                elif s == "returned":
                    status_rank = 3
                status_item.setData(SORT_ROLE, status_rank)
                self.setItem(row_position, 0, status_item)
                self._color_status_item(status_item, row_data.status)

                # Requester (Column 1) - Word wrapping will be enabled globally
                requester_item = self.SortableTableItem(row_data.requester_name)
                requester_item.setData(
                    Qt.ItemDataRole.UserRole, row_data.id
                )  # Store ID for selection
                # Case-insensitive alphabetical sort for requester
                requester_item.setData(
                    SORT_ROLE, (row_data.requester_name or "").lower()
                )
                self.setItem(row_position, 1, requester_item)

                # Expected Request (Column 2) - Show expected request datetime and set SortRole
                if row_data.expected_request:
                    date_str = format_date_short(row_data.expected_request)
                    time_str = format_time_12h(row_data.expected_request.time())
                    expected_date_str = f"{date_str}   -   {time_str}"
                    expected_item = self.SortableTableItem(expected_date_str)
                    # Sort by timestamp (recent first). Use negative timestamp so ascending order shows newest first
                    try:
                        ts = row_data.expected_request.timestamp()
                        expected_item.setData(SORT_ROLE, -float(ts))
                    except Exception:
                        expected_item.setData(SORT_ROLE, float("inf"))
                else:
                    # No expected request - use placeholder and set SortRole to +inf so it sorts to bottom
                    expected_item = self.SortableTableItem("")
                    expected_item.setData(SORT_ROLE, float("inf"))

                self.setItem(row_position, 2, expected_item)

            # After populating all data, resize columns to fit content with constraints
            self.resize_columns_to_contents()

            # Restore sorting state and set sensible default sort: Request Date recent-first
            self.setSortingEnabled(prev_sorting)
            if prev_sorting:
                header = self.horizontalHeader()
                # Default sort by status priority (active, overdue, returned)
                # Now includes requested as the highest priority
                if header is not None:
                    header.setSortIndicator(0, Qt.SortOrder.AscendingOrder)
                    header.setSortIndicatorShown(False)
                    # Ensure the rows are actually sorted according to this indicator
                    self.sortItems(0, Qt.SortOrder.AscendingOrder)

        except Exception as e:
            logger.error(f"Failed to populate requisitions table: {e}")
            QMessageBox.critical(
                self, "Error", f"Failed to load requisition data: {str(e)}"
            )

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
            if (
                requester_item
                and requester_item.data(Qt.ItemDataRole.UserRole) == requisition_id
            ):
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
                "status": status_item.text() if status_item else "",
                "requester": requester_item.text() if requester_item else "",
                "expected_request": requested_date_item.text()
                if requested_date_item
                else "",
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
        # Use centralized DarkTheme colors for consistent appearance with dashboard
        if status == "active":
            item.setForeground(QColor(DarkTheme.SUCCESS_COLOR))
        elif status == "requested":
            item.setForeground(QColor(DarkTheme.WARNING_COLOR))
        elif status == "overdue":
            item.setForeground(QColor(DarkTheme.ERROR_COLOR))
        elif status == "returned":
            item.setForeground(QColor(DarkTheme.RETURNED_COLOR))
        else:
            # Fallback to normal text color
            item.setForeground(QColor(DarkTheme.TEXT_PRIMARY))
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
        """Resize requester column to fit content with word wrapping."""
        # Enable word wrapping for proper text display in requester column
        self.setWordWrap(True)

        # Only resize the requester column (column 1) since others are fixed width
        # This allows the column to expand to fit content but won't exceed max width
        self.resizeColumnToContents(1)

        # Ensure requester column doesn't exceed maximum width
        if self.columnWidth(1) > 240:
            self.setColumnWidth(1, 240)

    def _on_header_clicked(self, section: int) -> None:
        """Handle initial header clicks to choose sensible default sort for each column.

        If a header is clicked and it is not currently the sort column, set a sensible
        default order and trigger the sort. Subsequent clicks will toggle normally.
        """
        header = self.horizontalHeader()
        current = header.sortIndicatorSection() if header is not None else -1

        # Status: default ascending => requested, active, overdue, returned
        if section == 0 and current != 0:
            self.sortItems(0, Qt.SortOrder.AscendingOrder)
            return

        # Requester: default alphabetical A->Z
        if section == 1 and current != 1:
            self.sortItems(1, Qt.SortOrder.AscendingOrder)
            return

        # Request Date: default recent->old (we store negative timestamps so ascending sorts newest first)
        if section == 2 and current != 2:
            self.sortItems(2, Qt.SortOrder.AscendingOrder)
            return

    def showEvent(self, a0: Optional[QShowEvent]) -> None:
        """Ensure layout and sorting are correct when the table becomes visible again."""
        super().showEvent(a0)
        # Reapply size and sort indicator on show to avoid visual glitches when switching tabs
        self.resize_columns_to_contents()
        header = self.horizontalHeader()
        if header is not None and self.isSortingEnabled():
            # Reapply the current sort indicator (no-op if none set)
            sort_col = header.sortIndicatorSection()
            sort_order = header.sortIndicatorOrder()
            header.setSortIndicator(sort_col, sort_order)
            header.setSortIndicatorShown(False)
            if sort_col >= 0:
                # Reapply actual sort to ensure rows match the indicator
                self.sortItems(sort_col, sort_order)
        # Force a repaint/update to avoid lingering visual artifacts
        _vp = self.viewport()
        if _vp is not None:
            _vp.update()
        self.repaint()
