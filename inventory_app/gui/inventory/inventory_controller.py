"""
Controller for inventory management.
Handles database operations and data loading for inventory items.
"""

from typing import List, Optional, Dict, Any
from datetime import date
from inventory_app.database.connection import db
from inventory_app.services.item_status_service import item_status_service
from inventory_app.utils.logger import logger
from inventory_app.services.movement_types import MovementType


class InventoryController:
    """Controller for inventory operations."""

    def __init__(self):
        pass

    def _get_stock_calculations(self, item_id: Optional[int] = None) -> str:
        """
        Get consistent stock calculation SQL that accounts for all stock movements.
        Returns SQL subquery for stock calculations.

        Args:
            item_id: Optional item ID filter for single item calculations

        Returns:
            SQL subquery string for stock calculations
        """
        base_query = """
            SELECT
                ib.item_id,
                SUM(ib.quantity_received) as original_stock,
                COALESCE(movements.consumed_qty, 0) as consumed_qty,
                COALESCE(movements.disposed_qty, 0) as disposed_qty,
                COALESCE(movements.returned_qty, 0) as returned_qty,
                SUM(ib.quantity_received) -
                COALESCE(movements.consumed_qty, 0) -
                COALESCE(movements.disposed_qty, 0) +
                COALESCE(movements.returned_qty, 0) as total_stock
            FROM Item_Batches ib
            LEFT JOIN (
                SELECT
                    sm.item_id,
                        SUM(CASE WHEN sm.movement_type = ? THEN sm.quantity ELSE 0 END) as consumed_qty,
                        SUM(CASE WHEN sm.movement_type = ? THEN sm.quantity ELSE 0 END) as disposed_qty,
                        SUM(CASE WHEN sm.movement_type = ? THEN sm.quantity ELSE 0 END) as returned_qty
                FROM Stock_Movements sm
                GROUP BY sm.item_id
            ) movements ON ib.item_id = movements.item_id
        """
        # The movement type params will be passed when executing the final query

        if item_id:
            base_query += f" WHERE ib.item_id = {item_id}"

        base_query += " GROUP BY ib.item_id"

        return base_query

    def _get_requested_calculations(self) -> str:
        """
        Get consistent requested quantity calculation SQL.
        Two-phase logic: Active requisitions reduce available stock via REQUEST/RESERVATION movements.
        Finalized requisitions don't reduce available stock (movements have been replaced).
        Returns SQL subquery for requested calculations.
        """
        return """
            SELECT ri.item_id, SUM(ri.quantity_requested) as requested_qty
            FROM Requisition_Items ri
            JOIN Requisitions r ON ri.requisition_id = r.id
            JOIN Items i ON ri.item_id = i.id
            WHERE r.status != 'returned'  -- Only active requisitions reduce available stock
            AND EXISTS (
                SELECT 1 FROM Stock_Movements sm
                WHERE sm.item_id = ri.item_id
                AND sm.source_id = r.id
                AND (
                    (i.is_consumable = 1 AND sm.movement_type = ?) OR
                    (i.is_consumable = 0 AND sm.movement_type = ?)
                )
            )
            GROUP BY ri.item_id
        """

    def load_inventory_data(self) -> List[Dict[str, Any]]:
        """Load inventory items with related data from database."""
        try:
            query = (
                """
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
                            AND sm.movement_type = ?
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
                """
                + self._get_stock_calculations()
                + """
            ) stock ON i.id = stock.item_id
            LEFT JOIN (
                """
                + self._get_requested_calculations()
                + """
            ) requested ON i.id = requested.item_id
            ORDER BY c.name, i.name
            """
            )

            # Prepare ordered params for placeholders inside query text.
            params = (
                # is_requested clause (RETURN)
                MovementType.RETURN.value,
                # _get_stock_calculations() placeholders: CONSUMPTION, DISPOSAL, RETURN
                MovementType.CONSUMPTION.value,
                MovementType.DISPOSAL.value,
                MovementType.RETURN.value,
                # _get_requested_calculations() placeholders: RESERVATION, REQUEST
                MovementType.RESERVATION.value,
                MovementType.REQUEST.value,
            )
            rows = db.execute_query(query, params)
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

            query = (
                """
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
                            AND sm.movement_type = ?
                            AND sm.source_id = r.id
                        )
                    ) THEN 1
                    ELSE 0
                END as is_requested
            FROM Items i
            LEFT JOIN Categories c ON i.category_id = c.id
            LEFT JOIN Suppliers s ON i.supplier_id = s.id
            LEFT JOIN (
                """
                + self._get_stock_calculations()
                + """
            ) stock ON i.id = stock.item_id
            LEFT JOIN (
                """
                + self._get_requested_calculations()
                + """
            ) requested ON i.id = requested.item_id
            WHERE i.name LIKE ? OR c.name LIKE ? OR s.name LIKE ?
            ORDER BY c.name, i.name
            """
            )

            search_pattern = f"%{search_term}%"
            # Params order mirrors placeholder order in the query:
            params = (
                MovementType.RETURN.value,
                MovementType.CONSUMPTION.value,
                MovementType.DISPOSAL.value,
                MovementType.RETURN.value,
                MovementType.RESERVATION.value,
                MovementType.REQUEST.value,
                search_pattern,
                search_pattern,
                search_pattern,
            )
            rows = db.execute_query(query, params)

            logger.debug(f"Search for '{search_term}' returned {len(rows)} items")
            return rows

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    def get_item_usage(
        self,
        item_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
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
                    "total_requisitions": row["total_requisitions"] or 0,
                    "total_quantity_used": row["total_quantity_used"] or 0,
                    "first_used": row["first_used"],
                    "last_used": row["last_used"],
                }
            return {
                "total_requisitions": 0,
                "total_quantity_used": 0,
                "first_used": None,
                "last_used": None,
            }

        except Exception as e:
            logger.error(f"Failed to get item usage for {item_id}: {e}")
            return {
                "total_requisitions": 0,
                "total_quantity_used": 0,
                "first_used": None,
                "last_used": None,
            }

    def get_batch_statistics(self) -> Dict[str, int]:
        """Get overall batch statistics for the inventory."""
        try:
            # Get consistent stock calculations and requested quantities
            stock_query = """
            SELECT
                COUNT(DISTINCT ib.id) as total_batches,
                COALESCE(SUM(ib.quantity_received), 0) as original_total_stock,
                COALESCE(movements.total_consumed, 0) as total_consumed,
                COALESCE(movements.total_disposed, 0) as total_disposed,
                COALESCE(movements.total_returned, 0) as total_returned,
                COALESCE(SUM(ib.quantity_received), 0) -
                COALESCE(movements.total_consumed, 0) -
                COALESCE(movements.total_disposed, 0) +
                COALESCE(movements.total_returned, 0) as total_stock
            FROM Item_Batches ib
            LEFT JOIN (
                SELECT
                    SUM(CASE WHEN sm.movement_type = ? THEN sm.quantity ELSE 0 END) as total_consumed,
                    SUM(CASE WHEN sm.movement_type = ? THEN sm.quantity ELSE 0 END) as total_disposed,
                    SUM(CASE WHEN sm.movement_type = ? THEN sm.quantity ELSE 0 END) as total_returned
                FROM Stock_Movements sm
            ) movements ON 1=1
            """
            stock_params = (
                MovementType.CONSUMPTION.value,
                MovementType.DISPOSAL.value,
                MovementType.RETURN.value,
            )
            stock_rows = db.execute_query(stock_query, stock_params)
            if not stock_rows:
                return {"total_batches": 0, "total_stock": 0, "available_stock": 0}

            batch_stats = stock_rows[0]

            # Calculate available stock using new two-phase logic
            available_query = """
            SELECT COALESCE(SUM(ri.quantity_requested), 0) as total_requested
            FROM Requisition_Items ri
            JOIN Requisitions r ON ri.requisition_id = r.id
            JOIN Items i ON ri.item_id = i.id
            WHERE r.status != 'returned'  -- Only active requisitions reduce available stock
            AND EXISTS (
                SELECT 1 FROM Stock_Movements sm
                WHERE sm.item_id = ri.item_id
                AND sm.source_id = r.id
                AND (
                    (i.is_consumable = 1 AND sm.movement_type = ?) OR
                    (i.is_consumable = 0 AND sm.movement_type = ?)
                )
            )
            """
            available_params = (
                MovementType.RESERVATION.value,
                MovementType.REQUEST.value,
            )
            requested_rows = db.execute_query(available_query, available_params)
            total_requested = (
                requested_rows[0]["total_requested"] if requested_rows else 0
            )

            return {
                "total_batches": batch_stats["total_batches"] or 0,
                "total_stock": batch_stats["total_stock"] or 0,
                "available_stock": max(
                    0, (batch_stats["total_stock"] or 0) - total_requested
                ),
            }

        except Exception as e:
            logger.error(f"Failed to get batch statistics: {e}")
            return {"total_batches": 0, "total_stock": 0, "available_stock": 0}

    def get_categories(self) -> List[str]:
        """Get list of unique categories."""
        try:
            rows = db.execute_query(
                "SELECT DISTINCT name FROM Categories ORDER BY name"
            )
            return [row["name"] for row in rows]
        except Exception as e:
            logger.error(f"Failed to get categories: {e}")
            return []

    def get_suppliers(self) -> List[str]:
        """Get list of unique suppliers."""
        try:
            rows = db.execute_query("SELECT DISTINCT name FROM Suppliers ORDER BY name")
            return [row["name"] for row in rows]
        except Exception as e:
            logger.error(f"Failed to get suppliers: {e}")
            return []

    def get_inventory_statistics(self) -> Dict[str, Any]:
        """Get complete inventory statistics including alerts."""
        try:
            # Get basic batch statistics
            batch_stats = self.get_batch_statistics()

            # Get alert counts from status service
            alert_counts = item_status_service.get_alert_counts()

            # Get low stock count
            low_stock_query = """
            SELECT COUNT(*) as count FROM (
                SELECT ib.item_id,
                        SUM(ib.quantity_received) -
                        COALESCE(SUM(CASE WHEN sm.movement_type = ? THEN sm.quantity ELSE 0 END), 0) -
                        COALESCE(SUM(CASE WHEN sm.movement_type = ? THEN sm.quantity ELSE 0 END), 0) +
                        COALESCE(SUM(CASE WHEN sm.movement_type = ? THEN sm.quantity ELSE 0 END), 0) as current_stock
                FROM Item_Batches ib
                LEFT JOIN Stock_Movements sm ON sm.item_id = ib.item_id
                WHERE ib.disposal_date IS NULL
                GROUP BY ib.item_id
                HAVING current_stock < 10 AND current_stock > 0
            )
            """
            low_stock_params = (
                MovementType.CONSUMPTION.value,
                MovementType.DISPOSAL.value,
                MovementType.RETURN.value,
            )
            low_stock_result = db.execute_query(low_stock_query, low_stock_params)
            low_stock_count = low_stock_result[0]["count"] if low_stock_result else 0

            # Combine all statistics
            stats = {
                "total_batches": batch_stats["total_batches"],
                "total_stock": batch_stats["total_stock"],
                "available_stock": batch_stats["available_stock"],
                "low_stock": low_stock_count,
                "expiring": alert_counts.get("expiring", 0),
                "expired": alert_counts.get("expired", 0),
                "calibration_warning": alert_counts.get("calibration_warning", 0),
                "calibration_due": alert_counts.get("calibration_due", 0),
            }

            logger.debug(f"Generated complete inventory statistics: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Failed to get inventory statistics: {e}")
            return {
                "total_batches": 0,
                "total_stock": 0,
                "available_stock": 0,
                "low_stock": 0,
                "expiring": 0,
                "expired": 0,
                "calibration_warning": 0,
                "calibration_due": 0,
            }
