"""Requester table - displays requester data in a table format.
Provides table widget for showing requesters with selection capabilities.
Uses composition pattern with RequesterModel.
Supports configurable columns for Students/Teachers/Faculty tabs.
"""

from typing import List, Optional
from PyQt6.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal

from inventory_app.gui.requesters.requester_model import RequesterRow
from inventory_app.utils.logger import logger

SORT_ROLE = getattr(Qt.ItemDataRole, "SortRole", int(Qt.ItemDataRole.UserRole) + 1)


COLUMN_CONFIGS = {
    "student": ["Requisitions", "Name", "Grade", "Section", "Created"],
    "teacher": ["Requisitions", "Name", "Department", "Created"],
    "faculty": ["Requisitions", "Name", "Created"],
}


class RequesterTable(QTableWidget):
    """
    Table widget for displaying requester information.
    Shows requester details with selection capabilities.
    Supports different column configurations for Students/Teachers/Faculty tabs.
    """

    requester_selected = pyqtSignal(int)
    requester_double_clicked = pyqtSignal(int)

    def __init__(self, parent=None, requester_type: str = "student"):
        super().__init__(parent)
        self._requester_type = requester_type
        self._configure_table()

    def set_requester_type(self, requester_type: str) -> None:
        """Change the table configuration based on requester type."""
        if requester_type != self._requester_type:
            self._requester_type = requester_type
            self._configure_table()

    def _configure_table(self) -> None:
        """Configure table appearance and behavior based on requester type."""
        columns = COLUMN_CONFIGS.get(self._requester_type, COLUMN_CONFIGS["faculty"])
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels(columns)

        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setSortingEnabled(True)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        header = self.horizontalHeader()
        if header:
            header.setStretchLastSection(True)
            header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            header.setSortIndicatorShown(False)
            header.sectionClicked.connect(self._on_header_clicked)

        self.setColumnWidth(0, 100)
        if self._requester_type == "student":
            self.setColumnWidth(1, 180)
            self.setColumnWidth(2, 100)
            self.setColumnWidth(3, 120)
            self.setColumnWidth(4, 100)
        elif self._requester_type == "teacher":
            self.setColumnWidth(1, 180)
            self.setColumnWidth(2, 200)
            self.setColumnWidth(3, 100)
        else:
            self.setColumnWidth(1, 250)
            self.setColumnWidth(2, 100)

        self.itemSelectionChanged.connect(self._on_selection_changed)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)

        logger.info(f"Requester table initialized for type: {self._requester_type}")

    class SortableTableItem(QTableWidgetItem):
        """QTableWidgetItem subclass that prefers SortRole for comparisons."""

        def __lt__(self, other):
            try:
                my = self.data(SORT_ROLE)
                ot = other.data(SORT_ROLE)
                if my is not None and ot is not None:
                    return my < ot
            except Exception as e:
                logger.warning(f"Failed to compare SortRole data: {e}")
            return (self.text() or "").lower() < (other.text() or "").lower()

    def populate_table(self, requesters: List[RequesterRow]) -> None:
        """Populate the table with requester data."""
        try:
            prev_sorting = self.isSortingEnabled()
            self.setSortingEnabled(False)
            self.setRowCount(0)

            for row_data in requesters:
                row_position = self.rowCount()
                self.insertRow(row_position)

                if self._requester_type == "student":
                    self._populate_student_row(row_position, row_data)
                elif self._requester_type == "teacher":
                    self._populate_teacher_row(row_position, row_data)
                else:
                    self._populate_faculty_row(row_position, row_data)

            logger.info(f"Populated {self._requester_type} table with {len(requesters)} requesters")

            self.setSortingEnabled(prev_sorting)
            if prev_sorting and self.columnCount() > 0:
                header = self.horizontalHeader()
                if header is not None:
                    last_col = self.columnCount() - 1
                    header.setSortIndicator(last_col, Qt.SortOrder.AscendingOrder)
                    header.setSortIndicatorShown(False)
                    self.sortItems(last_col, Qt.SortOrder.AscendingOrder)
        except Exception as e:
            logger.error(f"Failed to populate requesters table: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load requester data: {str(e)}")

    def _populate_student_row(self, row_position: int, row_data: RequesterRow) -> None:
        """Populate a row for student requesters."""
        requisitions_item = self.SortableTableItem(str(row_data.requisitions_count))
        try:
            requisitions_item.setData(SORT_ROLE, int(row_data.requisitions_count))
        except Exception:
            requisitions_item.setData(SORT_ROLE, 0)
        self.setItem(row_position, 0, requisitions_item)

        name_item = self.SortableTableItem(row_data.name)
        name_item.setData(Qt.ItemDataRole.UserRole, row_data.id)
        name_item.setData(SORT_ROLE, (row_data.name or "").lower())
        self.setItem(row_position, 1, name_item)

        grade_item = self.SortableTableItem(row_data.grade_level)
        grade_item.setData(SORT_ROLE, (row_data.grade_level or "").lower())
        self.setItem(row_position, 2, grade_item)

        section_item = self.SortableTableItem(row_data.section)
        section_item.setData(SORT_ROLE, (row_data.section or "").lower())
        self.setItem(row_position, 3, section_item)

        self._set_created_item(row_position, 4, row_data)

    def _populate_teacher_row(self, row_position: int, row_data: RequesterRow) -> None:
        """Populate a row for teacher requesters."""
        requisitions_item = self.SortableTableItem(str(row_data.requisitions_count))
        try:
            requisitions_item.setData(SORT_ROLE, int(row_data.requisitions_count))
        except Exception:
            requisitions_item.setData(SORT_ROLE, 0)
        self.setItem(row_position, 0, requisitions_item)

        name_item = self.SortableTableItem(row_data.name)
        name_item.setData(Qt.ItemDataRole.UserRole, row_data.id)
        name_item.setData(SORT_ROLE, (row_data.name or "").lower())
        self.setItem(row_position, 1, name_item)

        dept_item = self.SortableTableItem(row_data.department)
        dept_item.setData(SORT_ROLE, (row_data.department or "").lower())
        self.setItem(row_position, 2, dept_item)

        self._set_created_item(row_position, 3, row_data)

    def _populate_faculty_row(self, row_position: int, row_data: RequesterRow) -> None:
        """Populate a row for faculty/individual requesters."""
        requisitions_item = self.SortableTableItem(str(row_data.requisitions_count))
        try:
            requisitions_item.setData(SORT_ROLE, int(row_data.requisitions_count))
        except Exception:
            requisitions_item.setData(SORT_ROLE, 0)
        self.setItem(row_position, 0, requisitions_item)

        name_item = self.SortableTableItem(row_data.name)
        name_item.setData(Qt.ItemDataRole.UserRole, row_data.id)
        name_item.setData(SORT_ROLE, (row_data.name or "").lower())
        self.setItem(row_position, 1, name_item)

        self._set_created_item(row_position, 2, row_data)

    def _set_created_item(self, row_position: int, column: int, row_data: RequesterRow) -> None:
        """Set the created date item in the specified column."""
        created_item = None
        if row_data.created_datetime:
            from inventory_app.utils.date_utils import format_date_short, format_time_12h
            date_str = format_date_short(row_data.created_datetime)
            time_str = format_time_12h(row_data.created_datetime.time())
            created_str = f"{date_str} at {time_str}"
            created_item = self.SortableTableItem(created_str)
            try:
                ts = float(row_data.created_datetime.timestamp())
                created_item.setData(SORT_ROLE, -ts)
            except Exception:
                created_item.setData(SORT_ROLE, float("inf"))
        else:
            created_item = self.SortableTableItem("")
            created_item.setData(SORT_ROLE, float("inf"))

        self.setItem(row_position, column, created_item)

    def get_selected_requester_id(self) -> Optional[int]:
        """Get the ID of the currently selected requester."""
        current_row = self.currentRow()
        if current_row >= 0:
            name_item = self.item(current_row, 1)
            if name_item:
                return name_item.data(Qt.ItemDataRole.UserRole)
        return None

    def select_requester_by_id(self, requester_id: int) -> bool:
        """Select a requester by its ID."""
        for row in range(self.rowCount()):
            name_item = self.item(row, 1)
            if name_item and name_item.data(Qt.ItemDataRole.UserRole) == requester_id:
                self.selectRow(row)
                return True
        return False

    def clear_selection(self) -> None:
        """Clear the current selection."""
        self.clearSelection()

    def get_table_data_for_export(self) -> List[dict]:
        """Get table data in a format suitable for export."""
        data = []
        for row in range(self.rowCount()):
            row_data = {"requisitions": "", "name": "", "created": ""}
            req_item = self.item(row, 0)
            if req_item:
                row_data["requisitions"] = req_item.text()
            name_item = self.item(row, 1)
            if name_item:
                row_data["name"] = name_item.text()
            created_item = self.item(row, self.columnCount() - 1)
            if created_item:
                row_data["created"] = created_item.text()
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

    def _on_header_clicked(self, section: int) -> None:
        """Handle header clicks to set sensible default sorts for columns."""
        header = self.horizontalHeader()
        current = header.sortIndicatorSection() if header is not None else -1
        last_col = self.columnCount() - 1
        if section == last_col and current != last_col:
            self.sortItems(last_col, Qt.SortOrder.AscendingOrder)

    def showEvent(self, a0) -> None:
        """Ensure layout and sorting are correct when the table becomes visible."""
        super().showEvent(a0)
        self.resize_columns_to_contents()
        header = self.horizontalHeader()
        if header is not None and self.isSortingEnabled():
            sort_col = header.sortIndicatorSection()
            sort_order = header.sortIndicatorOrder()
            header.setSortIndicator(sort_col, sort_order)
            header.setSortIndicatorShown(False)
            if sort_col >= 0:
                self.sortItems(sort_col, sort_order)

    def resize_columns_to_contents(self) -> None:
        """Resize columns to fit their contents."""
        for column in range(self.columnCount()):
            self.resizeColumnToContents(column)
        self.setColumnWidth(0, max(self.columnWidth(0), 100))
