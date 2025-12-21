"""
Dashboard page component for the laboratory inventory application.
Focused on key metrics and quick access to main functions.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QGroupBox

from inventory_app.gui.styles import get_current_theme
from inventory_app.utils.logger import logger
from .metrics import MetricsManager
from .activity import ActivityManager
from .alerts import AlertsManager
from .schedule_chart import ScheduleChartManager


class DashboardPage(QWidget):
    """Dashboard page with laboratory inventory overview."""

    def __init__(self):
        super().__init__()

        Theme = get_current_theme()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)  # Reduced margins for compactness
        layout.setSpacing(10)  # Reduced spacing

        # Header
        header = QLabel("📊 Lab Inventory Dashboard")
        header.setStyleSheet(
            f"font-size: {Theme.FONT_SIZE_TITLE}pt; font-weight: bold; color: {Theme.TEXT_PRIMARY}; margin-bottom: 5px;"
        )
        layout.addWidget(header)

        # Initialize managers FIRST
        self.metrics_manager = MetricsManager()
        self.activity_manager = ActivityManager()
        self.alerts_manager = AlertsManager()
        self.schedule_manager = ScheduleChartManager()

        # Create widgets using managers
        self.metrics_widget = self.metrics_manager.create_metrics_widget()
        self.activity_text = self.activity_manager.create_activity_widget()
        self.alerts_table = self.alerts_manager.create_alerts_table()
        self.schedule_placeholder = self.schedule_manager.create_schedule_chart_widget()

        # Create 2x2 grid layout for main content
        grid_layout = QGridLayout()
        grid_layout.setSpacing(10)

        # Create sections with panel headers and add to grid
        # Top-left: Metrics
        metrics_group = QGroupBox("📊 Key Metrics")
        metrics_layout = QVBoxLayout(metrics_group)
        metrics_layout.addWidget(self.metrics_widget)
        grid_layout.addWidget(metrics_group, 0, 0)

        # Top-right: Activity
        activity_group = QGroupBox("📝 Recent Activity")
        activity_layout = QVBoxLayout(activity_group)
        activity_layout.addWidget(self.activity_text)
        grid_layout.addWidget(activity_group, 0, 1)

        # Bottom-left: Schedule Chart
        schedule_group = QGroupBox("⏰ Schedule Chart")
        schedule_layout = QVBoxLayout(schedule_group)
        schedule_layout.addWidget(self.schedule_placeholder)
        grid_layout.addWidget(schedule_group, 1, 0)

        # Bottom-right: Alerts
        alerts_group = QGroupBox("🚨 Critical Alerts")
        alerts_layout = QVBoxLayout(alerts_group)
        alerts_layout.addWidget(self.alerts_table)
        grid_layout.addWidget(alerts_group, 1, 1)

        # Set equal column and row stretches for balanced sizing
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 1)
        grid_layout.setRowStretch(0, 1)
        grid_layout.setRowStretch(1, 1)

        layout.addLayout(grid_layout)

        # Load initial data
        self.refresh_data()

    def refresh_data(self):
        """Refresh dashboard data."""
        try:
            # Update metrics widget
            self.metrics_manager.update_metrics_widget(self.metrics_widget)

            # Update activity
            self.activity_manager.update_recent_activity(self.activity_text)

            # Update alerts
            self.alerts_manager.update_alerts_table(self.alerts_table)

            # Update schedule chart
            self.schedule_manager.update_schedule_chart(self.schedule_placeholder)

        except Exception as e:
            logger.error(f"Failed to refresh dashboard: {e}")
