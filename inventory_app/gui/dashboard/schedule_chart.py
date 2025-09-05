"""
Schedule chart management for the dashboard.
Handles requisition timeline visualization.
"""

from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt

from inventory_app.gui.styles import DarkTheme
from inventory_app.database.connection import db
from inventory_app.utils.logger import logger


class ScheduleChartManager:
    """Manager for dashboard schedule chart."""

    def __init__(self):
        pass

    def create_schedule_chart_widget(self):
        """Create the schedule chart widget (placeholder for now)."""
        # Placeholder for chart implementation
        placeholder = QLabel("Schedule chart loading...")
        placeholder.setStyleSheet(f"color: {DarkTheme.TEXT_SECONDARY}; font-size: 10pt; padding: 20px;")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return placeholder

    def update_schedule_chart(self, chart_widget: QLabel):
        """Update the schedule chart with current data."""
        try:
            # Get upcoming requisitions (next 30 days)
            schedule_data = self.get_schedule_data()

            if not schedule_data:
                chart_widget.setText("No upcoming requisitions")
                return

            # For now, display as text summary
            # TODO: Implement actual chart visualization
            summary_lines = []
            for req in schedule_data[:5]:  # Show top 5
                requester = req.get('requester_name', 'Unknown')[:10]
                activity = req.get('lab_activity_name', 'Activity')[:15]
                status = req.get('status', 'pending')
                date = req.get('expected_request', 'TBD')
                line = f"• {requester}: {activity} ({status}) - {date}"
                summary_lines.append(line)

            chart_text = "\n".join(summary_lines)
            chart_widget.setText(chart_text)

        except Exception as e:
            logger.error(f"Failed to update schedule chart: {e}")
            chart_widget.setText("Error loading schedule")

    def get_schedule_data(self):
        """Get schedule data from database."""
        try:
            from datetime import datetime, timedelta
            start_date = datetime.now().date()
            end_date = start_date + timedelta(days=30)

            query = """
            SELECT r.id, r.expected_request, r.expected_return, r.status,
                   r.lab_activity_name, req.name as requester_name
            FROM Requisitions r
            JOIN Requesters req ON r.requester_id = req.id
            WHERE r.expected_request BETWEEN ? AND ?
            ORDER BY r.expected_request
            """

            rows = db.execute_query(query, (start_date.isoformat(), end_date.isoformat()))
            return rows if rows else []

        except Exception as e:
            logger.error(f"Failed to get schedule data: {e}")
            return []
