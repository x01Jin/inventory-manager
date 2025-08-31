"""
Item editor dialog for adding and editing inventory items.
Provides form for manual encoding of items (Spec #6).
"""

from typing import Optional, List
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QTextEdit, QCheckBox,
    QPushButton, QDateEdit, QGroupBox, QMessageBox
)
from PyQt6.QtCore import QDate
from datetime import date
from inventory_app.database.models import Item, Category, Supplier, Size, Brand
from inventory_app.utils.logger import logger


class ItemEditor(QDialog):
    """Dialog for adding and editing inventory items."""

    def __init__(self, parent=None, item_id: Optional[int] = None):
        super().__init__(parent)
        self.item_id = item_id
        self.existing_item = None
        self.categories: List[str] = []
        self.suppliers: List[str] = []
        self.sizes: List[str] = []
        self.brands: List[str] = []

        if item_id:
            self.existing_item = Item.get_by_id(item_id)
            self.setWindowTitle("Edit Item")
        else:
            self.setWindowTitle("Add New Item")

        self.setup_ui()
        self.load_dropdown_data()
        self.load_item_data()

    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Basic Information Group
        basic_group = QGroupBox("Basic Information")
        basic_layout = QVBoxLayout(basic_group)

        # Name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter item name...")
        name_layout.addWidget(self.name_input)
        basic_layout.addLayout(name_layout)

        # Category and Supplier
        cat_sup_layout = QHBoxLayout()
        cat_sup_layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItem("Select Category", "")
        cat_sup_layout.addWidget(self.category_combo)

        cat_sup_layout.addWidget(QLabel("Supplier:"))
        self.supplier_combo = QComboBox()
        self.supplier_combo.addItem("Select Supplier", "")
        cat_sup_layout.addWidget(self.supplier_combo)
        basic_layout.addLayout(cat_sup_layout)

        # Size and Brand
        size_brand_layout = QHBoxLayout()
        size_brand_layout.addWidget(QLabel("Size:"))
        self.size_combo = QComboBox()
        self.size_combo.addItem("Select Size", "")
        size_brand_layout.addWidget(self.size_combo)

        size_brand_layout.addWidget(QLabel("Brand:"))
        self.brand_combo = QComboBox()
        self.brand_combo.addItem("Select Brand", "")
        size_brand_layout.addWidget(self.brand_combo)
        basic_layout.addLayout(size_brand_layout)

        layout.addWidget(basic_group)

        # Specifications Group
        spec_group = QGroupBox("Specifications")
        spec_layout = QVBoxLayout(spec_group)

        # PO Number
        po_layout = QHBoxLayout()
        po_layout.addWidget(QLabel("PO Number:"))
        self.po_input = QLineEdit()
        self.po_input.setPlaceholderText("Purchase Order Number (optional)")
        po_layout.addWidget(self.po_input)
        spec_layout.addLayout(po_layout)

        # Other Specifications
        spec_layout.addWidget(QLabel("Other Specifications:"))
        self.spec_input = QTextEdit()
        self.spec_input.setPlaceholderText("Additional specifications, materials, etc.")
        self.spec_input.setMaximumHeight(60)
        spec_layout.addWidget(self.spec_input)

        layout.addWidget(spec_group)

        # Dates and Status Group
        dates_group = QGroupBox("Dates and Status")
        dates_layout = QVBoxLayout(dates_group)

        # Dates
        dates_row = QHBoxLayout()
        dates_row.addWidget(QLabel("Acquisition Date:"))
        self.acquisition_date = QDateEdit()
        self.acquisition_date.setDate(QDate.currentDate())
        self.acquisition_date.setCalendarPopup(True)
        dates_row.addWidget(self.acquisition_date)

        dates_row.addWidget(QLabel("Expiration Date:"))
        self.expiration_date = QDateEdit()
        self.expiration_date.setDate(QDate.currentDate())
        self.expiration_date.setCalendarPopup(True)
        self.expiration_date.setSpecialValueText("No Expiration")
        dates_row.addWidget(self.expiration_date)
        dates_layout.addLayout(dates_row)

        # Calibration and Consumable
        calib_cons_layout = QHBoxLayout()
        calib_cons_layout.addWidget(QLabel("Calibration Date:"))
        self.calibration_date = QDateEdit()
        self.calibration_date.setDate(QDate.currentDate())
        self.calibration_date.setCalendarPopup(True)
        self.calibration_date.setSpecialValueText("No Calibration")
        calib_cons_layout.addWidget(self.calibration_date)

        self.consumable_check = QCheckBox("Consumable Item")
        self.consumable_check.setChecked(True)  # Default to consumable
        calib_cons_layout.addWidget(self.consumable_check)
        dates_layout.addLayout(calib_cons_layout)

        layout.addWidget(dates_group)

        # Editor Information (Spec #14)
        editor_group = QGroupBox("Editor Information (Required)")
        editor_layout = QVBoxLayout(editor_group)
        editor_layout.addWidget(QLabel("Editor Name/Initials:"))
        self.editor_input = QLineEdit()
        self.editor_input.setPlaceholderText("Enter your name or initials...")
        editor_layout.addWidget(self.editor_input)
        layout.addWidget(editor_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.save_button = QPushButton("Save Item")
        self.save_button.clicked.connect(self.save_item)
        button_layout.addWidget(self.save_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

        self.setMinimumWidth(1000)
        self.setMinimumHeight(700)

    def load_dropdown_data(self):
        """Load data for dropdown lists."""
        try:
            # Load categories
            categories = Category.get_all()
            for category in categories:
                self.category_combo.addItem(category.name, category.id)

            # Load suppliers
            suppliers = Supplier.get_all()
            for supplier in suppliers:
                self.supplier_combo.addItem(supplier.name, supplier.id)

            # Load sizes
            sizes = Size.get_all()
            for size in sizes:
                self.size_combo.addItem(size.name, size.name)

            # Load brands
            brands = Brand.get_all()
            for brand in brands:
                self.brand_combo.addItem(brand.name, brand.name)

            logger.debug("Loaded dropdown data for item editor")

        except Exception as e:
            logger.error(f"Failed to load dropdown data: {e}")

    def load_item_data(self):
        """Load existing item data for editing."""
        if not self.existing_item:
            return

        try:
            # Basic info
            self.name_input.setText(self.existing_item.name or "")

            # Find and set category
            if self.existing_item.category_id:
                for i in range(self.category_combo.count()):
                    if self.category_combo.itemData(i) == self.existing_item.category_id:
                        self.category_combo.setCurrentIndex(i)
                        break

            # Find and set supplier
            if self.existing_item.supplier_id:
                for i in range(self.supplier_combo.count()):
                    if self.supplier_combo.itemData(i) == self.existing_item.supplier_id:
                        self.supplier_combo.setCurrentIndex(i)
                        break

            # Size and brand
            if self.existing_item.size:
                index = self.size_combo.findText(self.existing_item.size)
                if index >= 0:
                    self.size_combo.setCurrentIndex(index)

            if self.existing_item.brand:
                index = self.brand_combo.findText(self.existing_item.brand)
                if index >= 0:
                    self.brand_combo.setCurrentIndex(index)

            # Specifications
            self.po_input.setText(self.existing_item.po_number or "")
            self.spec_input.setPlainText(self.existing_item.other_specifications or "")

            # Dates
            if self.existing_item.acquisition_date:
                qdate = QDate(self.existing_item.acquisition_date.year,
                             self.existing_item.acquisition_date.month,
                             self.existing_item.acquisition_date.day)
                self.acquisition_date.setDate(qdate)

            if self.existing_item.expiration_date:
                qdate = QDate(self.existing_item.expiration_date.year,
                             self.existing_item.expiration_date.month,
                             self.existing_item.expiration_date.day)
                self.expiration_date.setDate(qdate)

            if self.existing_item.calibration_date:
                qdate = QDate(self.existing_item.calibration_date.year,
                             self.existing_item.calibration_date.month,
                             self.existing_item.calibration_date.day)
                self.calibration_date.setDate(qdate)

            # Status
            self.consumable_check.setChecked(self.existing_item.is_consumable == 1)

            logger.debug(f"Loaded data for item {self.item_id}")

        except Exception as e:
            logger.error(f"Failed to load item data: {e}")

    def save_item(self):
        """Save the item data."""
        try:
            # Validate required fields
            if not self.name_input.text().strip():
                QMessageBox.warning(self, "Validation Error", "Item name is required.")
                return

            if not self.editor_input.text().strip():
                QMessageBox.warning(self, "Validation Error", "Editor name is required (Spec #14).")
                return

            # Create or update item
            if self.existing_item:
                item = self.existing_item
            else:
                item = Item()

            # Basic info
            item.name = self.name_input.text().strip()
            item.category_id = self.category_combo.currentData() or 0
            item.supplier_id = self.supplier_combo.currentData()
            item.size = self.size_combo.currentData()
            item.brand = self.brand_combo.currentData()

            # Specifications
            item.po_number = self.po_input.text().strip() or None
            item.other_specifications = self.spec_input.toPlainText().strip() or None

            # Dates
            acq_date = self.acquisition_date.date()
            item.acquisition_date = date(acq_date.year(), acq_date.month(), acq_date.day())

            exp_date = self.expiration_date.date()
            if not self.expiration_date.specialValueText() or exp_date != self.expiration_date.minimumDate():
                item.expiration_date = date(exp_date.year(), exp_date.month(), exp_date.day())
            else:
                item.expiration_date = None

            cal_date = self.calibration_date.date()
            if not self.calibration_date.specialValueText() or cal_date != self.calibration_date.minimumDate():
                item.calibration_date = date(cal_date.year(), cal_date.month(), cal_date.day())
            else:
                item.calibration_date = None

            # Status
            item.is_consumable = 1 if self.consumable_check.isChecked() else 0

            # Save
            editor_name = self.editor_input.text().strip()
            success = item.save(editor_name)

            if success:
                logger.info(f"Successfully saved item: {item.name}")
                QMessageBox.information(self, "Success", "Item saved successfully!")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to save item. Please try again.")

        except Exception as e:
            logger.error(f"Error saving item: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save item: {str(e)}")
