"""
Dashboard page component for the laboratory inventory application.
Focused on key metrics and quick access to main functions.
"""

from functools import partial

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QGroupBox,
    QTabWidget,
)
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from inventory_app.gui.styles import get_current_theme
from inventory_app.utils.logger import logger
from .metrics import MetricsManager
from .activity import ActivityManager
from .alerts import AlertsManager
from .schedule_chart import ScheduleChartManager
from .metrics_worker import get_consolidated_metrics
from inventory_app.gui.utils.worker import worker_pool, Worker


class DashboardSignals(QObject):
    """Signals for dashboard data loading."""

    metrics_loaded = pyqtSignal(dict)
    activity_loaded = pyqtSignal(list)
    alerts_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str)


class DashboardPage(QWidget):
    """Dashboard page with laboratory inventory overview."""

    def __init__(self):
        super().__init__()

        self.signals = DashboardSignals()
        Theme = get_current_theme()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header = QLabel("📊 Lab Inventory Dashboard")
        header.setStyleSheet(
            f"font-size: {Theme.FONT_SIZE_TITLE}pt; font-weight: bold; color: {Theme.TEXT_PRIMARY}; margin-bottom: 2px;"
        )
        layout.addWidget(header)

        self.dashboard_loading_status = QLabel("")
        self.dashboard_loading_status.setStyleSheet(
            f"font-size: {max(8, Theme.FONT_SIZE_NORMAL - 1)}pt; color: {Theme.TEXT_SECONDARY}; margin-left: 2px;"
        )
        self.dashboard_loading_status.setVisible(False)

        self.metrics_manager = MetricsManager()
        self.activity_manager = ActivityManager()
        self.alerts_manager = AlertsManager()
        self.schedule_manager = ScheduleChartManager()

        self.metrics_widget = self.metrics_manager.create_metrics_widget(loading=True)
        self.activity_text = self.activity_manager.create_activity_widget()
        self.alerts_table = self.alerts_manager.create_alerts_table()
        self.all_alerts_table = self.alerts_manager.create_full_alerts_table()
        self.schedule_placeholder = self.schedule_manager.create_schedule_chart_widget()

        grid_layout = QGridLayout()
        grid_layout.setSpacing(8)

        metrics_group = QGroupBox("📊 Key Metrics")
        metrics_layout = QVBoxLayout(metrics_group)
        metrics_layout.addWidget(self.metrics_widget)
        grid_layout.addWidget(metrics_group, 0, 0)

        activity_group = QGroupBox("📝 Recent Activity")
        activity_layout = QVBoxLayout(activity_group)
        activity_layout.addWidget(self.activity_text)
        grid_layout.addWidget(activity_group, 0, 1)

        schedule_group = QGroupBox("⏰ Schedule Chart")
        schedule_layout = QVBoxLayout(schedule_group)
        schedule_layout.addWidget(self.schedule_placeholder)
        grid_layout.addWidget(schedule_group, 1, 0)

        alerts_group = QGroupBox("🚨 Critical Alerts")
        alerts_layout = QVBoxLayout(alerts_group)
        alerts_tabs = QTabWidget()
        alerts_tabs.addTab(self.alerts_table, "Summary")
        alerts_tabs.addTab(self.all_alerts_table, "All Alerts")
        alerts_layout.addWidget(alerts_tabs)
        grid_layout.addWidget(alerts_group, 1, 1)

        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 1)
        grid_layout.setRowStretch(0, 1)
        grid_layout.setRowStretch(1, 1)

        layout.addLayout(grid_layout)
        layout.addWidget(self.dashboard_loading_status)

        self._metrics_worker = None
        self._metrics_prepare_worker = None
        self._activity_worker = None
        self._alerts_worker = None
        self._schedule_worker = None
        self._refresh_scheduled = False
        self._load_total = 4
        self._load_completed = 0
        self._load_errors = 0
        self._load_finished_sections = set()
        self._load_cycle_id = 0
        self._is_disposing = False

        self.destroyed.connect(self._on_destroyed)

        self.refresh_data()

    def refresh_data(self):
        """Refresh dashboard data asynchronously."""
        try:
            if self._refresh_scheduled or self._is_disposing:
                return
            self._refresh_scheduled = True

            self._cancel_active_workers()
            cycle_id = self._start_loading_cycle()

            self._load_metrics_async(cycle_id)
            self._load_activity_async(cycle_id)
            self._load_alerts_async(cycle_id)
            self._load_schedule_async(cycle_id)

            # Allow a quick follow-up refresh after current work is queued.
            QTimer.singleShot(250, self._reset_refresh_scheduled)

        except Exception as e:
            self._refresh_scheduled = False
            logger.error(f"Failed to refresh dashboard: {e}")

    def _reset_refresh_scheduled(self):
        """Reset refresh guard for subsequent requests."""
        self._refresh_scheduled = False

    def _start_loading_cycle(self):
        """Reset loading state and show subtle staged status."""
        self._load_cycle_id += 1
        self._load_completed = 0
        self._load_errors = 0
        self._load_finished_sections.clear()
        self._set_loading_status_visible(True)
        self._set_loading_status_text(
            f"Loading dashboard data (0/{self._load_total})..."
        )
        return self._load_cycle_id

    def _mark_section_complete(
        self, cycle_id: int, section_name: str, success: bool = True
    ):
        """Update staged loading text as each dashboard section completes."""
        if not self._is_cycle_active(cycle_id) or self._is_disposing:
            return

        if section_name in self._load_finished_sections:
            return

        self._load_finished_sections.add(section_name)
        self._load_completed += 1
        if not success:
            self._load_errors += 1

        section_label = section_name.replace("_", " ").title()
        self._set_loading_status_text(
            f"Loading dashboard data ({self._load_completed}/{self._load_total}) - {section_label} ready"
        )

        if self._load_completed >= self._load_total:
            if self._load_errors:
                self._set_loading_status_text(
                    f"Dashboard loaded with {self._load_errors} section error(s)"
                )
            else:
                self._set_loading_status_text("Dashboard ready")
            QTimer.singleShot(1500, self._hide_loading_status)

    def _hide_loading_status(self):
        """Hide staged loading status after completion message is shown."""
        if self._load_completed >= self._load_total:
            self._set_loading_status_visible(False)

    def _is_cycle_active(self, cycle_id: int) -> bool:
        """Check if callback belongs to current refresh cycle."""
        return cycle_id == self._load_cycle_id

    def _set_loading_status_text(self, text: str) -> None:
        """Set loading text safely during rapid page teardown/navigation."""
        if self._is_disposing:
            return
        try:
            if self.dashboard_loading_status is not None:
                self.dashboard_loading_status.setText(text)
        except RuntimeError:
            # Widget can be deleted while queued callbacks are still flushing.
            return

    def _set_loading_status_visible(self, visible: bool) -> None:
        """Toggle loading status visibility safely."""
        if self._is_disposing:
            return
        try:
            if self.dashboard_loading_status is not None:
                self.dashboard_loading_status.setVisible(visible)
        except RuntimeError:
            return

    def _cancel_active_workers(self):
        """Cancel all active dashboard workers."""
        for worker_attr in (
            "_metrics_worker",
            "_metrics_prepare_worker",
            "_activity_worker",
            "_alerts_worker",
            "_schedule_worker",
        ):
            worker = getattr(self, worker_attr, None)
            if worker:
                worker.cancel()
                setattr(self, worker_attr, None)

    def _on_destroyed(self, *_args):
        """Ensure queued worker callbacks no-op after page destruction."""
        self._is_disposing = True
        self._load_cycle_id += 1
        self._cancel_active_workers()

    def closeEvent(self, a0):
        """Cancel workers when page is closing to avoid stale callback updates."""
        self._is_disposing = True
        self._load_cycle_id += 1
        self._cancel_active_workers()
        super().closeEvent(a0)

    def _load_metrics_async(self, cycle_id: int):
        """Load metrics in background thread."""
        if self._metrics_worker and worker_pool.active_thread_count > 0:
            self._metrics_worker.cancel()
        if self._metrics_prepare_worker and worker_pool.active_thread_count > 0:
            self._metrics_prepare_worker.cancel()

        self._metrics_worker = Worker(get_consolidated_metrics)
        self._metrics_worker.signals.result.connect(
            partial(self._on_metrics_loaded, cycle_id)
        )
        self._metrics_worker.signals.error.connect(
            partial(self._on_metrics_error, cycle_id)
        )
        worker_pool.start(self._metrics_worker)

    def _on_metrics_loaded(self, cycle_id: int, metrics: dict):
        """Handle loaded metrics data."""
        if not self._is_cycle_active(cycle_id) or self._is_disposing:
            return

        self._metrics_prepare_worker = Worker(
            self.metrics_manager.prepare_metrics_display_values,
            metrics,
        )
        self._metrics_prepare_worker.signals.result.connect(
            partial(self._on_metrics_display_values_ready, cycle_id)
        )
        self._metrics_prepare_worker.signals.error.connect(
            partial(self._on_metrics_error, cycle_id)
        )
        worker_pool.start(self._metrics_prepare_worker)

    def _on_metrics_display_values_ready(self, cycle_id: int, display_values: dict):
        """Apply metrics UI updates in small event-loop-friendly batches."""
        if not self._is_cycle_active(cycle_id) or self._is_disposing:
            return

        self.metrics_manager.update_metrics_widget_async(
            self.metrics_widget,
            display_values,
            on_complete=partial(self._mark_section_complete, cycle_id, "metrics", True),
            batch_size=3,
        )

    def _on_metrics_error(self, cycle_id: int, error: tuple):
        """Handle metrics loading error."""
        if not self._is_cycle_active(cycle_id) or self._is_disposing:
            return

        _exctype, value, _traceback = error
        logger.error(f"Metrics loading failed: {value}")
        self._mark_section_complete(cycle_id, "metrics", success=False)
        self.signals.error_occurred.emit(str(value))

    def _load_activity_async(self, cycle_id: int):
        """Load activity data in background thread."""
        if self._activity_worker:
            self._activity_worker.cancel()

        logger.debug("Starting activity data load")
        self._activity_worker = Worker(self.activity_manager.load_activity_data)
        self._activity_worker.signals.result.connect(
            partial(self._on_activity_loaded, cycle_id)
        )
        self._activity_worker.signals.error.connect(
            partial(self._on_activity_error, cycle_id)
        )
        worker_pool.start(self._activity_worker)

    def _on_activity_loaded(self, cycle_id: int, data):
        """Handle loaded activity data."""
        if not self._is_cycle_active(cycle_id) or self._is_disposing:
            return

        logger.debug(f"Activity data received: {len(data) if data else 0} items")
        try:
            self.activity_manager.populate_activity_widget(self.activity_text, data)
        except RuntimeError:
            return
        self._mark_section_complete(cycle_id, "activity")

    def _on_activity_error(self, cycle_id: int, error):
        """Handle activity loading error."""
        if not self._is_cycle_active(cycle_id) or self._is_disposing:
            return

        logger.error(f"Activity loading failed: {error}")
        self._mark_section_complete(cycle_id, "activity", success=False)

    def _load_alerts_async(self, cycle_id: int):
        """Load alerts data in background thread."""
        if self._alerts_worker:
            self._alerts_worker.cancel()

        self._alerts_worker = Worker(self.alerts_manager.load_alerts_payload)
        self._alerts_worker.signals.result.connect(
            partial(self._on_alerts_loaded, cycle_id)
        )
        self._alerts_worker.signals.error.connect(
            partial(self._on_alerts_error, cycle_id)
        )
        worker_pool.start(self._alerts_worker)

    def _on_alerts_loaded(self, cycle_id: int, payload):
        """Render both summary and full alerts tabs from loaded payload."""
        if not self._is_cycle_active(cycle_id) or self._is_disposing:
            return

        if not isinstance(payload, dict):
            payload = {"summary": [], "full": []}

        try:
            self.alerts_manager.populate_alerts_table(
                self.alerts_table,
                payload.get("summary", []),
            )
        except RuntimeError:
            return
        # Defer large full-table paint one event tick so summary becomes interactive first.
        QTimer.singleShot(
            0,
            partial(
                self._finalize_alerts_population,
                cycle_id,
                payload.get("full", []),
            ),
        )

    def _finalize_alerts_population(self, cycle_id: int, full_alerts):
        """Finalize deferred alerts table rendering for the active load cycle."""
        if not self._is_cycle_active(cycle_id) or self._is_disposing:
            return

        try:
            self.alerts_manager.populate_full_alerts_table(
                self.all_alerts_table,
                full_alerts,
            )
        except RuntimeError:
            return
        self._mark_section_complete(cycle_id, "alerts")

    def _on_alerts_error(self, cycle_id: int, error):
        """Handle alerts loading error."""
        if not self._is_cycle_active(cycle_id) or self._is_disposing:
            return

        logger.error(f"Alerts loading failed: {error}")
        self._mark_section_complete(cycle_id, "alerts", success=False)

    def _load_schedule_async(self, cycle_id: int):
        """Load schedule data in background thread."""
        if self._schedule_worker:
            self._schedule_worker.cancel()

        self._schedule_worker = Worker(self.schedule_manager.get_upcoming_requisitions)
        self._schedule_worker.signals.result.connect(
            partial(self._on_schedule_loaded, cycle_id)
        )
        self._schedule_worker.signals.error.connect(
            partial(self._on_schedule_error, cycle_id)
        )
        worker_pool.start(self._schedule_worker)

    def _on_schedule_loaded(self, cycle_id: int, requisitions):
        """Handle loaded schedule data."""
        if not self._is_cycle_active(cycle_id) or self._is_disposing:
            return

        try:
            self.schedule_manager.populate_schedule_chart(
                self.schedule_placeholder,
                requisitions or [],
            )
        except RuntimeError:
            return
        self._mark_section_complete(cycle_id, "schedule")

    def _on_schedule_error(self, cycle_id: int, error):
        """Handle schedule loading error."""
        if not self._is_cycle_active(cycle_id) or self._is_disposing:
            return

        logger.error(f"Schedule loading failed: {error}")
        self._mark_section_complete(cycle_id, "schedule", success=False)
