"""
Main inventory page that composes all inventory components.
Provides complete inventory management interface (Specs #1-21).

Uses background threading via QThreadPool for data loading to prevent
UI freezes on slower hardware.
"""

from typing import Optional, List, Dict, Any
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGroupBox,
    QMessageBox,
    QSplitter,
    QInputDialog,
    QProgressBar,
    QApplication,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from inventory_app.utils.logger import logger
from inventory_app.gui.utils.worker import run_in_background, Worker
from .inventory_controller import InventoryController
from .inventory_model import InventoryModel, ItemRow
from .inventory_table import InventoryTable
from .inventory_filters import InventoryFilters
from .inventory_stats import InventoryStats
from .item_editor import ItemEditor
from .import_dialog import ImportItemsDialog


class InventoryPage(QWidget):
    """Main inventory page widget using composition pattern with async loading."""

    # Signals for integration with main application
    item_selected = pyqtSignal(int)  # Item ID selected
    data_changed = pyqtSignal()  # Data was modified

    def __init__(self, parent=None):
        super().__init__(parent)

        # Initialize components using composition
        self.controller = InventoryController()
        self.model = InventoryModel()
        self.table = InventoryTable()
        self.filters = InventoryFilters()
        self.stats = InventoryStats()

        # Track current worker for cancellation
        self._current_worker: Optional[Worker] = None
        self._is_loading = False

        # Batch population state
        self._pending_rows: List[Dict[str, Any]] = []
        self._current_batch_index = 0
        self._batch_timer: Optional[QTimer] = None
        self._batch_size = 30  # Rows per batch - tuned for responsiveness

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

        # Import button (opens dialog explaining required headers and allows importing from excel)
        self.import_button = QPushButton("⬇️ Import Items")
        self.import_button.clicked.connect(self.open_import_dialog)

        header_layout.addWidget(self.import_button)
        header_layout.addWidget(self.add_button)
        header_layout.addWidget(self.edit_button)
        header_layout.addWidget(self.delete_button)
        header_layout.addWidget(self.refresh_button)

        layout.addLayout(header_layout)

        # Progress bar for loading indicator
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Loading inventory... %p%")
        self.progress_bar.setMaximumHeight(20)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

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
        """Refresh all inventory data asynchronously."""
        if self._is_loading:
            logger.debug("Load already in progress, skipping")
            return

        # Cancel any existing worker
        if self._current_worker:
            self._current_worker.cancel()

        self._is_loading = True
        self._set_loading_state(True)

        logger.info("Starting async inventory data refresh...")

        # Run data loading in background thread
        self._current_worker = run_in_background(
            self._load_data_background,
            on_result=self._on_data_loaded,
            on_error=self._on_load_error,
            on_finished=self._on_load_finished,
        )

    def _load_data_background(self) -> dict:
        """
        Load inventory data in background thread.

        Returns dict with all needed data for UI update.
        This method runs off the main thread.
        """
        raw_data = self.controller.load_inventory_data()
        categories = self.controller.get_categories()
        suppliers = self.controller.get_suppliers()

        # Convert to ItemRow objects for model
        items = []
        for row in raw_data:
            item = ItemRow(
                id=row.get("id"),
                name=row.get("name", ""),
                category_name=row.get("category_name", "Uncategorized"),
                size=row.get("size"),
                brand=row.get("brand"),
                supplier_name=row.get("supplier_name"),
                other_specifications=row.get("other_specifications"),
                po_number=row.get("po_number"),
                expiration_date=self._parse_date(row.get("expiration_date")),
                calibration_date=self._parse_date(row.get("calibration_date")),
                acquisition_date=self._parse_date(row.get("acquisition_date")),
                last_modified=self._parse_datetime(row.get("last_modified")),
                is_consumable=bool(row.get("is_consumable", 1)),
                total_stock=row.get("total_stock", 0),
                available_stock=row.get("available_stock", 0),
            )
            items.append(item)

        return {
            "raw_data": raw_data,
            "items": items,
            "categories": categories,
            "suppliers": suppliers,
        }

    def _on_data_loaded(self, result: dict):
        """Handle data loaded from background thread (runs on main thread)."""
        try:
            raw_data = result["raw_data"]
            items = result["items"]
            categories = result["categories"]
            suppliers = result["suppliers"]

            # Update model (main thread)
            self.model.set_items(items)

            # Update table with batched row insertion
            self._populate_table_async(raw_data)

            # Update filters
            self.filters.set_categories(categories)
            self.filters.set_suppliers(suppliers)

            # Update stats
            stats = self.model.get_statistics()
            self.stats.update_statistics(stats)

            logger.info(f"Refreshed inventory data: {len(items)} items loaded")

        except Exception as e:
            logger.error(f"Error processing loaded data: {e}")
            QMessageBox.critical(
                self, "Error", f"Failed to process inventory data: {str(e)}"
            )

    def _populate_table_async(self, raw_data: list):
        """
        Populate table rows in batches using QTimer to prevent UI freeze.

        Uses a timer-based approach to insert rows in small batches,
        allowing the event loop to process UI events between batches.
        """
        # Cancel any pending batch operation
        if self._batch_timer:
            self._batch_timer.stop()
            self._batch_timer = None

        # Store data for batched processing
        self._pending_rows = raw_data
        self._current_batch_index = 0

        # Disable sorting during population
        self.table.setSortingEnabled(False)

        # Pre-allocate rows for better performance
        self.table.setRowCount(len(raw_data))

        # Update progress bar for batch loading
        self.progress_bar.setRange(0, len(raw_data))
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Populating table... %v/%m rows")

        # Start batch timer
        self._batch_timer = QTimer(self)
        self._batch_timer.timeout.connect(self._process_row_batch)
        self._batch_timer.start(
            0
        )  # Process as fast as possible while yielding to event loop

    def _process_row_batch(self):
        """Process a batch of rows and schedule next batch."""
        if self._current_batch_index >= len(self._pending_rows):
            # All rows processed
            self._finish_table_population()
            return

        # Calculate batch end
        batch_end = min(
            self._current_batch_index + self._batch_size, len(self._pending_rows)
        )

        # Process this batch
        for row in range(self._current_batch_index, batch_end):
            self.table.populate_row(row, self._pending_rows[row])

        # Update progress
        self._current_batch_index = batch_end
        self.progress_bar.setValue(batch_end)

        # Process pending events to keep UI responsive
        QApplication.processEvents()

    def _finish_table_population(self):
        """Complete table population after all batches processed."""
        # Stop timer
        if self._batch_timer:
            self._batch_timer.stop()
            self._batch_timer = None

        # Clear pending data
        self._pending_rows = []
        self._current_batch_index = 0

        # Hide progress bar
        self.progress_bar.setVisible(False)

        # Restore sorting and apply default
        self.table.setSortingEnabled(True)
        hdr = self.table.horizontalHeader()
        if hdr is not None:
            hdr.setSortIndicator(0, Qt.SortOrder.AscendingOrder)
            hdr.setSortIndicatorShown(False)
            self.table.sortItems(0, Qt.SortOrder.AscendingOrder)

        # Resize columns
        QTimer.singleShot(100, self.table.resize_columns)

        logger.info("Table population complete")

    def _on_load_error(self, error_tuple: tuple):
        """Handle load error (runs on main thread)."""
        exctype, value, tb = error_tuple
        logger.error(f"Failed to refresh data: {value}\n{tb}")
        QMessageBox.critical(
            self, "Error", f"Failed to load inventory data: {str(value)}"
        )

    def _on_load_finished(self):
        """Handle load finished (runs on main thread)."""
        self._is_loading = False
        self._current_worker = None
        # Note: Don't hide progress bar here, _finish_table_population will handle it
        # after batched population completes
        self.refresh_button.setEnabled(True)
        self.add_button.setEnabled(True)
        self.import_button.setEnabled(True)
        logger.info("Refreshed inventory data")

    def _set_loading_state(self, is_loading: bool):
        """Update UI loading state."""
        self.progress_bar.setVisible(is_loading)
        if is_loading:
            self.progress_bar.setRange(0, 0)  # Indeterminate initially
            self.progress_bar.setFormat("Loading inventory data...")

        # Disable buttons during load
        self.refresh_button.setEnabled(not is_loading)
        self.add_button.setEnabled(not is_loading)
        self.import_button.setEnabled(not is_loading)

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
            QMessageBox.warning(
                self, "No Selection", "Please select an item to delete."
            )
            return

        # Get item details for confirmation
        selected_items = self.model.get_filtered_items()
        selected_item = next(
            (item for item in selected_items if item.id == item_id), None
        )

        if not selected_item:
            QMessageBox.warning(self, "Error", "Could not find selected item.")
            return

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete '{selected_item.name}'?\n\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            # Ask for editor name and reason (Spec #14, #16)
            editor_name, ok = QInputDialog.getText(
                self, "Editor Information", "Enter your name/initials (required):"
            )
            if not ok or not editor_name.strip():
                QMessageBox.warning(self, "Required", "Editor name is required.")
                return

            reason, ok = QInputDialog.getText(
                self, "Deletion Reason", "Reason for deletion:"
            )
            if not ok:
                return

            # Delete the item
            from inventory_app.database.models import Item

            item = Item.get_by_id(item_id)
            if item and item.delete(
                editor_name.strip(), reason.strip() or "No reason provided"
            ):
                logger.info(f"Item {item_id} deleted by {editor_name}")
                QMessageBox.information(self, "Success", "Item deleted successfully!")
                self.refresh_data()
                self.data_changed.emit()
            else:
                QMessageBox.critical(self, "Error", "Failed to delete item.")

        except Exception as e:
            logger.error(f"Failed to delete item {item_id}: {e}")
            QMessageBox.critical(self, "Error", f"Failed to delete item: {str(e)}")

    def open_import_dialog(self):
        """Open the import dialog to import items from an Excel file."""
        try:
            dialog = ImportItemsDialog(self)
            if dialog.exec() == ImportItemsDialog.DialogCode.Accepted:
                # Import succeeded (dialog returns Accepted after import)
                QMessageBox.information(
                    self, "Import", "Import completed. Inventory will refresh."
                )
                self.refresh_data()
                self.data_changed.emit()
        except Exception as e:
            logger.error(f"Import dialog failed: {e}")
            QMessageBox.critical(self, "Import Error", f"Import failed: {str(e)}")

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
        """Update table with current filtered data using batched population."""
        filtered_items = self.model.get_filtered_items()
        table_data = []
        for item in filtered_items:
            row = {
                "id": item.id,
                "name": item.name,
                "category_name": item.category_name,
                "size": item.size,
                "brand": item.brand,
                "supplier_name": item.supplier_name,
                "other_specifications": item.other_specifications,
                "po_number": item.po_number,
                "expiration_date": item.expiration_date.isoformat()
                if item.expiration_date
                else None,
                "calibration_date": item.calibration_date.isoformat()
                if item.calibration_date
                else None,
                "acquisition_date": item.acquisition_date.isoformat()
                if item.acquisition_date
                else None,
                "last_modified": item.last_modified.isoformat()
                if item.last_modified
                else None,
                "is_consumable": item.is_consumable,
                "total_stock": item.total_stock,
                "available_stock": item.available_stock,
            }
            table_data.append(row)

        # Use batched population for large datasets
        if len(table_data) > 50:
            self._populate_table_async(table_data)
        else:
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
