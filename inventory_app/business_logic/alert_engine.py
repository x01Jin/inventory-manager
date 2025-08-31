"""
Alert engine for the inventory application.
Handles calculation and retrieval of alerts for expiration, calibration, and lifecycle.
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
    alert_type: str  # 'Expiration Alert', 'Calibration Alert', 'Lifecycle Alert'
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
        Get all current alerts from the Alerts view.

        Returns:
            List of Alert objects
        """
        try:
            query = "SELECT * FROM Alerts ORDER BY reference_date ASC"
            rows = db.execute_query(query)

            alerts = []
            today = date.today()

            for row in rows:
                alert_date = date.fromisoformat(row['reference_date'])
                days_until = (alert_date - today).days

                # Determine severity based on days until and alert type
                severity = self._determine_severity(row['alert_type'], days_until)

                alert = Alert(
                    item_id=row['item_id'],
                    item_name=row['name'],
                    alert_type=row['alert_type'],
                    reference_date=alert_date,
                    days_until=days_until,
                    severity=severity
                )
                alerts.append(alert)

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
        Get equipment needing calibration.

        Args:
            lead_months: Months before due date to alert

        Returns:
            List of calibration alerts
        """
        try:
            query = """
            SELECT i.id, i.name, cal.next_calibration_date
            FROM Items i
            JOIN Item_Calibration_Due cal ON cal.item_id = i.id
            WHERE cal.next_calibration_date IS NOT NULL
              AND DATE('now') >= DATE(cal.next_calibration_date, '-{} months')
            ORDER BY cal.next_calibration_date ASC
            """.format(lead_months)

            rows = db.execute_query(query)
            alerts = []
            today = date.today()

            for row in rows:
                alert_date = date.fromisoformat(row['next_calibration_date'])
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

    def get_lifecycle_alerts(self) -> List[Alert]:
        """
        Get items reaching end of lifecycle.

        Returns:
            List of lifecycle alerts
        """
        try:
            query = """
            SELECT i.id, i.name, lr.lifespan_years, s.start_date
            FROM Items i
            JOIN Categories c ON i.category_id = c.id
            JOIN Lifecycle_Rules lr ON c.category_type_id = lr.category_type_id
            JOIN Item_Start_Dates s ON s.item_id = i.id
            WHERE lr.lifespan_years IS NOT NULL
              AND s.start_date IS NOT NULL
              AND DATE(s.start_date, '+' || lr.lifespan_years || ' years') <= DATE('now')
            ORDER BY DATE(s.start_date, '+' || lr.lifespan_years || ' years') ASC
            """

            rows = db.execute_query(query)
            alerts = []
            today = date.today()

            for row in rows:
                start_date = date.fromisoformat(row['start_date'])
                lifespan_years = row['lifespan_years']
                alert_date = start_date.replace(year=start_date.year + lifespan_years)
                days_until = (alert_date - today).days
                severity = self._determine_severity('Lifecycle Alert', days_until)

                alert = Alert(
                    item_id=row['id'],
                    item_name=row['name'],
                    alert_type='Lifecycle Alert',
                    reference_date=alert_date,
                    days_until=days_until,
                    severity=severity
                )
                alerts.append(alert)

            return alerts

        except Exception as e:
            logger.error(f"Failed to get lifecycle alerts: {e}")
            return []

    def get_alerts_by_item(self, item_id: int) -> List[Alert]:
        """
        Get all alerts for a specific item.

        Args:
            item_id: The item ID

        Returns:
            List of alerts for the item
        """
        try:
            all_alerts = self.get_all_alerts()
            return [alert for alert in all_alerts if alert.item_id == item_id]
        except Exception as e:
            logger.error(f"Failed to get alerts for item {item_id}: {e}")
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

    def get_alert_summary(self) -> Dict[str, int]:
        """
        Get summary counts of alerts by type.

        Returns:
            Dictionary with alert counts
        """
        try:
            alerts = self.get_all_alerts()
            summary = {
                'total': len(alerts),
                'expiration': len([a for a in alerts if a.alert_type == 'Expiration Alert']),
                'calibration': len([a for a in alerts if a.alert_type == 'Calibration Alert']),
                'lifecycle': len([a for a in alerts if a.alert_type == 'Lifecycle Alert']),
                'critical': len([a for a in alerts if a.severity == 'Critical'])
            }
            return summary
        except Exception as e:
            logger.error(f"Failed to get alert summary: {e}")
            return {'total': 0, 'expiration': 0, 'calibration': 0, 'lifecycle': 0, 'critical': 0}

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
