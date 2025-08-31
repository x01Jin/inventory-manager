"""
Simple inventory management page for laboratory equipment.
Implements core functionality from program specifications.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QLineEdit, QComboBox, QGroupBox, QMessageBox,
    QTextEdit, QDateEdit, QCheckBox, QSpinBox, QDialog, QDialogButtonBox
)
from PyQt6.QtCore import QDate
from PyQt6.QtGui import QColor

from inventory_app.gui.styles import DarkTheme
from inventory_app.database.models import Item, Category, Supplier
from inventory_app.database.connection import db
from inventory_app.utils.logger import logger


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
        """Setup the inventory table."""
        table_group = QGroupBox("Inventory Items")
        table_layout = QVBoxLayout(table_group)

        self.inventory_table = QTableWidget()
        self.inventory_table.setColumnCount(9)
        self.inventory_table.setHorizontalHeaderLabels([
            "Name", "Category", "Brand", "Expiration", "Status", "Notes", "Available", "Borrowed", "Actions"
        ])

        # Set reasonable column widths
        self.inventory_table.setColumnWidth(0, 150)  # Name
        self.inventory_table.setColumnWidth(1, 120)  # Category
        self.inventory_table.setColumnWidth(2, 120)  # Brand
        self.inventory_table.setColumnWidth(3, 100)  # Expiration
        self.inventory_table.setColumnWidth(4, 100)  # Status
        self.inventory_table.setColumnWidth(5, 200)  # Notes
        self.inventory_table.setColumnWidth(6, 80)   # Available
        self.inventory_table.setColumnWidth(7, 80)   # Borrowed
        self.inventory_table.setColumnWidth(8, 80)   # Actions

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
        """Refresh the inventory display."""
        try:
            items = Item.get_all()
            self.inventory_table.setRowCount(len(items))

            total_items = len(items)
            expiring_soon = 0

            from datetime import date, timedelta
            today = date.today()
            warning_date = today + timedelta(days=90)  # 3 months warning

            for row, item in enumerate(items):
                # Name
                self.inventory_table.setItem(row, 0, QTableWidgetItem(item.name or ""))

                # Category
                category_name = "Unknown"
                if item.category_id:
                    category = Category.get_by_id(item.category_id)
                    if category:
                        category_name = category.name
                self.inventory_table.setItem(row, 1, QTableWidgetItem(category_name))

                # Brand
                self.inventory_table.setItem(row, 2, QTableWidgetItem(item.brand or ""))

                # Expiration
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
                        self.inventory_table.setItem(row, 3, exp_item)
                    else:
                        self.inventory_table.setItem(row, 3, QTableWidgetItem(exp_text))
                else:
                    self.inventory_table.setItem(row, 3, QTableWidgetItem(exp_text))

                # Status
                status = "Consumable" if item.is_consumable else "Reusable"
                self.inventory_table.setItem(row, 4, QTableWidgetItem(status))

                # Notes
                self.inventory_table.setItem(row, 5, QTableWidgetItem(item.other_specifications or ""))

                # Available Units
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
                except Exception as e:
                    logger.error(f"Failed to get available quantity for item {item.id}: {e}")
                    available_qty = 0
                self.inventory_table.setItem(row, 6, QTableWidgetItem(str(available_qty)))

                # Borrowed Units
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
                self.inventory_table.setItem(row, 7, QTableWidgetItem(str(borrowed_qty)))

                # Actions button
                actions_btn = QPushButton("⋮")
                actions_btn.setFixedWidth(30)
                actions_btn.clicked.connect(lambda checked, r=row: self.show_actions_menu(r))
                self.inventory_table.setCellWidget(row, 8, actions_btn)

            # Update stats
            self.total_label.setText(f"📊 Total Items: {total_items}")
            self.expired_label.setText(f"⚠️ Expiring Soon: {expiring_soon}")

        except Exception as e:
            logger.error(f"Failed to refresh inventory: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load inventory: {str(e)}")

    def search_items(self):
        """Search items based on input."""
        search_text = self.search_input.text().lower()

        for row in range(self.inventory_table.rowCount()):
            show_row = True

            if search_text:
                # Search in name, brand, and notes columns
                name = self.inventory_table.item(row, 0)
                brand = self.inventory_table.item(row, 2)
                notes = self.inventory_table.item(row, 5)

                found = False
                if name and search_text in name.text().lower():
                    found = True
                if brand and search_text in brand.text().lower():
                    found = True
                if notes and search_text in notes.text().lower():
                    found = True

                if not found:
                    show_row = False

            self.inventory_table.setRowHidden(row, not show_row)

    def add_item_dialog(self):
        """Show dialog to add new item."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add New Laboratory Item")
        dialog.setModal(True)
        dialog.resize(400, 500)

        layout = QVBoxLayout(dialog)

        # Form fields
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("Item name (required)")

        category_combo = QComboBox()
        categories = Category.get_all()
        if categories:
            category_combo.addItem("-- Select Category --", None)
            for cat in categories:
                category_combo.addItem(cat.name, cat.id)
        else:
            category_combo.addItem("No categories available", None)

        brand_edit = QLineEdit()
        brand_edit.setPlaceholderText("Brand/Manufacturer")

        specs_edit = QTextEdit()
        specs_edit.setPlaceholderText("Specifications, size, etc.")
        specs_edit.setMaximumHeight(60)

        supplier_combo = QComboBox()
        supplier_combo.setEditable(True)
        suppliers = Supplier.get_all()
        for sup in suppliers:
            supplier_combo.addItem(sup.name, sup.id)

        po_edit = QLineEdit()
        po_edit.setPlaceholderText("Purchase Order number")

        quantity_edit = QSpinBox()
        quantity_edit.setRange(1, 10000)
        quantity_edit.setValue(1)
        quantity_edit.setSuffix(" units")

        exp_edit = QDateEdit()
        exp_edit.setCalendarPopup(True)
        exp_edit.setDate(QDate.currentDate().addMonths(12))

        consumable_check = QCheckBox("Consumable item")
        consumable_check.setChecked(True)

        # Add to form
        form_layout = QVBoxLayout()
        form_layout.addWidget(QLabel("Name:"))
        form_layout.addWidget(name_edit)
        form_layout.addWidget(QLabel("Category:"))
        form_layout.addWidget(category_combo)
        form_layout.addWidget(QLabel("Brand:"))
        form_layout.addWidget(brand_edit)
        form_layout.addWidget(QLabel("Specifications:"))
        form_layout.addWidget(specs_edit)
        form_layout.addWidget(QLabel("Supplier:"))
        form_layout.addWidget(supplier_combo)
        form_layout.addWidget(QLabel("PO Number:"))
        form_layout.addWidget(po_edit)
        form_layout.addWidget(QLabel("Initial Quantity:"))
        form_layout.addWidget(quantity_edit)
        form_layout.addWidget(QLabel("Expiration Date:"))
        form_layout.addWidget(exp_edit)
        form_layout.addWidget(consumable_check)

        layout.addLayout(form_layout)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )

        def save_item():
            try:
                if not name_edit.text().strip():
                    QMessageBox.warning(dialog, "Error", "Item name is required")
                    return

                category_id = category_combo.currentData()
                if category_id is None:
                    QMessageBox.warning(dialog, "Error", "Please select a category")
                    return

                item = Item(
                    name=name_edit.text().strip(),
                    category_id=category_id,
                    brand=brand_edit.text().strip(),
                    other_specifications=specs_edit.toPlainText().strip(),
                    supplier_id=supplier_combo.currentData(),
                    po_number=po_edit.text().strip(),
                    expiration_date=exp_edit.date().toPyDate(),
                    is_consumable=1 if consumable_check.isChecked() else 0
                )

                if item.save("System"):
                    # Create initial batch and stock movement
                    try:
                        quantity = quantity_edit.value()

                        # Create initial batch
                        batch_query = """
                        INSERT INTO Item_Batches (item_id, batch_number, date_received, quantity_received)
                        VALUES (?, 1, ?, ?)
                        """
                        current_date = QDate.currentDate().toString("yyyy-MM-dd")
                        db.execute_update(batch_query, (item.id, current_date, quantity))

                        # Create initial stock movement
                        movement_query = """
                        INSERT INTO Stock_Movements (item_id, batch_id, movement_type, quantity, movement_date, note)
                        VALUES (?, ?, 'RECEIPT', ?, ?, 'Initial stock entry')
                        """
                        # Get the batch ID we just created
                        batch_id_rows = db.execute_query("SELECT last_insert_rowid() as batch_id")
                        batch_id = batch_id_rows[0]['batch_id'] if batch_id_rows else None

                        if batch_id:
                            db.execute_update(movement_query, (item.id, batch_id, quantity, current_date))

                        QMessageBox.information(dialog, "Success", "Item added successfully!")
                        dialog.accept()
                        self.refresh_inventory()

                    except Exception as batch_error:
                        logger.error(f"Failed to create initial batch: {batch_error}")
                        QMessageBox.warning(dialog, "Warning",
                                          "Item saved but initial quantity setup failed. You may need to add stock manually.")
                        dialog.accept()
                        self.refresh_inventory()
                else:
                    QMessageBox.critical(dialog, "Error", "Failed to save item")

            except Exception as e:
                logger.error(f"Failed to save item: {e}")
                QMessageBox.critical(dialog, "Error", f"Failed to save item: {str(e)}")

        button_box.accepted.connect(save_item)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        dialog.exec()

    def show_edit_item_dialog(self, item):
        """Show dialog to edit an existing item."""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Edit Item: {item.name}")
        dialog.setModal(True)
        dialog.resize(400, 500)

        layout = QVBoxLayout(dialog)

        # Form fields
        name_edit = QLineEdit()
        name_edit.setText(item.name or "")
        name_edit.setPlaceholderText("Item name (required)")

        category_combo = QComboBox()
        categories = Category.get_all()
        current_category_index = 0
        if categories:
            category_combo.addItem("-- Select Category --", None)
            for idx, cat in enumerate(categories, 1):
                category_combo.addItem(cat.name, cat.id)
                if cat.id == item.category_id:
                    current_category_index = idx
        else:
            category_combo.addItem("No categories available", None)
        category_combo.setCurrentIndex(current_category_index)

        brand_edit = QLineEdit()
        brand_edit.setText(item.brand or "")
        brand_edit.setPlaceholderText("Brand/Manufacturer")

        specs_edit = QTextEdit()
        specs_edit.setPlainText(item.other_specifications or "")
        specs_edit.setPlaceholderText("Specifications, size, etc.")
        specs_edit.setMaximumHeight(60)

        supplier_combo = QComboBox()
        supplier_combo.setEditable(True)
        suppliers = Supplier.get_all()
        current_supplier_index = 0
        for idx, sup in enumerate(suppliers):
            supplier_combo.addItem(sup.name, sup.id)
            if sup.id == item.supplier_id:
                current_supplier_index = idx
        supplier_combo.setCurrentIndex(current_supplier_index)

        po_edit = QLineEdit()
        po_edit.setText(item.po_number or "")
        po_edit.setPlaceholderText("Purchase Order number")

        # Get current quantity from stock
        current_quantity = 0
        try:
            qty_rows = db.execute_query("""
                SELECT COALESCE(SUM(quantity_received), 0) as total_qty
                FROM Item_Batches
                WHERE item_id = ?
            """, (item.id,))
            if qty_rows:
                current_quantity = qty_rows[0]['total_qty'] or 0
        except Exception as e:
            logger.error(f"Failed to get current quantity: {e}")

        quantity_label = QLabel(f"Current Quantity: {current_quantity} units")
        quantity_label.setStyleSheet("font-weight: bold; color: #666;")

        exp_edit = QDateEdit()
        exp_edit.setCalendarPopup(True)
        if item.expiration_date:
            exp_edit.setDate(QDate(item.expiration_date))
        else:
            exp_edit.setDate(QDate.currentDate().addMonths(12))

        consumable_check = QCheckBox("Consumable item")
        consumable_check.setChecked(item.is_consumable == 1)

        # Add to form
        form_layout = QVBoxLayout()
        form_layout.addWidget(QLabel("Name:"))
        form_layout.addWidget(name_edit)
        form_layout.addWidget(QLabel("Category:"))
        form_layout.addWidget(category_combo)
        form_layout.addWidget(QLabel("Brand:"))
        form_layout.addWidget(brand_edit)
        form_layout.addWidget(QLabel("Specifications:"))
        form_layout.addWidget(specs_edit)
        form_layout.addWidget(QLabel("Supplier:"))
        form_layout.addWidget(supplier_combo)
        form_layout.addWidget(QLabel("PO Number:"))
        form_layout.addWidget(po_edit)
        form_layout.addWidget(quantity_label)
        form_layout.addWidget(QLabel("Expiration Date:"))
        form_layout.addWidget(exp_edit)
        form_layout.addWidget(consumable_check)

        layout.addLayout(form_layout)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )

        def save_item():
            try:
                if not name_edit.text().strip():
                    QMessageBox.warning(dialog, "Error", "Item name is required")
                    return

                category_id = category_combo.currentData()
                if category_id is None:
                    QMessageBox.warning(dialog, "Error", "Please select a category")
                    return

                # Update item properties
                item.name = name_edit.text().strip()
                item.category_id = category_id
                item.brand = brand_edit.text().strip()
                item.other_specifications = specs_edit.toPlainText().strip()
                item.supplier_id = supplier_combo.currentData()
                item.po_number = po_edit.text().strip()
                item.expiration_date = exp_edit.date().toPyDate()
                item.is_consumable = 1 if consumable_check.isChecked() else 0

                if item.save("System"):
                    QMessageBox.information(dialog, "Success", "Item updated successfully!")
                    dialog.accept()
                    self.refresh_inventory()
                else:
                    QMessageBox.critical(dialog, "Error", "Failed to update item")

            except Exception as e:
                logger.error(f"Failed to update item: {e}")
                QMessageBox.critical(dialog, "Error", f"Failed to update item: {str(e)}")

        button_box.accepted.connect(save_item)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        dialog.exec()

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
