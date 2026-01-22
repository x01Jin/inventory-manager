"""
Base async table model for PyQt6 tables with background data loading.

Provides a base class that wraps QTableWidget with async data loading
capabilities using QThreadPool workers. Uses signals for thread-safe
UI updates with beginInsertRows/endInsertRows pattern.
"""

from typing import Any, Callable, Dict, List, Optional
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QTableWidget, QProgressBar
from inventory_app.gui.utils.worker import (
    DataLoadWorker,
    worker_pool,
)
from inventory_app.utils.logger import logger


class AsyncTableSignals(QObject):
    """Signals for async table operations."""

    # Emitted when data loading starts
    loading_started = pyqtSignal()

    # Emitted with progress percentage during load
    loading_progress = pyqtSignal(int)

    # Emitted when data loading completes
    loading_finished = pyqtSignal()

    # Emitted on error with error message
    loading_error = pyqtSignal(str)

    # Emitted when rows should be inserted (start_row, rows_data)
    rows_ready = pyqtSignal(int, list)


class AsyncTableModel(QObject):
    """
    Base model for async table data loading.

    Handles background data loading and emits signals for
    thread-safe table updates. Subclasses should implement
    the load_data method.
    """

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.signals = AsyncTableSignals()
        self._current_worker: Optional[DataLoadWorker] = None
        self._data: List[Dict[str, Any]] = []
        self._is_loading = False
        self._batch_size = 100

    @property
    def is_loading(self) -> bool:
        """Check if currently loading data."""
        return self._is_loading

    @property
    def data(self) -> List[Dict[str, Any]]:
        """Get the current loaded data."""
        return self._data

    @property
    def row_count(self) -> int:
        """Get the current row count."""
        return len(self._data)

    def set_batch_size(self, size: int) -> None:
        """Set the batch size for data loading."""
        self._batch_size = max(10, size)

    def load_data(self) -> List[Dict[str, Any]]:
        """
        Load data from source. Override in subclasses.

        Returns:
            List of row dictionaries
        """
        raise NotImplementedError("Subclasses must implement load_data()")

    def start_async_load(self) -> None:
        """Start asynchronous data loading."""
        # Cancel any existing load
        self.cancel_load()

        self._is_loading = True
        self._data = []
        self.signals.loading_started.emit()

        # Create worker for data loading
        self._current_worker = DataLoadWorker(
            self.load_data, batch_size=self._batch_size
        )

        # Connect signals
        self._current_worker.signals.data_ready.connect(self._on_batch_ready)
        self._current_worker.signals.result.connect(self._on_load_complete)
        self._current_worker.signals.error.connect(self._on_load_error)
        self._current_worker.signals.progress.connect(self._on_progress)
        self._current_worker.signals.finished.connect(self._on_finished)

        # Start worker
        worker_pool.start(self._current_worker)
        logger.debug(f"Started async load for {self.__class__.__name__}")

    def cancel_load(self) -> None:
        """Cancel any ongoing data load."""
        if self._current_worker:
            self._current_worker.cancel()
            self._current_worker = None
        self._is_loading = False

    def _on_batch_ready(self, batch: List[Dict[str, Any]]) -> None:
        """Handle batch of data ready."""
        start_row = len(self._data)
        self._data.extend(batch)
        self.signals.rows_ready.emit(start_row, batch)

    def _on_load_complete(self, all_data: List[Dict[str, Any]]) -> None:
        """Handle complete data load."""
        self._data = all_data
        logger.debug(f"Async load complete: {len(all_data)} rows")

    def _on_load_error(self, error_tuple: tuple) -> None:
        """Handle load error."""
        self._is_loading = False
        exctype, value, tb = error_tuple
        error_msg = f"{exctype.__name__}: {value}"
        logger.error(f"Async load error: {error_msg}\n{tb}")
        self.signals.loading_error.emit(error_msg)

    def _on_progress(self, progress: int) -> None:
        """Handle progress update."""
        self.signals.loading_progress.emit(progress)

    def _on_finished(self) -> None:
        """Handle load finished."""
        self._is_loading = False
        self._current_worker = None
        self.signals.loading_finished.emit()


class AsyncTableController:
    """
    Controller for managing async table widget updates.

    Connects an AsyncTableModel to a QTableWidget and handles
    thread-safe row insertion using proper Qt patterns.
    """

    def __init__(
        self,
        table: QTableWidget,
        model: AsyncTableModel,
        row_factory: Callable[[int, Dict[str, Any]], None],
        progress_bar: Optional[QProgressBar] = None,
    ):
        """
        Initialize the controller.

        Args:
            table: The QTableWidget to populate
            model: The AsyncTableModel providing data
            row_factory: Function to populate a single row (row_index, data_dict)
            progress_bar: Optional progress bar widget
        """
        self.table = table
        self.model = model
        self.row_factory = row_factory
        self.progress_bar = progress_bar

        # Connect model signals
        self.model.signals.loading_started.connect(self._on_loading_started)
        self.model.signals.rows_ready.connect(self._on_rows_ready)
        self.model.signals.loading_progress.connect(self._on_progress)
        self.model.signals.loading_finished.connect(self._on_loading_finished)
        self.model.signals.loading_error.connect(self._on_error)

    def start_load(self) -> None:
        """Start loading data asynchronously."""
        self.model.start_async_load()

    def cancel_load(self) -> None:
        """Cancel any ongoing load."""
        self.model.cancel_load()

    def _on_loading_started(self) -> None:
        """Handle load started."""
        # Disable sorting during load
        self._prev_sorting = self.table.isSortingEnabled()
        self.table.setSortingEnabled(False)

        # Clear existing rows
        self.table.setRowCount(0)

        # Show progress bar
        if self.progress_bar:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)

        logger.debug("Table loading started")

    def _on_rows_ready(self, start_row: int, batch: List[Dict[str, Any]]) -> None:
        """
        Handle batch of rows ready for insertion.

        Uses proper Qt pattern for row insertion to avoid UI freezes.
        """
        if not batch:
            return

        # Get current row count and new row count
        current_count = self.table.rowCount()
        new_count = current_count + len(batch)

        # Expand table for new rows
        self.table.setRowCount(new_count)

        # Populate each row in the batch
        for i, row_data in enumerate(batch):
            row_index = start_row + i
            try:
                self.row_factory(row_index, row_data)
            except Exception as e:
                logger.error(f"Error populating row {row_index}: {e}")

    def _on_progress(self, progress: int) -> None:
        """Handle progress update."""
        if self.progress_bar:
            self.progress_bar.setValue(progress)

    def _on_loading_finished(self) -> None:
        """Handle load finished."""
        # Restore sorting
        self.table.setSortingEnabled(getattr(self, "_prev_sorting", True))

        # Apply default sort if needed
        if self.table.isSortingEnabled():
            header = self.table.horizontalHeader()
            if header:
                section = header.sortIndicatorSection()
                order = header.sortIndicatorOrder()
                if section >= 0:
                    self.table.sortItems(section, order)

        # Hide progress bar
        if self.progress_bar:
            self.progress_bar.setVisible(False)

        logger.debug(f"Table loading finished: {self.table.rowCount()} rows")

    def _on_error(self, error_msg: str) -> None:
        """Handle load error."""
        if self.progress_bar:
            self.progress_bar.setVisible(False)

        # Restore sorting
        self.table.setSortingEnabled(getattr(self, "_prev_sorting", True))

        logger.error(f"Table load error: {error_msg}")
