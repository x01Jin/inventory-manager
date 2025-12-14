"""
Schedule chart manager for the dashboard.
Displays upcoming requisitions in a compact table format.
"""

from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from PyQt6.QtGui import QColor

from inventory_app.gui.styles import DarkTheme
from inventory_app.database.connection import db
from inventory_app.utils.logger import logger
from inventory_app.utils.date_utils import (
    parse_datetime_iso,
    format_date_short,
    format_time_12h,
)


class ScheduleChartManager:
    """Manager for dashboard schedule chart display."""

    def __init__(self):
        pass

    def create_schedule_chart_widget(self):
        """Create and configure the schedule chart table widget."""
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(
            ["Status", "Requester", "Expected Request", "Expected Return"]
        )
        table.setSizePolicy(
            table.sizePolicy().Policy.Expanding, table.sizePolicy().Policy.Expanding
        )
        table.setWordWrap(True)
        table.setAlternatingRowColors(False)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        # Disable cell editing on double-click
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # Configure column resizing
        header = table.horizontalHeader()
        if header:
            header.setMinimumSectionSize(40)
            header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        # Configure row resizing
        vertical_header = table.verticalHeader()
        if vertical_header:
            vertical_header.setSectionResizeMode(
                QHeaderView.ResizeMode.ResizeToContents
            )

        # Apply compact styling to override default styles
        table.setStyleSheet(f"""
            QTableWidget {{
                border: 1px solid {DarkTheme.BORDER_COLOR} !important;
                border-radius: 3px !important;
                font-size: 8pt !important;
            }}

            QTableWidget::item {{
                padding: 1px !important;
                border-bottom: 1px solid {DarkTheme.BORDER_COLOR} !important;
                font-size: 8pt !important;
            }}

            QHeaderView::section {{
                padding: 2px !important;
                border: 1px solid {DarkTheme.BORDER_COLOR} !important;
                font-weight: bold !important;
                font-size: 8pt !important;
            }}

            QGroupBox {{
                font-size: 10pt !important;
                border: 1px solid {DarkTheme.BORDER_COLOR} !important;
                border-radius: 3px !important;
                margin-top: 0.5ex !important;
                padding-top: 4px !important;
            }}

            QGroupBox::title {{
                font-size: 9pt !important;
                padding: 0 2px 0 2px !important;
            }}
        """)

        return table

    def update_schedule_chart(self, schedule_table: QTableWidget):
        """Update schedule chart with upcoming requisitions."""
        try:
            # Get upcoming requisitions
            requisitions = self._get_upcoming_requisitions()

            # Set table row count
            schedule_table.setRowCount(
                min(len(requisitions), 5)
            )  # Limit to 5 rows for compactness

            for row, req in enumerate(requisitions[:5]):
                # Status column with color coding
                status_item = QTableWidgetItem(req["status"])
                if req["status"] == "active":
                    status_item.setForeground(QColor(DarkTheme.SUCCESS_COLOR))
                elif req["status"] == "requested":
                    status_item.setForeground(QColor(DarkTheme.WARNING_COLOR))
                elif req["status"] == "returned":
                    # In case returned items are ever displayed here, use returned blue
                    status_item.setForeground(QColor(DarkTheme.RETURNED_COLOR))
                elif req["status"] == "overdue":
                    status_item.setForeground(QColor(DarkTheme.ERROR_COLOR))
                schedule_table.setItem(row, 0, status_item)

                # Requester name
                schedule_table.setItem(row, 1, QTableWidgetItem(req["requester_name"]))

                # Expected request date/time
                expected_request = self._format_datetime(req["expected_request"])
                schedule_table.setItem(row, 2, QTableWidgetItem(expected_request))

                # Expected return date/time
                expected_return = self._format_datetime(req["expected_return"])
                schedule_table.setItem(row, 3, QTableWidgetItem(expected_return))

        except Exception as e:
            logger.error(f"Failed to update schedule chart: {e}")

    def _get_upcoming_requisitions(self):
        """Get upcoming requisitions from database."""
        try:
            query = """
            SELECT
                r.status,
                req.name as requester_name,
                r.expected_request,
                r.expected_return
            FROM Requisitions r
            JOIN Requesters req ON r.requester_id = req.id
            WHERE r.expected_request >= CURRENT_TIMESTAMP
                AND r.status IN ('requested', 'active', 'overdue')
            ORDER BY r.expected_request ASC
            LIMIT 7
            """

            rows = db.execute_query(query)
            return rows if rows else []

        except Exception as e:
            logger.error(f"Failed to get upcoming requisitions: {e}")
            return []

    def _format_datetime(self, datetime_str):
        """Format datetime string for display using date_utils."""
        if not datetime_str:
            return "N/A"

        try:
            # Use date_utils to parse the datetime
            dt = parse_datetime_iso(datetime_str)
            if dt:
                # Format as "Jan 15, 2025 at 02:13 PM"
                date_str = format_date_short(dt)
                time_str = format_time_12h(dt.time())
                return f"{date_str} at {time_str}"
            else:
                return "N/A"
        except Exception:
            return str(datetime_str)[:16]  # Fallback: show first 16 chars
