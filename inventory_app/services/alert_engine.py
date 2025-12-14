"""
Alert engine for the inventory application.
Handles calculation and retrieval of alerts for expiration and calibration.
Uses the item status service for efficient status calculation.
"""

from typing import List, Optional
from datetime import date
from dataclasses import dataclass

from inventory_app.services.item_status_service import item_status_service, ItemStatus
from inventory_app.utils.logger import logger


@dataclass
class Alert:
    """Represents an alert for an item."""

    item_id: int
    item_name: str
    alert_type: str  # 'low stock', 'expiring', 'expired', 'calibration overdue', 'calibration warning'
    reference_date: date
    days_until: int
    severity: str  # 'Critical', 'Warning', 'Info'


class AlertEngine:
    """
    Handles alert calculations and retrieval.
    Uses the item status service for efficient processing.
    """

    def __init__(self):
        """Initialize alert engine."""

    def get_all_alerts(self) -> List[Alert]:
        """
        Get all current alerts using the item status service.

        Returns:
            List of Alert objects
        """
        try:
            # Get all items with their status
            all_statuses = item_status_service.get_all_items_status()

            alerts = []
            for status in all_statuses:
                if status.status != "OK":  # Only include items with alerts
                    alert = self._status_to_alert(status)
                    if alert:
                        alerts.append(alert)

            # Sort by reference date
            alerts.sort(key=lambda x: x.reference_date)

            logger.debug(f"Retrieved {len(alerts)} alerts")
            return alerts

        except Exception as e:
            logger.error(f"Failed to get alerts: {e}")
            return []

    def get_expiration_alerts(self, lead_months: int = 6) -> List[Alert]:
        """
        Get items nearing expiration.

        Args:
            lead_months: Months before expiration to alert

        Returns:
            List of expiration alerts
        """
        try:
            all_alerts = self.get_all_alerts()
            return [alert for alert in all_alerts if alert.alert_type == "expiring"]
        except Exception as e:
            logger.error(f"Failed to get expiration alerts: {e}")
            return []

    def get_calibration_alerts(self, lead_months: int = 3) -> List[Alert]:
        """
        Get equipment needing calibration.

        Args:
            lead_months: Months before due date to alert

        Returns:
            List of calibration alerts
        """
        try:
            all_alerts = self.get_all_alerts()
            return [
                alert
                for alert in all_alerts
                if alert.alert_type in ("calibration overdue", "calibration warning")
            ]
        except Exception as e:
            logger.error(f"Failed to get calibration alerts: {e}")
            return []

    def get_critical_alerts(self) -> List[Alert]:
        """
        Get only critical severity alerts.

        Returns:
            List of critical alerts
        """
        try:
            all_alerts = self.get_all_alerts()
            return [alert for alert in all_alerts if alert.severity == "Critical"]
        except Exception as e:
            logger.error(f"Failed to get critical alerts: {e}")
            return []

    def _status_to_alert(self, status: ItemStatus) -> Optional[Alert]:
        """
        Convert ItemStatus to Alert format.
        Handles combined statuses like "CAL_WARNING and EXPIRING".

        Args:
            status: ItemStatus object

        Returns:
            Alert object or None if conversion fails
        """
        try:
            # Get item name
            from inventory_app.database.models import Item

            item = Item.get_by_id(status.item_id)
            if not item:
                return None

            # Skip if no reference date
            if not status.reference_date:
                return None

            # Handle combined statuses (split by " and ")
            status_parts = status.status.split(" and ")

            # For combined statuses, create alerts for each part
            alerts = []
            for status_part in status_parts:
                alert = self._create_alert_for_status(
                    status, status_part.strip(), item.name
                )
                if alert:
                    alerts.append(alert)

            # Return the most urgent alert (smallest days_until)
            if alerts:
                return min(alerts, key=lambda x: x.days_until)
            else:
                return None

        except Exception as e:
            logger.error(
                f"Failed to convert status to alert for item {status.item_id}: {e}"
            )
            return None

    def _create_alert_for_status(
        self, status: ItemStatus, status_part: str, item_name: str
    ) -> Optional[Alert]:
        """
        Create an alert for a specific status part.

        Args:
            status: Original ItemStatus object
            status_part: Individual status part (e.g., 'CAL_WARNING')
            item_name: Name of the item

        Returns:
            Alert object or None
        """
        # Determine alert type using specific, display-friendly labels
        if status_part == "EXPIRED":
            alert_type = "expired"
        elif status_part == "EXPIRING":
            alert_type = "expiring"
        elif status_part == "CAL_WARNING":
            alert_type = "calibration warning"
        elif status_part == "CAL_DUE":
            alert_type = "calibration overdue"
        else:
            return None

        # Determine severity
        severity = self._determine_severity(status)

        # Ensure we have a valid reference date
        if not status.reference_date:
            return None

        return Alert(
            item_id=status.item_id,
            item_name=item_name,
            alert_type=alert_type,
            reference_date=status.reference_date,
            days_until=status.days_until or 0,
            severity=severity,
        )

    def _determine_severity(self, status: ItemStatus) -> str:
        """
        Determine alert severity based on status and days remaining.

        Args:
            status: ItemStatus object

        Returns:
            Severity level: 'Critical', 'Warning', or 'Info'
        """
        days_until = status.days_until or 0

        if status.status in ["EXPIRED", "CAL_DUE"]:
            return "Critical"  # Already past due
        elif days_until < 0:
            return "Critical"  # Already past due
        elif days_until <= 7:
            return "Critical"  # Within a week
        elif days_until <= 30:
            return "Warning"  # Within a month
        else:
            return "Info"  # More than a month away


# Global alert engine instance
alert_engine = AlertEngine()
