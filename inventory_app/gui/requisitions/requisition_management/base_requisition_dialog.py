"""
Base Requisition Dialog - Base class for requisition dialogs.

Provides common UI structure and functionality for creating and editing requisitions.
Uses composition pattern with services and managers for maintainable architecture.

Uses background threading via QThreadPool for item loading to prevent UI freezes.
"""

from typing import Dict, List, Optional
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QGroupBox,
    QMessageBox,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QWidget,
    QProgressBar,
)
from PyQt6.QtCore import Qt, pyqtSignal

from inventory_app.database.models import Requester
from inventory_app.services.item_service import ItemService
from inventory_app.services.stock_movement_service import StockMovementService
from inventory_app.gui.utils.worker import run_in_background, Worker
from .item_selection_manager import ItemSelectionManager
from .requisition_validator import RequisitionValidator
from inventory_app.utils.logger import logger
from inventory_app.utils.date_utils import (
    MONTH_NAMES,
    get_valid_days_for_month,
    get_year_range,
    format_date_iso,
    get_current_date,
    get_current_datetime,
    convert_12h_to_24h,
    convert_24h_to_12h,
    get_minutes_options,
    get_hour_options_12h,
    get_ampm_options,
)


class CompactDateTimeSelector(QWidget):
    """Compact scrollable date/time selector widget with smart day limits."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()
        self._populate_initial_data()

    def _setup_ui(self):
        """Setup the compact horizontal layout without labels."""
        from PyQt6.QtWidgets import QHBoxLayout, QComboBox, QLabel, QSizePolicy

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)  # Tighter spacing for compactness

        # Month selector - responsive sizing
        self.month_combo = QComboBox()
        self.month_combo.setMinimumWidth(45)
        self.month_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        layout.addWidget(self.month_combo)

        # Separator
        layout.addWidget(QLabel("/"))

        # Day selector - responsive sizing
        self.day_combo = QComboBox()
        self.day_combo.setMinimumWidth(35)
        self.day_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        layout.addWidget(self.day_combo)

        # Separator
        layout.addWidget(QLabel("/"))

        # Year selector - responsive sizing
        self.year_combo = QComboBox()
        self.year_combo.setMinimumWidth(55)
        self.year_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        layout.addWidget(self.year_combo)

    def _connect_signals(self):
        """Connect signals for dynamic updates."""
        self.month_combo.currentIndexChanged.connect(self._on_month_year_changed)
        self.year_combo.currentIndexChanged.connect(self._on_month_year_changed)

    def _populate_initial_data(self):
        """Populate all dropdowns with initial data."""
        # Months
        for month_num, month_name in MONTH_NAMES.items():
            self.month_combo.addItem(month_name, month_num)

        # Years (current ± 5 years)
        years = get_year_range()
        for year in years:
            self.year_combo.addItem(str(year), year)

        # Set initial date to current date
        self.set_date(get_current_date())

    def _on_month_year_changed(self):
        """Update day dropdown when month or year changes."""
        current_year = self.year_combo.currentData()
        current_month = self.month_combo.currentData()

        if current_year and current_month:
            # Get valid days for this month/year
            valid_days = get_valid_days_for_month(current_year, current_month)

            # Store current day selection
            current_day = self.day_combo.currentData()

            # Repopulate day dropdown
            self.day_combo.clear()
            for day in valid_days:
                self.day_combo.addItem(str(day), day)

            # Try to restore previous day selection, or select last valid day
            if current_day and current_day in valid_days:
                self.day_combo.setCurrentText(str(current_day))
            else:
                # Select the last valid day if current day is invalid
                if valid_days:
                    last_day = valid_days[-1]
                    self.day_combo.setCurrentText(str(last_day))

    def set_date(self, date_obj):
        """Set the selector to a specific date."""
        from datetime import date

        if isinstance(date_obj, date):
            # Set month
            self.month_combo.setCurrentText(MONTH_NAMES.get(date_obj.month, ""))

            # Set year
            self.year_combo.setCurrentText(str(date_obj.year))

            # Set day (will be validated by _on_month_year_changed)
            self.day_combo.setCurrentText(str(date_obj.day))

    def set_datetime(self, dt_obj):
        """Set the selector to a specific datetime."""
        from datetime import datetime

        if isinstance(dt_obj, datetime):
            # Set date part
            self.set_date(dt_obj.date())

    def get_selected_date(self):
        """Get the selected date as a date object."""
        from datetime import date

        year = self.year_combo.currentData()
        month = self.month_combo.currentData()
        day = self.day_combo.currentData()

        if year and month and day:
            try:
                return date(year, month, day)
            except ValueError:
                return None
        return None

    def get_selected_datetime(self):
        """Get the selected date and time as a datetime object."""

        date_obj = self.get_selected_date()
        if not date_obj:
            return None

    def get_selected_date_iso(self):
        """Get the selected date as ISO string (YYYY-MM-DD)."""
        date_obj = self.get_selected_date()
        return format_date_iso(date_obj) if date_obj else ""

    def get_selected_datetime_iso(self):
        """Get the selected datetime as ISO string."""
        from inventory_app.utils.date_utils import format_datetime_iso

        dt_obj = self.get_selected_datetime()
        return format_datetime_iso(dt_obj) if dt_obj else ""


class DateTimeSelectionManager:
    """Manager for date/time selection using composition pattern."""

    def __init__(self):
        self.selector = None

    def create_selector(self, parent=None):
        """Create and return the date/time selector widget."""
        self.selector = CompactDateTimeSelector(parent)
        return self.selector

    def set_defaults(self):
        """Set selector to current date/time defaults."""
        if self.selector:
            from inventory_app.utils.date_utils import get_current_datetime

            self.selector.set_datetime(get_current_datetime())

    def load_from_date(self, date_obj):
        """Load date from database into selector."""
        if self.selector and date_obj:
            from datetime import date

            if isinstance(date_obj, date):
                self.selector.set_date(date_obj)

    def get_selected_date_iso(self):
        """Get selected date as ISO string."""
        if self.selector:
            return self.selector.get_selected_date_iso()
        return ""

    def get_selected_datetime(self):
        """Get selected date/time as datetime object."""
        if self.selector:
            return self.selector.get_selected_datetime()
        return None

    def get_widget(self):
        """Get the selector widget for adding to layouts."""
        return self.selector


class BaseRequisitionDialog(QDialog):
    """
    Abstract base class for all requisition dialogs.

    Provides common UI structure, signals, and standardized data structures.
    Subclasses implement mode-specific behavior.
    Uses async loading for available items to prevent UI freezes.
    """

    # Signal emitted when requisition is successfully saved
    requisition_saved = pyqtSignal(int)  # Requisition ID

    def __init__(self, mode: str, parent=None):
        """
        Initialize the base requisition dialog.

        Args:
            mode: 'create' or 'edit'
            parent: Parent widget
        """
        super().__init__(parent)
        self.mode = mode  # 'create' or 'edit'

        # Compose with services and managers
        self.item_service = ItemService()
        self.stock_service = StockMovementService()
        self.item_manager = ItemSelectionManager(self.item_service)
        self.datetime_manager = DateTimeSelectionManager()
        self.schedule_manager = RequisitionScheduleManager()
        self.validator = RequisitionValidator()

        # Standardized data structures
        self.selected_requester: Optional[Requester] = None
        self.selected_items: List[Dict] = []  # Standardized item format

        # Async loading state
        self._items_worker: Optional[Worker] = None
        self._is_loading_items = False

        self._setup_ui()
        logger.info(f"Base requisition dialog initialized in {mode} mode")

    def _setup_ui(self):
        """Setup the common UI structure with responsive layout."""
        self.setWindowTitle(
            f"{'Create' if self.mode == 'create' else 'Edit'} Laboratory Requisition"
        )
        self.setModal(True)
        self.setMinimumSize(1000, 540)  # Set minimum size for usability

        layout = QVBoxLayout(self)
        layout.setSpacing(5)

        # Main horizontal splitter for the entire layout
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setChildrenCollapsible(False)  # Prevent panels from collapsing
        layout.addWidget(main_splitter)

        # Left section: Vertical splitter containing left/middle panels and schedule
        left_section = QWidget()
        left_section.setMinimumWidth(500)  # Ensure minimum width for left section
        left_layout = QVBoxLayout(left_section)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Top horizontal splitter for left and middle panels
        top_splitter = QSplitter(Qt.Orientation.Horizontal)
        top_splitter.setChildrenCollapsible(False)
        left_layout.addWidget(top_splitter)

        # Left panel
        left_panel = self._create_requisition_details_panel()
        top_splitter.addWidget(left_panel)

        # Middle panel
        middle_panel = self._create_item_selection_panel()
        top_splitter.addWidget(middle_panel)

        # Set top splitter proportions (35% left, 35% middle)
        top_splitter.setStretchFactor(0, 35)
        top_splitter.setStretchFactor(1, 35)

        # Schedule panel below left and middle panels
        schedule_panel = self._create_requisition_schedule_panel()
        schedule_panel.setMinimumHeight(120)  # Ensure schedule has minimum height
        left_layout.addWidget(schedule_panel)

        # Set vertical proportions for left section (top panels get more space than schedule)
        left_layout.setStretchFactor(top_splitter, 4)
        left_layout.setStretchFactor(schedule_panel, 1)

        main_splitter.addWidget(left_section)

        # Right section: Right panel spanning full height
        right_panel = self._create_selected_items_summary()
        main_splitter.addWidget(right_panel)

        # Set main splitter proportions (70% left, 30% right)
        main_splitter.setStretchFactor(0, 70)
        main_splitter.setStretchFactor(1, 30)

        # Buttons (abstract - implemented by subclasses)
        self._setup_buttons(layout)

    def _create_requisition_details_panel(self) -> QWidget:
        """Create mode-specific requisition details panel."""
        raise NotImplementedError(
            "Subclasses must implement _create_requisition_details_panel"
        )

    def _create_item_selection_panel(self) -> QWidget:
        """Create the common item selection panel with responsive height and async loading."""
        from PyQt6.QtWidgets import QSizePolicy

        panel = QWidget()
        panel.setMinimumHeight(200)  # Minimum height for usability
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(panel)

        # Search and filter
        search_group = QGroupBox("🔍 Search Items")
        search_group.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        search_layout = QVBoxLayout(search_group)

        self.item_search = QLineEdit()
        self.item_search.setPlaceholderText("Search items by name...")
        self.item_search.textChanged.connect(self.search_items)
        search_layout.addWidget(self.item_search)

        layout.addWidget(search_group)

        # Progress bar for loading items
        self.items_progress_bar = QProgressBar()
        self.items_progress_bar.setTextVisible(True)
        self.items_progress_bar.setFormat("Loading items...")
        self.items_progress_bar.setMaximumHeight(18)
        self.items_progress_bar.setVisible(False)
        layout.addWidget(self.items_progress_bar)

        # Available items list
        items_group = QGroupBox("📦 Available Items")
        items_group.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        items_layout = QVBoxLayout(items_group)

        self.available_items_list = QListWidget()
        self.available_items_list.setMinimumHeight(100)  # Minimum height for list
        self.available_items_list.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.available_items_list.setWordWrap(
            True
        )  # Enable text wrapping for long item names
        self.available_items_list.itemDoubleClicked.connect(self.add_item_to_selection)
        items_layout.addWidget(self.available_items_list)

        # Add item button
        self.add_item_btn = QPushButton("➕ Add Selected Item")
        self.add_item_btn.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.add_item_btn.clicked.connect(self.add_item_to_selection)
        items_layout.addWidget(self.add_item_btn)

        layout.addWidget(items_group)

        # Load initial items asynchronously
        self.load_available_items()

        return panel

    def _create_selected_items_summary(self) -> QGroupBox:
        """Create the common selected items summary panel with responsive height."""
        from PyQt6.QtWidgets import QSizePolicy

        group = QGroupBox("🛒 Selected Items")
        group.setMinimumHeight(200)  # Minimum height for usability
        group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(group)

        self.selected_items_list = QListWidget()
        self.selected_items_list.setMinimumHeight(100)  # Minimum height for list
        self.selected_items_list.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.selected_items_list.setWordWrap(
            True
        )  # Enable text wrapping for long item names
        self.selected_items_list.itemDoubleClicked.connect(
            self.edit_selected_item_amount
        )
        layout.addWidget(self.selected_items_list)

        # Summary info
        self.items_summary = QLabel("No items selected")
        self.items_summary.setStyleSheet("font-weight: bold; padding: 5px;")
        self.items_summary.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.items_summary.setWordWrap(True)  # Enable text wrapping for long summaries
        layout.addWidget(self.items_summary)

        # Edit amount button
        edit_amount_btn = QPushButton("📝 Edit Amount")
        edit_amount_btn.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        edit_amount_btn.clicked.connect(self.edit_selected_item_amount)
        layout.addWidget(edit_amount_btn)

        # Remove item button
        remove_btn = QPushButton("➖ Remove Selected Item")
        remove_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        remove_btn.clicked.connect(self.remove_selected_item)
        layout.addWidget(remove_btn)

        # Action buttons container (Create/Update and Cancel will be placed here)
        # Use a horizontal layout so primary action is right-aligned
        from PyQt6.QtWidgets import QHBoxLayout, QWidget

        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.addStretch()
        layout.addWidget(action_widget)
        # Keep a reference so subclasses can place their action buttons here
        self.action_buttons_layout = action_layout

        return group

    def _create_requisition_schedule_panel(self) -> QGroupBox:
        """Create the requisition schedule panel with requisition times."""
        group = QGroupBox("📅 Requisition Schedule")
        layout = QVBoxLayout(group)

        # Create and add the compact schedule widget
        schedule_widget = self.schedule_manager.create_schedule(self)
        layout.addWidget(schedule_widget)

        return group

    def _setup_buttons(self, layout: QVBoxLayout):
        """Setup mode-specific buttons."""
        raise NotImplementedError("Subclasses must implement _setup_buttons")

    # Common methods used by both dialogs
    def load_available_items(self):
        """Load available items for selection asynchronously."""
        if self._is_loading_items:
            return

        # Cancel any existing worker
        if self._items_worker:
            self._items_worker.cancel()

        self._is_loading_items = True

        # Show progress bar immediately with indeterminate state
        self.items_progress_bar.setRange(0, 0)  # Indeterminate
        self.items_progress_bar.setFormat("Loading items from database...")
        self.items_progress_bar.setVisible(True)

        # Disable add button during load
        if hasattr(self, "add_item_btn"):
            self.add_item_btn.setEnabled(False)

        # Get exclusion ID for editing mode
        exclude_requisition_id = getattr(self, "temp_requisition_id", None)

        # Run data loading in background thread
        self._items_worker = run_in_background(
            self._load_items_background,
            exclude_requisition_id,
            on_result=self._on_items_loaded,
            on_error=self._on_items_load_error,
            on_finished=self._on_items_load_finished,
        )

    def _load_items_background(self, exclude_requisition_id: Optional[int]) -> list:
        """
        Load items in background thread.

        This method runs off the main thread.
        """
        items = self.item_service.get_inventory_batches_for_selection(
            exclude_requisition_id=exclude_requisition_id
        )
        return items

    def _on_items_loaded(self, items: list):
        """Handle items loaded - start batched population on main thread."""
        from PyQt6.QtCore import QTimer

        try:
            self._loaded_items = items

            # Clear list and prepare for batched loading
            self.available_items_list.clear()

            # Pre-filter items based on currently selected items
            # (subtract selected quantities from available stock)
            self._items_to_display = []

            for item in items:
                # Calculate real-time available: DB available - currently selected
                db_available = item.get("available_stock", 0)
                selected_qty = sum(
                    sel.get("quantity", 0)
                    for sel in self.selected_items
                    if sel.get("batch_id") == item.get("batch_id")
                )
                real_time_available = max(0, db_available - selected_qty)

                # Skip items with no available stock
                if real_time_available <= 0:
                    continue

                # Store the real-time stock for display
                item["real_time_available_stock"] = real_time_available
                self._items_to_display.append(item)

            # Setup batched population
            self._items_batch_index = 0
            self._items_batch_size = 50  # Can be larger now since no DB calls

            # Show progress bar for batched loading
            total_items = len(self._items_to_display)
            self.items_progress_bar.setRange(0, total_items)
            self.items_progress_bar.setValue(0)
            self.items_progress_bar.setFormat(f"Loading items... %v/{total_items}")
            self.items_progress_bar.setVisible(True)

            # Start batched population using QTimer for smooth UI
            self._batch_timer = QTimer(self)
            self._batch_timer.timeout.connect(self._process_items_batch)
            self._batch_timer.start(0)

        except Exception as e:
            logger.error(f"Error processing loaded items: {e}")
            QMessageBox.critical(self, "Error", f"Failed to process items: {str(e)}")

    def _process_items_batch(self):
        """Process one batch of items - add to list widget."""
        from PyQt6.QtWidgets import QApplication

        # Safety check - ensure we have data to process
        if not hasattr(self, "_items_to_display") or self._items_to_display is None:
            self._finish_items_population()
            return

        total_items = len(self._items_to_display)
        start = self._items_batch_index
        end = min(start + self._items_batch_size, total_items)

        if start >= total_items:
            self._finish_items_population()
            return

        # Process batch - just add to list widget (no DB calls!)
        for idx in range(start, end):
            item = self._items_to_display[idx]
            real_time_stock = item.get("real_time_available_stock", 0)

            # Add to list widget
            display_text = (
                f"{item['item_name']} "
                f"[{item['category_name']}] - "
                f"available: {real_time_stock}"
            )
            list_item = QListWidgetItem(display_text)
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            self.available_items_list.addItem(list_item)

        # Update progress
        self._items_batch_index = end
        self.items_progress_bar.setValue(end)

        # Process events to keep UI responsive
        QApplication.processEvents()

        # Check if done
        if self._items_to_display is None or end >= total_items:
            self._finish_items_population()

    def _finish_items_population(self):
        """Finish item population."""
        # Stop timer
        if hasattr(self, "_batch_timer") and self._batch_timer:
            self._batch_timer.stop()
            self._batch_timer = None

        # Hide progress bar
        self.items_progress_bar.setVisible(False)

        # Enable add button
        if hasattr(self, "add_item_btn"):
            self.add_item_btn.setEnabled(True)

        # Clean up
        self._items_to_display = None
        self._items_batch_index = 0

        logger.info(
            f"Loaded {self.available_items_list.count()} available items with real-time stock"
        )

    def _on_items_load_error(self, error_tuple: tuple):
        """Handle items load error (runs on main thread)."""
        exctype, value, tb = error_tuple
        logger.error(f"Failed to load available items: {value}\n{tb}")
        self.items_progress_bar.setVisible(False)
        if hasattr(self, "add_item_btn"):
            self.add_item_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", f"Failed to load items: {str(value)}")

    def _on_items_load_finished(self):
        """Handle items load finished (runs on main thread)."""
        self._is_loading_items = False
        self._items_worker = None

    def search_items(self, search_text: str):
        """Filter items based on search text with batched processing to prevent UI freeze."""

        total_items = self.available_items_list.count()

        # For small lists, filter directly
        if total_items <= 100:
            self._filter_items_direct(search_text)
            return

        # For large lists, use batched filtering
        self._search_text = search_text
        self._filter_batch_index = 0
        self._filter_batch_size = 50
        self._process_filter_batch()

    def _filter_items_direct(self, search_text: str):
        """Filter items directly for small lists."""
        search_lower = search_text.lower().strip()
        for i in range(self.available_items_list.count()):
            item = self.available_items_list.item(i)
            if item is not None:
                item_data = item.data(Qt.ItemDataRole.UserRole)
                if item_data:
                    item_name = item_data.get("item_name", "").lower()
                    category = item_data.get("category_name", "").lower()

                    visible = (
                        search_lower in item_name
                        or search_lower in category
                        or not search_text.strip()
                    )
                    item.setHidden(not visible)

    def _process_filter_batch(self):
        """Process one batch of filter operations."""
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QTimer

        if not hasattr(self, "_search_text"):
            return

        search_lower = self._search_text.lower().strip()
        total_items = self.available_items_list.count()
        start = self._filter_batch_index
        end = min(start + self._filter_batch_size, total_items)

        if start >= total_items:
            return

        # Process batch
        for i in range(start, end):
            item = self.available_items_list.item(i)
            if item is not None:
                item_data = item.data(Qt.ItemDataRole.UserRole)
                if item_data:
                    item_name = item_data.get("item_name", "").lower()
                    category = item_data.get("category_name", "").lower()

                    visible = (
                        search_lower in item_name
                        or search_lower in category
                        or not self._search_text.strip()
                    )
                    item.setHidden(not visible)

        # Process events to keep UI responsive
        QApplication.processEvents()

        # Schedule next batch
        self._filter_batch_index = end
        if end < total_items:
            QTimer.singleShot(0, self._process_filter_batch)

    def add_item_to_selection(self):
        """Add selected item to requisition using ItemSelectionManager."""
        current_item = self.available_items_list.currentItem()
        if not current_item:
            QMessageBox.information(
                self, "No Selection", "Please select an item first."
            )
            return

        item_data = current_item.data(Qt.ItemDataRole.UserRole)
        if not item_data:
            return

        # Get quantity from user using real-time available stock
        available_stock = item_data.get(
            "real_time_available_stock", item_data["available_stock"]
        )
        quantity, ok = self._get_quantity_from_user(
            item_data["item_name"], available_stock, item_data["batch_number"]
        )

        if ok and quantity > 0:
            # Use ItemSelectionManager for smart addition with duplicate handling
            success = self.item_manager.add_item_to_selection(
                self.selected_items, item_data, quantity
            )

            if success:
                # Refresh available items to update real-time stock display
                self.load_available_items()
                self.update_selected_items_display()
                self.update_create_button_state()
                logger.info(
                    f"Added item {item_data['item_name']} (x{quantity}) to selection"
                )

    def _get_quantity_from_user(
        self, item_name: str, max_quantity: int, batch_number: int
    ) -> tuple[int, bool]:
        """Get quantity from user with validation."""
        from PyQt6.QtWidgets import QInputDialog

        quantity, ok = QInputDialog.getInt(
            self,
            "Select Quantity",
            f"Enter quantity for {item_name} (Batch #{batch_number}):\n"
            f"Available: {max_quantity}",
            value=1,
            min=1,
            max=max_quantity,
        )

        return quantity, ok if ok is not None else False

    def edit_selected_item_amount(self):
        """Edit the quantity of a selected item using ItemSelectionManager."""
        current_row = self.selected_items_list.currentRow()
        if current_row < 0 or current_row >= len(self.selected_items):
            QMessageBox.information(
                self, "No Selection", "Please select an item to edit its quantity."
            )
            return

        # Use ItemSelectionManager for proper editing with current value as default
        success = self.item_manager.edit_item_quantity(self.selected_items, current_row)

        if success:
            # Refresh available items to update real-time stock display
            self.load_available_items()
            self.update_selected_items_display()
            self.update_create_button_state()

    def remove_selected_item(self):
        """Remove selected item from requisition."""
        current_row = self.selected_items_list.currentRow()
        if current_row >= 0 and current_row < len(self.selected_items):
            removed_item = self.selected_items.pop(current_row)

            # Refresh available items to update real-time stock display
            self.load_available_items()
            self.update_selected_items_display()
            self.update_create_button_state()
            logger.info(f"Removed item {removed_item['item_name']} from selection")

    def update_selected_items_display(self):
        """Update the display of selected items."""
        self.selected_items_list.clear()

        total_quantity = 0
        for item in self.selected_items:
            display_text = (
                f"{item['item_name']} "
                f"[{item['category_name']}] - "
                f"qty: {item['quantity']}"
            )

            list_item = QListWidgetItem(display_text)
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            self.selected_items_list.addItem(list_item)

            total_quantity += item["quantity"]

        # Update summary
        if self.selected_items:
            self.items_summary.setText(
                f"Total Items: {len(self.selected_items)} | "
                f"Total Quantity: {total_quantity}"
            )
        else:
            self.items_summary.setText("No items selected")

    def update_create_button_state(self):
        """Update the create/edit button enabled state."""
        raise NotImplementedError(
            "Subclasses must implement update_create_button_state"
        )

    def get_editor_name(self) -> str:
        """
        Get editor name from user input dialog.

        Returns:
            str: Editor name or empty string if cancelled
        """
        from PyQt6.QtWidgets import QInputDialog

        editor_name, ok = QInputDialog.getText(
            self, "Editor Information", "Enter your name/initials (required):"
        )

        if ok and editor_name.strip():
            return editor_name.strip()
        return ""


class CompactRequisitionSchedule(QWidget):
    """Compact request and return schedule widget with horizontal layout."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()
        self._populate_initial_data()

    def _setup_ui(self):
        """Setup the compact horizontal layout for requisition schedule."""
        from PyQt6.QtWidgets import (
            QHBoxLayout,
            QVBoxLayout,
            QLabel,
            QComboBox,
            QSizePolicy,
        )

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(8)

        # Request schedule row
        request_layout = QHBoxLayout()
        request_layout.setSpacing(5)

        request_layout.addWidget(QLabel("Expected to get at :      "))

        # Request time selectors - responsive sizing
        self.request_hour = QComboBox()
        self.request_hour.setMinimumWidth(35)
        self.request_hour.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        request_layout.addWidget(self.request_hour)

        request_layout.addWidget(QLabel(":"))

        self.request_minute = QComboBox()
        self.request_minute.setMinimumWidth(35)
        self.request_minute.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        request_layout.addWidget(self.request_minute)

        self.request_ampm = QComboBox()
        self.request_ampm.setMinimumWidth(35)
        self.request_ampm.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        request_layout.addWidget(self.request_ampm)

        request_layout.addWidget(QLabel("  -  "))

        # Request date selectors - responsive sizing
        self.request_month = QComboBox()
        self.request_month.setMinimumWidth(45)
        self.request_month.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        request_layout.addWidget(self.request_month)

        request_layout.addWidget(QLabel("/"))

        self.request_day = QComboBox()
        self.request_day.setMinimumWidth(35)
        self.request_day.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        request_layout.addWidget(self.request_day)

        request_layout.addWidget(QLabel("/"))

        self.request_year = QComboBox()
        self.request_year.setMinimumWidth(55)
        self.request_year.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        request_layout.addWidget(self.request_year)

        request_layout.addStretch()
        main_layout.addLayout(request_layout)

        # Return schedule row
        return_layout = QHBoxLayout()
        return_layout.setSpacing(5)

        return_layout.addWidget(QLabel("Expected return at :      "))

        # Return time selectors - responsive sizing
        self.return_hour = QComboBox()
        self.return_hour.setMinimumWidth(35)
        self.return_hour.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        return_layout.addWidget(self.return_hour)

        return_layout.addWidget(QLabel(":"))

        self.return_minute = QComboBox()
        self.return_minute.setMinimumWidth(35)
        self.return_minute.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        return_layout.addWidget(self.return_minute)

        self.return_ampm = QComboBox()
        self.return_ampm.setMinimumWidth(35)
        self.return_ampm.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        return_layout.addWidget(self.return_ampm)

        return_layout.addWidget(QLabel("  -  "))

        # Return date selectors - responsive sizing
        self.return_month = QComboBox()
        self.return_month.setMinimumWidth(45)
        self.return_month.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        return_layout.addWidget(self.return_month)

        return_layout.addWidget(QLabel("/"))

        self.return_day = QComboBox()
        self.return_day.setMinimumWidth(35)
        self.return_day.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        return_layout.addWidget(self.return_day)

        return_layout.addWidget(QLabel("/"))

        self.return_year = QComboBox()
        self.return_year.setMinimumWidth(55)
        self.return_year.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        return_layout.addWidget(self.return_year)

        return_layout.addStretch()
        main_layout.addLayout(return_layout)

    def _connect_signals(self):
        """Connect signals for dynamic updates."""
        self.request_month.currentIndexChanged.connect(self._on_request_date_changed)
        self.request_year.currentIndexChanged.connect(self._on_request_date_changed)
        self.return_month.currentIndexChanged.connect(self._on_return_date_changed)
        self.return_year.currentIndexChanged.connect(self._on_return_date_changed)

    def _populate_initial_data(self):
        """Populate all dropdowns with initial data."""
        from datetime import timedelta

        now = get_current_datetime()
        default_return = now + timedelta(days=7)

        # Populate all dropdowns
        self._populate_dropdowns()
        self.set_request_datetime(now)
        self.set_return_datetime(default_return)

    def _populate_dropdowns(self):
        """Populate all comboboxes with data."""
        # Months
        for month_num, month_name in MONTH_NAMES.items():
            self.request_month.addItem(month_name, month_num)
            self.return_month.addItem(month_name, month_num)

        # Years
        years = get_year_range()
        for year in years:
            self.request_year.addItem(str(year), year)
            self.return_year.addItem(str(year), year)

        # Hours (1-12)
        hours = get_hour_options_12h()
        for hour in hours:
            self.request_hour.addItem(str(hour), hour)
            self.return_hour.addItem(str(hour), hour)

        # Minutes (00-59 with proper formatting)
        minutes = get_minutes_options()
        for minute_val, minute_str in enumerate(minutes):
            self.request_minute.addItem(minute_str, minute_val)
            self.return_minute.addItem(minute_str, minute_val)

        # AM/PM
        ampm_options = get_ampm_options()
        for ampm in ampm_options:
            self.request_ampm.addItem(ampm, ampm)
            self.return_ampm.addItem(ampm, ampm)

    def _on_request_date_changed(self):
        """Update request day dropdown when month or year changes."""
        self._update_days_dropdown(
            self.request_day, self.request_year, self.request_month
        )

    def _on_return_date_changed(self):
        """Update return day dropdown when month or year changes."""
        self._update_days_dropdown(self.return_day, self.return_year, self.return_month)

    def _update_days_dropdown(self, day_combo, year_combo, month_combo):
        """Update day dropdown based on selected month and year."""
        year = year_combo.currentData()
        month = month_combo.currentData()

        if year and month:
            valid_days = get_valid_days_for_month(year, month)
            current_day = day_combo.currentData()

            day_combo.clear()
            for day in valid_days:
                day_combo.addItem(str(day), day)

            # Restore previous selection if valid
            if current_day in valid_days:
                day_combo.setCurrentText(str(current_day))
            else:
                day_combo.setCurrentText(str(valid_days[-1]))

    def set_request_datetime(self, dt_obj):
        """Set the request date/time."""
        from datetime import datetime

        if isinstance(dt_obj, datetime):
            hour_12, am_pm = convert_24h_to_12h(dt_obj.hour)

            self.request_month.setCurrentText(MONTH_NAMES.get(dt_obj.month, ""))
            self.request_year.setCurrentText(str(dt_obj.year))
            self._update_days_dropdown(
                self.request_day, self.request_year, self.request_month
            )
            self.request_day.setCurrentText(str(dt_obj.day))

            self.request_hour.setCurrentText(str(hour_12))
            self.request_minute.setCurrentText(f"{dt_obj.minute:02d}")
            self.request_ampm.setCurrentText(am_pm)

    def set_return_datetime(self, dt_obj):
        """Set the return date/time."""
        from datetime import datetime

        if isinstance(dt_obj, datetime):
            hour_12, am_pm = convert_24h_to_12h(dt_obj.hour)

            self.return_month.setCurrentText(MONTH_NAMES.get(dt_obj.month, ""))
            self.return_year.setCurrentText(str(dt_obj.year))
            self._update_days_dropdown(
                self.return_day, self.return_year, self.return_month
            )
            self.return_day.setCurrentText(str(dt_obj.day))

            self.return_hour.setCurrentText(str(hour_12))
            self.return_minute.setCurrentText(f"{dt_obj.minute:02d}")
            self.return_ampm.setCurrentText(am_pm)

    def get_request_datetime(self):
        """Get the selected request date/time as datetime object."""
        from datetime import datetime

        year = self.request_year.currentData()
        month = self.request_month.currentData()
        day = self.request_day.currentData()
        hour_12 = self.request_hour.currentData()
        minute = self.request_minute.currentData()
        am_pm = self.request_ampm.currentData()

        if all([year, month, day, hour_12, minute is not None, am_pm]):
            hour_24 = convert_12h_to_24h(hour_12, am_pm)
            try:
                return datetime(year, month, day, hour_24, minute)
            except ValueError:
                return None
        return None

    def get_return_datetime(self):
        """Get the selected return date/time as datetime object."""
        from datetime import datetime

        year = self.return_year.currentData()
        month = self.return_month.currentData()
        day = self.return_day.currentData()
        hour_12 = self.return_hour.currentData()
        minute = self.return_minute.currentData()
        am_pm = self.return_ampm.currentData()

        if all([year, month, day, hour_12, minute is not None, am_pm]):
            hour_24 = convert_12h_to_24h(hour_12, am_pm)
            try:
                return datetime(year, month, day, hour_24, minute)
            except ValueError:
                return None
        return None


class RequisitionScheduleManager:
    """Manager for requisition schedule selection using composition pattern."""

    def __init__(self):
        self.schedule = None

    def create_schedule(self, parent=None):
        """Create and return the requisition schedule widget."""
        self.schedule = CompactRequisitionSchedule(parent)
        return self.schedule

    def set_request_datetime(self, dt_obj):
        """Set request datetime in the schedule."""
        if self.schedule:
            self.schedule.set_request_datetime(dt_obj)

    def set_return_datetime(self, dt_obj):
        """Set return datetime in the schedule."""
        if self.schedule:
            self.schedule.set_return_datetime(dt_obj)

    def get_request_datetime(self):
        """Get selected request datetime."""
        if self.schedule:
            return self.schedule.get_request_datetime()
        return None

    def get_return_datetime(self):
        """Get selected return datetime."""
        if self.schedule:
            return self.schedule.get_return_datetime()
        return None

    def get_widget(self):
        """Get the schedule widget for adding to layouts."""
        return self.schedule

    # Date/Time helper methods
    def create_activity_date_selector(self):
        """Create and return a CompactDateTimeSelector for activity date."""
        return CompactDateTimeSelector(self)
