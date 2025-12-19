"""
Item editor dialog for adding and editing inventory items.
Provides form for manual encoding of items (Spec #6).
"""

from typing import Optional, List
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QTextEdit,
    QPushButton,
    QDateEdit,
    QGroupBox,
    QMessageBox,
    QSizePolicy,
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
        self.on_item_type_changed()  # Initialize the date field based on default selection

    def setup_ui(self):
        """Setup the dialog UI with a responsive two-column layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Left column will contain Basic Information and Dates & Status stacked vertically.
        # Right column will contain Specifications and Editor Information.
        main_h_layout = QHBoxLayout()

        # Basic Information Group (left column)
        basic_group = QGroupBox("Basic Information")
        basic_layout = QVBoxLayout(basic_group)

        # Name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter item name...")
        name_layout.addWidget(self.name_input)
        basic_layout.addLayout(name_layout)

        # Category, Supplier, Size, Brand Grid (2x4 arrangement: labels and inputs in two columns)
        grid_layout = QGridLayout()

        # Row 0: Category and Supplier
        grid_layout.addWidget(QLabel("Category:"), 0, 0)
        self.category_combo = QComboBox()
        self.category_combo.addItem("Select Category", "")
        grid_layout.addWidget(self.category_combo, 0, 1)

        grid_layout.addWidget(QLabel("Supplier:"), 0, 2)
        self.supplier_combo = QComboBox()
        self.supplier_combo.addItem("Select Supplier", "")
        grid_layout.addWidget(self.supplier_combo, 0, 3)

        # Row 1: Size and Brand
        grid_layout.addWidget(QLabel("Size:"), 1, 0)
        self.size_combo = QComboBox()
        self.size_combo.addItem("Select Size", "")
        grid_layout.addWidget(self.size_combo, 1, 1)

        grid_layout.addWidget(QLabel("Brand:"), 1, 2)
        self.brand_combo = QComboBox()
        self.brand_combo.addItem("Select Brand", "")
        grid_layout.addWidget(self.brand_combo, 1, 3)

        # Set column stretches so input columns expand
        grid_layout.setColumnStretch(1, 1)
        grid_layout.setColumnStretch(3, 1)

        basic_layout.addLayout(grid_layout)

        # Dates and Status Group (left column, below basic info)
        dates_group = QGroupBox("Dates and Status")
        dates_layout = QVBoxLayout(dates_group)

        # Dates Grid (4x2: labels on the left, inputs on the right)
        dates_grid_layout = QGridLayout()

        # Row 0: Item Type
        dates_grid_layout.addWidget(QLabel("Item Type:"), 0, 0)
        self.item_type_combo = QComboBox()
        self.item_type_combo.addItem("Consumable", "consumable")
        self.item_type_combo.addItem("Non-Consumable", "non_consumable")
        self.item_type_combo.setCurrentIndex(0)  # Default to consumable
        self.item_type_combo.currentIndexChanged.connect(self.on_item_type_changed)
        dates_grid_layout.addWidget(self.item_type_combo, 0, 1)

        # Row 1: Acquisition Date
        dates_grid_layout.addWidget(QLabel("Acquisition Date:"), 1, 0)
        self.acquisition_date = QDateEdit()
        self.acquisition_date.setDate(QDate.currentDate())
        self.acquisition_date.setCalendarPopup(True)
        dates_grid_layout.addWidget(self.acquisition_date, 1, 1)

        # Row 2: Expiration / Calibration (variable)
        self.variable_label = QLabel("Expiration Date:")
        dates_grid_layout.addWidget(self.variable_label, 2, 0)
        self.variable_input = QDateEdit()
        self.variable_input.setDate(QDate.currentDate())
        self.variable_input.setCalendarPopup(True)
        self.variable_input.setSpecialValueText("No Expiration")
        dates_grid_layout.addWidget(self.variable_input, 2, 1)

        # Row 3: Disposal Date
        self.disposal_label = QLabel("Disposal Date:")
        dates_grid_layout.addWidget(self.disposal_label, 3, 0)
        self.disposal_date = QDateEdit()
        self.disposal_date.setDate(QDate.currentDate())
        self.disposal_date.setCalendarPopup(True)
        self.disposal_date.setSpecialValueText("No Disposal Date")
        dates_grid_layout.addWidget(self.disposal_date, 3, 1)

        # Initially hide disposal controls for consumables
        self.disposal_label.hide()
        self.disposal_date.hide()

        # Make the input column expand vertically and horizontally as needed
        dates_grid_layout.setColumnStretch(1, 1)
        dates_layout.addLayout(dates_grid_layout)

        # Add left column layouts
        left_v = QVBoxLayout()
        left_v.addWidget(basic_group)
        left_v.addWidget(dates_group)
        left_v.addStretch()
        main_h_layout.addLayout(left_v, 1)

        # Specifications Group (right column)
        spec_group = QGroupBox("Specifications")
        spec_layout = QVBoxLayout(spec_group)

        # PO Number
        po_layout = QHBoxLayout()
        po_layout.addWidget(QLabel("PO Number:"))
        self.po_input = QLineEdit()
        self.po_input.setPlaceholderText("Purchase Order Number (optional)")
        po_layout.addWidget(self.po_input)
        spec_layout.addLayout(po_layout)

        # Batch Quantity (only for new items)
        if not self.item_id:  # Only show for new items
            batch_layout = QHBoxLayout()
            batch_layout.addWidget(QLabel("Batch Quantity:"))
            self.batch_quantity_input = QLineEdit()
            self.batch_quantity_input.setPlaceholderText("Total units (e.g., 25)")
            self.batch_quantity_input.setText("1")  # Default to 1
            batch_layout.addWidget(self.batch_quantity_input)
            spec_layout.addLayout(batch_layout)

        # Other Specifications
        spec_layout.addWidget(QLabel("Other Specifications:"))
        self.spec_input = QTextEdit()
        self.spec_input.setPlaceholderText("Additional specifications, materials, etc.")
        # Make the specifications field responsive: it expands with available space
        # No fixed minimum height so it can shrink on narrow/small displays
        self.spec_input.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        spec_layout.addWidget(self.spec_input)

        # Editor Information (required) sits under specifications in right column
        editor_group = QGroupBox("Editor Information (Required)")
        editor_layout = QVBoxLayout(editor_group)
        editor_layout.addWidget(QLabel("Editor Name/Initials:"))
        self.editor_input = QLineEdit()
        self.editor_input.setPlaceholderText("Enter your name or initials...")
        editor_layout.addWidget(self.editor_input)

        # Build right column
        right_v = QVBoxLayout()
        right_v.addWidget(spec_group, 3)
        right_v.addWidget(editor_group, 1)
        right_v.addStretch()
        main_h_layout.addLayout(right_v, 2)

        # Add the two-column layout to the main dialog layout
        layout.addLayout(main_h_layout)

        # Buttons (bottom-right)
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.save_button = QPushButton("Save Item")
        self.save_button.clicked.connect(self.save_item)
        button_layout.addWidget(self.save_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

        # Make window size responsive:
        # prefer 90% of available screen width and 60% of available screen height
        screen = QApplication.primaryScreen()
        if screen is not None:
            try:
                geom = screen.availableGeometry()
                desired_height = int(geom.height() * 0.6)
                desired_width = int(geom.width() * 0.9)
            except Exception:
                desired_height = 700
                desired_width = 900
        else:
            desired_height = 700
            desired_width = 900

        # Set initial size and reasonable minimums so the dialog remains usable on small displays
        self.resize(desired_width, desired_height)
        # Allow shrinking down to 50% of desired size before layout collapses
        self.setMinimumWidth(int(desired_width * 0.5))
        self.setMinimumHeight(int(desired_height * 0.5))

    def on_item_type_changed(self):
        """Update the date field visibility and labels based on item type selection."""
        item_type = self.item_type_combo.currentData()

        if item_type == "consumable":
            # Hide disposal controls
            self.disposal_label.hide()
            self.disposal_date.hide()

            # Show expiration in bottom-right
            self.variable_label.setText("Expiration Date:")
            self.variable_input.setSpecialValueText("No Expiration")
            self.variable_label.show()
            self.variable_input.show()

            # Populate with existing expiration date if available
            if self.existing_item and self.existing_item.expiration_date:
                qdate = QDate(
                    self.existing_item.expiration_date.year,
                    self.existing_item.expiration_date.month,
                    self.existing_item.expiration_date.day,
                )
                self.variable_input.setDate(qdate)
            else:
                self.variable_input.setDate(QDate.currentDate())
        else:  # non_consumable
            # Show disposal in top-right
            self.disposal_label.show()
            self.disposal_date.show()

            # Show calibration in bottom-right
            self.variable_label.setText("Calibration Date:")
            self.variable_input.setSpecialValueText("No Calibration")
            self.variable_label.show()
            self.variable_input.show()

            # Populate with existing dates if available
            if self.existing_item:
                if self.existing_item.calibration_date:
                    qdate = QDate(
                        self.existing_item.calibration_date.year,
                        self.existing_item.calibration_date.month,
                        self.existing_item.calibration_date.day,
                    )
                    self.variable_input.setDate(qdate)
                else:
                    self.variable_input.setDate(QDate.currentDate())

                if self.existing_item.expiration_date:
                    qdate = QDate(
                        self.existing_item.expiration_date.year,
                        self.existing_item.expiration_date.month,
                        self.existing_item.expiration_date.day,
                    )
                    self.disposal_date.setDate(qdate)
                else:
                    self.disposal_date.setDate(QDate.currentDate())
            else:
                # Default dates for new items
                self.variable_input.setDate(QDate.currentDate())
                self.disposal_date.setDate(QDate.currentDate())

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
                    if (
                        self.category_combo.itemData(i)
                        == self.existing_item.category_id
                    ):
                        self.category_combo.setCurrentIndex(i)
                        break

            # Find and set supplier
            if self.existing_item.supplier_id:
                for i in range(self.supplier_combo.count()):
                    if (
                        self.supplier_combo.itemData(i)
                        == self.existing_item.supplier_id
                    ):
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
                qdate = QDate(
                    self.existing_item.acquisition_date.year,
                    self.existing_item.acquisition_date.month,
                    self.existing_item.acquisition_date.day,
                )
                self.acquisition_date.setDate(qdate)

            # Set item type based on is_consumable
            if self.existing_item.is_consumable == 1:
                self.item_type_combo.setCurrentIndex(0)  # Consumable
            else:
                self.item_type_combo.setCurrentIndex(1)  # Non-Consumable

            # Update the layout based on the loaded item type
            self.on_item_type_changed()

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
                QMessageBox.warning(
                    self, "Validation Error", "Editor name is required (Spec #14)."
                )
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
            item.acquisition_date = date(
                acq_date.year(), acq_date.month(), acq_date.day()
            )

            # Set dates based on item type
            item_type = self.item_type_combo.currentData()

            if item_type == "consumable":
                item.is_consumable = 1
                # Set expiration date from the variable_input field
                exp_date = self.variable_input.date()
                if (
                    self.variable_input.specialValueText()
                    and exp_date == self.variable_input.minimumDate()
                ):
                    item.expiration_date = None
                else:
                    item.expiration_date = date(
                        exp_date.year(), exp_date.month(), exp_date.day()
                    )
                item.calibration_date = None  # Clear calibration date for consumables
            else:  # non_consumable
                item.is_consumable = 0
                # Set calibration date from the variable_input field
                cal_date = self.variable_input.date()
                if (
                    self.variable_input.specialValueText()
                    and cal_date == self.variable_input.minimumDate()
                ):
                    item.calibration_date = None
                else:
                    item.calibration_date = date(
                        cal_date.year(), cal_date.month(), cal_date.day()
                    )

                # Set disposal date (stored in expiration_date) from the disposal_date field
                disp_date = self.disposal_date.date()
                if (
                    self.disposal_date.specialValueText()
                    and disp_date == self.disposal_date.minimumDate()
                ):
                    item.expiration_date = None
                else:
                    item.expiration_date = date(
                        disp_date.year(), disp_date.month(), disp_date.day()
                    )

            # Get batch quantity for new items
            batch_quantity = 0
            if not self.item_id and hasattr(self, "batch_quantity_input"):
                try:
                    batch_quantity = int(self.batch_quantity_input.text().strip())
                    if batch_quantity <= 0:
                        QMessageBox.warning(
                            self,
                            "Validation Error",
                            "Batch quantity must be a positive number.",
                        )
                        return
                except ValueError:
                    QMessageBox.warning(
                        self,
                        "Validation Error",
                        "Batch quantity must be a valid number.",
                    )
                    return

            # Save
            editor_name = self.editor_input.text().strip()
            success = item.save(editor_name, batch_quantity)

            if success:
                batch_msg = (
                    f" with {batch_quantity} batches" if batch_quantity > 0 else ""
                )
                logger.info(f"Successfully saved item: {item.name}{batch_msg}")
                QMessageBox.information(
                    self, "Success", f"Item saved successfully{batch_msg}!"
                )
                self.accept()
            else:
                QMessageBox.critical(
                    self, "Error", "Failed to save item. Please try again."
                )

        except Exception as e:
            logger.error(f"Error saving item: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save item: {str(e)}")
