"""
Inventory table widget for displaying inventory items.
Provides table display with sorting, and styling.
"""

from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QAbstractItemView, QHBoxLayout, QWidget
)
from PyQt6.QtCore import Qt, QTimer
from inventory_app.gui.styles import DarkTheme
from inventory_app.utils.logger import logger


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
        "Stock/Available", "Name", "Size", "Brand", "Other Specifications", "Supplier",
        "Calibration/Expiration Date", "Item Type", "Acquisition Date",
        "Last Modified"
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
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSortingEnabled(True)

        # Disable cell editing on double-click
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        # Configure header
        header = self.horizontalHeader()
        if header:
            header.setSortIndicatorShown(True)
            header.setSectionsMovable(False)
            header.setStretchLastSection(True)

            # Set column widths
            self.setColumnWidth(0, 100)  # Stock/Available
            self.setColumnWidth(1, 200)  # Name
            self.setColumnWidth(2, 80)   # Size
            self.setColumnWidth(3, 100)  # Brand
            self.setColumnWidth(4, 120)  # Other Specifications
            self.setColumnWidth(5, 120)  # Supplier
            self.setColumnWidth(6, 100)  # Calibration/Expiration Date
            self.setColumnWidth(7, 80)   # Item Type
            self.setColumnWidth(8, 100)  # Acquisition Date
            self.setColumnWidth(9, 120)  # Last Modified

        # Configure vertical header
        v_header = self.verticalHeader()
        if v_header:
            v_header.setDefaultSectionSize(25)
            v_header.setVisible(False)

        # Apply dark theme styling
        self.apply_styling()

    def apply_styling(self):
        """Apply dark theme styling to the table."""
        self.setStyleSheet(f"""
            QTableWidget {{
                gridline-color: {DarkTheme.BORDER_COLOR};
                background-color: {DarkTheme.SECONDARY_DARK};
                border: 1px solid {DarkTheme.BORDER_COLOR};
                border-radius: 6px;
                selection-background-color: {DarkTheme.ACCENT_COLOR};
            }}

            QTableWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {DarkTheme.BORDER_COLOR};
                color: {DarkTheme.TEXT_PRIMARY};
            }}

            QTableWidget::item:selected {{
                background-color: {DarkTheme.ACCENT_COLOR};
            }}
        """)

    def populate_table(self, items: List[Dict[str, Any]]):
        """Populate the table with inventory items."""
        try:
            self.setRowCount(len(items))
            logger.debug(f"Populating table with {len(items)} items")

            for row, item in enumerate(items):
                self.populate_row(row, item)

            # Resize columns to content
            QTimer.singleShot(100, self.resize_columns)

        except Exception as e:
            logger.error(f"Error populating table: {e}")

    def populate_row(self, row: int, item: Dict[str, Any]):
        """Populate a single row with item data."""
        try:
            # Extract data from item dict
            item_id = item.get('id')
            name = item.get('name', '')
            size = item.get('size', '')
            brand = item.get('brand', '')
            other_specifications = item.get('other_specifications', '')
            supplier_name = item.get('supplier_name', '')
            expiration_date = self.format_date(item.get('expiration_date'))
            calibration_date = self.format_date(item.get('calibration_date'))
            acquisition_date = self.format_date(item.get('acquisition_date'))
            is_consumable = item.get('is_consumable', False)
            last_modified = self.format_datetime(item.get('last_modified'))

            # Calculate stock/available format
            total_stock = item.get('total_stock', 0)
            available_stock = item.get('available_stock', 0)
            stock_display = f"{total_stock}/{available_stock}"

            # Combine calibration/expiration date - use expiration for consumables, calibration for non-consumables
            combined_date = expiration_date if expiration_date != "N/A" else calibration_date

            # Determine item type
            item_type = "Consumable" if is_consumable else "Non-Consumable"

            # Create table items
            status_item = QTableWidgetItem(stock_display)
            self.setItem(row, 0, status_item)  # Stock/Available

            name_item = QTableWidgetItem(name)
            self.setItem(row, 1, name_item)  # Name
            self.setItem(row, 2, QTableWidgetItem(size or "N/A"))  # Size
            self.setItem(row, 3, QTableWidgetItem(brand or "N/A"))  # Brand
            self.setItem(row, 4, QTableWidgetItem(other_specifications or "N/A"))  # Other Specifications
            self.setItem(row, 5, QTableWidgetItem(supplier_name or "N/A"))  # Supplier
            self.setItem(row, 6, QTableWidgetItem(combined_date))  # Calibration/Expiration Date
            self.setItem(row, 7, QTableWidgetItem(item_type))  # Item Type
            self.setItem(row, 8, QTableWidgetItem(acquisition_date))  # Acquisition Date
            self.setItem(row, 9, QTableWidgetItem(last_modified))  # Last Modified

            # Store item ID in row for later retrieval
            if item_id is not None:
                name_item.setData(Qt.ItemDataRole.UserRole, item_id)

        except Exception as e:
            logger.error(f"Error populating row {row}: {e}")

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
