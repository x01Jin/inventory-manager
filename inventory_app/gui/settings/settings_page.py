"""
Settings page for managing combo box selections and preferences.
Allows editing sizes, brands, suppliers, and application preferences.
Categories are fixed and cannot be modified (defined in category_config.py).
"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
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
)

from inventory_app.database.models import Size, Brand, Supplier
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
            "⚠️ Theme changes will take effect after restarting the application."
        )
        self.restart_notice.setStyleSheet(
            "color: #f59e0b; padding: 10px; font-style: italic;"
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

            QMessageBox.information(
                self,
                "Theme Changed",
                f"Theme has been changed to {new_theme.title()} Mode.\n\n"
                "The theme has been applied. Some UI elements may require "
                "a restart to fully update.",
            )

    def create_sizes_tab(self):
        """Create the sizes management tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # List
        self.sizes_list = QListWidget()
        self.populate_sizes_list()
        layout.addWidget(self.sizes_list)

        # Buttons
        button_layout = QHBoxLayout()
        add_btn = QPushButton("Add Size")
        add_btn.clicked.connect(self.add_size)
        button_layout.addWidget(add_btn)

        edit_btn = QPushButton("Edit Size")
        edit_btn.clicked.connect(self.edit_size)
        button_layout.addWidget(edit_btn)

        delete_btn = QPushButton("Delete Size")
        delete_btn.clicked.connect(self.delete_size)
        button_layout.addWidget(delete_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        self.tab_widget.addTab(tab, "Sizes")

    def create_brands_tab(self):
        """Create the brands management tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # List
        self.brands_list = QListWidget()
        self.populate_brands_list()
        layout.addWidget(self.brands_list)

        # Buttons
        button_layout = QHBoxLayout()
        add_btn = QPushButton("Add Brand")
        add_btn.clicked.connect(self.add_brand)
        button_layout.addWidget(add_btn)

        edit_btn = QPushButton("Edit Brand")
        edit_btn.clicked.connect(self.edit_brand)
        button_layout.addWidget(edit_btn)

        delete_btn = QPushButton("Delete Brand")
        delete_btn.clicked.connect(self.delete_brand)
        button_layout.addWidget(delete_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        self.tab_widget.addTab(tab, "Brands")

    def create_suppliers_tab(self):
        """Create the suppliers management tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # List
        self.suppliers_list = QListWidget()
        self.populate_suppliers_list()
        layout.addWidget(self.suppliers_list)

        # Buttons
        button_layout = QHBoxLayout()
        add_btn = QPushButton("Add Supplier")
        add_btn.clicked.connect(self.add_supplier)
        button_layout.addWidget(add_btn)

        edit_btn = QPushButton("Edit Supplier")
        edit_btn.clicked.connect(self.edit_supplier)
        button_layout.addWidget(edit_btn)

        delete_btn = QPushButton("Delete Supplier")
        delete_btn.clicked.connect(self.delete_supplier)
        button_layout.addWidget(delete_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        self.tab_widget.addTab(tab, "Suppliers")

    def populate_sizes_list(self):
        """Populate the sizes list."""
        self.sizes_list.clear()
        sizes = Size.get_all()
        for s in sizes:
            self.sizes_list.addItem(s.name)

    def populate_brands_list(self):
        """Populate the brands list."""
        self.brands_list.clear()
        brands = Brand.get_all()
        for b in brands:
            self.brands_list.addItem(b.name)

    def populate_suppliers_list(self):
        """Populate the suppliers list."""
        self.suppliers_list.clear()
        suppliers = Supplier.get_all()
        for s in suppliers:
            self.suppliers_list.addItem(s.name)

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
        current_item = self.sizes_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a size to edit")
            return

        old_name = current_item.text()
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
        current_item = self.sizes_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a size to delete")
            return

        name = current_item.text()
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
                if size_to_delete.delete():
                    self.populate_sizes_list()
                    QMessageBox.information(
                        self, "Success", "Size deleted successfully!"
                    )
                else:
                    # Provide informative error message about why deletion failed
                    QMessageBox.warning(
                        self,
                        "Cannot Delete",
                        f"Cannot delete size '{name}' because it is currently being used by one or more items.\n\n"
                        "Please remove this size from all items before deleting it.",
                    )

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
        current_item = self.brands_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a brand to edit")
            return

        old_name = current_item.text()
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
        current_item = self.brands_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a brand to delete")
            return

        name = current_item.text()
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
                if brand_to_delete.delete():
                    self.populate_brands_list()
                    QMessageBox.information(
                        self, "Success", "Brand deleted successfully!"
                    )
                else:
                    # Provide informative error message about why deletion failed
                    QMessageBox.warning(
                        self,
                        "Cannot Delete",
                        f"Cannot delete brand '{name}' because it is currently being used by one or more items.\n\n"
                        "Please remove this brand from all items before deleting it.",
                    )

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
        current_item = self.suppliers_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a supplier to edit")
            return

        old_name = current_item.text()
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
        """Delete the selected supplier."""
        current_item = self.suppliers_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a supplier to delete")
            return

        name = current_item.text()
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
                if supplier_to_delete.delete():
                    self.populate_suppliers_list()
                    QMessageBox.information(
                        self, "Success", "Supplier deleted successfully!"
                    )
                else:
                    # Provide informative error message about why deletion failed
                    QMessageBox.warning(
                        self,
                        "Cannot Delete",
                        f"Cannot delete supplier '{name}' because it is currently being used by one or more items.\n\n"
                        "Please remove this supplier from all items before deleting it.",
                    )


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
