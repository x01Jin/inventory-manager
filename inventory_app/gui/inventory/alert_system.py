"""
Alert system for inventory items.
Handles expiration and calibration alerts (Specs #10-11).
"""

from typing import List, Dict, Any, Optional
from datetime import date
from inventory_app.database.connection import db
from inventory_app.utils.logger import logger


class AlertSystem:
    """System for managing and displaying inventory alerts."""

    def __init__(self):
        pass

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts from the database."""
        try:
            query = """
            SELECT
                i.id,
                i.name,
                c.name as category_name,
                ct.name as category_type_name,
                i.expiration_date,
                i.calibration_date,
                lr.expiry_lead_months,
                lr.lifespan_years,
                lr.calibration_interval_months,
                lr.calibration_lead_months,
                ib.date_received as first_batch_date,
                CASE
                    WHEN i.expiration_date IS NOT NULL AND lr.expiry_lead_months IS NOT NULL
                         AND i.expiration_date <= DATE('now', '+' || lr.expiry_lead_months || ' months')
                    THEN 'expiration'
                    WHEN lr.calibration_interval_months IS NOT NULL AND i.calibration_date IS NOT NULL
                         AND DATE('now') >= DATE(i.calibration_date, '+' || lr.calibration_interval_months || ' months', '-' || COALESCE(lr.calibration_lead_months, 0) || ' months')
                    THEN 'calibration'
                    WHEN lr.lifespan_years IS NOT NULL AND ib.date_received IS NOT NULL
                         AND DATE('now') >= DATE(ib.date_received, '+' || lr.lifespan_years || ' years')
                    THEN 'lifecycle'
                    ELSE NULL
                END as alert_type,
                CASE
                    WHEN i.expiration_date IS NOT NULL AND lr.expiry_lead_months IS NOT NULL
                         AND i.expiration_date <= DATE('now', '+' || lr.expiry_lead_months || ' months')
                    THEN DATE(i.expiration_date, '-' || lr.expiry_lead_months || ' months')
                    WHEN lr.calibration_interval_months IS NOT NULL AND i.calibration_date IS NOT NULL
                         AND DATE('now') >= DATE(i.calibration_date, '+' || lr.calibration_interval_months || ' months', '-' || COALESCE(lr.calibration_lead_months, 0) || ' months')
                    THEN DATE(i.calibration_date, '+' || lr.calibration_interval_months || ' months')
                    WHEN lr.lifespan_years IS NOT NULL AND ib.date_received IS NOT NULL
                         AND DATE('now') >= DATE(ib.date_received, '+' || lr.lifespan_years || ' years')
                    THEN DATE(ib.date_received, '+' || lr.lifespan_years || ' years')
                    ELSE NULL
                END as alert_date
            FROM Items i
            LEFT JOIN Categories c ON i.category_id = c.id
            LEFT JOIN Category_Types ct ON c.category_type_id = ct.id
            LEFT JOIN Suppliers s ON i.supplier_id = s.id
            LEFT JOIN Lifecycle_Rules lr ON ct.id = lr.category_type_id
            LEFT JOIN (
                SELECT item_id, MIN(date_received) as date_received
                FROM Item_Batches
                GROUP BY item_id
            ) ib ON i.id = ib.item_id
            WHERE alert_type IS NOT NULL
            ORDER BY alert_date ASC, c.name, i.name
            """

            rows = db.execute_query(query)
            alerts = []

            for row in rows:
                alert = {
                    'id': row['id'],
                    'name': row['name'],
                    'category_name': row['category_name'] or 'Uncategorized',
                    'category_type_name': row['category_type_name'],
                    'alert_type': row['alert_type'],
                    'alert_date': row.get('alert_date'),
                    'expiration_date': row.get('expiration_date'),
                    'calibration_date': row.get('calibration_date'),
                    'first_batch_date': row.get('first_batch_date')
                }
                alerts.append(alert)

            logger.debug(f"Found {len(alerts)} active alerts")
            return alerts

        except Exception as e:
            logger.error(f"Failed to get active alerts: {e}")
            return []

    def get_expiring_alerts(self, days_ahead: int = 180) -> List[Dict[str, Any]]:
        """Get items expiring within specified days (Spec #10)."""
        try:
            query = """
            SELECT
                i.id, i.name, c.name as category_name,
                i.expiration_date, lr.expiry_lead_months,
                DATE('now', '+' || ? || ' days') as cutoff_date
            FROM Items i
            LEFT JOIN Categories c ON i.category_id = c.id
            LEFT JOIN Category_Types ct ON c.category_type_id = ct.id
            LEFT JOIN Lifecycle_Rules lr ON ct.id = lr.category_type_id
            WHERE i.expiration_date IS NOT NULL
              AND lr.expiry_lead_months IS NOT NULL
              AND i.expiration_date <= DATE('now', '+' || lr.expiry_lead_months || ' months')
            ORDER BY i.expiration_date ASC
            """

            rows = db.execute_query(query, (days_ahead,))
            alerts = []

            for row in rows:
                alert = {
                    'id': row['id'],
                    'name': row['name'],
                    'category_name': row['category_name'] or 'Uncategorized',
                    'expiration_date': row['expiration_date'],
                    'days_until_expiry': self._calculate_days_until(row['expiration_date']),
                    'alert_type': 'expiration'
                }
                alerts.append(alert)

            logger.debug(f"Found {len(alerts)} expiring alerts within {days_ahead} days")
            return alerts

        except Exception as e:
            logger.error(f"Failed to get expiring alerts: {e}")
            return []

    def get_calibration_alerts(self, days_ahead: int = 90) -> List[Dict[str, Any]]:
        """Get items due for calibration within specified days (Spec #11)."""
        try:
            query = """
            SELECT
                i.id, i.name, c.name as category_name,
                i.calibration_date, lr.calibration_interval_months, lr.calibration_lead_months,
                DATE(i.calibration_date, '+' || lr.calibration_interval_months || ' months') as next_calibration
            FROM Items i
            LEFT JOIN Categories c ON i.category_id = c.id
            LEFT JOIN Category_Types ct ON c.category_type_id = ct.id
            LEFT JOIN Lifecycle_Rules lr ON ct.id = lr.category_type_id
            WHERE lr.calibration_interval_months IS NOT NULL
              AND i.calibration_date IS NOT NULL
              AND DATE('now') >= DATE(i.calibration_date, '+' || lr.calibration_interval_months || ' months', '-' || COALESCE(lr.calibration_lead_months, 0) || ' months')
            ORDER BY next_calibration ASC
            """

            rows = db.execute_query(query)
            alerts = []

            for row in rows:
                next_cal = row.get('next_calibration')
                alert = {
                    'id': row['id'],
                    'name': row['name'],
                    'category_name': row['category_name'] or 'Uncategorized',
                    'calibration_date': row['calibration_date'],
                    'next_calibration': next_cal,
                    'days_until_calibration': self._calculate_days_until(next_cal) if next_cal else None,
                    'alert_type': 'calibration'
                }
                alerts.append(alert)

            logger.debug(f"Found {len(alerts)} calibration alerts within {days_ahead} days")
            return alerts

        except Exception as e:
            logger.error(f"Failed to get calibration alerts: {e}")
            return []

    def get_lifecycle_alerts(self) -> List[Dict[str, Any]]:
        """Get items reaching end of lifecycle (Spec #10)."""
        try:
            query = """
            SELECT
                i.id, i.name, c.name as category_name,
                ib.date_received as first_batch_date,
                lr.lifespan_years,
                DATE(ib.date_received, '+' || lr.lifespan_years || ' years') as end_of_life
            FROM Items i
            LEFT JOIN Categories c ON i.category_id = c.id
            LEFT JOIN Category_Types ct ON c.category_type_id = ct.id
            LEFT JOIN Lifecycle_Rules lr ON ct.id = lr.category_type_id
            LEFT JOIN (
                SELECT item_id, MIN(date_received) as date_received
                FROM Item_Batches
                GROUP BY item_id
            ) ib ON i.id = ib.item_id
            WHERE lr.lifespan_years IS NOT NULL
              AND ib.date_received IS NOT NULL
              AND DATE('now') >= DATE(ib.date_received, '+' || lr.lifespan_years || ' years')
            ORDER BY end_of_life ASC
            """

            rows = db.execute_query(query)
            alerts = []

            for row in rows:
                end_of_life = row.get('end_of_life')
                alert = {
                    'id': row['id'],
                    'name': row['name'],
                    'category_name': row['category_name'] or 'Uncategorized',
                    'first_batch_date': row['first_batch_date'],
                    'lifespan_years': row['lifespan_years'],
                    'end_of_life': end_of_life,
                    'days_past_lifecycle': self._calculate_days_since(end_of_life) if end_of_life else None,
                    'alert_type': 'lifecycle'
                }
                alerts.append(alert)

            logger.debug(f"Found {len(alerts)} lifecycle alerts")
            return alerts

        except Exception as e:
            logger.error(f"Failed to get lifecycle alerts: {e}")
            return []

    def get_alert_summary(self) -> Dict[str, int]:
        """Get summary of all alert types."""
        alerts = self.get_active_alerts()
        summary = {
            'total_alerts': len(alerts),
            'expiration_alerts': sum(1 for a in alerts if a['alert_type'] == 'expiration'),
            'calibration_alerts': sum(1 for a in alerts if a['alert_type'] == 'calibration'),
            'lifecycle_alerts': sum(1 for a in alerts if a['alert_type'] == 'lifecycle')
        }
        return summary

    def get_item_alerts(self, item_id: int) -> List[Dict[str, Any]]:
        """Get all alerts for a specific item."""
        alerts = self.get_active_alerts()
        return [alert for alert in alerts if alert['id'] == item_id]

    def _calculate_days_until(self, target_date: Optional[str]) -> Optional[int]:
        """Calculate days until target date."""
        if not target_date:
            return None

        try:
            target = date.fromisoformat(target_date)
            today = date.today()
            return (target - today).days
        except (ValueError, TypeError):
            return None

    def _calculate_days_since(self, target_date: Optional[str]) -> Optional[int]:
        """Calculate days since target date."""
        if not target_date:
            return None

        try:
            target = date.fromisoformat(target_date)
            today = date.today()
            return (today - target).days
        except (ValueError, TypeError):
            return None
