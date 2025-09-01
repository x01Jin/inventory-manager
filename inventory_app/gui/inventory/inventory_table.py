"""
Inventory table widget for displaying inventory items.
Provides table display with sorting, alerts, and styling.
"""

from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QAbstractItemView, QHBoxLayout, QWidget, QLabel
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from inventory_app.gui.styles import DarkTheme
from inventory_app.utils.logger import logger


class AlertIndicator(QWidget):
    """Widget to display alert indicators in table cells."""

    def __init__(self, alert_type: str = "", parent=None):
        super().__init__(parent)
        self.alert_type = alert_type
        self.setup_ui()

    def setup_ui(self):
        """Setup the alert indicator UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)

        # Alert indicator dot
        self.indicator = QLabel("●")
        self.indicator.setFixedSize(8, 8)

        if self.alert_type == "expiration":
            self.indicator.setStyleSheet(f"color: {DarkTheme.ERROR_COLOR}; font-weight: bold;")
        elif self.alert_type == "calibration":
            self.indicator.setStyleSheet(f"color: {DarkTheme.WARNING_COLOR}; font-weight: bold;")
        elif self.alert_type == "lifecycle":
            self.indicator.setStyleSheet(f"color: {DarkTheme.WARNING_COLOR}; font-weight: bold;")
        else:
            self.indicator.setVisible(False)

        layout.addWidget(self.indicator)
        layout.addStretch()


class InventoryTable(QTableWidget):
    """Table widget for displaying inventory items with alerts and styling."""

    # Column definitions
    COLUMNS = [
        "Stock/Available", "Name", "Category", "Size", "Brand", "Supplier",
        "Expiration Date", "Calibration Date", "Acquisition Date",
        "Consumable", "Last Modified", "Alert Status"
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_table()
        logger.info("Inventory table initialized")

    def setup_table(self):
        """Setup the table structure and styling."""
        # Set column count and headers
        self.setColumnCount(len(self.COLUMNS))
        self.setHorizontalHeaderLabels(self.COLUMNS)

        # Configure table properties
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSortingEnabled(True)

        # Configure header
        header = self.horizontalHeader()
        if header:
            header.setSortIndicatorShown(True)
            header.setSectionsMovable(False)
            header.setStretchLastSection(True)

            # Set column widths
            self.setColumnWidth(0, 100)  # Status
            self.setColumnWidth(1, 200)  # Name
            self.setColumnWidth(2, 120)  # Category
            self.setColumnWidth(3, 80)   # Size
            self.setColumnWidth(4, 100)  # Brand
            self.setColumnWidth(5, 120)  # Supplier
            self.setColumnWidth(6, 100)  # Expiration Date
            self.setColumnWidth(7, 100)  # Calibration Date
            self.setColumnWidth(8, 100)  # Acquisition Date
            self.setColumnWidth(9, 80)   # Consumable
            self.setColumnWidth(10, 120) # Last Modified
            self.setColumnWidth(11, 100) # Alert Status

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
            category_name = item.get('category_name', 'Uncategorized')
            size = item.get('size', '')
            brand = item.get('brand', '')
            supplier_name = item.get('supplier_name', '')
            expiration_date = self.format_date(item.get('expiration_date'))
            calibration_date = self.format_date(item.get('calibration_date'))
            acquisition_date = self.format_date(item.get('acquisition_date'))
            is_consumable = "Yes" if item.get('is_consumable') else "No"
            last_modified = self.format_datetime(item.get('last_modified'))
            alert_status = item.get('alert_status', '')

            # Calculate stock/available format
            total_stock = item.get('total_stock', 0)
            available_stock = item.get('available_stock', 0)
            stock_display = f"{total_stock}/{available_stock}"

            # Create table items
            status_item = QTableWidgetItem(stock_display)
            self.setItem(row, 0, status_item)  # Stock/Available

            name_item = QTableWidgetItem(name)
            self.setItem(row, 1, name_item)  # Name
            self.setItem(row, 2, QTableWidgetItem(category_name))  # Category
            self.setItem(row, 3, QTableWidgetItem(size or "N/A"))  # Size
            self.setItem(row, 4, QTableWidgetItem(brand or "N/A"))  # Brand
            self.setItem(row, 5, QTableWidgetItem(supplier_name or "N/A"))  # Supplier
            self.setItem(row, 6, QTableWidgetItem(expiration_date))  # Expiration Date
            self.setItem(row, 7, QTableWidgetItem(calibration_date))  # Calibration Date
            self.setItem(row, 8, QTableWidgetItem(acquisition_date))  # Acquisition Date
            self.setItem(row, 9, QTableWidgetItem(is_consumable))  # Consumable
            self.setItem(row, 10, QTableWidgetItem(last_modified))  # Last Modified
            self.setItem(row, 11, QTableWidgetItem(alert_status or "None"))  # Alert Status

            # Apply status styling based on stock availability
            self.apply_stock_styling(row, total_stock, available_stock)

            # Apply alert styling
            self.apply_alert_styling(row, alert_status)

            # Store item ID in row for later retrieval
            if item_id is not None:
                name_item.setData(Qt.ItemDataRole.UserRole, item_id)

        except Exception as e:
            logger.error(f"Error populating row {row}: {e}")

    def apply_stock_styling(self, row: int, total_stock: int, available_stock: int):
        """Apply styling based on stock availability."""
        # Determine status based on stock levels
        if available_stock == 0:
            # Out of stock - red/warning styling
            for col in range(self.columnCount()):
                item = self.item(row, col)
                if item:
                    item.setBackground(QColor(DarkTheme.ERROR_COLOR).lighter(180))
                    if col == 0:  # Stock/Available column
                        item.setForeground(QColor(DarkTheme.ERROR_COLOR))
        elif available_stock < total_stock:
            # Partially available - yellow/warning styling
            for col in range(self.columnCount()):
                item = self.item(row, col)
                if item:
                    item.setBackground(QColor(DarkTheme.WARNING_COLOR).lighter(180))
                    if col == 0:  # Stock/Available column
                        item.setForeground(QColor(DarkTheme.WARNING_COLOR))
        else:
            # Fully available - green/success styling
            for col in range(self.columnCount()):
                item = self.item(row, col)
                if item and col == 0:  # Stock/Available column
                    item.setForeground(QColor(DarkTheme.SUCCESS_COLOR))

    def apply_alert_styling(self, row: int, alert_status: str):
        """Apply styling based on alert status."""
        if not alert_status:
            return

        # Set background color for alert rows
        alert_color = None
        if alert_status == "expiration":
            alert_color = QColor(DarkTheme.ERROR_COLOR).lighter(180)
        elif alert_status in ["calibration", "lifecycle"]:
            alert_color = QColor(DarkTheme.WARNING_COLOR).lighter(180)

        if alert_color:
            for col in range(self.columnCount()):
                item = self.item(row, col)
                if item:
                    item.setBackground(alert_color)

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
