"""
Simple inventory management page for laboratory equipment.
Implements core functionality from program specifications.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QLineEdit, QGroupBox, QMessageBox,
    QDialog, QHeaderView
)
from PyQt6.QtGui import QColor

from inventory_app.gui.styles import DarkTheme
from inventory_app.database.models import Item, Category, CategoryType, Supplier
from inventory_app.database.connection import db
from inventory_app.utils.logger import logger
from inventory_app.gui.item_dialog import ItemDialog


class InventoryPage(QWidget):
    """Simple inventory management page."""

    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.refresh_inventory()

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header with title and actions
        header_layout = QHBoxLayout()
        title = QLabel("📦 Laboratory Inventory Management")
        title.setStyleSheet(f"font-size: {DarkTheme.FONT_SIZE_TITLE}pt; font-weight: bold;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        # Action buttons
        add_btn = QPushButton("➕ Add Item")
        add_btn.clicked.connect(self.add_item_dialog)
        header_layout.addWidget(add_btn)

        layout.addLayout(header_layout)

        # Search functionality
        search_layout = QHBoxLayout()
        search_label = QLabel("🔍 Search:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search items...")
        self.search_input.textChanged.connect(self.search_items)

        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # Inventory table
        self.setup_inventory_table(layout)

        # Quick stats
        self.setup_stats(layout)

    def setup_inventory_table(self, parent_layout):
        """Setup the inventory table with comprehensive columns."""
        table_group = QGroupBox("Laboratory Inventory Items")
        table_layout = QVBoxLayout(table_group)

        self.inventory_table = QTableWidget()
        self.inventory_table.setColumnCount(13)
        self.inventory_table.setHorizontalHeaderLabels([
            "Name", "Category", "Size", "Brand", "Specifications", "Supplier",
            "PO Number", "Expiration", "Calibration", "Status", "Available", "Borrowed", "Actions"
        ])

        # Configure responsive column sizing
        header = self.inventory_table.horizontalHeader()
        if header:
            header.setMinimumSectionSize(60)  # Minimum width for any column

            # Set specific minimum widths for key columns
            self.inventory_table.setColumnWidth(0, 150)  # Name
            self.inventory_table.setColumnWidth(1, 120)  # Category
            self.inventory_table.setColumnWidth(2, 80)   # Size
            self.inventory_table.setColumnWidth(3, 100)  # Brand
            self.inventory_table.setColumnWidth(4, 180)  # Specifications
            self.inventory_table.setColumnWidth(5, 120)  # Supplier
            self.inventory_table.setColumnWidth(6, 100)  # PO Number
            self.inventory_table.setColumnWidth(7, 100)  # Expiration
            self.inventory_table.setColumnWidth(8, 100)  # Calibration
            self.inventory_table.setColumnWidth(9, 100)  # Status
            self.inventory_table.setColumnWidth(10, 80)  # Available
            self.inventory_table.setColumnWidth(11, 80)  # Borrowed
            self.inventory_table.setColumnWidth(12, 120) # Actions

            # Make specifications column stretch to fill space
            header.setStretchLastSection(False)
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # Specifications column stretches

        self.inventory_table.setAlternatingRowColors(True)
        table_layout.addWidget(self.inventory_table)

        parent_layout.addWidget(table_group)

    def setup_stats(self, parent_layout):
        """Setup quick statistics."""
        stats_layout = QHBoxLayout()

        self.total_label = QLabel("📊 Total Items: 0")
        self.expired_label = QLabel("⚠️ Expiring Soon: 0")
        self.low_stock_label = QLabel("🔴 Low Stock: 0")

        stats_layout.addWidget(self.total_label)
        stats_layout.addWidget(self.expired_label)
        stats_layout.addWidget(self.low_stock_label)
        stats_layout.addStretch()

        parent_layout.addLayout(stats_layout)

    def refresh_inventory(self):
        """Refresh the inventory display with comprehensive data."""
        try:
            items = Item.get_all()
            self.inventory_table.setRowCount(len(items))

            total_items = len(items)
            expiring_soon = 0
            calibrating_soon = 0
            low_stock = 0

            from datetime import date, timedelta
            today = date.today()
            warning_date = today + timedelta(days=90)  # 3 months warning

            for row, item in enumerate(items):
                # Column 0: Name
                self.inventory_table.setItem(row, 0, QTableWidgetItem(item.name or ""))

                # Column 1: Category (with type)
                category_display = "Unknown"
                if item.category_id:
                    category = Category.get_by_id(item.category_id)
                    if category:
                        category_display = category.name
                        # Try to get category type for enhanced display
                        if category.category_type_id:
                            category_type = CategoryType.get_by_id(category.category_type_id)
                            if category_type:
                                category_display = f"{category_type.name}: {category.name}"
                self.inventory_table.setItem(row, 1, QTableWidgetItem(category_display))

                # Column 2: Size
                self.inventory_table.setItem(row, 2, QTableWidgetItem(item.size or ""))

                # Column 3: Brand
                self.inventory_table.setItem(row, 3, QTableWidgetItem(item.brand or ""))

                # Column 4: Specifications
                self.inventory_table.setItem(row, 4, QTableWidgetItem(item.other_specifications or ""))

                # Column 5: Supplier
                supplier_name = ""
                if item.supplier_id:
                    supplier = Supplier.get_by_id(item.supplier_id)
                    if supplier:
                        supplier_name = supplier.name
                self.inventory_table.setItem(row, 5, QTableWidgetItem(supplier_name))

                # Column 6: PO Number
                self.inventory_table.setItem(row, 6, QTableWidgetItem(item.po_number or ""))

                # Column 7: Expiration Date
                exp_text = "No expiration"
                if item.expiration_date:
                    exp_text = item.expiration_date.strftime("%Y-%m-%d")
                    if item.expiration_date <= warning_date:
                        expiring_soon += 1
                        # Color code expiration
                        exp_item = QTableWidgetItem(exp_text)
                        if item.expiration_date < today:
                            exp_item.setBackground(QColor(DarkTheme.ERROR_COLOR))
                        else:
                            exp_item.setBackground(QColor(DarkTheme.WARNING_COLOR))
                        self.inventory_table.setItem(row, 7, exp_item)
                    else:
                        self.inventory_table.setItem(row, 7, QTableWidgetItem(exp_text))
                else:
                    self.inventory_table.setItem(row, 7, QTableWidgetItem(exp_text))

                # Column 8: Calibration Date
                calib_text = "No calibration"
                if item.calibration_date:
                    calib_text = item.calibration_date.strftime("%Y-%m-%d")
                    # Color code calibration due dates
                    if item.calibration_date <= warning_date:
                        calibrating_soon += 1
                        calib_item = QTableWidgetItem(calib_text)
                        if item.calibration_date < today:
                            calib_item.setBackground(QColor(DarkTheme.ERROR_COLOR))
                        else:
                            calib_item.setBackground(QColor(DarkTheme.WARNING_COLOR))
                        self.inventory_table.setItem(row, 8, calib_item)
                    else:
                        self.inventory_table.setItem(row, 8, QTableWidgetItem(calib_text))
                else:
                    self.inventory_table.setItem(row, 8, QTableWidgetItem(calib_text))

                # Column 9: Status
                status = "Consumable" if item.is_consumable else "Reusable"
                self.inventory_table.setItem(row, 9, QTableWidgetItem(status))

                # Column 10: Available Units
                try:
                    available_query = """
                    SELECT COALESCE(SUM(
                      CASE
                        WHEN movement_type = 'RECEIPT' THEN quantity
                        WHEN movement_type IN ('CONSUMPTION', 'DISPOSAL') THEN -quantity
                        WHEN movement_type = 'RETURN' THEN quantity
                        ELSE 0
                      END
                    ), 0) as available_qty
                    FROM Stock_Movements
                    WHERE item_id = ?
                    """
                    available_rows = db.execute_query(available_query, (item.id,))
                    available_qty = available_rows[0]['available_qty'] if available_rows else 0

                    # Check for low stock (less than 10 units for consumables)
                    if item.is_consumable and available_qty < 10 and available_qty > 0:
                        low_stock += 1

                except Exception as e:
                    logger.error(f"Failed to get available quantity for item {item.id}: {e}")
                    available_qty = 0
                self.inventory_table.setItem(row, 10, QTableWidgetItem(str(available_qty)))

                # Column 11: Borrowed Units
                try:
                    borrowed_query = """
                    SELECT
                      COALESCE((SELECT SUM(ri.quantity_borrowed) FROM Requisition_Items ri WHERE ri.item_id = ?), 0) -
                      COALESCE((SELECT SUM(sm.quantity) FROM Stock_Movements sm WHERE sm.item_id = ? AND sm.movement_type = 'RETURN'), 0)
                    as borrowed_qty
                    """
                    borrowed_rows = db.execute_query(borrowed_query, (item.id, item.id))
                    borrowed_qty = borrowed_rows[0]['borrowed_qty'] if borrowed_rows else 0
                    borrowed_qty = max(0, borrowed_qty)  # Ensure non-negative
                except Exception as e:
                    logger.error(f"Failed to get borrowed quantity for item {item.id}: {e}")
                    borrowed_qty = 0
                self.inventory_table.setItem(row, 11, QTableWidgetItem(str(borrowed_qty)))

                # Column 12: Actions button
                actions_btn = QPushButton("⋮")
                actions_btn.setFixedWidth(80)
                actions_btn.clicked.connect(lambda checked, r=row: self.show_actions_menu(r))
                self.inventory_table.setCellWidget(row, 12, actions_btn)

            # Update stats
            self.total_label.setText(f"📊 Total Items: {total_items}")
            self.expired_label.setText(f"⚠️ Alerts: {expiring_soon + calibrating_soon}")
            self.low_stock_label.setText(f"🔴 Low Stock: {low_stock}")

        except Exception as e:
            logger.error(f"Failed to refresh inventory: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load inventory: {str(e)}")

    def search_items(self):
        """Search items based on input across all relevant columns."""
        search_text = self.search_input.text().lower()

        for row in range(self.inventory_table.rowCount()):
            show_row = True

            if search_text:
                found = False
                # Search across multiple columns: Name (0), Category (1), Size (2), Brand (3), Specifications (4), Supplier (5), PO Number (6)
                for col in [0, 1, 2, 3, 4, 5, 6]:
                    cell_item = self.inventory_table.item(row, col)
                    if cell_item and search_text in cell_item.text().lower():
                        found = True
                        break

                if not found:
                    show_row = False

            self.inventory_table.setRowHidden(row, not show_row)

    def add_item_dialog(self):
        """Show dialog to add new item using composition pattern."""
        result = ItemDialog.add_item(self)
        if result == QDialog.DialogCode.Accepted:
            self.refresh_inventory()

    def show_edit_item_dialog(self, item):
        """Show dialog to edit an existing item using composition pattern."""
        result = ItemDialog.edit_item(self, item)
        if result == QDialog.DialogCode.Accepted:
            self.refresh_inventory()

    def show_actions_menu(self, row):
        """Show actions menu for item."""
        # Simple action buttons for now
        actions_dialog = QDialog(self)
        actions_dialog.setWindowTitle("Item Actions")
        actions_dialog.setModal(True)

        layout = QVBoxLayout(actions_dialog)

        edit_btn = QPushButton("✏️ Edit Item")
        edit_btn.clicked.connect(lambda: self.edit_item(row, actions_dialog))

        delete_btn = QPushButton("🗑️ Delete Item")
        delete_btn.setStyleSheet("QPushButton { color: red; }")
        delete_btn.clicked.connect(lambda: self.delete_item(row, actions_dialog))

        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.clicked.connect(actions_dialog.reject)

        layout.addWidget(edit_btn)
        layout.addWidget(delete_btn)
        layout.addWidget(cancel_btn)

        actions_dialog.exec()

    def edit_item(self, row, parent_dialog):
        """Edit an existing item."""
        parent_dialog.accept()  # Close actions dialog

        # Get item ID from table
        name_item = self.inventory_table.item(row, 0)
        if not name_item:
            return

        # Find item by name (simplified approach)
        items = Item.get_all()
        item = None
        for i in items:
            if i.name == name_item.text():
                item = i
                break

        if not item:
            QMessageBox.warning(self, "Error", "Item not found")
            return

        self.show_edit_item_dialog(item)

    def delete_item(self, row, parent_dialog):
        """Delete an item with confirmation."""
        parent_dialog.accept()  # Close actions dialog

        name_item = self.inventory_table.item(row, 0)
        if not name_item:
            return

        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete '{name_item.text()}'?\n\n"
            "This will mark the item as disposed and cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Find and delete item
                items = Item.get_all()
                for item in items:
                    if item.name == name_item.text():
                        if item.delete("System", "Deleted via inventory management interface"):
                            QMessageBox.information(self, "Success", "Item deleted successfully!")
                            self.refresh_inventory()
                        else:
                            QMessageBox.critical(self, "Error", "Failed to delete item")
                        break

            except Exception as e:
                logger.error(f"Failed to delete item: {e}")
                QMessageBox.critical(self, "Error", f"Failed to delete item: {str(e)}")
