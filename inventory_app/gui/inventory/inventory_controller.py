"""
Controller for inventory management.
Handles database operations and data loading for inventory items.
"""

from typing import List, Optional, Dict, Any
from datetime import date
from inventory_app.database.connection import db
from inventory_app.utils.logger import logger


class InventoryController:
    """Controller for inventory operations."""

    def __init__(self):
        pass

    def load_inventory_data(self) -> List[Dict[str, Any]]:
        """Load inventory items with related data from database."""
        try:
            query = """
            SELECT
                i.id,
                i.name,
                c.name as category_name,
                ct.name as category_type_name,
                i.size,
                i.brand,
                s.name as supplier_name,
                i.other_specifications,
                i.po_number,
                i.expiration_date,
                i.calibration_date,
                i.is_consumable,
                i.acquisition_date,
                i.last_modified,
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
                    ELSE ''
                END as alert_status
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
            ORDER BY c.name, i.name
            """

            rows = db.execute_query(query)
            logger.info(f"Loaded {len(rows)} inventory items from database")
            return rows

        except Exception as e:
            logger.error(f"Error loading inventory data: {e}")
            raise

    def search_items(self, search_term: str) -> List[Dict[str, Any]]:
        """Search items by name, category, or supplier."""
        try:
            if not search_term:
                return []

            query = """
            SELECT
                i.id, i.name, c.name as category_name, i.size, i.brand,
                s.name as supplier_name, i.other_specifications, i.po_number,
                i.expiration_date, i.calibration_date, i.is_consumable,
                i.acquisition_date, i.last_modified
            FROM Items i
            LEFT JOIN Categories c ON i.category_id = c.id
            LEFT JOIN Suppliers s ON i.supplier_id = s.id
            WHERE i.name LIKE ? OR c.name LIKE ? OR s.name LIKE ?
            ORDER BY c.name, i.name
            """

            search_pattern = f"%{search_term}%"
            rows = db.execute_query(query, (search_pattern, search_pattern, search_pattern))

            logger.debug(f"Search for '{search_term}' returned {len(rows)} items")
            return rows

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    def get_item_usage(self, item_id: int, start_date: Optional[date] = None, end_date: Optional[date] = None) -> Dict[str, Any]:
        """Get usage statistics for a specific item (Spec #12)."""
        try:
            query = """
            SELECT
                COUNT(ri.id) as total_requisitions,
                SUM(ri.quantity_borrowed) as total_quantity_used,
                MIN(r.lab_activity_date) as first_used,
                MAX(r.lab_activity_date) as last_used
            FROM Requisition_Items ri
            JOIN Requisitions r ON ri.requisition_id = r.id
            WHERE ri.item_id = ?
            """

            params = [str(item_id)]

            if start_date and end_date:
                query += " AND r.lab_activity_date BETWEEN ? AND ?"
                params.extend([start_date.isoformat(), end_date.isoformat()])

            params = tuple(params)

            rows = db.execute_query(query, params)

            if rows:
                row = rows[0]
                return {
                    "total_requisitions": row['total_requisitions'] or 0,
                    "total_quantity_used": row['total_quantity_used'] or 0,
                    "first_used": row['first_used'],
                    "last_used": row['last_used']
                }
            return {
                "total_requisitions": 0,
                "total_quantity_used": 0,
                "first_used": None,
                "last_used": None
            }

        except Exception as e:
            logger.error(f"Failed to get item usage for {item_id}: {e}")
            return {
                "total_requisitions": 0,
                "total_quantity_used": 0,
                "first_used": None,
                "last_used": None
            }

    def get_categories(self) -> List[str]:
        """Get list of unique categories."""
        try:
            rows = db.execute_query("SELECT DISTINCT name FROM Categories ORDER BY name")
            return [row['name'] for row in rows]
        except Exception as e:
            logger.error(f"Failed to get categories: {e}")
            return []

    def get_suppliers(self) -> List[str]:
        """Get list of unique suppliers."""
        try:
            rows = db.execute_query("SELECT DISTINCT name FROM Suppliers ORDER BY name")
            return [row['name'] for row in rows]
        except Exception as e:
            logger.error(f"Failed to get suppliers: {e}")
            return []
