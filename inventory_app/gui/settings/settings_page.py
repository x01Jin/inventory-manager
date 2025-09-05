"""
Settings page for managing combo box selections.
Allows editing sizes, brands, and suppliers.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
    QTabWidget, QDialog, QLineEdit, QDialogButtonBox, QMessageBox, QLabel
)

from inventory_app.database.models import Size, Brand, Supplier, Category


class SettingsPage(QWidget):
    """
    Settings page with tabs for managing sizes, brands, and suppliers.
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
        title = QLabel("Settings")
        title.setStyleSheet("font-size: 18pt; font-weight: bold;")
        layout.addWidget(title)

        # Tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Sizes tab
        self.create_sizes_tab()

        # Brands tab
        self.create_brands_tab()

        # Suppliers tab
        self.create_suppliers_tab()

        # Categories tab
        self.create_categories_tab()

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

    def create_categories_tab(self):
        """Create the categories management tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # List
        self.categories_list = QListWidget()
        self.populate_categories_list()
        layout.addWidget(self.categories_list)

        # Buttons
        button_layout = QHBoxLayout()
        add_btn = QPushButton("Add Category")
        add_btn.clicked.connect(self.add_category)
        button_layout.addWidget(add_btn)

        edit_btn = QPushButton("Edit Category")
        edit_btn.clicked.connect(self.edit_category)
        button_layout.addWidget(edit_btn)

        delete_btn = QPushButton("Delete Category")
        delete_btn.clicked.connect(self.delete_category)
        button_layout.addWidget(delete_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        self.tab_widget.addTab(tab, "Categories")

    def populate_categories_list(self):
        """Populate the categories list."""
        self.categories_list.clear()
        categories = Category.get_all()
        for c in categories:
            self.categories_list.addItem(c.name)

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
                if size.save():
                    self.populate_sizes_list()
                    QMessageBox.information(self, "Success", "Size added successfully!")
                else:
                    QMessageBox.critical(self, "Error", "Failed to add size")

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
                    if size_to_edit.save():
                        self.populate_sizes_list()
                        QMessageBox.information(self, "Success", "Size updated successfully!")
                    else:
                        QMessageBox.critical(self, "Error", "Failed to update size")

    def delete_size(self):
        """Delete the selected size."""
        current_item = self.sizes_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a size to delete")
            return

        name = current_item.text()
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete size '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            sizes = Size.get_all()
            size_to_delete = next((s for s in sizes if s.name == name), None)
            if size_to_delete:
                if size_to_delete.delete():
                    self.populate_sizes_list()
                    QMessageBox.information(self, "Success", "Size deleted successfully!")
                else:
                    QMessageBox.critical(self, "Error", "Failed to delete size")

    def add_brand(self):
        """Add a new brand."""
        dialog = NameDialog("Add Brand", self)
        if dialog.exec():
            name = dialog.get_name()
            if name:
                brand = Brand(name=name)
                if brand.save():
                    self.populate_brands_list()
                    QMessageBox.information(self, "Success", "Brand added successfully!")
                else:
                    QMessageBox.critical(self, "Error", "Failed to add brand")

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
                    if brand_to_edit.save():
                        self.populate_brands_list()
                        QMessageBox.information(self, "Success", "Brand updated successfully!")
                    else:
                        QMessageBox.critical(self, "Error", "Failed to update brand")

    def delete_brand(self):
        """Delete the selected brand."""
        current_item = self.brands_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a brand to delete")
            return

        name = current_item.text()
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete brand '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            brands = Brand.get_all()
            brand_to_delete = next((b for b in brands if b.name == name), None)
            if brand_to_delete:
                if brand_to_delete.delete():
                    self.populate_brands_list()
                    QMessageBox.information(self, "Success", "Brand deleted successfully!")
                else:
                    QMessageBox.critical(self, "Error", "Failed to delete brand")

    def add_supplier(self):
        """Add a new supplier."""
        dialog = NameDialog("Add Supplier", self)
        if dialog.exec():
            name = dialog.get_name()
            if name:
                supplier = Supplier(name=name)
                if supplier.save():
                    self.populate_suppliers_list()
                    QMessageBox.information(self, "Success", "Supplier added successfully!")
                else:
                    QMessageBox.critical(self, "Error", "Failed to add supplier")

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
                supplier_to_edit = next((s for s in suppliers if s.name == old_name), None)
                if supplier_to_edit:
                    supplier_to_edit.name = new_name
                    if supplier_to_edit.save():
                        self.populate_suppliers_list()
                        QMessageBox.information(self, "Success", "Supplier updated successfully!")
                    else:
                        QMessageBox.critical(self, "Error", "Failed to update supplier")

    def delete_supplier(self):
        """Delete the selected supplier."""
        current_item = self.suppliers_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a supplier to delete")
            return

        name = current_item.text()
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete supplier '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            suppliers = Supplier.get_all()
            supplier_to_delete = next((s for s in suppliers if s.name == name), None)
            if supplier_to_delete:
                if supplier_to_delete.delete():
                    self.populate_suppliers_list()
                    QMessageBox.information(self, "Success", "Supplier deleted successfully!")
                else:
                    QMessageBox.critical(self, "Error", "Failed to delete supplier")

    def add_category(self):
        """Add a new category."""
        dialog = NameDialog("Add Category", self)
        if dialog.exec():
            name = dialog.get_name()
            if name:
                category = Category(name=name)
                if category.save():
                    self.populate_categories_list()
                    QMessageBox.information(self, "Success", "Category added successfully!")
                else:
                    QMessageBox.critical(self, "Error", "Failed to add category")

    def edit_category(self):
        """Edit the selected category."""
        current_item = self.categories_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a category to edit")
            return

        old_name = current_item.text()
        dialog = NameDialog("Edit Category", self, old_name)
        if dialog.exec():
            new_name = dialog.get_name()
            if new_name and new_name != old_name:
                categories = Category.get_all()
                category_to_edit = next((c for c in categories if c.name == old_name), None)
                if category_to_edit:
                    category_to_edit.name = new_name
                    if category_to_edit.save():
                        self.populate_categories_list()
                        QMessageBox.information(self, "Success", "Category updated successfully!")
                    else:
                        QMessageBox.critical(self, "Error", "Failed to update category")

    def delete_category(self):
        """Delete the selected category."""
        current_item = self.categories_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a category to delete")
            return

        name = current_item.text()
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete category '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            categories = Category.get_all()
            category_to_delete = next((c for c in categories if c.name == name), None)
            if category_to_delete:
                if category_to_delete.delete():
                    self.populate_categories_list()
                    QMessageBox.information(self, "Success", "Category deleted successfully!")
                else:
                    QMessageBox.critical(self, "Error", "Failed to delete category")

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
