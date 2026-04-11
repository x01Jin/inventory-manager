"""Alerts management for dashboard summary and full alerts tab."""

from typing import Optional

from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from PyQt6.QtGui import QColor
from datetime import date

from inventory_app.gui.styles import DarkTheme
from inventory_app.services.alert_engine import alert_engine
from inventory_app.gui.reports.data_sources import get_low_stock_data
from inventory_app.utils.logger import logger


class AlertsManager:
    """Manager for dashboard alerts display."""

    SUMMARY_MAX_ROWS = 50

    def __init__(self):
        pass

    @staticmethod
    def _format_due_date(value: Optional[date]) -> str:
        if not value:
            return "N/A"
        return value.strftime("%m/%d/%Y")

    def load_alerts_data(self):
        """Backward-compatible summary-only loader used by older callsites/tests."""
        payload = self.load_alerts_payload()
        return payload.get("summary", [])

    def _build_alert_rows(self, include_low_stock: bool) -> list:
        """Collect raw alert rows from status alerts and optional low-stock alerts."""
        rows = []

        allowed = {
            "expiring",
            "expired",
            "disposal warning",
            "disposal overdue",
            "calibration overdue",
            "calibration warning",
        }
        type_to_status = {
            "expired": "Critical",
            "disposal overdue": "Critical",
            "calibration overdue": "Critical",
            "expiring": "Warning",
            "disposal warning": "Warning",
            "calibration warning": "Warning",
        }

        all_alerts = alert_engine.get_all_alerts()
        for alert in all_alerts:
            if alert.alert_type not in allowed:
                continue

            rows.append(
                {
                    "item": alert.item_name,
                    "type": alert.alert_type,
                    "status": type_to_status.get(alert.alert_type, alert.severity),
                    "days_until": alert.days_until,
                    "due_date": self._format_due_date(alert.reference_date),
                    "category": alert.category_name or "Uncategorized",
                }
            )

        if include_low_stock:
            low = get_low_stock_data()
            for entry in low:
                name = entry.get("Item Name") or entry.get("ITEMS") or ""
                rows.append(
                    {
                        "item": name,
                        "type": "low stock",
                        "status": "Warning",
                        "days_until": None,
                        "due_date": "N/A",
                        "category": entry.get("Category") or "N/A",
                    }
                )

        return rows

    def _dedupe_and_sort_rows(self, rows: list) -> list:
        """Deduplicate by item and sort by urgency."""
        status_priority = {"Critical": 2, "Warning": 1, "Info": 0}
        type_order = {
            "expired": 0,
            "disposal overdue": 1,
            "calibration overdue": 2,
            "calibration warning": 3,
            "disposal warning": 4,
            "expiring": 5,
            "low stock": 6,
        }

        dedup = {}
        for row in rows:
            key = row["item"]
            existing = dedup.get(key)
            if not existing:
                dedup[key] = row
                continue

            new_priority = status_priority.get(row["status"], 0)
            old_priority = status_priority.get(existing["status"], 0)

            if new_priority > old_priority:
                dedup[key] = row
            elif new_priority == old_priority and type_order.get(
                row["type"], 99
            ) < type_order.get(existing["type"], 99):
                dedup[key] = row

        final = list(dedup.values())
        final.sort(
            key=lambda x: (
                -status_priority.get(x["status"], 0),
                x["days_until"] if x["days_until"] is not None else 9999,
                type_order.get(x["type"], 99),
                x["item"].lower(),
            )
        )
        return final

    def load_alerts_payload(self):
        """Load summary + full alerts data for dashboard tabs."""
        try:
            full_rows = self._dedupe_and_sort_rows(
                self._build_alert_rows(include_low_stock=False)
            )
            summary_rows = self._dedupe_and_sort_rows(
                self._build_alert_rows(include_low_stock=True)
            )
            return {
                "summary": summary_rows,
                "full": full_rows,
            }
        except Exception as e:
            logger.error(f"Failed to load alerts payload: {e}")
            return {"summary": [], "full": []}

    def populate_alerts_table(self, alerts_table: QTableWidget, alerts_data: list):
        """Populate alerts table with loaded data."""
        try:
            display_count = min(len(alerts_data), self.SUMMARY_MAX_ROWS)
            alerts_table.setRowCount(display_count)

            if len(alerts_data) > self.SUMMARY_MAX_ROWS:
                alerts_table.setToolTip(
                    f"Showing {self.SUMMARY_MAX_ROWS} of {len(alerts_data)} critical alerts"
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
            payload = self.load_alerts_payload()
            self.populate_alerts_table(alerts_table, payload.get("summary", []))

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

    def create_full_alerts_table(self):
        """Create and configure full alerts table for dedicated alerts tab."""
        alerts_table = QTableWidget()
        alerts_table.setColumnCount(6)
        alerts_table.setHorizontalHeaderLabels(
            ["Alert Type", "Item", "Category", "Due Date", "Days Left", "Status"]
        )
        alerts_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        alerts_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        alerts_table.setWordWrap(False)
        alerts_table.setSortingEnabled(True)

        header = alerts_table.horizontalHeader()
        if header:
            header.setMinimumSectionSize(40)
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        return alerts_table

    def populate_full_alerts_table(self, alerts_table: QTableWidget, alerts_data: list):
        """Populate full alerts table without summary cap."""
        try:
            alerts_table.setSortingEnabled(False)
            alerts_table.setRowCount(len(alerts_data))

            for row, data in enumerate(alerts_data):
                alerts_table.setItem(row, 0, QTableWidgetItem(data["type"]))
                alerts_table.setItem(row, 1, QTableWidgetItem(data["item"]))
                alerts_table.setItem(
                    row, 2, QTableWidgetItem(data.get("category", "N/A"))
                )
                alerts_table.setItem(
                    row, 3, QTableWidgetItem(data.get("due_date", "N/A"))
                )
                alerts_table.setItem(
                    row,
                    4,
                    QTableWidgetItem(
                        "N/A"
                        if data.get("days_until") is None
                        else str(data.get("days_until"))
                    ),
                )

                status_item = QTableWidgetItem(data["status"])
                if data["status"] == "Critical":
                    status_item.setBackground(QColor(DarkTheme.ERROR_COLOR))
                elif data["status"] == "Warning":
                    status_item.setBackground(QColor(DarkTheme.WARNING_COLOR))
                alerts_table.setItem(row, 5, status_item)

            alerts_table.setSortingEnabled(True)

        except Exception as e:
            logger.error(f"Failed to populate full alerts table: {e}")
