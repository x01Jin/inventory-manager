"""
Inventory table widget for displaying inventory items.
Provides table display with sorting, and styling.
"""

from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
    QHBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QShowEvent
from PyQt6.QtGui import QColor
from inventory_app.services.item_status_service import item_status_service
from inventory_app.utils.logger import logger

# Pylance may not expose Qt.ItemDataRole.SortRole in type stubs; use fallback.
SORT_ROLE = getattr(Qt.ItemDataRole, "SortRole", int(Qt.ItemDataRole.UserRole) + 1)


class AlertIndicator(QWidget):
    """Widget to display indicators in table cells."""

    def __init__(self, alert_type: str = "", parent=None):
        super().__init__(parent)
        self.alert_type = alert_type
        self.setup_ui()

    def setup_ui(self):
        """Setup the alert indicator UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)

        layout.addStretch()


class InventoryTable(QTableWidget):
    """Table widget for displaying inventory items with styling."""

    # Column definitions
    COLUMNS = [
        "Stock/Available",
        "Name",
        "Size",
        "Brand",
        "Other Specifications",
        "Supplier",
        "Calibration Date",
        "Expiry/Disposal Date",
        "Item Type",
        "Acquisition Date",
        "Last Modified",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_table()

    def setup_table(self):
        """Setup the table structure and styling."""
        # Set column count and headers
        self.setColumnCount(len(self.COLUMNS))
        self.setHorizontalHeaderLabels(self.COLUMNS)

        # Configure table properties
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSortingEnabled(True)

        # Disable cell editing on double-click
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        # Configure header
        header = self.horizontalHeader()
        if header:
            header.setSortIndicatorShown(False)
            header.setSectionsMovable(False)
            header.setStretchLastSection(True)
            header.sectionClicked.connect(self._on_header_clicked)

            # Set column widths
            self.setColumnWidth(0, 140)  # Stock/Available (wider for label)
            self.setColumnWidth(1, 200)  # Name
            self.setColumnWidth(2, 80)  # Size
            self.setColumnWidth(3, 100)  # Brand
            self.setColumnWidth(4, 120)  # Other Specifications
            self.setColumnWidth(5, 120)  # Supplier
            self.setColumnWidth(6, 100)  # Calibration Date
            self.setColumnWidth(7, 100)  # Expiry/Disposal Date
            self.setColumnWidth(8, 80)  # Item Type
            self.setColumnWidth(9, 100)  # Acquisition Date
            self.setColumnWidth(10, 120)  # Last Modified

        # Configure vertical header
        v_header = self.verticalHeader()
        if v_header:
            v_header.setDefaultSectionSize(25)
            v_header.setVisible(False)

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
            # Fallback: numeric parts then case-insensitive text
            try:
                return (self.text() or "").lower() < (other.text() or "").lower()
            except Exception:
                return super().__lt__(other)

    def _on_header_clicked(self, section: int) -> None:
        """Handle initial header clicks to choose sensible default sort for inventory columns.

        First click on a column that is not currently sorted will set a sensible default
        ordering (e.g., name A->Z, stock highest-first, dates recent-first). Subsequent
        clicks will toggle the sort order automatically by the header.
        """
        header = self.horizontalHeader()
        current = header.sortIndicatorSection() if header is not None else -1

        # Stock (col 0): default ascending so negative SortRole makes highest available show first
        if section == 0 and current != 0:
            self.sortItems(0, Qt.SortOrder.AscendingOrder)
            return

        # Name (col 1): alphabetical A->Z
        if section == 1 and current != 1:
            self.sortItems(1, Qt.SortOrder.AscendingOrder)
            return

        # Supplier (col 5): alphabetical A->Z
        if section == 5 and current != 5:
            self.sortItems(5, Qt.SortOrder.AscendingOrder)
            return

        # Date columns (6,7,9,10): default recent->old (we store negative timestamps so ascending sorts newest first)
        if section in (6, 7, 9, 10) and current != section:
            self.sortItems(section, Qt.SortOrder.AscendingOrder)
            return

    def populate_table(self, items: List[Dict[str, Any]]):
        """Populate the table with inventory items."""
        try:
            # Disable sorting while repopulating to avoid visual/sorting glitches
            prev_sorting = self.isSortingEnabled()
            self.setSortingEnabled(False)

            self.setRowCount(len(items))
            logger.debug(f"Populating table with {len(items)} items")

            for row, item in enumerate(items):
                self.populate_row(row, item)

            # Resize columns to content
            QTimer.singleShot(100, self.resize_columns)

            # Restore sorting and set sensible default: Stock available (highest first)
            self.setSortingEnabled(prev_sorting)
            if prev_sorting:
                hdr = self.horizontalHeader()
                if hdr is not None:
                    # We use negative available stock as SortRole so ascending order shows highest stock first
                    hdr.setSortIndicator(0, Qt.SortOrder.AscendingOrder)
                    hdr.setSortIndicatorShown(False)
                    self.sortItems(0, Qt.SortOrder.AscendingOrder)

        except Exception as e:
            logger.error(f"Error populating table: {e}")

    def populate_row(self, row: int, item: Dict[str, Any]):
        """Populate a single row with item data."""
        try:
            # Extract data from item dict
            item_id = item.get("id")
            name = item.get("name", "N/A")
            size = item.get("size", "")
            brand = item.get("brand", "")
            other_specifications = item.get("other_specifications", "")
            supplier_name = item.get("supplier_name", "")
            expiration_date = self.format_date(item.get("expiration_date"))
            calibration_date = self.format_date(item.get("calibration_date"))
            acquisition_date = self.format_date(item.get("acquisition_date"))
            is_consumable = item.get("is_consumable", False)
            last_modified = self.format_datetime(item.get("last_modified"))

            # Calculate stock/available format
            total_stock = item.get("total_stock", 0)
            available_stock = item.get("available_stock", 0)
            stock_display = f"{total_stock}/{available_stock}"

            # Determine item type
            item_type = "Consumable" if is_consumable else "Non-Consumable"

            # Get item status for coloring
            item_status = None
            if item_id:
                item_status = item_status_service.get_item_status(item_id)

            # Create table items
            stock_item = self.SortableTableItem(stock_display)
            # Sort by available stock (show highest first by using negative value)
            try:
                stock_item.setData(SORT_ROLE, -int(available_stock))
            except Exception:
                stock_item.setData(SORT_ROLE, 0)
            self.setItem(row, 0, stock_item)  # Stock/Available

            name_item = self.SortableTableItem(name)
            # Case-insensitive alphabetical sort for name
            name_item.setData(SORT_ROLE, (name or "").lower())
            self.setItem(row, 1, name_item)  # Name
            self.setItem(row, 2, QTableWidgetItem(size or "N/A"))  # Size
            self.setItem(row, 3, QTableWidgetItem(brand or "N/A"))  # Brand
            self.setItem(
                row, 4, QTableWidgetItem(other_specifications or "N/A")
            )  # Other Specifications
            supplier_item = self.SortableTableItem(supplier_name or "N/A")
            supplier_item.setData(SORT_ROLE, (supplier_name or "").lower())
            self.setItem(row, 5, supplier_item)  # Supplier

            # Calibration Date with status-based coloring
            cal_date_item = self.SortableTableItem(calibration_date or "N/A")
            # Parse original ISO date to set sortable value (recent first)
            try:
                from datetime import datetime

                cal_src = item.get("calibration_date")
                if cal_src:
                    cal_ts = datetime.fromisoformat(cal_src).timestamp()
                    cal_date_item.setData(SORT_ROLE, -float(cal_ts))
                else:
                    cal_date_item.setData(SORT_ROLE, float("inf"))
            except Exception:
                cal_date_item.setData(SORT_ROLE, float("inf"))
            self._color_date_item(cal_date_item, item_status, "calibration")
            self.setItem(row, 6, cal_date_item)  # Calibration Date

            # Expiry/Disposal Date with status-based coloring
            exp_date_item = self.SortableTableItem(expiration_date or "N/A")
            try:
                from datetime import datetime

                exp_src = item.get("expiration_date")
                if exp_src:
                    exp_ts = datetime.fromisoformat(exp_src).timestamp()
                    exp_date_item.setData(SORT_ROLE, -float(exp_ts))
                else:
                    exp_date_item.setData(SORT_ROLE, float("inf"))
            except Exception:
                exp_date_item.setData(SORT_ROLE, float("inf"))
            self._color_date_item(exp_date_item, item_status, "expiration")
            self.setItem(row, 7, exp_date_item)  # Expiry/Disposal Date

            self.setItem(row, 8, QTableWidgetItem(item_type))  # Item Type
            # Acquisition Date - sortable by timestamp (recent first)
            acq_item = self.SortableTableItem(acquisition_date)
            try:
                from datetime import datetime

                acq_src = item.get("acquisition_date")
                if acq_src:
                    acq_ts = datetime.fromisoformat(acq_src).timestamp()
                    acq_item.setData(SORT_ROLE, -float(acq_ts))
                else:
                    acq_item.setData(SORT_ROLE, float("inf"))
            except Exception:
                acq_item.setData(SORT_ROLE, float("inf"))
            self.setItem(row, 9, acq_item)  # Acquisition Date

            # Last Modified - sortable by timestamp (recent first)
            lm_item = self.SortableTableItem(last_modified)
            try:
                from datetime import datetime

                lm_src = item.get("last_modified")
                if lm_src:
                    lm_ts = datetime.fromisoformat(lm_src).timestamp()
                    lm_item.setData(SORT_ROLE, -float(lm_ts))
                else:
                    lm_item.setData(SORT_ROLE, float("inf"))
            except Exception:
                lm_item.setData(SORT_ROLE, float("inf"))
            self.setItem(row, 10, lm_item)  # Last Modified

            # Store item ID in row for later retrieval
            if item_id is not None:
                name_item.setData(Qt.ItemDataRole.UserRole, item_id)

        except Exception as e:
            logger.error(f"Error populating row {row}: {e}")

    def showEvent(self, a0: Optional[QShowEvent]) -> None:
        """Refresh layout and sort indicator on show (fixes visual glitches when switching tabs)."""
        super().showEvent(a0)
        # Resize columns to contents to ensure proper layout when becoming visible
        QTimer.singleShot(0, self.resize_columns)
        # Force a repaint/update to avoid lingering visual artifacts
        _vp = self.viewport()
        if _vp is not None:
            _vp.update()
        self.repaint()
        # Reapply sort based on current header indicator to ensure ordering is consistent
        header = self.horizontalHeader()
        if header is not None and self.isSortingEnabled():
            sc = header.sortIndicatorSection()
            so = header.sortIndicatorOrder()
            if sc >= 0:
                self.sortItems(sc, so)
                header.setSortIndicatorShown(False)

    def format_date(self, date_str: Optional[str]) -> str:
        """Format date string for display."""
        if not date_str:
            return "N/A"

        try:
            from datetime import datetime

            date_obj = datetime.fromisoformat(date_str)
            return date_obj.strftime("%m/%d/%Y")
        except (ValueError, TypeError):
            return str(date_str)

    def format_datetime(self, datetime_str: Optional[str]) -> str:
        """Format datetime string for display."""
        if not datetime_str:
            return "N/A"

        try:
            from datetime import datetime

            dt_obj = datetime.fromisoformat(datetime_str)
            return dt_obj.strftime("%m/%d/%Y %H:%M")
        except (ValueError, TypeError):
            return str(datetime_str)

    def resize_columns(self):
        """Resize columns to fit content."""
        try:
            for col in range(self.columnCount()):
                self.resizeColumnToContents(col)
                # Set minimum and maximum widths
                width = self.columnWidth(col)
                self.setColumnWidth(col, max(80, min(width, 200)))
        except Exception as e:
            logger.error(f"Error resizing columns: {e}")

    def get_selected_item_id(self) -> Optional[int]:
        """Get the ID of the currently selected item."""
        current_row = self.currentRow()
        if current_row >= 0:
            item = self.item(current_row, 1)  # Name is in column 1
            if item:
                return item.data(Qt.ItemDataRole.UserRole)
        return None

    def clear_table(self):
        """Clear all items from the table."""
        self.setRowCount(0)
        logger.debug("Table cleared")

    def get_row_count(self) -> int:
        """Get the number of rows in the table."""
        return self.rowCount()

    def _color_date_item(
        self, item: QTableWidgetItem, item_status, date_type: str
    ) -> None:
        """
        Color-code the date item based on item status and date type.

        Args:
            item: The table item to color
            item_status: ItemStatus object or None
            date_type: "calibration" or "expiration"
        """
        if not item_status:
            # Default color for OK status
            item.setForeground(QColor("#FFFFFF"))  # Black
            return

        status = item_status.status

        # Handle combined statuses by checking for specific components
        if date_type == "calibration":
            if "CAL_DUE" in status:
                item.setForeground(QColor("#DC3545"))  # Red
            elif "CAL_WARNING" in status:
                item.setForeground(QColor("#FD7E14"))  # Orange
            else:
                item.setForeground(QColor("#FFFFFF"))  # Black
        elif date_type == "expiration":
            if "EXPIRED" in status:
                item.setForeground(QColor("#DC3545"))  # Red
            elif "EXPIRING" in status:
                item.setForeground(QColor("#FFC107"))  # Yellow
            else:
                item.setForeground(QColor("#FFFFFF"))  # Black
        else:
            # Default for other date types
            item.setForeground(QColor("#000000"))  # Black
