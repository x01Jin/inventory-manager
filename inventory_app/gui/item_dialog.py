"""
Item dialog for adding and editing laboratory inventory items.
Uses composition pattern with proper separation of concerns.
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox, QMessageBox,
    QTextEdit, QDateEdit, QCheckBox, QSpinBox, QDialog, QDialogButtonBox,
    QGroupBox, QFormLayout
)
from PyQt6.QtCore import QDate

from inventory_app.database.models import Item, Category, CategoryType, Supplier, Size, Brand


class ItemDialog(QDialog):
    """
    Dialog for adding and editing inventory items.
    Uses composition pattern for clean separation of concerns.
    """

    def __init__(self, parent=None, item=None):
        super().__init__(parent)
        self.item = item  # None for add, Item instance for edit
        self.setup_ui()

    def setup_ui(self):
        """Setup the user interface with two-row layout."""
        if self.item:
            self.setWindowTitle(f"Edit Item: {self.item.name}")
        else:
            self.setWindowTitle("Add New Laboratory Item")

        self.setModal(True)
        self.resize(800, 600)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Create form sections
        self.create_basic_info_section()
        self.create_specifications_section()
        self.create_dates_section()
        self.create_buttons()

        # Add sections to layout
        layout.addWidget(self.basic_group)
        layout.addWidget(self.specs_group)
        layout.addWidget(self.dates_group)
        layout.addStretch()
        layout.addWidget(self.button_box)

    def create_basic_info_section(self):
        """Create the basic information section (first row)."""
        self.basic_group = QGroupBox("Basic Information")
        basic_layout = QHBoxLayout(self.basic_group)

        # Left column
        left_form = QFormLayout()
        left_form.setContentsMargins(10, 10, 10, 10)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Item name (required)")
        left_form.addRow("Name:", self.name_edit)

        self.category_combo = QComboBox()
        self.populate_category_combo()
        left_form.addRow("Category:", self.category_combo)

        self.size_combo = QComboBox()
        self.size_combo.setEditable(True)
        self.populate_size_combo()
        left_form.addRow("Size:", self.size_combo)

        self.brand_combo = QComboBox()
        self.brand_combo.setEditable(True)
        self.populate_brand_combo()
        left_form.addRow("Brand:", self.brand_combo)

        # Right column
        right_form = QFormLayout()
        right_form.setContentsMargins(10, 10, 10, 10)

        self.supplier_combo = QComboBox()
        self.supplier_combo.setEditable(True)
        self.populate_supplier_combo()
        right_form.addRow("Supplier:", self.supplier_combo)

        self.po_edit = QLineEdit()
        self.po_edit.setPlaceholderText("Purchase Order number")
        right_form.addRow("PO Number:", self.po_edit)

        self.quantity_edit = QSpinBox()
        self.quantity_edit.setRange(1, 10000)
        self.quantity_edit.setValue(1)
        self.quantity_edit.setSuffix(" units")
        right_form.addRow("Initial Quantity:", self.quantity_edit)

        self.consumable_check = QCheckBox("Consumable item")
        self.consumable_check.setChecked(True)
        right_form.addRow("", self.consumable_check)

        # Add columns to basic layout
        basic_layout.addLayout(left_form)
        basic_layout.addLayout(right_form)

    def create_specifications_section(self):
        """Create the specifications section."""
        self.specs_group = QGroupBox("Specifications")
        specs_layout = QVBoxLayout(self.specs_group)

        self.specs_edit = QTextEdit()
        self.specs_edit.setPlaceholderText("Additional specifications, notes, or details")
        self.specs_edit.setMaximumHeight(80)
        specs_layout.addWidget(self.specs_edit)

    def create_dates_section(self):
        """Create the dates and editor section (second row)."""
        self.dates_group = QGroupBox("Dates & Editor Information")
        dates_layout = QHBoxLayout(self.dates_group)

        # Left side - dates
        dates_form = QFormLayout()
        dates_form.setContentsMargins(10, 10, 10, 10)

        self.exp_edit = QDateEdit()
        self.exp_edit.setCalendarPopup(True)
        self.exp_edit.setDate(QDate.currentDate().addMonths(12))
        dates_form.addRow("Expiration Date:", self.exp_edit)

        self.calib_edit = QDateEdit()
        self.calib_edit.setCalendarPopup(True)
        self.calib_edit.setDate(QDate.currentDate().addYears(1))
        dates_form.addRow("Calibration Date:", self.calib_edit)

        # Right side - editor
        editor_form = QFormLayout()
        editor_form.setContentsMargins(10, 10, 10, 10)

        self.editor_edit = QLineEdit()
        self.editor_edit.setPlaceholderText("Your name/initials (required)")
        self.editor_edit.setText("Admin")
        editor_form.addRow("Editor:", self.editor_edit)

        # Add to dates layout
        dates_layout.addLayout(dates_form)
        dates_layout.addLayout(editor_form)
        dates_layout.addStretch()

    def create_buttons(self):
        """Create the button box."""
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.save_item)
        self.button_box.rejected.connect(self.reject)

    def populate_category_combo(self):
        """Populate the category combo box."""
        categories = Category.get_all()
        if categories:
            self.category_combo.addItem("-- Select Category --", None)
            for cat in categories:
                category_display = cat.name
                # Try to get category type for enhanced display
                if cat.category_type_id:
                    category_type = CategoryType.get_by_id(cat.category_type_id)
                    if category_type:
                        category_display = f"{category_type.name}: {cat.name}"
                self.category_combo.addItem(category_display, cat.id)
        else:
            self.category_combo.addItem("No categories available", None)

    def populate_supplier_combo(self):
        """Populate the supplier combo box."""
        suppliers = Supplier.get_all()
        for sup in suppliers:
            self.supplier_combo.addItem(sup.name, sup.id)

    def populate_size_combo(self):
        """Populate the size combo box."""
        sizes = Size.get_all()
        for s in sizes:
            self.size_combo.addItem(s.name)

    def populate_brand_combo(self):
        """Populate the brand combo box."""
        brands = Brand.get_all()
        for b in brands:
            self.brand_combo.addItem(b.name)

    def load_item_data(self):
        """Load existing item data for editing."""
        if not self.item:
            return

        self.name_edit.setText(self.item.name or "")
        self.size_combo.setCurrentText(self.item.size or "")
        self.brand_combo.setCurrentText(self.item.brand or "")
        self.specs_edit.setPlainText(self.item.other_specifications or "")
        self.po_edit.setText(self.item.po_number or "")
        self.consumable_check.setChecked(self.item.is_consumable == 1)

        # Set category selection
        if self.item.category_id:
            for i in range(self.category_combo.count()):
                if self.category_combo.itemData(i) == self.item.category_id:
                    self.category_combo.setCurrentIndex(i)
                    break

        # Set supplier selection
        if self.item.supplier_id:
            for i in range(self.supplier_combo.count()):
                if self.supplier_combo.itemData(i) == self.item.supplier_id:
                    self.supplier_combo.setCurrentIndex(i)
                    break

        # Set dates
        if self.item.expiration_date:
            self.exp_edit.setDate(QDate(self.item.expiration_date))
        if self.item.calibration_date:
            self.calib_edit.setDate(QDate(self.item.calibration_date))

    def save_item(self):
        """Save the item data."""
        try:
            # Validation
            if not self.name_edit.text().strip():
                QMessageBox.warning(self, "Error", "Item name is required")
                return

            category_id = self.category_combo.currentData()
            if category_id is None:
                QMessageBox.warning(self, "Error", "Please select a category")
                return

            editor_name = self.editor_edit.text().strip()
            if not editor_name:
                QMessageBox.warning(self, "Error", "Editor name/initials is required")
                return

            # Create or update item
            if self.item:
                # Update existing
                self.item.name = self.name_edit.text().strip()
                self.item.category_id = category_id
                self.item.size = self.size_combo.currentText().strip()
                self.item.brand = self.brand_combo.currentText().strip()
                self.item.other_specifications = self.specs_edit.toPlainText().strip()
                self.item.supplier_id = self.supplier_combo.currentData()
                self.item.po_number = self.po_edit.text().strip()
                self.item.expiration_date = self.exp_edit.date().toPyDate()
                self.item.calibration_date = self.calib_edit.date().toPyDate()
                self.item.is_consumable = 1 if self.consumable_check.isChecked() else 0

                if self.item.save(editor_name):
                    QMessageBox.information(self, "Success", "Item updated successfully!")
                    self.accept()
                else:
                    QMessageBox.critical(self, "Error", "Failed to update item")
            else:
                # Create new
                new_item = Item(
                    name=self.name_edit.text().strip(),
                    category_id=category_id,
                    size=self.size_combo.currentText().strip(),
                    brand=self.brand_combo.currentText().strip(),
                    other_specifications=self.specs_edit.toPlainText().strip(),
                    supplier_id=self.supplier_combo.currentData(),
                    po_number=self.po_edit.text().strip(),
                    expiration_date=self.exp_edit.date().toPyDate(),
                    calibration_date=self.calib_edit.date().toPyDate(),
                    is_consumable=1 if self.consumable_check.isChecked() else 0
                )

                if new_item.save(editor_name):
                    QMessageBox.information(self, "Success", "Item added successfully!")
                    self.accept()
                else:
                    QMessageBox.critical(self, "Error", "Failed to save item")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save item: {str(e)}")

    @staticmethod
    def add_item(parent=None):
        """Static method to show add item dialog."""
        dialog = ItemDialog(parent)
        return dialog.exec()

    @staticmethod
    def edit_item(parent=None, item=None):
        """Static method to show edit item dialog."""
        dialog = ItemDialog(parent, item)
        dialog.load_item_data()
        return dialog.exec()
