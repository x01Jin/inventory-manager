"""
Dashboard page component for the laboratory inventory application.
Focused on key metrics and quick access to main functions.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QTableWidget, QTableWidgetItem
from PyQt6.QtGui import QColor

from inventory_app.gui.styles import DarkTheme
from inventory_app.database.models import Item, Requisition, Borrower
from inventory_app.business_logic.alert_engine import alert_engine


class DashboardPage(QWidget):
    """Dashboard page with laboratory inventory overview."""

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header
        header = QLabel("📊 Laboratory Inventory Dashboard")
        header.setStyleSheet(f"font-size: {DarkTheme.FONT_SIZE_TITLE}pt; font-weight: bold; color: {DarkTheme.TEXT_PRIMARY}; margin-bottom: 10px;")
        layout.addWidget(header)

        # Quick action buttons
        self.create_quick_actions(layout)

        # Key metrics
        self.create_metrics_section(layout)

        # Recent activity
        self.create_recent_activity(layout)

        # Critical alerts
        self.create_alerts_section(layout)

        # Load initial data
        self.refresh_data()

    def create_quick_actions(self, parent_layout):
        """Create quick action buttons for common tasks."""
        actions_group = QGroupBox("Quick Actions")
        actions_layout = QHBoxLayout(actions_group)

        # Action buttons
        new_req_btn = QPushButton("📋 New Requisition")
        new_req_btn.setStyleSheet(f"font-size: {DarkTheme.FONT_SIZE_LARGE}pt; padding: 15px; min-width: 150px;")

        add_item_btn = QPushButton("➕ Add Item")
        add_item_btn.setStyleSheet(f"font-size: {DarkTheme.FONT_SIZE_LARGE}pt; padding: 15px; min-width: 150px;")

        generate_report_btn = QPushButton("📊 Generate Report")
        generate_report_btn.setStyleSheet(f"font-size: {DarkTheme.FONT_SIZE_LARGE}pt; padding: 15px; min-width: 150px;")

        actions_layout.addWidget(new_req_btn)
        actions_layout.addWidget(add_item_btn)
        actions_layout.addWidget(generate_report_btn)

        parent_layout.addWidget(actions_group)

    def create_metrics_section(self, parent_layout):
        """Create key metrics display."""
        metrics_layout = QHBoxLayout()

        # Total inventory
        total_items = len(Item.get_all())
        inventory_metric = self.create_metric_card("📦 Total Inventory", str(total_items), "Items in laboratory")

        # Active requisitions
        active_reqs = len(Requisition.get_all())
        reqs_metric = self.create_metric_card("📋 Active Requisitions", str(active_reqs), "Current borrowings")

        # Total borrowers
        total_borrowers = len(Borrower.get_all())
        borrowers_metric = self.create_metric_card("👥 Registered Borrowers", str(total_borrowers), "Students/Staff")

        metrics_layout.addWidget(inventory_metric)
        metrics_layout.addWidget(reqs_metric)
        metrics_layout.addWidget(borrowers_metric)

        parent_layout.addLayout(metrics_layout)

    def create_metric_card(self, title: str, value: str, subtitle: str):
        """Create a metric card widget."""
        card = QWidget()
        card.setStyleSheet(f"background-color: {DarkTheme.SECONDARY_DARK}; border: 1px solid {DarkTheme.BORDER_COLOR}; border-radius: 8px; padding: 15px;")

        layout = QVBoxLayout(card)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-size: {DarkTheme.FONT_SIZE_NORMAL}pt; color: {DarkTheme.TEXT_SECONDARY};")

        value_label = QLabel(value)
        value_label.setStyleSheet(f"font-size: 28pt; font-weight: bold; color: {DarkTheme.ACCENT_COLOR};")

        subtitle_label = QLabel(subtitle)
        subtitle_label.setStyleSheet(f"font-size: {DarkTheme.FONT_SIZE_NORMAL}pt; color: {DarkTheme.TEXT_MUTED};")

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        layout.addWidget(subtitle_label)

        return card

    def create_recent_activity(self, parent_layout):
        """Create recent activity section."""
        activity_group = QGroupBox("Recent Activity")
        activity_layout = QVBoxLayout(activity_group)

        activity_text = QLabel("• New requisition: Chemistry Lab - 25 students\n• Item added: Beaker 250ml\n• Report generated: Weekly usage\n• Calibration alert: Spectrophotometer")
        activity_text.setStyleSheet(f"color: {DarkTheme.TEXT_SECONDARY}; font-size: {DarkTheme.FONT_SIZE_NORMAL}pt;")

        activity_layout.addWidget(activity_text)
        parent_layout.addWidget(activity_group)

    def create_alerts_section(self, parent_layout):
        """Create critical alerts section."""
        alerts_group = QGroupBox("Critical Alerts")
        alerts_layout = QVBoxLayout(alerts_group)

        # Alerts table
        self.alerts_table = QTableWidget()
        self.alerts_table.setColumnCount(3)
        self.alerts_table.setHorizontalHeaderLabels(["Alert Type", "Item", "Urgency"])
        self.alerts_table.setMaximumHeight(150)

        alerts_layout.addWidget(self.alerts_table)
        parent_layout.addWidget(alerts_group)

    def refresh_data(self):
        """Refresh dashboard data."""
        try:
            self.update_alerts_table()
        except Exception as e:
            print(f"Failed to refresh dashboard: {e}")

    def update_alerts_table(self):
        """Update alerts table with critical alerts."""
        try:
            alerts = alert_engine.get_critical_alerts()

            self.alerts_table.setRowCount(min(len(alerts), 5))  # Show max 5 alerts

            for row, alert in enumerate(alerts[:5]):
                self.alerts_table.setItem(row, 0, QTableWidgetItem(alert.alert_type))
                self.alerts_table.setItem(row, 1, QTableWidgetItem(alert.item_name))

                urgency_item = QTableWidgetItem(alert.severity)
                if alert.severity == "Critical":
                    urgency_item.setBackground(QColor(DarkTheme.ERROR_COLOR))
                elif alert.severity == "Warning":
                    urgency_item.setBackground(QColor(DarkTheme.WARNING_COLOR))
                self.alerts_table.setItem(row, 2, urgency_item)

        except Exception as e:
            print(f"Failed to update alerts: {e}")
