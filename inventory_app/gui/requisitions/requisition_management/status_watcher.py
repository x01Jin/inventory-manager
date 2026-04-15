"""
Status Watcher - Clean, real-time status updates for requisitions.

Provides simple, efficient status calculation and updates based on requisition dates.
Called immediately after date changes to maintain accurate status in real-time.
"""

from datetime import datetime
from typing import Optional

from inventory_app.database.connection import db
from inventory_app.services.requisition_service import RequisitionService
from inventory_app.utils.logger import logger


class StatusWatcher:
    """
    Clean status watcher for real-time requisition status updates.

    Calculates status based on current time and requisition dates:
    - requested: current_time < expected_request
    - active: expected_request <= current_time < expected_return
    - overdue: expected_return <= current_time (and not returned)
    - returned: when return processing is complete
    """

    def __init__(self):
        """Initialize the status watcher."""
        self.current_time = datetime.now()
        self.requisition_service = RequisitionService()

    def update_status_for_requisition(self, requisition_id: int) -> str:
        """
        Update and return the status for a requisition based on its dates.

        Args:
            requisition_id: ID of the requisition to update

        Returns:
            str: New status that was set
        """
        try:
            # Update current time to ensure fresh calculations
            self.current_time = datetime.now()

            # Get current requisition dates
            dates = self._get_requisition_dates(requisition_id)
            if not dates:
                logger.warning(f"No dates found for requisition {requisition_id}")
                return "requested"

            # Calculate new status
            new_status = self._calculate_status(dates)

            # Update in database only when status changes.
            self._update_status_in_db(requisition_id, dates, new_status)

            logger.info(f"Updated requisition {requisition_id} status to: {new_status}")
            return new_status

        except Exception as e:
            logger.error(
                f"Failed to update status for requisition {requisition_id}: {e}"
            )
            return "requested"

    def _get_requisition_dates(self, requisition_id: int) -> Optional[dict]:
        """
        Get the relevant dates for status calculation.

        Args:
            requisition_id: ID of the requisition

        Returns:
            dict: Dictionary with expected_request, expected_return, and current status
        """
        try:
            query = """
            SELECT expected_request, expected_return, status
            FROM Requisitions
            WHERE id = ?
            """
            rows = db.execute_query(query, (requisition_id,))
            if rows:
                row = rows[0]
                return {
                    "expected_request": self._parse_datetime(row["expected_request"]),
                    "expected_return": self._parse_datetime(row["expected_return"]),
                    "current_status": row["status"],
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get dates for requisition {requisition_id}: {e}")
            return None

    def _parse_datetime(self, dt_str: str) -> Optional[datetime]:
        """Parse datetime string to datetime object."""
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str)
        except (ValueError, TypeError):
            logger.warning(f"Failed to parse datetime: {dt_str}")
            return None

    def _calculate_status(self, dates: dict) -> str:
        """
        Calculate the appropriate status based on dates.

        Args:
            dates: Dictionary with expected_request, expected_return, current_status

        Returns:
            str: Calculated status
        """
        expected_request = dates.get("expected_request")
        expected_return = dates.get("expected_return")
        current_status = dates.get("current_status", "requested")

        # Don't change status if already returned (final state)
        if current_status == "returned":
            return "returned"

        # Calculate based on current time vs expected dates
        if expected_request and self.current_time < expected_request:
            return "requested"
        elif expected_request and expected_return:
            if expected_request <= self.current_time < expected_return:
                return "active"
            elif self.current_time >= expected_return:
                return "overdue"

        # Fallback to requested if dates are invalid
        return "requested"

    def _update_status_in_db(self, requisition_id: int, dates: dict, new_status: str):
        """
        Update the status in the database.

        Args:
            requisition_id: ID of the requisition
            new_status: New status to set
        """
        try:
            previous_status = (dates.get("current_status") or "").strip()
            if previous_status == new_status:
                return

            reason = (
                "Automatic status transition from date watcher "
                f"({previous_status or 'unknown'} -> {new_status})"
            )
            self.requisition_service.update_status(
                requisition_id,
                new_status,
                user_name="System Auto",
                reason=reason,
            )

        except Exception as e:
            logger.error(
                f"Failed to update status in DB for requisition {requisition_id}: {e}"
            )
            raise


# Global instance for easy access
status_watcher = StatusWatcher()
