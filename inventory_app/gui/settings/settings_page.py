"""
Settings page for managing combo box selections and preferences.
Allows editing sizes, brands, suppliers, and application preferences.
Categories are fixed and cannot be modified (defined in category_config.py).
"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTabWidget,
    QDialog,
    QLineEdit,
    QDialogButtonBox,
    QMessageBox,
    QLabel,
    QRadioButton,
    QButtonGroup,
    QGroupBox,
    QApplication,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
)
from PyQt6.QtCore import Qt

from inventory_app.database.models import Size, Brand, Supplier
from inventory_app.services.category_config import DEFAULT_CATEGORIES
from inventory_app.gui.styles import ThemeManager, DarkTheme, LightTheme


class SettingsPage(QWidget):
    """
    Settings page with tabs for managing sizes, brands, and suppliers.
    Categories are fixed and not editable through settings.
    """

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title = QLabel("⚙️ Settings")
        title.setStyleSheet("font-size: 18pt; font-weight: bold;")
        layout.addWidget(title)

        # Tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Preferences tab (first)
        self.create_preferences_tab()

        # Sizes tab
        self.create_sizes_tab()

        # Brands tab
        self.create_brands_tab()

        # Suppliers tab
        self.create_suppliers_tab()

        # Categories tab (read-only)
        self.create_categories_tab()

    def create_preferences_tab(self):
        """Create the preferences tab for theme selection."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(20)

        # Theme section
        theme_group = QGroupBox("Appearance")
        theme_layout = QVBoxLayout(theme_group)
        theme_layout.setSpacing(15)

        # Theme description
        theme_desc = QLabel("Choose your preferred theme for the application.")
        theme_desc.setWordWrap(True)
        theme_layout.addWidget(theme_desc)

        # Theme options
        self.theme_button_group = QButtonGroup(self)

        # Get current theme
        theme_manager = ThemeManager.instance()
        current_theme = theme_manager.current_theme

        # Dark mode option
        dark_option_widget = QWidget()
        dark_option_layout = QHBoxLayout(dark_option_widget)
        dark_option_layout.setContentsMargins(0, 0, 0, 0)

        self.dark_radio = QRadioButton()
        self.dark_radio.setChecked(current_theme == "dark")
        self.theme_button_group.addButton(self.dark_radio, 0)
        dark_option_layout.addWidget(self.dark_radio)

        dark_info = QWidget()
        dark_info_layout = QVBoxLayout(dark_info)
        dark_info_layout.setContentsMargins(0, 0, 0, 0)
        dark_info_layout.setSpacing(2)

        dark_title = QLabel("🌙 Dark Mode")
        dark_title.setStyleSheet("font-weight: bold; font-size: 11pt;")
        dark_info_layout.addWidget(dark_title)

        dark_desc = QLabel(
            "Dark background with purple accent colors. Easier on the eyes in low-light environments."
        )
        dark_desc.setWordWrap(True)
        dark_desc.setStyleSheet("color: gray;")
        dark_info_layout.addWidget(dark_desc)

        # Dark mode preview colors
        dark_preview = QWidget()
        dark_preview_layout = QHBoxLayout(dark_preview)
        dark_preview_layout.setContentsMargins(0, 5, 0, 0)
        dark_preview_layout.setSpacing(5)

        for color in [
            DarkTheme.PRIMARY_DARK,
            DarkTheme.SECONDARY_DARK,
            DarkTheme.ACCENT_COLOR,
            DarkTheme.ACCENT_HOVER,
        ]:
            color_box = QLabel()
            color_box.setFixedSize(24, 24)
            color_box.setStyleSheet(
                f"background-color: {color}; border: 1px solid #555; border-radius: 4px;"
            )
            dark_preview_layout.addWidget(color_box)
        dark_preview_layout.addStretch()
        dark_info_layout.addWidget(dark_preview)

        dark_option_layout.addWidget(dark_info)
        dark_option_layout.addStretch()
        theme_layout.addWidget(dark_option_widget)

        # Light mode option
        light_option_widget = QWidget()
        light_option_layout = QHBoxLayout(light_option_widget)
        light_option_layout.setContentsMargins(0, 0, 0, 0)

        self.light_radio = QRadioButton()
        self.light_radio.setChecked(current_theme == "light")
        self.theme_button_group.addButton(self.light_radio, 1)
        light_option_layout.addWidget(self.light_radio)

        light_info = QWidget()
        light_info_layout = QVBoxLayout(light_info)
        light_info_layout.setContentsMargins(0, 0, 0, 0)
        light_info_layout.setSpacing(2)

        light_title = QLabel("☀️ Light Mode")
        light_title.setStyleSheet("font-weight: bold; font-size: 11pt;")
        light_info_layout.addWidget(light_title)

        light_desc = QLabel(
            "Light background with green accent colors. Better visibility in bright environments."
        )
        light_desc.setWordWrap(True)
        light_desc.setStyleSheet("color: gray;")
        light_info_layout.addWidget(light_desc)

        # Light mode preview colors
        light_preview = QWidget()
        light_preview_layout = QHBoxLayout(light_preview)
        light_preview_layout.setContentsMargins(0, 5, 0, 0)
        light_preview_layout.setSpacing(5)

        for color in [
            LightTheme.PRIMARY_DARK,
            LightTheme.SECONDARY_DARK,
            LightTheme.ACCENT_COLOR,
            LightTheme.ACCENT_HOVER,
        ]:
            color_box = QLabel()
            color_box.setFixedSize(24, 24)
            color_box.setStyleSheet(
                f"background-color: {color}; border: 1px solid #ccc; border-radius: 4px;"
            )
            light_preview_layout.addWidget(color_box)
        light_preview_layout.addStretch()
        light_info_layout.addWidget(light_preview)

        light_option_layout.addWidget(light_info)
        light_option_layout.addStretch()
        theme_layout.addWidget(light_option_widget)

        # Connect theme change
        self.theme_button_group.buttonClicked.connect(self.on_theme_changed)

        layout.addWidget(theme_group)

        # Restart notice
        self.restart_notice = QLabel(
            "⚠️ RESTART REQUIRED: Close and reopen the app to fully apply theme colors."
        )
        self.restart_notice.setStyleSheet(
            "color: #92400e; background-color: #fef3c7; border: 1px solid #f59e0b; border-radius: 4px; padding: 10px; font-weight: bold;"
        )
        self.restart_notice.setVisible(False)
        layout.addWidget(self.restart_notice)

        layout.addStretch()

        self.tab_widget.addTab(tab, "Preferences")

    def on_theme_changed(self, button):
        """Handle theme selection change."""
        theme_manager = ThemeManager.instance()

        if button == self.dark_radio:
            new_theme = "dark"
        else:
            new_theme = "light"

        if new_theme != theme_manager.current_theme:
            theme_manager.current_theme = new_theme
            self.restart_notice.setVisible(True)

            # Apply theme immediately
            app = QApplication.instance()
            if app and isinstance(app, QApplication):
                theme_manager.apply_theme(app)

            QMessageBox.warning(
                self,
                "Theme Changed - Restart Required",
                f"Theme changed to {new_theme.title()} Mode.\n\n"
                "Restart the application now to fully update all pages.\n"
                "If you continue without restart, some screens may still show old colors.",
            )

    def create_sizes_tab(self):
        """Create the sizes management tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Table
        self.sizes_table = self._create_reference_table()
        self.sizes_table.cellDoubleClicked.connect(lambda *_: self.edit_size())
        layout.addWidget(self.sizes_table)

        # Buttons
        button_layout = QHBoxLayout()
        add_btn = QPushButton("Add Size")
        add_btn.clicked.connect(self.add_size)
        button_layout.addWidget(add_btn)

        edit_btn = QPushButton("Edit Size")
        edit_btn.clicked.connect(self.edit_size)
        button_layout.addWidget(edit_btn)

        self.delete_size_btn = QPushButton("Delete Size")
        self.delete_size_btn.clicked.connect(self.delete_size)
        self.delete_size_btn.setEnabled(False)
        button_layout.addWidget(self.delete_size_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        self.size_usage_label = QLabel("Select a size to view usage status.")
        self.size_usage_label.setWordWrap(True)
        layout.addWidget(self.size_usage_label)

        self.sizes_table.itemSelectionChanged.connect(self.on_size_selection_changed)
        self.populate_sizes_list()

        self.tab_widget.addTab(tab, "Sizes")

    def create_brands_tab(self):
        """Create the brands management tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Table
        self.brands_table = self._create_reference_table()
        self.brands_table.cellDoubleClicked.connect(lambda *_: self.edit_brand())
        layout.addWidget(self.brands_table)

        # Buttons
        button_layout = QHBoxLayout()
        add_btn = QPushButton("Add Brand")
        add_btn.clicked.connect(self.add_brand)
        button_layout.addWidget(add_btn)

        edit_btn = QPushButton("Edit Brand")
        edit_btn.clicked.connect(self.edit_brand)
        button_layout.addWidget(edit_btn)

        self.delete_brand_btn = QPushButton("Delete Brand")
        self.delete_brand_btn.clicked.connect(self.delete_brand)
        self.delete_brand_btn.setEnabled(False)
        button_layout.addWidget(self.delete_brand_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        self.brand_usage_label = QLabel("Select a brand to view usage status.")
        self.brand_usage_label.setWordWrap(True)
        layout.addWidget(self.brand_usage_label)

        self.brands_table.itemSelectionChanged.connect(self.on_brand_selection_changed)
        self.populate_brands_list()

        self.tab_widget.addTab(tab, "Brands")

    def create_suppliers_tab(self):
        """Create the suppliers management tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Table
        self.suppliers_table = self._create_reference_table()
        self.suppliers_table.cellDoubleClicked.connect(lambda *_: self.edit_supplier())
        layout.addWidget(self.suppliers_table)

        # Buttons
        button_layout = QHBoxLayout()
        add_btn = QPushButton("Add Supplier")
        add_btn.clicked.connect(self.add_supplier)
        button_layout.addWidget(add_btn)

        edit_btn = QPushButton("Edit Supplier")
        edit_btn.clicked.connect(self.edit_supplier)
        button_layout.addWidget(edit_btn)

        self.delete_supplier_btn = QPushButton("Delete Supplier")
        self.delete_supplier_btn.clicked.connect(self.delete_supplier)
        self.delete_supplier_btn.setEnabled(False)
        button_layout.addWidget(self.delete_supplier_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        self.supplier_usage_label = QLabel("Select a supplier to view usage status.")
        self.supplier_usage_label.setWordWrap(True)
        layout.addWidget(self.supplier_usage_label)

        self.suppliers_table.itemSelectionChanged.connect(
            self.on_supplier_selection_changed
        )
        self.populate_suppliers_list()

        self.tab_widget.addTab(tab, "Suppliers")

    def create_categories_tab(self):
        """Create a read-only categories tab with lifecycle rules."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        intro = QLabel(
            "Categories are fixed system values and are used to drive item lifecycle calculations."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        categories_table = QTableWidget(len(DEFAULT_CATEGORIES), 4)
        categories_table.setHorizontalHeaderLabels(
            ["Category", "Item Type", "Lifecycle Rule", "Calibration"]
        )
        categories_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        categories_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)

        for row, category in enumerate(DEFAULT_CATEGORIES):
            is_special_no_type = category.name in {"Others", "Uncategorized"}
            item_type = (
                "N/A"
                if is_special_no_type
                else "Consumable"
                if category.is_consumable
                else "Non-consumable"
            )
            if category.expiry_months:
                lifecycle_rule = (
                    f"Expiration = acquisition + {category.expiry_months} months"
                )
            elif category.disposal_years:
                lifecycle_rule = (
                    f"Disposal = acquisition + {category.disposal_years} years"
                )
            else:
                lifecycle_rule = "No auto lifecycle date"

            calibration = "Yearly" if category.has_calibration else "No"

            categories_table.setItem(row, 0, QTableWidgetItem(category.name))
            categories_table.setItem(row, 1, QTableWidgetItem(item_type))
            categories_table.setItem(row, 2, QTableWidgetItem(lifecycle_rule))
            categories_table.setItem(row, 3, QTableWidgetItem(calibration))

        categories_table.resizeColumnsToContents()
        header = categories_table.horizontalHeader()
        if header is not None:
            header.setStretchLastSection(True)
        layout.addWidget(categories_table, 1)

        note = QLabel(
            "these categories are fixed and is essential on how an item's lifecycle is categorized. changing or adding categories would require a calculation of it's lifecycle and and other core functions to become a proper item category."
        )
        note.setWordWrap(True)
        note.setStyleSheet(
            "background-color: #fef3c7; border: 1px solid #f59e0b; border-radius: 4px; padding: 10px; color: #1f2937; font-weight: 500;"
        )
        layout.addWidget(note)
        self.tab_widget.addTab(tab, "Categories")

    def _create_reference_table(self) -> QTableWidget:
        """Create a shared table layout for settings reference data."""
        table = QTableWidget(0, 3)
        table.setHorizontalHeaderLabels(["Name", "Usage", "Status"])
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setAlternatingRowColors(True)
        vertical_header = table.verticalHeader()
        if vertical_header is not None:
            vertical_header.setVisible(False)

        header = table.horizontalHeader()
        if header is not None:
            header.setStretchLastSection(False)
            header.setSectionResizeMode(0, header.ResizeMode.Stretch)
            header.setSectionResizeMode(1, header.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(2, header.ResizeMode.ResizeToContents)
        return table

    @staticmethod
    def _selected_reference_data(table: QTableWidget):
        """Return selected row metadata for a settings table."""
        selected_items = table.selectedItems()
        if not selected_items:
            return None

        row = selected_items[0].row()
        name_item = table.item(row, 0)
        if name_item is None:
            return None
        return name_item.data(Qt.ItemDataRole.UserRole) or {}

    def populate_sizes_list(self):
        """Populate the sizes list."""
        self.sizes_table.setRowCount(0)
        sizes = Size.get_all()
        for s in sizes:
            usage_count = s.get_usage_count()
            row = self.sizes_table.rowCount()
            self.sizes_table.insertRow(row)

            name_item = QTableWidgetItem(s.name)
            usage_item = QTableWidgetItem(f"{usage_count} item(s)")
            status_item = QTableWidgetItem(
                "NON-DELETABLE" if usage_count > 0 else "Unused"
            )

            name_item.setData(
                Qt.ItemDataRole.UserRole,
                {"id": s.id, "name": s.name, "usage_count": usage_count},
            )

            self.sizes_table.setItem(row, 0, name_item)
            self.sizes_table.setItem(row, 1, usage_item)
            self.sizes_table.setItem(row, 2, status_item)

            if usage_count > 0:
                muted = self.palette().color(self.foregroundRole()).darker(150)
                name_item.setForeground(muted)
                usage_item.setForeground(muted)
                status_item.setForeground(muted)

        if self.sizes_table.rowCount() > 0:
            self.sizes_table.selectRow(0)
        else:
            self.on_size_selection_changed()

    def populate_brands_list(self):
        """Populate the brands list."""
        self.brands_table.setRowCount(0)
        brands = Brand.get_all()
        for b in brands:
            usage_count = b.get_usage_count()
            row = self.brands_table.rowCount()
            self.brands_table.insertRow(row)

            name_item = QTableWidgetItem(b.name)
            usage_item = QTableWidgetItem(f"{usage_count} item(s)")
            status_item = QTableWidgetItem(
                "NON-DELETABLE" if usage_count > 0 else "Unused"
            )

            name_item.setData(
                Qt.ItemDataRole.UserRole,
                {"id": b.id, "name": b.name, "usage_count": usage_count},
            )

            self.brands_table.setItem(row, 0, name_item)
            self.brands_table.setItem(row, 1, usage_item)
            self.brands_table.setItem(row, 2, status_item)

            if usage_count > 0:
                muted = self.palette().color(self.foregroundRole()).darker(150)
                name_item.setForeground(muted)
                usage_item.setForeground(muted)
                status_item.setForeground(muted)

        if self.brands_table.rowCount() > 0:
            self.brands_table.selectRow(0)
        else:
            self.on_brand_selection_changed()

    def populate_suppliers_list(self):
        """Populate the suppliers list."""
        self.suppliers_table.setRowCount(0)
        suppliers = Supplier.get_all()
        for s in suppliers:
            usage_count = s.get_usage_count()
            row = self.suppliers_table.rowCount()
            self.suppliers_table.insertRow(row)

            name_item = QTableWidgetItem(s.name)
            usage_item = QTableWidgetItem(f"{usage_count} item(s)")
            status_item = QTableWidgetItem(
                "NON-DELETABLE" if usage_count > 0 else "Unused"
            )

            name_item.setData(
                Qt.ItemDataRole.UserRole,
                {"id": s.id, "name": s.name, "usage_count": usage_count},
            )

            self.suppliers_table.setItem(row, 0, name_item)
            self.suppliers_table.setItem(row, 1, usage_item)
            self.suppliers_table.setItem(row, 2, status_item)

            if usage_count > 0:
                muted = self.palette().color(self.foregroundRole()).darker(150)
                name_item.setForeground(muted)
                usage_item.setForeground(muted)
                status_item.setForeground(muted)

        if self.suppliers_table.rowCount() > 0:
            self.suppliers_table.selectRow(0)
        else:
            self.on_supplier_selection_changed()

    def on_size_selection_changed(self):
        """Update delete state and usage helper text for size selection."""
        data = self._selected_reference_data(self.sizes_table)
        if not data:
            self.delete_size_btn.setEnabled(False)
            self.size_usage_label.setText("Select a size to view usage status.")
            return

        usage_count = data.get("usage_count", 0)
        name = data.get("name", "")
        self.delete_size_btn.setEnabled(usage_count == 0)
        if usage_count > 0:
            self.size_usage_label.setText(
                f"'{name}' is currently used by {usage_count} item(s) and cannot be deleted."
            )
        else:
            self.size_usage_label.setText(f"'{name}' is unused and can be deleted.")

    def on_brand_selection_changed(self):
        """Update delete state and usage helper text for brand selection."""
        data = self._selected_reference_data(self.brands_table)
        if not data:
            self.delete_brand_btn.setEnabled(False)
            self.brand_usage_label.setText("Select a brand to view usage status.")
            return

        usage_count = data.get("usage_count", 0)
        name = data.get("name", "")
        self.delete_brand_btn.setEnabled(usage_count == 0)
        if usage_count > 0:
            self.brand_usage_label.setText(
                f"'{name}' is currently used by {usage_count} item(s) and cannot be deleted."
            )
        else:
            self.brand_usage_label.setText(f"'{name}' is unused and can be deleted.")

    def on_supplier_selection_changed(self):
        """Update delete state and usage helper text for supplier selection."""
        data = self._selected_reference_data(self.suppliers_table)
        if not data:
            self.delete_supplier_btn.setEnabled(False)
            self.supplier_usage_label.setText("Select a supplier to view usage status.")
            return

        usage_count = data.get("usage_count", 0)
        name = data.get("name", "")
        self.delete_supplier_btn.setEnabled(usage_count == 0)
        if usage_count > 0:
            self.supplier_usage_label.setText(
                f"'{name}' is currently used by {usage_count} item(s) and cannot be deleted."
            )
        else:
            self.supplier_usage_label.setText(f"'{name}' is unused and can be deleted.")

    def add_size(self):
        """Add a new size."""
        dialog = NameDialog("Add Size", self)
        if dialog.exec():
            name = dialog.get_name()
            if name:
                size = Size(name=name)
                success, message = size.save()
                if success:
                    self.populate_sizes_list()
                    QMessageBox.information(self, "Success", "Size added successfully!")
                else:
                    QMessageBox.critical(self, "Error", message)

    def edit_size(self):
        """Edit the selected size."""
        data = self._selected_reference_data(self.sizes_table)
        if not data:
            QMessageBox.warning(self, "Warning", "Please select a size to edit")
            return

        old_name = data.get("name", "")
        dialog = NameDialog("Edit Size", self, old_name)
        if dialog.exec():
            new_name = dialog.get_name()
            if new_name and new_name != old_name:
                sizes = Size.get_all()
                size_to_edit = next((s for s in sizes if s.name == old_name), None)
                if size_to_edit:
                    size_to_edit.name = new_name
                    success, message = size_to_edit.save()
                    if success:
                        self.populate_sizes_list()
                        QMessageBox.information(
                            self, "Success", "Size updated successfully!"
                        )
                    else:
                        QMessageBox.critical(self, "Error", message)

    def delete_size(self):
        """Delete the selected size."""
        data = self._selected_reference_data(self.sizes_table)
        if not data:
            QMessageBox.warning(self, "Warning", "Please select a size to delete")
            return

        name = data.get("name", "")
        usage_count = data.get("usage_count", 0)
        if usage_count > 0:
            QMessageBox.warning(
                self,
                "Cannot Delete",
                f"Cannot delete size '{name}' because it is currently being used by {usage_count} item(s).",
            )
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete size '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            sizes = Size.get_all()
            size_to_delete = next((s for s in sizes if s.name == name), None)
            if size_to_delete:
                success, message, _ = size_to_delete.delete()
                if success:
                    self.populate_sizes_list()
                    QMessageBox.information(
                        self, "Success", "Size deleted successfully!"
                    )
                else:
                    QMessageBox.warning(self, "Cannot Delete", message)

    def add_brand(self):
        """Add a new brand."""
        dialog = NameDialog("Add Brand", self)
        if dialog.exec():
            name = dialog.get_name()
            if name:
                brand = Brand(name=name)
                success, message = brand.save()
                if success:
                    self.populate_brands_list()
                    QMessageBox.information(
                        self, "Success", "Brand added successfully!"
                    )
                else:
                    QMessageBox.critical(self, "Error", message)

    def edit_brand(self):
        """Edit the selected brand."""
        data = self._selected_reference_data(self.brands_table)
        if not data:
            QMessageBox.warning(self, "Warning", "Please select a brand to edit")
            return

        old_name = data.get("name", "")
        dialog = NameDialog("Edit Brand", self, old_name)
        if dialog.exec():
            new_name = dialog.get_name()
            if new_name and new_name != old_name:
                brands = Brand.get_all()
                brand_to_edit = next((b for b in brands if b.name == old_name), None)
                if brand_to_edit:
                    brand_to_edit.name = new_name
                    success, message = brand_to_edit.save()
                    if success:
                        self.populate_brands_list()
                        QMessageBox.information(
                            self, "Success", "Brand updated successfully!"
                        )
                    else:
                        QMessageBox.critical(self, "Error", message)

    def delete_brand(self):
        """Delete the selected brand."""
        data = self._selected_reference_data(self.brands_table)
        if not data:
            QMessageBox.warning(self, "Warning", "Please select a brand to delete")
            return

        name = data.get("name", "")
        usage_count = data.get("usage_count", 0)
        if usage_count > 0:
            QMessageBox.warning(
                self,
                "Cannot Delete",
                f"Cannot delete brand '{name}' because it is currently being used by {usage_count} item(s).",
            )
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete brand '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            brands = Brand.get_all()
            brand_to_delete = next((b for b in brands if b.name == name), None)
            if brand_to_delete:
                success, message, _ = brand_to_delete.delete()
                if success:
                    self.populate_brands_list()
                    QMessageBox.information(
                        self, "Success", "Brand deleted successfully!"
                    )
                else:
                    QMessageBox.warning(self, "Cannot Delete", message)

    def add_supplier(self):
        """Add a new supplier."""
        dialog = NameDialog("Add Supplier", self)
        if dialog.exec():
            name = dialog.get_name()
            if name:
                supplier = Supplier(name=name)
                success, message = supplier.save()
                if success:
                    self.populate_suppliers_list()
                    QMessageBox.information(
                        self, "Success", "Supplier added successfully!"
                    )
                else:
                    QMessageBox.critical(self, "Error", message)

    def edit_supplier(self):
        """Edit the selected supplier."""
        data = self._selected_reference_data(self.suppliers_table)
        if not data:
            QMessageBox.warning(self, "Warning", "Please select a supplier to edit")
            return

        old_name = data.get("name", "")
        dialog = NameDialog("Edit Supplier", self, old_name)
        if dialog.exec():
            new_name = dialog.get_name()
            if new_name and new_name != old_name:
                suppliers = Supplier.get_all()
                supplier_to_edit = next(
                    (s for s in suppliers if s.name == old_name), None
                )
                if supplier_to_edit:
                    supplier_to_edit.name = new_name
                    success, message = supplier_to_edit.save()
                    if success:
                        self.populate_suppliers_list()
                        QMessageBox.information(
                            self, "Success", "Supplier updated successfully!"
                        )
                    else:
                        QMessageBox.critical(self, "Error", message)

    def delete_supplier(self):
        """Delete the selected supplier if it is not used by any item."""
        data = self._selected_reference_data(self.suppliers_table)
        if not data:
            QMessageBox.warning(self, "Warning", "Please select a supplier to delete")
            return

        name = data.get("name", "")
        usage_count = data.get("usage_count", 0)
        if usage_count > 0:
            QMessageBox.warning(
                self,
                "Cannot Delete",
                f"Cannot delete supplier '{name}' because it is currently being used by {usage_count} item(s).",
            )
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete supplier '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            suppliers = Supplier.get_all()
            supplier_to_delete = next((s for s in suppliers if s.name == name), None)
            if supplier_to_delete:
                success, message, _ = supplier_to_delete.delete()

                if success:
                    self.populate_suppliers_list()
                    QMessageBox.information(
                        self, "Success", "Supplier deleted successfully!"
                    )
                else:
                    QMessageBox.warning(self, "Cannot Delete", message)


class NameDialog(QDialog):
    """
    Simple dialog for entering a name.
    """

    def __init__(self, title, parent=None, initial_name=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        self.name_edit = QLineEdit()
        self.name_edit.setText(initial_name)
        layout.addWidget(self.name_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_name(self):
        """Get the entered name."""
        return self.name_edit.text().strip()
