"""
Alerts management for the dashboard.
Handles critical alerts display.
"""

from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from PyQt6.QtGui import QColor

from inventory_app.gui.styles import DarkTheme
from inventory_app.services.alert_engine import alert_engine
from inventory_app.utils.logger import logger


class AlertsManager:
    """Manager for dashboard alerts display."""

    def __init__(self):
        pass

    def update_alerts_table(self, alerts_table: QTableWidget):
        """Update alerts table with critical alerts."""
        try:
            alerts = alert_engine.get_critical_alerts()

            alerts_table.setRowCount(min(len(alerts), 3))  # Reduced to 3 for compactness

            for row, alert in enumerate(alerts[:3]):
                alerts_table.setItem(row, 0, QTableWidgetItem(alert.alert_type))
                alerts_table.setItem(row, 1, QTableWidgetItem(alert.item_name))

                urgency_item = QTableWidgetItem(alert.severity)
                if alert.severity == "Critical":
                    urgency_item.setBackground(QColor(DarkTheme.ERROR_COLOR))
                elif alert.severity == "Warning":
                    urgency_item.setBackground(QColor(DarkTheme.WARNING_COLOR))
                alerts_table.setItem(row, 2, urgency_item)

        except Exception as e:
            logger.error(f"Failed to update alerts: {e}")

    def create_alerts_table(self):
        """Create and configure the alerts table widget."""
        alerts_table = QTableWidget()
        alerts_table.setColumnCount(3)
        alerts_table.setHorizontalHeaderLabels(["Type", "Item", "Status"])
        # Removed maximum height to allow vertical expansion
        alerts_table.setSizePolicy(alerts_table.sizePolicy().Policy.Expanding, alerts_table.sizePolicy().Policy.Expanding)
        alerts_table.setStyleSheet("font-size: 9pt;")
        alerts_table.setWordWrap(True)

        # Configure column resizing to fit content with minimum width
        header = alerts_table.horizontalHeader()
        if header:
            header.setMinimumSectionSize(40)
            header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        # Allow vertical expansion of cells
        vertical_header = alerts_table.verticalHeader()
        if vertical_header:
            vertical_header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        return alerts_table
