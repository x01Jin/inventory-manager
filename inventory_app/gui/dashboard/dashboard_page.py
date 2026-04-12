"""
Dashboard page component for the laboratory inventory application.
Focused on key metrics and quick access to main functions.
"""

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

        self._metrics_worker = None
        self._activity_worker = None
        self._alerts_worker = None
        self._schedule_worker = None
        self._refresh_scheduled = False

        self.refresh_data()

    def refresh_data(self):
        """Refresh dashboard data asynchronously."""
        try:
            if self._refresh_scheduled:
                return
            self._refresh_scheduled = True

            self._load_metrics_async()
            self._load_activity_async()
            self._load_alerts_async()
            self._load_schedule_async()

            # Allow a quick follow-up refresh after current work is queued.
            QTimer.singleShot(250, self._reset_refresh_scheduled)

        except Exception as e:
            self._refresh_scheduled = False
            logger.error(f"Failed to refresh dashboard: {e}")

    def _reset_refresh_scheduled(self):
        """Reset refresh guard for subsequent requests."""
        self._refresh_scheduled = False

    def _load_metrics_async(self):
        """Load metrics in background thread."""
        if self._metrics_worker and worker_pool.active_thread_count > 0:
            self._metrics_worker.cancel()

        self._metrics_worker = Worker(get_consolidated_metrics)
        self._metrics_worker.signals.result.connect(self._on_metrics_loaded)
        self._metrics_worker.signals.error.connect(self._on_metrics_error)
        worker_pool.start(self._metrics_worker)

    def _on_metrics_loaded(self, metrics: dict):
        """Handle loaded metrics data."""
        self.metrics_manager.update_metrics_widget(self.metrics_widget, metrics)

    def _on_metrics_error(self, error: tuple):
        """Handle metrics loading error."""
        exctype, value, traceback = error
        logger.error(f"Metrics loading failed: {value}")
        self.signals.error_occurred.emit(str(value))

    def _load_activity_async(self):
        """Load activity data in background thread."""
        if self._activity_worker:
            self._activity_worker.cancel()

        logger.debug("Starting activity data load")
        self._activity_worker = Worker(self.activity_manager.load_activity_data)
        self._activity_worker.signals.result.connect(
            lambda data: self._on_activity_loaded(data)
        )
        self._activity_worker.signals.error.connect(
            lambda e: logger.error(f"Activity loading failed: {e}")
        )
        worker_pool.start(self._activity_worker)

    def _on_activity_loaded(self, data):
        """Handle loaded activity data."""
        logger.debug(f"Activity data received: {len(data) if data else 0} items")
        self.activity_manager.populate_activity_widget(self.activity_text, data)

    def _load_alerts_async(self):
        """Load alerts data in background thread."""
        if self._alerts_worker:
            self._alerts_worker.cancel()

        self._alerts_worker = Worker(self.alerts_manager.load_alerts_payload)
        self._alerts_worker.signals.result.connect(self._on_alerts_loaded)
        self._alerts_worker.signals.error.connect(
            lambda e: logger.error(f"Alerts loading failed: {e}")
        )
        worker_pool.start(self._alerts_worker)

    def _on_alerts_loaded(self, payload):
        """Render both summary and full alerts tabs from loaded payload."""
        if not isinstance(payload, dict):
            payload = {"summary": [], "full": []}

        self.alerts_manager.populate_alerts_table(
            self.alerts_table,
            payload.get("summary", []),
        )
        self.alerts_manager.populate_full_alerts_table(
            self.all_alerts_table,
            payload.get("full", []),
        )

    def _load_schedule_async(self):
        """Load schedule data in background thread."""
        if self._schedule_worker:
            self._schedule_worker.cancel()

        self._schedule_worker = Worker(self.schedule_manager.get_upcoming_requisitions)
        self._schedule_worker.signals.result.connect(self._on_schedule_loaded)
        self._schedule_worker.signals.error.connect(
            lambda e: logger.error(f"Schedule loading failed: {e}")
        )
        worker_pool.start(self._schedule_worker)

    def _on_schedule_loaded(self, requisitions):
        """Handle loaded schedule data."""
        self.schedule_manager.populate_schedule_chart(
            self.schedule_placeholder,
            requisitions or [],
        )
