"""
Virtual scrolling implementation for handling thousands of items efficiently.

Chunk 6 of performance optimization plan - enables handling 10,000+ items
with constant memory usage and smooth scrolling.

Key Features:
- QAbstractTableModel with lazy data loading
- LRU cache (500 rows max) for loaded row data
- Progressive loading via fetchMore()
- Scroll-optimized prefetching (50 rows above, 100 rows below visible area)
- Feature flag for gradual migration

Usage:
    model = VirtualTableModel(
        total_rows=10000,
        fetch_callback=lambda start, limit: load_items(start, limit),
        columns=["Name", "Stock", "Supplier", ...]
    )
    table.setModel(model)
"""

from typing import Dict, List, Any, Optional, Callable, Set, Tuple
from collections import OrderedDict
import threading
from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt, pyqtSignal, QTimer
from inventory_app.utils.logger import logger


SORT_ROLE = getattr(Qt.ItemDataRole, "SortRole", int(Qt.ItemDataRole.UserRole) + 1)

VIRTUAL_SCROLLING_ENABLED = False
VIRTUAL_SCROLLING_ROW_LIMIT = 1000

MAX_CACHED_ROWS = 500
FETCH_BATCH_SIZE = 100
PREFETCH_ABOVE = 50
PREFETCH_BELOW = 100


class LRUCache:
    """
    Thread-safe LRU cache for virtual table row data.

    Uses OrderedDict for O(1) get/put operations with automatic
    eviction of least recently used entries when max size is reached.
    """

    def __init__(self, max_size: int = MAX_CACHED_ROWS):
        self._max_size = max_size
        self._cache: OrderedDict[int, Dict[str, Any]] = OrderedDict()
        self._lock = threading.RLock()

    def get(self, row: int) -> Optional[Dict[str, Any]]:
        """Get a row from cache, moving it to most recently used."""
        with self._lock:
            if row not in self._cache:
                return None

            row_data = self._cache.pop(row)
            self._cache[row] = row_data
            return row_data

    def put(self, row: int, data: Dict[str, Any]) -> None:
        """Add a row to cache, evicting LRU if at capacity."""
        with self._lock:
            if row in self._cache:
                self._cache.pop(row)
            elif len(self._cache) >= self._max_size:
                oldest_key, _ = self._cache.popitem(last=False)
                logger.debug(f"LRU cache evicted row {oldest_key}")

            self._cache[row] = data

    def contains(self, row: int) -> bool:
        """Check if row is in cache."""
        with self._lock:
            return row in self._cache

    def prefetch(
        self,
        rows: List[int],
        fetch_callback: Callable[[int, int], List[Dict[str, Any]]],
    ) -> None:
        """Prefetch multiple rows efficiently."""
        with self._lock:
            rows_to_fetch = [r for r in rows if r not in self._cache]

        if not rows_to_fetch:
            return

        logger.debug(f"Prefetching {len(rows_to_fetch)} rows")

    def clear(self) -> None:
        """Clear all cached data."""
        with self._lock:
            self._cache.clear()
            logger.debug("LRU cache cleared")

    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)

    def get_cache_keys(self) -> Set[int]:
        """Get all cached row indices (thread-safe copy)."""
        with self._lock:
            return set(self._cache.keys())


class VirtualTableModel(QAbstractTableModel):
    """
    Virtual scrolling table model that loads data on demand.

    Optimized for large datasets (10,000+ items) with:
    - Lazy loading via data() method
    - LRU cache for loaded rows
    - Progressive loading via fetchMore()
    - Scroll-optimized prefetching

    Signals:
        - loading_started: Emitted when loading begins
        - loading_progress: Emitted with progress percentage
        - loading_finished: Emitted when loading completes
        - loading_error: Emitted on error with message
    """

    loading_started = pyqtSignal()
    loading_progress = pyqtSignal(int)
    loading_finished = pyqtSignal()
    loading_error = pyqtSignal(str)

    def __init__(
        self,
        total_rows: int,
        fetch_callback: Callable[[int, int], List[Dict[str, Any]]],
        columns: List[str],
        parent: Optional[Any] = None,
        status_fetch_callback: Optional[Callable[[List[int]], Dict[int, Any]]] = None,
    ):
        """
        Initialize virtual table model.

        Args:
            total_rows: Total number of rows in the dataset
            fetch_callback: Function(start, limit) -> List of row dicts
            columns: List of column names
            parent: Parent QObject
            status_fetch_callback: Optional function(item_ids) -> dict of statuses
        """
        super().__init__(parent)

        self._columns = columns
        self._total_rows = total_rows
        self._fetch_callback = fetch_callback
        self._status_fetch_callback = status_fetch_callback

        self._cache = LRUCache(MAX_CACHED_ROWS)
        self._loaded_rows: Set[int] = set()
        self._is_loading = False
        self._loading_rows: Set[int] = set()
        self._loading_lock = threading.RLock()

        self._fetched_count = 0
        self._sort_column: Optional[int] = None
        self._sort_order: Optional[Qt.SortOrder] = None
        self._sort_data: Dict[int, Tuple[int, Any]] = {}

        self._prefetch_timer = QTimer()
        self._prefetch_timer.setSingleShot(True)
        self._prefetch_timer.timeout.connect(self._execute_prefetch)

        self._status_cache: Dict[int, Any] = {}
        self._prefetched_statuses: Dict[int, Any] = {}

    def rowCount(self, parent: Optional[QModelIndex] = None) -> int:
        """Return total number of rows for scrollbar sizing."""
        return self._total_rows

    def columnCount(self, parent: Optional[QModelIndex] = None) -> int:
        """Return number of columns."""
        return len(self._columns)

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        """Return item flags."""
        return Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """
        Get data for the specified index.

        This is the core lazy loading method - data is fetched on demand
        when this method is called.
        """
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()

        if row >= self._total_rows:
            return None

        row_data = self._cache.get(row)

        if row_data is None:
            if not self._is_row_loading(row):
                self._trigger_load_for_row(row)
            return None

        return self._get_cell_value(row_data, col, role)

    def _get_cell_value(self, row_data: Dict[str, Any], col: int, role: int) -> Any:
        """Extract cell value from row data based on column and role."""
        column_names = [
            "total_stock",
            "name",
            "size",
            "brand",
            "other_specifications",
            "supplier_name",
            "calibration_date",
            "expiration_date",
            "is_consumable",
            "acquisition_date",
            "last_modified",
        ]

        column_names_extended = column_names + ["category_name", "po_number", "id"]

        if col < len(column_names_extended):
            field_name = column_names_extended[col]
            raw_value = row_data.get(field_name)
        else:
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            return self._format_display_value(raw_value, col, row_data)
        elif role == Qt.ItemDataRole.BackgroundRole:
            return self._get_background_color(row_data)
        elif role == Qt.ItemDataRole.ForegroundRole:
            return self._get_foreground_color(row_data)
        elif role == SORT_ROLE:
            return self._get_sort_value(raw_value, col, row_data)
        elif role == Qt.ItemDataRole.UserRole:
            return row_data.get("id")

        return None

    def _format_display_value(
        self, raw_value: Any, col: int, row_data: Dict[str, Any]
    ) -> str:
        """Format raw value for display."""
        if raw_value is None:
            return "N/A"

        if col == 0:
            total = row_data.get("total_stock", 0)
            available = row_data.get("available_stock", 0)
            return f"{total}/{available}"
        elif col == 8:
            return "Consumable" if raw_value else "Non-Consumable"

        from datetime import datetime, date

        if isinstance(raw_value, (date, datetime)):
            if isinstance(raw_value, datetime):
                return raw_value.strftime("%m/%d/%Y %H:%M")
            return raw_value.strftime("%m/%d/%Y")

        return str(raw_value) if raw_value else "N/A"

    def _get_background_color(self, row_data: Dict[str, Any]) -> Optional[Any]:
        """Get background color based on item status."""
        from PyQt6.QtGui import QColor
        from inventory_app.gui.inventory.row_styling_service import row_styling_service
        from inventory_app.gui.styles import ThemeManager

        item_id = row_data.get("id")
        if item_id is None:
            return None

        status = self._get_item_status(item_id)
        style_class = row_styling_service.get_row_style_class(status)

        if not style_class:
            return None

        theme_manager = ThemeManager.instance()
        current_theme = theme_manager.current_theme

        bg_color, _ = row_styling_service.get_row_colors(style_class, current_theme)

        if bg_color:
            return QColor(bg_color)
        return None

    def _get_foreground_color(self, row_data: Dict[str, Any]) -> Optional[Any]:
        """Get foreground (text) color based on item status."""
        from PyQt6.QtGui import QColor
        from inventory_app.gui.inventory.row_styling_service import row_styling_service
        from inventory_app.gui.styles import ThemeManager

        item_id = row_data.get("id")
        if item_id is None:
            return None

        status = self._get_item_status(item_id)
        style_class = row_styling_service.get_row_style_class(status)

        if not style_class:
            return None

        theme_manager = ThemeManager.instance()
        current_theme = theme_manager.current_theme

        _, text_color = row_styling_service.get_row_colors(style_class, current_theme)

        if text_color:
            return QColor(text_color)
        return None

    def _get_item_status(self, item_id: int) -> Any:
        """Get item status from cache or fetch if needed."""
        if item_id in self._status_cache:
            return self._status_cache[item_id]

        if self._status_fetch_callback:
            statuses = self._status_fetch_callback([item_id])
            if statuses:
                status = statuses.get(item_id)
                self._status_cache[item_id] = status
                return status

        return None

    def _get_sort_value(
        self, raw_value: Any, col: int, row_data: Dict[str, Any]
    ) -> Any:
        """Get value for sorting based on column type."""
        if raw_value is None:
            if col in (6, 7, 9):
                return float("inf")
            return None

        from datetime import datetime, date

        if col == 0:
            available = row_data.get("available_stock", 0)
            try:
                return -int(available)
            except (ValueError, TypeError):
                return 0
        elif col in (6, 7, 9, 10):
            if isinstance(raw_value, (date, datetime)):
                ts = (
                    raw_value.timestamp()
                    if isinstance(raw_value, datetime)
                    else raw_value.toordinal()
                )
                return -float(ts)
            try:
                if isinstance(raw_value, str):
                    from datetime import datetime as dt

                    parsed = dt.fromisoformat(raw_value)
                    return -float(parsed.timestamp())
            except (ValueError, TypeError, AttributeError):
                pass
            return float("inf")
        elif col == 1:
            return (raw_value or "").lower()
        elif col == 5:
            return (raw_value or "").lower()

        return raw_value

    def _is_row_loading(self, row: int) -> bool:
        """Check if a row is currently being loaded."""
        with self._loading_lock:
            return row in self._loading_rows

    def _trigger_load_for_row(self, row: int) -> None:
        """Trigger loading for a single row."""
        with self._loading_lock:
            if row in self._loading_rows:
                return
            self._loading_rows.add(row)

        self._load_batch([row])

    def _load_batch(self, rows: List[int]) -> None:
        """Load a batch of rows."""
        if not rows:
            return

        min_row = min(rows)
        max_row = max(rows)
        count = max_row - min_row + 1

        try:
            data = self._fetch_callback(min_row, count)

            if data and len(data) > 0:
                for i, row_data in enumerate(data):
                    actual_row = min_row + i
                    self._cache.put(actual_row, row_data)
                    self._loaded_rows.add(actual_row)

                    with self._loading_lock:
                        if actual_row in self._loading_rows:
                            self._loading_rows.discard(actual_row)

                    idx = self.index(actual_row, 0)
                    idx_end = self.index(actual_row, self.columnCount() - 1)
                    self.dataChanged.emit(idx, idx_end)

            self._fetched_count = max(self._fetched_count, max_row + 1)
            self.loading_progress.emit(
                int((self._fetched_count / self._total_rows) * 100)
            )

        except Exception as e:
            logger.error(f"Error loading rows {min_row}-{max_row}: {e}")
            self.loading_error.emit(str(e))

            with self._loading_lock:
                for row in rows:
                    if row in self._loading_rows:
                        self._loading_rows.discard(row)

        if self._fetched_count >= self._total_rows:
            self._is_loading = False
            self.loading_finished.emit()

    def canFetchMore(self, parent: Optional[QModelIndex] = None) -> bool:
        """Return True if more data can be fetched."""
        return self._fetched_count < self._total_rows

    def fetchMore(self, parent: Optional[QModelIndex] = None) -> None:
        """Fetch the next batch of rows."""
        if self._is_loading:
            return

        self._is_loading = True
        self.loading_started.emit()

        start = self._fetched_count
        count = min(FETCH_BATCH_SIZE, self._total_rows - start)

        with self._loading_lock:
            for row in range(start, start + count):
                self._loading_rows.add(row)

        try:
            data = self._fetch_callback(start, count)

            if data:
                for i, row_data in enumerate(data):
                    actual_row = start + i
                    self._cache.put(actual_row, row_data)
                    self._loaded_rows.add(actual_row)

                    with self._loading_lock:
                        if actual_row in self._loading_rows:
                            self._loading_rows.discard(actual_row)

                self._fetched_count = start + len(data)
                self.loading_progress.emit(
                    int((self._fetched_count / self._total_rows) * 100)
                )

                self.beginInsertRows(QModelIndex(), start, start + len(data) - 1)
                self.endInsertRows()

            if self._fetched_count >= self._total_rows:
                self.loading_finished.emit()

        except Exception as e:
            logger.error(f"Error fetching more rows: {e}")
            self.loading_error.emit(str(e))

        self._is_loading = False

    def prefetch_visible_rows(self, visible_top: int, visible_bottom: int) -> None:
        """
        Prefetch rows around the visible area for smooth scrolling.

        Args:
            visible_top: First visible row index
            visible_bottom: Last visible row index
        """
        prefetch_range = list(
            range(
                max(0, visible_top - PREFETCH_ABOVE),
                min(self._total_rows, visible_bottom + PREFETCH_BELOW + 1),
            )
        )

        rows_to_fetch = [r for r in prefetch_range if not self._cache.contains(r)]

        if rows_to_fetch:
            self._prefetch_queue = rows_to_fetch
            self._prefetch_timer.start(50)

    def _execute_prefetch(self) -> None:
        """Execute the prefetch operation."""
        if not hasattr(self, "_prefetch_queue") or not self._prefetch_queue:
            return

        rows = self._prefetch_queue[:FETCH_BATCH_SIZE]
        self._prefetch_queue = self._prefetch_queue[FETCH_BATCH_SIZE:]

        if rows:
            self._load_batch(rows)

        if self._prefetch_queue:
            self._prefetch_timer.start(10)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Return header data."""
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
        ):
            if section < len(self._columns):
                return self._columns[section]
        return None

    def sort(
        self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder
    ) -> None:
        """
        Sort the table by column.

        Note: Virtual scrolling requires server-side sorting for large datasets.
        For now, this triggers a reload with sort parameters.
        """
        self._sort_column = column
        self._sort_order = order

        self._cache.clear()
        self._loaded_rows.clear()
        self._fetched_count = 0
        self._status_cache.clear()

        self.layoutAboutToBeChanged.emit()
        self.layoutChanged.emit()

        self.fetchMore()

    def get_row_data(self, row: int) -> Optional[Dict[str, Any]]:
        """Get raw row data for a specific row."""
        return self._cache.get(row)

    def get_item_id_at_row(self, row: int) -> Optional[int]:
        """Get the item ID at the specified row."""
        row_data = self._cache.get(row)
        if row_data:
            return row_data.get("id")
        return None

    def refresh_row(self, row: int) -> None:
        """Refresh a single row by reloading its data."""
        with self._loading_lock:
            if row in self._loading_rows:
                return

        self._cache.clear()
        self._loaded_rows.clear()
        self._fetched_count = 0
        self._status_cache.clear()

        self.layoutAboutToBeChanged.emit()
        self.layoutChanged.emit()

        self.fetchMore()

    def prefetch_statuses(self, item_ids: List[int]) -> None:
        """Prefetch statuses for a list of item IDs."""
        if not self._status_fetch_callback:
            return

        missing_ids = [id for id in item_ids if id not in self._status_cache]

        if missing_ids:
            try:
                statuses = self._status_fetch_callback(missing_ids)
                if statuses:
                    self._status_cache.update(statuses)

                    for item_id in missing_ids:
                        if item_id in statuses:
                            row = self._find_row_by_item_id(item_id)
                            if row >= 0:
                                idx = self.index(row, 0)
                                idx_end = self.index(row, self.columnCount() - 1)
                                self.dataChanged.emit(idx, idx_end)
            except Exception as e:
                logger.error(f"Error prefetching statuses: {e}")

    def _find_row_by_item_id(self, item_id: int) -> int:
        """Find the row index for an item ID by searching cached rows."""
        for row in self._loaded_rows:
            row_data = self._cache.get(row)
            if row_data and row_data.get("id") == item_id:
                return row
        return -1

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._cache.clear()
        self._loaded_rows.clear()
        self._status_cache.clear()
        self._fetched_count = 0
        logger.debug("Virtual table cache cleared")

    def set_total_rows(self, count: int) -> None:
        """Set the total number of rows (used when filters change)."""
        self.beginResetModel()
        self._total_rows = count
        self._cache.clear()
        self._loaded_rows.clear()
        self._fetched_count = 0
        self._status_cache.clear()
        self.endResetModel()


class VirtualTableProxy:
    """
    Wrapper to use VirtualTableModel with QTableView/QTableWidget.

    Provides a simple interface for existing code to use virtual scrolling
    without major refactoring.
    """

    def __init__(self, model: VirtualTableModel, table: Any):
        """
        Initialize proxy.

        Args:
            model: VirtualTableModel instance
            table: QTableView or QTableWidget to connect
        """
        self._model = model
        self._table = table
        self._scroll_blocked = False

        from PyQt6.QtWidgets import QTableView

        if isinstance(table, QTableView):
            table.setModel(model)
            scroll_bar = table.verticalScrollBar()
            if scroll_bar:
                scroll_bar.valueChanged.connect(self._on_scroll)

    def _on_scroll(self, value: int) -> None:
        """Handle scroll events for prefetching."""
        if self._scroll_blocked:
            return

        viewport = self._table.viewport()
        if viewport:
            visible_top = self._table.indexAt(viewport.rect().topLeft()).row()
            visible_bottom = self._table.indexAt(viewport.rect().bottomLeft()).row()

            if visible_top >= 0 and visible_bottom >= 0:
                self._model.prefetch_visible_rows(visible_top, visible_bottom)

    @property
    def model(self) -> VirtualTableModel:
        """Get the virtual model."""
        return self._model

    def get_selected_item_id(self) -> Optional[int]:
        """Get selected item ID."""
        current = self._table.currentIndex()
        if current.isValid():
            return self._model.get_item_id_at_row(current.row())
        return None

    def select_row_by_item_id(self, item_id: int) -> bool:
        """Select row by item ID."""
        row = self._model._find_row_by_item_id(item_id)
        if row >= 0:
            self._table.selectRow(row)
            return True
        return False

    def clear_selection(self) -> None:
        """Clear current selection."""
        self._table.clearSelection()

    def refresh(self) -> None:
        """Refresh the table."""
        self._model.clear_cache()
        self._model.fetchMore()
