"""
Main inventory page that composes all inventory components.
Provides complete inventory management interface (Specs #1-21).
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QMessageBox, QSplitter, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from inventory_app.utils.logger import logger
from .inventory_controller import InventoryController
from .inventory_model import InventoryModel, ItemRow
from .inventory_table import InventoryTable
from .inventory_filters import InventoryFilters
from .inventory_stats import InventoryStats
from .item_editor import ItemEditor
from .alert_system import AlertSystem


class InventoryPage(QWidget):
    """Main inventory page widget using composition pattern."""

    # Signals for integration with main application
    item_selected = pyqtSignal(int)  # Item ID selected
    data_changed = pyqtSignal()      # Data was modified

    def __init__(self, parent=None):
        super().__init__(parent)

        # Initialize components using composition
        self.controller = InventoryController()
        self.model = InventoryModel()
        self.table = InventoryTable()
        self.filters = InventoryFilters()
        self.stats = InventoryStats()
        self.alert_system = AlertSystem()

        # Setup connections between components
        self._setup_connections()

        # Setup UI
        self.setup_ui()

        # Load initial data
        self.refresh_data()

        logger.info("Inventory page initialized with all components")

    def setup_ui(self):
        """Setup the main UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header with title and action buttons
        header_layout = QHBoxLayout()
        title = QLabel("📦 Inventory")
        title.setStyleSheet("font-size: 16pt; font-weight: bold;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        # Action buttons
        self.add_button = QPushButton("➕ Add Item")
        self.add_button.clicked.connect(self.add_item)

        self.edit_button = QPushButton("✏️ Edit Item")
        self.edit_button.clicked.connect(self.edit_selected_item)
        self.edit_button.setEnabled(False)

        self.delete_button = QPushButton("🗑️ Delete Item")
        self.delete_button.clicked.connect(self.delete_selected_item)
        self.delete_button.setEnabled(False)

        self.refresh_button = QPushButton("🔄 Refresh")
        self.refresh_button.clicked.connect(self.refresh_data)

        header_layout.addWidget(self.add_button)
        header_layout.addWidget(self.edit_button)
        header_layout.addWidget(self.delete_button)
        header_layout.addWidget(self.refresh_button)

        layout.addLayout(header_layout)

        # Main content area with splitter
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Top section: Filters and Stats
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addWidget(self.filters)
        top_layout.addWidget(self.stats)
        splitter.addWidget(top_widget)

        # Bottom section: Inventory table (now shows batches)
        table_group = QGroupBox("Inventory Batches")
        table_layout = QVBoxLayout(table_group)
        table_layout.addWidget(self.table)
        splitter.addWidget(table_group)

        # Set splitter proportions (30% top, 70% bottom)
        splitter.setSizes([300, 700])
        layout.addWidget(splitter)

    def _setup_connections(self):
        """Setup signal connections between components."""
        # Table selection changes
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)

        # Filter signals
        self.filters.search_changed.connect(self._on_search_changed)
        self.filters.category_filter_changed.connect(self._on_category_filter_changed)
        self.filters.supplier_filter_changed.connect(self._on_supplier_filter_changed)
        self.filters.clear_filters_requested.connect(self._on_clear_filters)

        # Table double-click for editing
        self.table.itemDoubleClicked.connect(self._on_table_double_click)

    def refresh_data(self):
        """Refresh all inventory data."""
        try:
            logger.info("Refreshing inventory data...")

            # Load data from database
            raw_data = self.controller.load_inventory_data()

            # Convert to ItemRow objects for model
            items = []
            for row in raw_data:
                item = ItemRow(
                    id=row.get('id'),
                    name=row.get('name', ''),
                    category_name=row.get('category_name', 'Uncategorized'),
                    size=row.get('size'),
                    brand=row.get('brand'),
                    supplier_name=row.get('supplier_name'),
                    other_specifications=row.get('other_specifications'),
                    po_number=row.get('po_number'),
                    expiration_date=self._parse_date(row.get('expiration_date')),
                    calibration_date=self._parse_date(row.get('calibration_date')),
                    acquisition_date=self._parse_date(row.get('acquisition_date')),
                    last_modified=self._parse_datetime(row.get('last_modified')),
                    is_consumable=bool(row.get('is_consumable', 1)),
                    alert_status=row.get('alert_status', '')
                )
                items.append(item)

            # Update model
            self.model.set_items(items)

            # Update table
            self.table.populate_table(raw_data)

            # Update filters
            categories = self.controller.get_categories()
            suppliers = self.controller.get_suppliers()
            self.filters.set_categories(categories)
            self.filters.set_suppliers(suppliers)

            # Update stats
            stats = self.model.get_statistics()
            self.stats.update_statistics(stats)

            logger.info(f"Refreshed inventory data: {len(items)} items loaded")

        except Exception as e:
            logger.error(f"Failed to refresh data: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load inventory data: {str(e)}")

    def add_item(self):
        """Add a new item."""
        try:
            dialog = ItemEditor(self)
            if dialog.exec() == ItemEditor.DialogCode.Accepted:
                logger.info("New item added")
                self.refresh_data()
                self.data_changed.emit()
        except Exception as e:
            logger.error(f"Failed to add item: {e}")
            QMessageBox.critical(self, "Error", f"Failed to add item: {str(e)}")

    def edit_selected_item(self):
        """Edit the currently selected item."""
        item_id = self.table.get_selected_item_id()
        if not item_id:
            QMessageBox.warning(self, "No Selection", "Please select an item to edit.")
            return

        try:
            dialog = ItemEditor(self, item_id)
            if dialog.exec() == ItemEditor.DialogCode.Accepted:
                logger.info(f"Item {item_id} edited")
                self.refresh_data()
                self.data_changed.emit()
        except Exception as e:
            logger.error(f"Failed to edit item {item_id}: {e}")
            QMessageBox.critical(self, "Error", f"Failed to edit item: {str(e)}")

    def delete_selected_item(self):
        """Delete the currently selected item."""
        item_id = self.table.get_selected_item_id()
        if not item_id:
            QMessageBox.warning(self, "No Selection", "Please select an item to delete.")
            return

        # Get item details for confirmation
        selected_items = self.model.get_filtered_items()
        selected_item = next((item for item in selected_items if item.id == item_id), None)

        if not selected_item:
            QMessageBox.warning(self, "Error", "Could not find selected item.")
            return

        # Confirm deletion
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete '{selected_item.name}'?\n\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            # Ask for editor name and reason (Spec #14, #16)
            editor_name, ok = QInputDialog.getText(self, "Editor Information",
                                                  "Enter your name/initials (required):")
            if not ok or not editor_name.strip():
                QMessageBox.warning(self, "Required", "Editor name is required.")
                return

            reason, ok = QInputDialog.getText(self, "Deletion Reason",
                                             "Reason for deletion:")
            if not ok:
                return

            # Delete the item
            from inventory_app.database.models import Item
            item = Item.get_by_id(item_id)
            if item and item.delete(editor_name.strip(), reason.strip() or "No reason provided"):
                logger.info(f"Item {item_id} deleted by {editor_name}")
                QMessageBox.information(self, "Success", "Item deleted successfully!")
                self.refresh_data()
                self.data_changed.emit()
            else:
                QMessageBox.critical(self, "Error", "Failed to delete item.")

        except Exception as e:
            logger.error(f"Failed to delete item {item_id}: {e}")
            QMessageBox.critical(self, "Error", f"Failed to delete item: {str(e)}")


    def _on_table_selection_changed(self):
        """Handle table selection changes."""
        has_selection = self.table.get_selected_item_id() is not None
        self.edit_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)

        if has_selection:
            item_id = self.table.get_selected_item_id()
            self.item_selected.emit(item_id)

    def _on_search_changed(self, search_term: str):
        """Handle search term changes."""
        self.model.filter_by_search(search_term)
        self._update_filtered_table()

    def _on_category_filter_changed(self, category: str):
        """Handle category filter changes."""
        self.model.filter_by_category(category)
        self._update_filtered_table()

    def _on_supplier_filter_changed(self, supplier: str):
        """Handle supplier filter changes."""
        self.model.filter_by_supplier(supplier)
        self._update_filtered_table()

    def _on_clear_filters(self):
        """Handle clear filters request."""
        self.model.clear_filters()
        self.refresh_data()

    def _on_table_double_click(self, item):
        """Handle table double-click for editing."""
        self.edit_selected_item()

    def _update_filtered_table(self):
        """Update table with current filtered data."""
        filtered_items = self.model.get_filtered_items()
        table_data = []
        for item in filtered_items:
            row = {
                'id': item.id,
                'name': item.name,
                'category_name': item.category_name,
                'size': item.size,
                'brand': item.brand,
                'supplier_name': item.supplier_name,
                'other_specifications': item.other_specifications,
                'po_number': item.po_number,
                'expiration_date': item.expiration_date.isoformat() if item.expiration_date else None,
                'calibration_date': item.calibration_date.isoformat() if item.calibration_date else None,
                'acquisition_date': item.acquisition_date.isoformat() if item.acquisition_date else None,
                'last_modified': item.last_modified.isoformat() if item.last_modified else None,
                'is_consumable': item.is_consumable,
                'alert_status': item.alert_status
            }
            table_data.append(row)

        self.table.populate_table(table_data)

    def _parse_date(self, date_str: Optional[str]):
        """Parse date string to date object."""
        if not date_str:
            return None
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(date_str)
            return dt.date()
        except (ValueError, TypeError):
            return None

    def _parse_datetime(self, datetime_str: Optional[str]):
        """Parse datetime string to datetime object."""
        if not datetime_str:
            return None
        try:
            from datetime import datetime
            return datetime.fromisoformat(datetime_str)
        except (ValueError, TypeError):
            return None
