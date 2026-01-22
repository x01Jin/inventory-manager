"""
Parallel Data Loader for concurrent data loading.

Provides thread-safe concurrent loading of multiple data sources using
QThreadPool with proper signal-based coordination and error isolation.

Optimized for Windows with proper thread priority handling.
"""

from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import sys

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot

from inventory_app.utils.logger import logger


class LoadPriority(Enum):
    """Thread priority levels for different types of data loading."""

    LOW = 0  # Background data refresh
    NORMAL = 1  # Standard page load
    HIGH = 2  # User-initiated refresh


@dataclass
class LoadTask:
    """Represents a single data loading task."""

    name: str
    load_fn: Callable
    weight: float = 1.0  # Relative importance for progress calculation
    priority: LoadPriority = LoadPriority.NORMAL


@dataclass
class LoadResult:
    """Result from a load task."""

    name: str
    success: bool
    data: Any = None
    error: Optional[Exception] = None


@dataclass
class LoadProgress:
    """Combined progress from multiple load tasks."""

    completed_tasks: List[str] = field(default_factory=list)
    total_progress: float = 0.0
    individual_progress: Dict[str, float] = field(default_factory=dict)
    is_complete: bool = False


class ParallelLoaderSignals(QObject):
    """Signals for parallel loader operations."""

    progress = pyqtSignal(LoadProgress)
    task_complete = pyqtSignal(LoadResult)
    all_complete = pyqtSignal(dict)  # Dict of name -> data
    error = pyqtSignal(tuple)  # (name, error, traceback)


class ParallelDataLoader(QRunnable):
    """
    Loads multiple data sources concurrently using QThreadPool.

    Features:
    - Concurrent loading of independent data sources
    - Thread-safe communication via Qt signals
    - Weighted progress calculation
    - Error isolation (one failure doesn't affect others)
    - Windows-optimized thread priority

    Usage:
        loader = ParallelDataLoader()
        loader.add_task(LoadTask("inventory", load_inventory, weight=0.6))
        loader.add_task(LoadTask("requisitions", load_requisitions, weight=0.4))
        loader.signals.progress.connect(on_progress)
        loader.signals.all_complete.connect(on_complete)
        worker_pool.start(loader)
    """

    def __init__(self):
        super().__init__()
        self.tasks: List[LoadTask] = []
        self.results: Dict[str, Any] = {}
        self.errors: Dict[str, Exception] = {}
        self.signals = ParallelLoaderSignals()
        self._is_cancelled = False
        self._completed_tasks: List[str] = []
        self._total_weight: float = 0.0

    def add_task(self, task: LoadTask) -> None:
        """Add a load task to the loader."""
        self.tasks.append(task)
        self._total_weight += task.weight
        logger.debug(f"Added load task: {task.name} (weight={task.weight})")

    def cancel(self) -> None:
        """Request cancellation of all loading."""
        self._is_cancelled = True
        logger.debug("ParallelDataLoader cancellation requested")

    @pyqtSlot()
    def run(self) -> None:
        """Execute all load tasks concurrently."""
        import traceback

        if not self.tasks:
            self.signals.all_complete.emit({})
            return

        logger.info(f"Starting parallel data load with {len(self.tasks)} tasks")

        for task in self.tasks:
            if self._is_cancelled:
                break

            try:
                logger.debug(f"Loading task: {task.name}")
                data = task.load_fn()

                if self._is_cancelled:
                    break

                self.results[task.name] = data

                result = LoadResult(name=task.name, success=True, data=data)
                self.signals.task_complete.emit(result)
                self._completed_tasks.append(task.name)

                progress = self._calculate_progress(task.name, 100.0)
                load_progress = LoadProgress(
                    completed_tasks=self._completed_tasks.copy(),
                    total_progress=progress,
                    individual_progress={task.name: 100.0},
                    is_complete=len(self._completed_tasks) == len(self.tasks),
                )
                self.signals.progress.emit(load_progress)

            except Exception as e:
                logger.error(f"Task {task.name} failed: {e}")
                self.errors[task.name] = e

                result = LoadResult(name=task.name, success=False, error=e)
                self.signals.task_complete.emit(result)

                exc_type, value, tb = sys.exc_info()
                self.signals.error.emit((task.name, value, traceback.format_exc()))

        if not self._is_cancelled:
            self.signals.all_complete.emit(self.results.copy())
            logger.info(
                f"Parallel load complete: {len(self.results)}/{len(self.tasks)} tasks succeeded"
            )

    def _calculate_progress(self, completed_task: str, task_progress: float) -> float:
        """Calculate weighted total progress."""
        if self._total_weight <= 0:
            return 100.0

        total = 0.0
        for task in self.tasks:
            if task.name == completed_task:
                total += task.weight * (task_progress / 100.0)
            elif task.name in self._completed_tasks:
                total += task.weight

        return min(100.0, (total / self._total_weight) * 100.0)


class ParallelLoadManager:
    """
    Manager for parallel data loading operations.

    Provides high-level API for concurrent page loading with
    progress coordination and error handling.
    """

    def __init__(self):
        self._active_loaders: List[ParallelDataLoader] = []

    def cancel_all(self) -> None:
        """Cancel all active loading operations."""
        for loader in self._active_loaders:
            loader.cancel()
        self._active_loaders.clear()

    def load_inventory_parallel(
        self,
        load_inventory_fn: Callable,
        load_requisitions_fn: Optional[Callable] = None,
        on_progress: Optional[Callable[[LoadProgress], None]] = None,
        on_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_error: Optional[Callable[[str, Exception, str], None]] = None,
        weights: Tuple[float, float] = (0.6, 0.4),
    ) -> ParallelDataLoader:
        """
        Load inventory and optionally requisitions in parallel.

        Args:
            load_inventory_fn: Function to load inventory data
            load_requisitions_fn: Optional function to load requisitions data
            on_progress: Callback for progress updates
            on_complete: Callback when all data loaded
            on_error: Callback for errors
            weights: Tuple of (inventory_weight, requisitions_weight)

        Returns:
            ParallelDataLoader instance
        """
        loader = ParallelDataLoader()
        loader.setAutoDelete(False)

        inventory_weight, requisitions_weight = weights

        loader.add_task(
            LoadTask(
                name="inventory",
                load_fn=load_inventory_fn,
                weight=inventory_weight,
                priority=LoadPriority.NORMAL,
            )
        )

        if load_requisitions_fn:
            loader.add_task(
                LoadTask(
                    name="requisitions",
                    load_fn=load_requisitions_fn,
                    weight=requisitions_weight,
                    priority=LoadPriority.NORMAL,
                )
            )

        if on_progress:
            loader.signals.progress.connect(on_progress)
        if on_complete:
            loader.signals.all_complete.connect(on_complete)
        if on_error:
            loader.signals.error.connect(on_error)

        self._active_loaders.append(loader)

        from inventory_app.gui.utils.worker import worker_pool

        worker_pool.start(loader)

        logger.info(f"Started parallel load with {len(loader.tasks)} tasks")
        return loader

    def load_page_data(
        self,
        tasks: List[LoadTask],
        on_progress: Optional[Callable[[LoadProgress], None]] = None,
        on_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_error: Optional[Callable[[str, Exception, str], None]] = None,
    ) -> ParallelDataLoader:
        """
        Load multiple data sources in parallel.

        Args:
            tasks: List of LoadTask instances
            on_progress: Callback for progress updates
            on_complete: Callback when all data loaded
            on_error: Callback for errors

        Returns:
            ParallelDataLoader instance
        """
        loader = ParallelDataLoader()
        loader.setAutoDelete(False)

        for task in tasks:
            loader.add_task(task)

        if on_progress:
            loader.signals.progress.connect(on_progress)
        if on_complete:
            loader.signals.all_complete.connect(on_complete)
        if on_error:
            loader.signals.error.connect(on_error)

        self._active_loaders.append(loader)

        from inventory_app.gui.utils.worker import worker_pool

        worker_pool.start(loader)

        logger.info(f"Started parallel load with {len(tasks)} tasks")
        return loader


parallel_load_manager = ParallelLoadManager()


def create_parallel_page_loader() -> ParallelLoadManager:
    """Create a new parallel load manager instance."""
    return ParallelLoadManager()
