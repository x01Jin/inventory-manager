"""
Alerts management for the dashboard.
Handles critical alerts display.
"""

from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from PyQt6.QtGui import QColor

from inventory_app.gui.styles import DarkTheme
from inventory_app.services.alert_engine import alert_engine
from inventory_app.gui.reports.data_sources import get_low_stock_data
from inventory_app.utils.logger import logger


class AlertsManager:
    """Manager for dashboard alerts display."""

    def __init__(self):
        pass

    def load_alerts_data(self):
        """Load alerts data from database. Called in background thread."""
        try:
            all_alerts = alert_engine.get_all_alerts()

            rows = []

            allowed = {
                "expiring",
                "expired",
                "calibration overdue",
                "calibration warning",
            }
            type_to_status = {
                "expired": "Critical",
                "calibration overdue": "Critical",
                "expiring": "Warning",
                "calibration warning": "Warning",
            }

            for a in all_alerts:
                if a.alert_type in allowed:
                    status = type_to_status.get(a.alert_type, "Warning")
                    rows.append(
                        {
                            "item": a.item_name,
                            "type": a.alert_type,
                            "status": status,
                            "days_until": a.days_until or 0,
                        }
                    )

            low = get_low_stock_data()
            for r in low:
                name = r.get("Item Name") or r.get("ITEMS") or ""
                rows.append(
                    {
                        "item": name,
                        "type": "low stock",
                        "status": "Warning",
                        "days_until": None,
                    }
                )

            status_priority = {"Critical": 2, "Warning": 1}
            type_order = {
                "expired": 0,
                "calibration overdue": 1,
                "calibration warning": 2,
                "expiring": 3,
                "low stock": 4,
            }

            dedup = {}
            for r in rows:
                key = r["item"]
                existing = dedup.get(key)
                if not existing:
                    dedup[key] = r
                    continue

                if status_priority[r["status"]] > status_priority[existing["status"]]:
                    dedup[key] = r
                elif (
                    status_priority[r["status"]] == status_priority[existing["status"]]
                ):
                    if type_order.get(r["type"], 99) < type_order.get(
                        existing["type"], 99
                    ):
                        dedup[key] = r

            final = list(dedup.values())
            final.sort(
                key=lambda x: (
                    -status_priority[x["status"]],
                    x["days_until"] if x["days_until"] is not None else 9999,
                    type_order.get(x["type"], 99),
                )
            )

            return final

        except Exception as e:
            logger.error(f"Failed to load alerts data: {e}")
            return []

    def populate_alerts_table(self, alerts_table: QTableWidget, alerts_data: list):
        """Populate alerts table with loaded data."""
        try:
            MAX_DISPLAY_ROWS = 50
            display_count = min(len(alerts_data), MAX_DISPLAY_ROWS)
            alerts_table.setRowCount(display_count)

            if len(alerts_data) > MAX_DISPLAY_ROWS:
                alerts_table.setToolTip(
                    f"Showing {MAX_DISPLAY_ROWS} of {len(alerts_data)} critical alerts"
                )
            else:
                alerts_table.setToolTip("")

            for row, r in enumerate(alerts_data[:display_count]):
                alerts_table.setItem(row, 0, QTableWidgetItem(r["type"]))
                alerts_table.setItem(row, 1, QTableWidgetItem(r["item"]))

                status_item = QTableWidgetItem(r["status"])
                if r["status"] == "Critical":
                    status_item.setBackground(QColor(DarkTheme.ERROR_COLOR))
                elif r["status"] == "Warning":
                    status_item.setBackground(QColor(DarkTheme.WARNING_COLOR))
                alerts_table.setItem(row, 2, status_item)

        except Exception as e:
            logger.error(f"Failed to populate alerts table: {e}")

    def update_alerts_table(self, alerts_table: QTableWidget):
        """Update alerts table with critical alerts."""
        try:
            alerts_data = self.load_alerts_data()
            self.populate_alerts_table(alerts_table, alerts_data)

        except Exception as e:
            logger.error(f"Failed to update alerts: {e}")

    def create_alerts_table(self):
        """Create and configure the alerts table widget."""
        alerts_table = QTableWidget()
        alerts_table.setColumnCount(3)
        alerts_table.setHorizontalHeaderLabels(["Alert Type", "Item", "Status"])
        # Removed maximum height to allow vertical expansion
        alerts_table.setSizePolicy(
            alerts_table.sizePolicy().Policy.Expanding,
            alerts_table.sizePolicy().Policy.Expanding,
        )
        alerts_table.setStyleSheet("font-size: 9pt;")
        alerts_table.setWordWrap(True)
        # Disable cell editing on double-click
        alerts_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        alerts_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)

        # Configure column resizing to fit content with minimum width
        header = alerts_table.horizontalHeader()
        if header:
            header.setMinimumSectionSize(40)
            header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        # Allow vertical expansion of cells
        vertical_header = alerts_table.verticalHeader()
        if vertical_header:
            vertical_header.setSectionResizeMode(
                QHeaderView.ResizeMode.ResizeToContents
            )

        return alerts_table
