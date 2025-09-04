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
                ib.date_received as first_batch_date,
                COALESCE(stock.total_stock, 0) as total_stock,
                COALESCE(stock.total_stock, 0) - COALESCE(requested.requested_qty, 0) as available_stock,
                CASE
                    WHEN i.expiration_date IS NOT NULL
                         AND i.expiration_date <= DATE('now', '+6 months')
                    THEN 'expiration'
                    WHEN i.calibration_date IS NOT NULL
                         AND DATE('now') >= DATE(i.calibration_date, '+12 months')
                    THEN 'calibration'
                    ELSE ''
                END as alert_status,
                CASE
                    WHEN EXISTS (
                        SELECT 1 FROM Requisition_Items ri
                        JOIN Requisitions r ON ri.requisition_id = r.id
                        WHERE ri.item_id = i.id
                        AND NOT EXISTS (
                            SELECT 1 FROM Stock_Movements sm
                            WHERE sm.item_id = ri.item_id
                            AND sm.movement_type = 'RETURN'
                            AND sm.source_id = r.id
                        )
                    ) THEN 1
                    ELSE 0
                END as is_requested
            FROM Items i
            LEFT JOIN Categories c ON i.category_id = c.id
            LEFT JOIN Suppliers s ON i.supplier_id = s.id
            LEFT JOIN (
                SELECT item_id, MIN(date_received) as date_received
                FROM Item_Batches
                GROUP BY item_id
            ) ib ON i.id = ib.item_id
            LEFT JOIN (
                SELECT
                    ib.item_id,
                    SUM(ib.quantity_received) as original_stock,
                    COALESCE(disposed.disposed_qty, 0) as disposed_qty,
                    SUM(ib.quantity_received) - COALESCE(disposed.disposed_qty, 0) as total_stock
                FROM Item_Batches ib
                LEFT JOIN (
                    SELECT item_id, SUM(quantity) as disposed_qty
                    FROM Stock_Movements
                    WHERE movement_type = 'DISPOSAL'
                    GROUP BY item_id
                ) disposed ON ib.item_id = disposed.item_id
                GROUP BY ib.item_id
            ) stock ON i.id = stock.item_id
            LEFT JOIN (
                SELECT ri.item_id, SUM(ri.quantity_requested) as requested_qty
                FROM Requisition_Items ri
                JOIN Requisitions r ON ri.requisition_id = r.id
                WHERE NOT EXISTS (
                    SELECT 1 FROM Stock_Movements sm
                    WHERE sm.item_id = ri.item_id
                    AND sm.movement_type = 'RETURN'
                    AND sm.source_id = r.id
                )
                GROUP BY ri.item_id
            ) requested ON i.id = requested.item_id
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
                i.acquisition_date, i.last_modified,
                COALESCE(stock.total_stock, 0) as total_stock,
                COALESCE(stock.total_stock, 0) - COALESCE(requested.requested_qty, 0) as available_stock,
                CASE
                    WHEN EXISTS (
                        SELECT 1 FROM Requisition_Items ri
                        JOIN Requisitions r ON ri.requisition_id = r.id
                        WHERE ri.item_id = i.id
                        AND NOT EXISTS (
                            SELECT 1 FROM Stock_Movements sm
                            WHERE sm.item_id = ri.item_id
                            AND sm.movement_type = 'RETURN'
                            AND sm.source_id = r.id
                        )
                    ) THEN 1
                    ELSE 0
                END as is_requested
            FROM Items i
            LEFT JOIN Categories c ON i.category_id = c.id
            LEFT JOIN Suppliers s ON i.supplier_id = s.id
            LEFT JOIN (
                SELECT
                    ib.item_id,
                    SUM(ib.quantity_received) as original_stock,
                    COALESCE(disposed.disposed_qty, 0) as disposed_qty,
                    SUM(ib.quantity_received) - COALESCE(disposed.disposed_qty, 0) as total_stock
                FROM Item_Batches ib
                LEFT JOIN (
                    SELECT item_id, SUM(quantity) as disposed_qty
                    FROM Stock_Movements
                    WHERE movement_type = 'DISPOSAL'
                    GROUP BY item_id
                ) disposed ON ib.item_id = disposed.item_id
                GROUP BY ib.item_id
            ) stock ON i.id = stock.item_id
            LEFT JOIN (
                SELECT ri.item_id, SUM(ri.quantity_requested) as requested_qty
                FROM Requisition_Items ri
                JOIN Requisitions r ON ri.requisition_id = r.id
                WHERE NOT EXISTS (
                    SELECT 1 FROM Stock_Movements sm
                    WHERE sm.item_id = ri.item_id
                    AND sm.movement_type = 'RETURN'
                    AND sm.source_id = r.id
                )
                GROUP BY ri.item_id
            ) requested ON i.id = requested.item_id
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
                SUM(ri.quantity_requested) as total_quantity_used,
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

    def get_batch_statistics(self) -> Dict[str, int]:
        """Get overall batch statistics for the inventory."""
        try:
            # Query to get batch count and total stock across all batches
            query = """
            SELECT
                COUNT(*) as total_batches,
                COALESCE(SUM(ib.quantity_received), 0) as original_total_stock,
                COALESCE(disposed.disposed_qty, 0) as total_disposed,
                COALESCE(SUM(ib.quantity_received), 0) - COALESCE(disposed.disposed_qty, 0) as active_total_stock
            FROM Item_Batches ib
            LEFT JOIN (
                SELECT SUM(quantity) as disposed_qty
                FROM Stock_Movements
                WHERE movement_type = 'DISPOSAL'
            ) disposed ON 1=1
            """

            rows = db.execute_query(query)
            if not rows:
                return {'total_batches': 0, 'total_stock': 0, 'available_stock': 0}

            batch_stats = rows[0]

            # Calculate available stock (total - currently requested)
            available_query = """
            SELECT COALESCE(SUM(ri.quantity_requested), 0) as total_requested
            FROM Requisition_Items ri
            JOIN Requisitions r ON ri.requisition_id = r.id
            WHERE NOT EXISTS (
                SELECT 1 FROM Stock_Movements sm
                WHERE sm.item_id = ri.item_id
                AND sm.movement_type = 'RETURN'
                AND sm.source_id = r.id
            )
            """

            requested_rows = db.execute_query(available_query)
            total_requested = requested_rows[0]['total_requested'] if requested_rows else 0

            return {
                'total_batches': batch_stats['total_batches'] or 0,
                'total_stock': batch_stats['active_total_stock'] or 0,
                'available_stock': max(0, (batch_stats['active_total_stock'] or 0) - total_requested)
            }

        except Exception as e:
            logger.error(f"Failed to get batch statistics: {e}")
            return {'total_batches': 0, 'total_stock': 0, 'available_stock': 0}

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
