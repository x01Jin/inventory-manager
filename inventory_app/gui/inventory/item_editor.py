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
    QFileDialog,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QInputDialog,
)
from PyQt6.QtCore import QDate, Qt
from datetime import date
from inventory_app.database.models import Item, Category, Supplier, Size, Brand, ItemSDS
from inventory_app.services.category_config import get_category_config
from inventory_app.services.sds_storage_service import sds_storage_service
from inventory_app.utils.logger import logger
from inventory_app.utils.reference_normalization import (
    build_size_compare_key,
    normalize_metric_size_value,
)


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
        self.sds_source_path: Optional[str] = None
        self.current_sds: Optional[ItemSDS] = None
        self.batch_rows: List[dict] = []

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
        layout.setSpacing(8)

        # Left column will contain Basic Information and Dates & Status stacked vertically.
        # Right column will contain Specifications and Editor Information.
        main_h_layout = QHBoxLayout()
        main_h_layout.setSpacing(8)

        # Basic Information Group (left column)
        basic_group = QGroupBox("Basic Information")
        basic_layout = QVBoxLayout(basic_group)
        basic_layout.setSpacing(8)

        # Name
        name_layout = QHBoxLayout()
        name_layout.setSpacing(8)
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
        # Connect category change to auto-update dates and item type
        self.category_combo.currentIndexChanged.connect(self.on_category_changed)
        grid_layout.addWidget(self.category_combo, 0, 1)

        grid_layout.addWidget(QLabel("Supplier:"), 0, 2)
        self.supplier_combo = QComboBox()
        self.supplier_combo.addItem("Select Supplier", "")
        grid_layout.addWidget(self.supplier_combo, 0, 3)

        # Row 1: Size and Brand
        grid_layout.addWidget(QLabel("Size:"), 1, 0)
        self.size_combo = QComboBox()
        self.size_combo.addItem("Select Size", "")
        self.size_combo.setEditable(True)
        self.size_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        size_line_edit = self.size_combo.lineEdit()
        if size_line_edit is not None:
            size_line_edit.setPlaceholderText("Select or type size (e.g., 500 mL)")

        size_completer = self.size_combo.completer()
        if size_completer is not None:
            size_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            size_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        grid_layout.addWidget(self.size_combo, 1, 1)

        grid_layout.addWidget(QLabel("Brand:"), 1, 2)
        self.brand_combo = QComboBox()
        self.brand_combo.addItem("Select Brand", "")
        grid_layout.addWidget(self.brand_combo, 1, 3)

        # Set column stretches so input columns expand
        grid_layout.setSpacing(8)
        grid_layout.setColumnStretch(1, 1)
        grid_layout.setColumnStretch(3, 1)

        basic_layout.addLayout(grid_layout)

        # Dates and Status Group (left column, below basic info)
        dates_group = QGroupBox("Dates and Status")
        dates_layout = QVBoxLayout(dates_group)
        dates_layout.setSpacing(8)

        # Dates Grid (4x2: labels on the left, inputs on the right)
        dates_grid_layout = QGridLayout()
        dates_grid_layout.setSpacing(8)

        # Row 0: Item Type
        dates_grid_layout.addWidget(QLabel("Item Type:"), 0, 0)
        self.item_type_combo = QComboBox()
        self.item_type_combo.addItem("Consumable", "consumable")
        self.item_type_combo.addItem("Non-Consumable", "non_consumable")
        self.item_type_combo.addItem("TA, Non-Consumable", "ta_non_consumable")
        self.item_type_combo.setCurrentIndex(0)  # Default to consumable
        self.item_type_combo.currentIndexChanged.connect(self.on_item_type_changed)
        dates_grid_layout.addWidget(self.item_type_combo, 0, 1)

        # Row 1: Acquisition Date
        dates_grid_layout.addWidget(QLabel("Acquisition Date:"), 1, 0)
        self.acquisition_date = QDateEdit()
        self.acquisition_date.setDate(QDate.currentDate())
        self.acquisition_date.setCalendarPopup(True)
        # Connect acquisition date change to recalculate expiration/disposal dates
        self.acquisition_date.dateChanged.connect(self.on_acquisition_date_changed)
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

        self.lifecycle_note = QLabel()
        self.lifecycle_note.setWordWrap(True)
        dates_grid_layout.addWidget(self.lifecycle_note, 4, 0, 1, 2)

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
        spec_layout.setSpacing(8)

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

        # SDS section (chemical categories only)
        self.sds_label = QLabel("SDS File (optional):")
        spec_layout.addWidget(self.sds_label)

        sds_row = QHBoxLayout()
        self.sds_file_input = QLineEdit()
        self.sds_file_input.setReadOnly(True)
        self.sds_file_input.setPlaceholderText("No SDS file selected")
        sds_row.addWidget(self.sds_file_input)

        self.sds_browse_btn = QPushButton("Browse")
        self.sds_browse_btn.clicked.connect(self._select_sds_file)
        sds_row.addWidget(self.sds_browse_btn)
        spec_layout.addLayout(sds_row)

        self.sds_notes_label = QLabel("SDS Notes (optional):")
        spec_layout.addWidget(self.sds_notes_label)
        self.sds_notes_input = QTextEdit()
        self.sds_notes_input.setPlaceholderText(
            "Optional quick SDS notes (hazards, first aid, handling)."
        )
        self.sds_notes_input.setMaximumHeight(90)
        spec_layout.addWidget(self.sds_notes_input)

        # Editor Information (required) sits under specifications in right column
        editor_group = QGroupBox("Editor Information (Required)")
        editor_layout = QVBoxLayout(editor_group)
        editor_layout.setSpacing(8)
        editor_layout.addWidget(QLabel("Editor Name/Initials:"))
        self.editor_input = QLineEdit()
        self.editor_input.setPlaceholderText("Enter your name or initials...")
        editor_layout.addWidget(self.editor_input)

        # Build right column
        right_v = QVBoxLayout()
        right_v.addWidget(spec_group, 3)
        if self.item_id:
            self.batch_group = QGroupBox("Batch Acquisition Records")
            batch_group_layout = QVBoxLayout(self.batch_group)

            self.batch_table = QTableWidget()
            self.batch_table.setColumnCount(3)
            self.batch_table.setHorizontalHeaderLabels(
                ["Batch", "Date Received", "Quantity"]
            )
            self.batch_table.setSelectionBehavior(
                QTableWidget.SelectionBehavior.SelectRows
            )
            self.batch_table.setSelectionMode(
                QTableWidget.SelectionMode.SingleSelection
            )
            self.batch_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            batch_header = self.batch_table.horizontalHeader()
            if batch_header:
                batch_header.setSectionResizeMode(
                    0, QHeaderView.ResizeMode.ResizeToContents
                )
                batch_header.setSectionResizeMode(
                    1, QHeaderView.ResizeMode.ResizeToContents
                )
                batch_header.setSectionResizeMode(
                    2, QHeaderView.ResizeMode.ResizeToContents
                )
                batch_header.setStretchLastSection(True)
            batch_group_layout.addWidget(self.batch_table)

            batch_actions = QHBoxLayout()
            self.batch_add_btn = QPushButton("Add Batch")
            self.batch_add_btn.clicked.connect(self._add_batch)
            batch_actions.addWidget(self.batch_add_btn)

            self.batch_edit_btn = QPushButton("Edit Selected")
            self.batch_edit_btn.clicked.connect(self._edit_selected_batch)
            batch_actions.addWidget(self.batch_edit_btn)

            self.batch_remove_btn = QPushButton("Remove Selected")
            self.batch_remove_btn.clicked.connect(self._remove_selected_batch)
            batch_actions.addWidget(self.batch_remove_btn)
            batch_actions.addStretch()
            batch_group_layout.addLayout(batch_actions)

            right_v.addWidget(self.batch_group, 2)
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

        # SDS controls are shown only for chemical categories.
        self._update_sds_visibility("")

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
            self.lifecycle_note.setText(
                "Alerts use Expiration Date directly for consumables (warning within 180 days)."
            )

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
            self.variable_label.setText("Last Calibration Date:")
            self.variable_input.setSpecialValueText("No Calibration")
            self.variable_label.show()
            self.variable_input.show()
            self.lifecycle_note.setText(
                "Calibration Due is auto-calculated as Last Calibration Date + 1 year; warning starts within 90 days. Disposal alerts use Disposal Date."
            )

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

    def on_category_changed(self):
        """Update item type and auto-calculate dates based on selected category.

        When a category is selected:
        1. Set item type (consumable/non-consumable) based on category config
        2. Calculate expiration/disposal dates based on category thresholds
        3. Set calibration date if category requires calibration

        Dates are pre-filled but remain editable by the user.
        """
        category_name = self.category_combo.currentText()
        if not category_name or category_name == "Select Category":
            return

        # Get category configuration
        cat_config = get_category_config(category_name)
        if not cat_config:
            return

        # Get acquisition date for calculations
        acq_qdate = self.acquisition_date.date()
        acquisition_date = date(acq_qdate.year(), acq_qdate.month(), acq_qdate.day())

        # Set item type based on category.
        # Preserve explicit TA non-consumable selection across non-consumable categories.
        current_item_type = self.item_type_combo.currentData()
        if cat_config.is_consumable:
            # Find and select "Consumable"
            for i in range(self.item_type_combo.count()):
                if self.item_type_combo.itemData(i) == "consumable":
                    self.item_type_combo.setCurrentIndex(i)
                    break
        else:
            if current_item_type != "ta_non_consumable":
                # Find and select "Non-Consumable"
                for i in range(self.item_type_combo.count()):
                    if self.item_type_combo.itemData(i) == "non_consumable":
                        self.item_type_combo.setCurrentIndex(i)
                        break

        # Calculate and set dates based on category
        # For consumables: set expiration date
        # For non-consumables: set disposal date and calibration date

        if cat_config.is_consumable:
            # Calculate expiration date
            exp_date = cat_config.calculate_expiration_date(acquisition_date)
            if exp_date:
                self.variable_input.setDate(
                    QDate(exp_date.year, exp_date.month, exp_date.day)
                )
        else:
            # Calculate disposal date
            disposal_date = cat_config.calculate_expiration_date(acquisition_date)
            if disposal_date:
                self.disposal_date.setDate(
                    QDate(disposal_date.year, disposal_date.month, disposal_date.day)
                )

            # Calculate calibration date if applicable
            if cat_config.has_calibration:
                cal_date = cat_config.calculate_calibration_date(acquisition_date)
                if cal_date:
                    self.variable_input.setDate(
                        QDate(cal_date.year, cal_date.month, cal_date.day)
                    )

        self._update_sds_visibility(category_name)

    def on_acquisition_date_changed(self):
        """Recalculate expiration/disposal dates when acquisition date changes.

        This keeps the dates in sync with the category thresholds when the user
        changes the acquisition date.
        """
        # Trigger category change handler to recalculate dates
        self.on_category_changed()

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
                else:
                    self.size_combo.setCurrentText(self.existing_item.size)

            if self.existing_item.brand:
                index = self.brand_combo.findText(self.existing_item.brand)
                if index >= 0:
                    self.brand_combo.setCurrentIndex(index)

            # Specifications
            self.po_input.setText(self.existing_item.po_number or "")
            self.spec_input.setPlainText(self.existing_item.other_specifications or "")

            self.current_sds = ItemSDS.get_by_item_id(self.existing_item.id or 0)
            if self.current_sds:
                self.sds_file_input.setText(
                    self.current_sds.original_filename
                    or self.current_sds.file_path
                    or ""
                )
                self.sds_notes_input.setPlainText(self.current_sds.sds_notes or "")

            # Dates
            if self.existing_item.acquisition_date:
                qdate = QDate(
                    self.existing_item.acquisition_date.year,
                    self.existing_item.acquisition_date.month,
                    self.existing_item.acquisition_date.day,
                )
                self.acquisition_date.setDate(qdate)

            # Set item type based on is_consumable
            item_type_text = (self.existing_item.item_type or "").strip().lower()
            if item_type_text == "consumable":
                self.item_type_combo.setCurrentIndex(0)
            elif item_type_text == "ta, non-consumable":
                self.item_type_combo.setCurrentIndex(2)
            elif self.existing_item.is_consumable == 1:
                self.item_type_combo.setCurrentIndex(0)
            else:
                self.item_type_combo.setCurrentIndex(1)

            # Update the layout based on the loaded item type
            self.on_item_type_changed()
            self._update_sds_visibility(self.category_combo.currentText())
            self._load_batch_data()

            logger.debug(f"Loaded data for item {self.item_id}")

        except Exception as e:
            logger.error(f"Failed to load item data: {e}")

    def save_item(self):
        """Save the item data."""
        save_label = self.save_button.text()
        self.save_button.setEnabled(False)
        self.save_button.setText("Saving...")
        try:
            # Validate required fields with specific guidance before saving
            validation_issues = []
            item_name = self.name_input.text().strip()
            if not item_name:
                validation_issues.append("Item Name is required.")

            category_data = self.category_combo.currentData()
            if not isinstance(category_data, int) or category_data <= 0:
                validation_issues.append(
                    "Category is required. Please choose a value from the Category dropdown."
                )

            if not self.editor_input.text().strip():
                validation_issues.append("Editor Name/Initials is required.")

            if validation_issues:
                QMessageBox.warning(
                    self,
                    "Validation Error",
                    "Please complete the required fields before saving:\n- "
                    + "\n- ".join(validation_issues),
                )
                return

            if not self.existing_item:
                likely_duplicates = Item.find_likely_duplicates(
                    item_name, category_data
                )
                if likely_duplicates and not self._confirm_likely_duplicate_item(
                    item_name,
                    self.category_combo.currentText(),
                    likely_duplicates,
                ):
                    return

            supplier_data = self.supplier_combo.currentData()
            normalized_supplier_id = None
            if supplier_data not in (None, "", 0):
                if isinstance(supplier_data, int) and supplier_data > 0:
                    normalized_supplier_id = supplier_data
                elif isinstance(supplier_data, str) and supplier_data.strip().isdigit():
                    normalized_supplier_id = int(supplier_data.strip())
                else:
                    QMessageBox.warning(
                        self,
                        "Validation Error",
                        "Supplier selection is invalid. Please pick a supplier from the list or leave it as Select Supplier.",
                    )
                    return

            normalized_size = normalize_metric_size_value(self.size_combo.currentText())
            normalized_brand = self._normalize_optional_text_value(
                self.brand_combo.currentData()
            )

            if normalized_size is not None:
                resolved_size = self._resolve_or_create_size_value(normalized_size)
                if resolved_size is None:
                    return
                normalized_size = resolved_size

            missing_optional_entries = []
            if normalized_supplier_id is None:
                missing_optional_entries.append("Supplier")
            if normalized_size is None:
                missing_optional_entries.append("Size")
            if normalized_brand is None:
                missing_optional_entries.append("Brand")

            if missing_optional_entries and not self._confirm_missing_optional_entries(
                missing_optional_entries
            ):
                return

            # Create or update item
            if self.existing_item:
                item = self.existing_item
            else:
                item = Item()

            # Basic info
            item.name = item_name
            item.category_id = category_data
            item.supplier_id = normalized_supplier_id
            item.size = normalized_size
            item.brand = normalized_brand

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
                item.item_type = "Consumable"
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
            else:  # non_consumable or ta_non_consumable
                item.is_consumable = 0
                if item_type == "ta_non_consumable":
                    item.item_type = "TA, non-consumable"
                else:
                    item.item_type = "Non-consumable"
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

            if success and self.item_id:
                batches_saved, batch_message = Item.sync_batches_for_item(
                    item.id or 0,
                    self.batch_rows,
                    editor_name,
                )
                if not batches_saved:
                    QMessageBox.critical(self, "Batch Error", batch_message)
                    return

            if success:
                self._save_sds_if_needed(item.id or 0, editor_name)
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
        finally:
            if self.isVisible():
                self.save_button.setEnabled(True)
                self.save_button.setText(save_label)

    def _normalize_optional_text_value(self, value: Optional[str]) -> Optional[str]:
        """Normalize optional text dropdown value to None when empty."""
        if value is None:
            return None

        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned if cleaned else None

        return str(value).strip() or None

    def _confirm_missing_optional_entries(self, entries: List[str]) -> bool:
        """Ask user to proceed when optional dropdown fields are left unselected."""
        message = (
            "The following optional fields were not selected:\n"
            f"- {'\n- '.join(entries)}\n\n"
            "These will be displayed as N/A.\n"
            "Do you want to proceed with saving?"
        )

        response = QMessageBox.question(
            self,
            "Optional Fields Not Filled",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return response == QMessageBox.StandardButton.Yes

    def _confirm_likely_duplicate_item(
        self,
        item_name: str,
        category_name: str,
        duplicates: List[dict],
    ) -> bool:
        """Warn users when likely duplicate items exist in the same category."""
        preview_lines = []
        for duplicate in duplicates[:5]:
            preview_lines.append(
                "- "
                f"{duplicate.get('name', 'Unknown')} "
                f"(Size: {duplicate.get('size') or 'N/A'}, "
                f"Brand: {duplicate.get('brand') or 'N/A'}, "
                f"Supplier: {duplicate.get('supplier_name') or 'N/A'})"
            )

        extra_count = max(0, len(duplicates) - 5)
        if extra_count > 0:
            preview_lines.append(f"- ...and {extra_count} more")

        message = (
            f"A likely duplicate item already exists in '{category_name}'.\n\n"
            f"New item: {item_name}\n\n"
            "Possible matches:\n"
            + "\n".join(preview_lines)
            + "\n\nDo you want to continue saving this item?"
        )

        reply = QMessageBox.question(
            self,
            "Likely Duplicate Item",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    def _resolve_or_create_size_value(self, size_value: str) -> Optional[str]:
        """Resolve typed size to existing canonical value or create it."""
        target_key = build_size_compare_key(size_value)
        if not target_key:
            return None

        sizes = Size.get_all()
        for size in sizes:
            if build_size_compare_key(size.name) == target_key:
                return normalize_metric_size_value(size.name) or size.name

        new_size = Size(name=size_value)
        success, message = new_size.save()
        if success:
            saved_name = new_size.name
            self.size_combo.addItem(saved_name, saved_name)
            self.size_combo.setCurrentText(saved_name)
            return saved_name

        # Another editor flow may have created an equivalent value first.
        refreshed_sizes = Size.get_all()
        for size in refreshed_sizes:
            if build_size_compare_key(size.name) == target_key:
                existing_name = normalize_metric_size_value(size.name) or size.name
                self.size_combo.setCurrentText(existing_name)
                return existing_name

        QMessageBox.critical(
            self,
            "Size Error",
            f"Failed to create size value '{size_value}'.\n{message}",
        )
        return None

    def _is_chemical_category(self, category_name: str) -> bool:
        """Return True when category supports SDS controls."""
        return category_name in {"Chemicals-Solid", "Chemicals-Liquid"}

    def _update_sds_visibility(self, category_name: str) -> None:
        """Show SDS controls only for chemical categories."""
        is_chemical = self._is_chemical_category(category_name)

        self.sds_label.setVisible(is_chemical)
        self.sds_file_input.setVisible(is_chemical)
        self.sds_browse_btn.setVisible(is_chemical)
        self.sds_notes_label.setVisible(is_chemical)
        self.sds_notes_input.setVisible(is_chemical)

        if not is_chemical:
            self.sds_source_path = None
            self.sds_file_input.clear()
            self.sds_notes_input.clear()

    def _select_sds_file(self) -> None:
        """Select an SDS file from disk."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select SDS File",
            "",
            "Documents (*.pdf *.doc *.docx *.txt *.png *.jpg *.jpeg);;All Files (*.*)",
        )
        if not file_path:
            return

        self.sds_source_path = file_path
        self.sds_file_input.setText(file_path)

    def _save_sds_if_needed(self, item_id: int, editor_name: str) -> None:
        """Persist optional SDS metadata/file for chemical items."""
        if item_id <= 0:
            return

        if not self._is_chemical_category(self.category_combo.currentText()):
            return

        sds_notes = self.sds_notes_input.toPlainText().strip() or None
        existing = ItemSDS.get_by_item_id(item_id)
        sds_record = existing or ItemSDS(item_id=item_id)

        copied_path = None
        old_path = existing.file_path if existing else None
        if self.sds_source_path:
            metadata = sds_storage_service.store_file(item_id, self.sds_source_path)
            if not metadata:
                QMessageBox.warning(
                    self,
                    "SDS Warning",
                    "Item was saved, but SDS file upload failed.",
                )
                return

            copied_path = metadata["file_path"]
            sds_record.stored_filename = metadata["stored_filename"]
            sds_record.original_filename = metadata["original_filename"]
            sds_record.file_path = metadata["file_path"]
            sds_record.mime_type = metadata["mime_type"]

        sds_record.sds_notes = sds_notes

        if not sds_record.file_path and not sds_record.sds_notes:
            return

        reason = "SDS uploaded" if existing is None else "SDS updated"
        if not sds_record.save(editor_name, reason=reason):
            if copied_path:
                sds_storage_service.remove_file(copied_path)
            QMessageBox.warning(
                self,
                "SDS Warning",
                "Item was saved, but SDS metadata could not be saved.",
            )
            return

        if self.sds_source_path and old_path and old_path != sds_record.file_path:
            sds_storage_service.remove_file(old_path)

    def _load_batch_data(self) -> None:
        """Load existing batch rows for edit mode."""
        if not self.item_id:
            return

        rows = Item.get_batches_for_item(self.item_id)
        self.batch_rows = []
        for row in rows:
            self.batch_rows.append(
                {
                    "id": row.get("id"),
                    "batch_number": int(row.get("batch_number") or 0),
                    "date_received": row.get("date_received"),
                    "quantity_received": int(row.get("quantity_received") or 0),
                    "disposal_date": row.get("disposal_date"),
                    "movement_count": int(row.get("movement_count") or 0),
                }
            )

        self._refresh_batch_table()

    def _refresh_batch_table(self) -> None:
        """Render in-memory batch rows to table."""
        if not self.item_id:
            return

        self.batch_rows.sort(key=lambda row: row.get("batch_number", 0))
        self.batch_table.setRowCount(len(self.batch_rows))
        for idx, row in enumerate(self.batch_rows):
            self.batch_table.setItem(
                idx,
                0,
                QTableWidgetItem(f"B{int(row.get('batch_number') or 0)}"),
            )
            self.batch_table.setItem(
                idx,
                1,
                QTableWidgetItem(str(row.get("date_received") or "N/A")),
            )
            quantity_text = str(int(row.get("quantity_received") or 0))
            if int(row.get("movement_count") or 0) > 0:
                quantity_text = f"{quantity_text} (locked by movement history)"
            self.batch_table.setItem(idx, 2, QTableWidgetItem(quantity_text))

    def _next_batch_number(self) -> int:
        """Get next available batch number."""
        if not self.batch_rows:
            return 1
        return max(int(row.get("batch_number") or 0) for row in self.batch_rows) + 1

    def _add_batch(self) -> None:
        """Add a new batch entry to in-memory rows."""
        next_number = self._next_batch_number()

        date_text, date_ok = QInputDialog.getText(
            self,
            "Add Batch",
            f"Date Received for B{next_number} (YYYY-MM-DD):",
            text=date.today().isoformat(),
        )
        if not date_ok:
            return

        date_text = date_text.strip()
        try:
            parsed_date = date.fromisoformat(date_text)
        except Exception:
            QMessageBox.warning(
                self, "Invalid Date", "Please enter a valid ISO date (YYYY-MM-DD)."
            )
            return

        qty, qty_ok = QInputDialog.getInt(
            self,
            "Add Batch",
            f"Quantity for B{next_number}:",
            1,
            1,
            1000000,
            1,
        )
        if not qty_ok:
            return

        self.batch_rows.append(
            {
                "id": None,
                "batch_number": next_number,
                "date_received": parsed_date.isoformat(),
                "quantity_received": qty,
                "disposal_date": None,
                "movement_count": 0,
            }
        )
        self._refresh_batch_table()

    def _selected_batch_row(self) -> Optional[int]:
        """Get selected table row index for batch table."""
        if not self.item_id:
            return None
        selection_model = self.batch_table.selectionModel()
        if selection_model is None:
            return None
        selected = selection_model.selectedRows()
        if not selected:
            return None
        return selected[0].row()

    def _edit_selected_batch(self) -> None:
        """Edit selected batch date/quantity in memory."""
        row_idx = self._selected_batch_row()
        if row_idx is None or row_idx < 0 or row_idx >= len(self.batch_rows):
            QMessageBox.information(self, "No Selection", "Select a batch first.")
            return

        batch = self.batch_rows[row_idx]
        batch_label = f"B{int(batch.get('batch_number') or 0)}"

        date_text, date_ok = QInputDialog.getText(
            self,
            "Edit Batch",
            f"Date Received for {batch_label} (YYYY-MM-DD):",
            text=str(batch.get("date_received") or date.today().isoformat()),
        )
        if not date_ok:
            return

        date_text = date_text.strip()
        try:
            parsed_date = date.fromisoformat(date_text)
        except Exception:
            QMessageBox.warning(
                self, "Invalid Date", "Please enter a valid ISO date (YYYY-MM-DD)."
            )
            return

        current_qty = int(batch.get("quantity_received") or 1)
        qty, qty_ok = QInputDialog.getInt(
            self,
            "Edit Batch",
            f"Quantity for {batch_label}:",
            current_qty,
            1,
            1000000,
            1,
        )
        if not qty_ok:
            return

        batch["date_received"] = parsed_date.isoformat()
        batch["quantity_received"] = qty
        self._refresh_batch_table()

    def _remove_selected_batch(self) -> None:
        """Remove selected batch in memory with movement guardrails."""
        row_idx = self._selected_batch_row()
        if row_idx is None or row_idx < 0 or row_idx >= len(self.batch_rows):
            QMessageBox.information(self, "No Selection", "Select a batch first.")
            return

        if len(self.batch_rows) <= 1:
            QMessageBox.warning(
                self, "Batch Required", "At least one batch must remain."
            )
            return

        batch = self.batch_rows[row_idx]
        movement_count = int(batch.get("movement_count") or 0)
        if movement_count > 0:
            QMessageBox.warning(
                self,
                "Cannot Remove Batch",
                "This batch has stock movement history and cannot be removed.",
            )
            return

        batch_label = f"B{int(batch.get('batch_number') or 0)}"
        confirm = QMessageBox.question(
            self,
            "Remove Batch",
            f"Remove {batch_label}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.batch_rows.pop(row_idx)
        self._refresh_batch_table()
