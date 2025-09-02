"""
Alert engine for the inventory application.
Handles calculation and retrieval of alerts for expiration and calibration.
Uses composition pattern with DatabaseConnection.
"""

from typing import List, Dict
from datetime import date
from dataclasses import dataclass

from inventory_app.database.connection import db
from inventory_app.utils.logger import logger

@dataclass
class Alert:
    """Represents an alert for an item."""
    item_id: int
    item_name: str
    alert_type: str  # 'Expiration Alert', 'Calibration Alert'
    reference_date: date
    days_until: int
    severity: str  # 'Critical', 'Warning', 'Info'

class AlertEngine:
    """
    Handles alert calculations and retrieval.
    Uses composition with DatabaseConnection.
    """

    def __init__(self):
        """Initialize alert engine."""
        logger.info("Alert engine initialized")

    def get_all_alerts(self) -> List[Alert]:
        """
        Get all current alerts by querying Items table directly.
        Combines expiration and calibration alerts.

        Returns:
            List of Alert objects
        """
        try:
            alerts = []

            # Get expiration alerts
            exp_alerts = self.get_expiration_alerts(6)
            alerts.extend(exp_alerts)

            # Get calibration alerts
            cal_alerts = self.get_calibration_alerts(3)
            alerts.extend(cal_alerts)

            # Sort by reference date and take unique items (no duplicates if item has both)
            seen_items = set()
            unique_alerts = []
            for alert in sorted(alerts, key=lambda x: x.reference_date):
                if alert.item_id not in seen_items:
                    seen_items.add(alert.item_id)
                    unique_alerts.append(alert)

            logger.debug(f"Retrieved {len(unique_alerts)} unique alerts")
            return unique_alerts

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
            query = """
            SELECT i.id, i.name, i.expiration_date
            FROM Items i
            WHERE i.expiration_date IS NOT NULL
              AND i.expiration_date <= DATE('now', '+{} months')
            ORDER BY i.expiration_date ASC
            """.format(lead_months)

            rows = db.execute_query(query)
            alerts = []
            today = date.today()

            for row in rows:
                alert_date = date.fromisoformat(row['expiration_date'])
                days_until = (alert_date - today).days
                severity = self._determine_severity('Expiration Alert', days_until)

                alert = Alert(
                    item_id=row['id'],
                    item_name=row['name'],
                    alert_type='Expiration Alert',
                    reference_date=alert_date,
                    days_until=days_until,
                    severity=severity
                )
                alerts.append(alert)

            return alerts

        except Exception as e:
            logger.error(f"Failed to get expiration alerts: {e}")
            return []

    def get_calibration_alerts(self, lead_months: int = 3) -> List[Alert]:
        """
        Get equipment needing calibration based on calibration_date + 12 months.

        Args:
            lead_months: Months before due date to alert

        Returns:
            List of calibration alerts
        """
        try:
            query = """
            SELECT i.id, i.name, i.calibration_date,
                   DATE(i.calibration_date, '+12 months') as next_calibration
            FROM Items i
            WHERE i.calibration_date IS NOT NULL
              AND DATE('now') >= DATE(i.calibration_date, '+12 months', '-{} months')
            ORDER BY next_calibration ASC
            """.format(lead_months)

            rows = db.execute_query(query)
            alerts = []
            today = date.today()

            for row in rows:
                next_cal = row['next_calibration']
                if next_cal:
                    alert_date = date.fromisoformat(next_cal)
                    days_until = (alert_date - today).days
                    severity = self._determine_severity('Calibration Alert', days_until)

                    alert = Alert(
                        item_id=row['id'],
                        item_name=row['name'],
                        alert_type='Calibration Alert',
                        reference_date=alert_date,
                        days_until=days_until,
                        severity=severity
                    )
                    alerts.append(alert)

            return alerts

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
            return [alert for alert in all_alerts if alert.severity == 'Critical']
        except Exception as e:
            logger.error(f"Failed to get critical alerts: {e}")
            return []

    def _determine_severity(self, alert_type: str, days_until: int) -> str:
        """
        Determine alert severity based on type and days remaining.

        Args:
            alert_type: Type of alert
            days_until: Days until the alert date

        Returns:
            Severity level: 'Critical', 'Warning', or 'Info'
        """
        if days_until < 0:
            return 'Critical'  # Already past due
        elif days_until <= 7:
            return 'Critical'  # Within a week
        elif days_until <= 30:
            return 'Warning'   # Within a month
        else:
            return 'Info'      # More than a month away

# Global alert engine instance
alert_engine = AlertEngine()
