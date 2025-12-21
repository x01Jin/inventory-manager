"""
Background worker utilities using QThreadPool and QRunnable.

Provides thread-safe background task execution for heavy database operations
and data processing without blocking the main GUI thread.

Usage:
    1. Create a Worker with a function and optional args/kwargs
    2. Connect signals for results, errors, progress
    3. Execute via WorkerPool.start(worker)
"""

from typing import Any, Callable, Optional, Tuple
from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal, pyqtSlot
from inventory_app.utils.logger import logger


class WorkerSignals(QObject):
    """
    Defines signals available from a running worker thread.

    Signals:
        finished: Emitted when task completes (no data)
        error: Emitted on exception (exception tuple)
        result: Emitted with task return value
        progress: Emitted with progress percentage (0-100)
        data_ready: Emitted with list of rows for batch table updates
    """

    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)
    data_ready = pyqtSignal(list)


class Worker(QRunnable):
    """
    Worker thread using QRunnable for background task execution.

    Inherits from QRunnable to be executed by QThreadPool.
    Emits signals for results, errors, and progress updates.
    """

    def __init__(
        self,
        fn: Callable,
        *args,
        progress_callback: Optional[Callable[[int], None]] = None,
        **kwargs,
    ):
        """
        Initialize worker with a function to execute.

        Args:
            fn: Function to execute in background
            *args: Arguments to pass to function
            progress_callback: Optional callback for progress updates
            **kwargs: Keyword arguments to pass to function
        """
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.progress_callback = progress_callback
        self._is_cancelled = False

        # Pass progress callback to function if it accepts it
        if progress_callback:
            self.kwargs["progress_callback"] = self._emit_progress

    def _emit_progress(self, value: int) -> None:
        """Emit progress signal with value 0-100."""
        if not self._is_cancelled:
            self.signals.progress.emit(value)

    def cancel(self) -> None:
        """Request cancellation of the worker."""
        self._is_cancelled = True

    def is_cancelled(self) -> bool:
        """Check if cancellation was requested."""
        return self._is_cancelled

    @pyqtSlot()
    def run(self) -> None:
        """Execute the function with error handling."""
        try:
            if self._is_cancelled:
                return

            result = self.fn(*self.args, **self.kwargs)

            if not self._is_cancelled:
                self.signals.result.emit(result)

        except Exception as e:
            import traceback
            import sys

            logger.error(f"Worker error: {e}")
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))

        finally:
            if not self._is_cancelled:
                self.signals.finished.emit()


class DataLoadWorker(QRunnable):
    """
    Specialized worker for loading data in batches.

    Emits data_ready signals with batches of rows to allow
    progressive table population without blocking.
    """

    def __init__(self, load_fn: Callable, batch_size: int = 100, *args, **kwargs):
        """
        Initialize data load worker.

        Args:
            load_fn: Function that returns list of data rows
            batch_size: Number of rows per batch emission
            *args: Arguments for load function
            **kwargs: Keyword arguments for load function
        """
        super().__init__()
        self.load_fn = load_fn
        self.batch_size = batch_size
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self._is_cancelled = False

    def cancel(self) -> None:
        """Request cancellation."""
        self._is_cancelled = True

    @pyqtSlot()
    def run(self) -> None:
        """Load data and emit in batches."""
        try:
            if self._is_cancelled:
                return

            # Execute load function to get all data
            all_data = self.load_fn(*self.args, **self.kwargs)

            if self._is_cancelled:
                return

            if not all_data:
                self.signals.data_ready.emit([])
                self.signals.progress.emit(100)
                self.signals.finished.emit()
                return

            total_rows = len(all_data)

            # Emit data in batches for progressive loading
            for i in range(0, total_rows, self.batch_size):
                if self._is_cancelled:
                    return

                batch = all_data[i : i + self.batch_size]
                self.signals.data_ready.emit(batch)

                # Calculate and emit progress
                progress = min(100, int((i + len(batch)) / total_rows * 100))
                self.signals.progress.emit(progress)

            # Emit final result with all data
            self.signals.result.emit(all_data)

        except Exception as e:
            import traceback
            import sys

            logger.error(f"DataLoadWorker error: {e}")
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))

        finally:
            if not self._is_cancelled:
                self.signals.finished.emit()


class WorkerPool:
    """
    Singleton manager for the application's thread pool.

    Provides centralized control over background workers
    with configurable thread count for different hardware.
    """

    _instance: Optional["WorkerPool"] = None
    _pool: Optional[QThreadPool] = None

    def __new__(cls) -> "WorkerPool":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._pool is None:
            self._pool = QThreadPool.globalInstance()
            if self._pool is not None:
                # Configure for weak/old CPUs - limit thread count
                # Default is usually CPU count, we cap it for older hardware
                max_threads = min(self._pool.maxThreadCount(), 4)
                self._pool.setMaxThreadCount(max_threads)
                logger.info(f"WorkerPool initialized with {max_threads} threads")

    @property
    def pool(self) -> Optional[QThreadPool]:
        """Get the thread pool instance."""
        return self._pool

    def start(self, worker: QRunnable, priority: int = 0) -> None:
        """
        Start a worker in the thread pool.

        Args:
            worker: QRunnable worker to execute
            priority: Execution priority (higher = sooner)
        """
        if self._pool is not None:
            self._pool.start(worker, priority)

    def clear(self) -> None:
        """Clear all pending workers from the pool."""
        if self._pool is not None:
            self._pool.clear()

    def wait_for_done(self, msecs: int = -1) -> bool:
        """
        Wait for all workers to complete.

        Args:
            msecs: Timeout in milliseconds (-1 for infinite)

        Returns:
            True if all workers completed, False on timeout
        """
        if self._pool is not None:
            return self._pool.waitForDone(msecs)
        return True

    @property
    def active_thread_count(self) -> int:
        """Get number of active threads."""
        if self._pool is not None:
            return self._pool.activeThreadCount()
        return 0

    def set_max_threads(self, count: int) -> None:
        """
        Set maximum thread count.

        Args:
            count: Maximum number of concurrent threads
        """
        if self._pool is not None:
            self._pool.setMaxThreadCount(count)
            logger.info(f"WorkerPool max threads set to {count}")


# Global worker pool instance
worker_pool = WorkerPool()


def run_in_background(
    fn: Callable,
    *args,
    on_result: Optional[Callable[[Any], None]] = None,
    on_error: Optional[Callable[[Tuple], None]] = None,
    on_finished: Optional[Callable[[], None]] = None,
    on_progress: Optional[Callable[[int], None]] = None,
    **kwargs,
) -> Worker:
    """
    Convenience function to run a task in the background.

    Args:
        fn: Function to execute
        *args: Arguments for function
        on_result: Callback for successful result
        on_error: Callback for errors
        on_finished: Callback when task completes
        on_progress: Callback for progress updates
        **kwargs: Keyword arguments for function

    Returns:
        Worker instance (can be used for cancellation)
    """
    worker = Worker(fn, *args, **kwargs)

    if on_result:
        worker.signals.result.connect(on_result)
    if on_error:
        worker.signals.error.connect(on_error)
    if on_finished:
        worker.signals.finished.connect(on_finished)
    if on_progress:
        worker.signals.progress.connect(on_progress)

    worker_pool.start(worker)
    return worker


def load_data_in_background(
    load_fn: Callable,
    *args,
    batch_size: int = 50,
    on_batch: Optional[Callable[[list], None]] = None,
    on_complete: Optional[Callable[[list], None]] = None,
    on_error: Optional[Callable[[Tuple], None]] = None,
    on_progress: Optional[Callable[[int], None]] = None,
    **kwargs,
) -> DataLoadWorker:
    """
    Convenience function to load data in background with batching.

    Args:
        load_fn: Function that returns list of data
        *args: Arguments for load function
        batch_size: Rows per batch emission
        on_batch: Callback for each batch of rows
        on_complete: Callback when all data loaded
        on_error: Callback for errors
        on_progress: Callback for progress updates
        **kwargs: Keyword arguments for load function

    Returns:
        DataLoadWorker instance
    """
    worker = DataLoadWorker(load_fn, batch_size, *args, **kwargs)

    if on_batch:
        worker.signals.data_ready.connect(on_batch)
    if on_complete:
        worker.signals.result.connect(on_complete)
    if on_error:
        worker.signals.error.connect(on_error)
    if on_progress:
        worker.signals.progress.connect(on_progress)

    worker_pool.start(worker)
    return worker
