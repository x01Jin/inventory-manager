"""
Stock calculation service - centralized stock calculations for inventory.
Eliminates duplicate SQL patterns across the codebase.
"""

from typing import Optional, Tuple
from inventory_app.database.connection import db
from inventory_app.services.movement_types import MovementType
from inventory_app.utils.logger import logger


class StockCalculationService:
    """
    Centralized service for stock calculations.
    Provides consistent SQL patterns for calculating stock across all movements.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def instance(cls):
        """Get the singleton instance."""
        return cls()

    def get_stock_calculation_subquery(self, item_id: Optional[int] = None) -> str:
        """
        Get consistent stock calculation SQL subquery.
        Accounts for all stock movements: CONSUMPTION, DISPOSAL, RETURN.

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

        if item_id is not None:
            base_query += f" WHERE ib.item_id = {item_id}"

        base_query += " GROUP BY ib.item_id"

        return base_query

    def get_stock_calculation_params(self) -> Tuple:
        """Get the parameters for stock calculation queries."""
        return (
            MovementType.CONSUMPTION.value,
            MovementType.DISPOSAL.value,
            MovementType.RETURN.value,
        )

    def get_requisition_calculation_subquery(self) -> str:
        """
        Get consistent requested quantity calculation SQL subquery.
        Two-phase logic: Active requisitions reduce available stock via REQUEST/RESERVATION movements.

        Returns:
            SQL subquery string for requested calculations
        """
        return """
            SELECT ri.item_id, SUM(ri.quantity_requested) as requested_qty
            FROM Requisition_Items ri
            JOIN Requisitions r ON ri.requisition_id = r.id
            JOIN Items i ON ri.item_id = i.id
            WHERE r.status != 'returned'
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

    def get_requisition_calculation_params(self) -> Tuple:
        """Get the parameters for requisition calculation queries."""
        return (
            MovementType.RESERVATION.value,
            MovementType.REQUEST.value,
        )

    def get_aggregated_stock_query(self) -> str:
        """
        Get query for aggregated stock statistics across all batches.

        Returns:
            SQL query string for aggregated stock
        """
        return """
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
                    SUM(CASE WHEN movement_type = ? THEN quantity ELSE 0 END) as total_consumed,
                    SUM(CASE WHEN movement_type = ? THEN quantity ELSE 0 END) as total_disposed,
                    SUM(CASE WHEN movement_type = ? THEN quantity ELSE 0 END) as total_returned
                FROM Stock_Movements
            ) movements ON 1=1
            WHERE ib.disposal_date IS NULL
        """

    def get_low_stock_subquery(self) -> str:
        """
        Get subquery for identifying low stock items.

        Returns:
            SQL subquery for low stock items
        """
        return """
            SELECT ib.item_id,
                    SUM(ib.quantity_received) -
                    COALESCE(SUM(CASE WHEN sm.movement_type = ? THEN sm.quantity ELSE 0 END), 0) -
                    COALESCE(SUM(CASE WHEN sm.movement_type = ? THEN sm.quantity ELSE 0 END), 0) +
                    COALESCE(SUM(CASE WHEN sm.movement_type = ? THEN sm.quantity ELSE 0 END), 0) as current_stock
            FROM Item_Batches ib
            LEFT JOIN Stock_Movements sm ON sm.item_id = ib.item_id
            WHERE ib.disposal_date IS NULL
            GROUP BY ib.item_id
            HAVING current_stock < ? AND current_stock > 0
        """

    def get_low_stock_params(self, threshold: int = 10) -> Tuple:
        """Get parameters for low stock query."""
        return (
            MovementType.CONSUMPTION.value,
            MovementType.DISPOSAL.value,
            MovementType.RETURN.value,
            threshold,
        )

    def get_item_status_stock_subquery(self) -> str:
        """
        Get subquery for item status service stock calculation.
        Used to exclude items with 0 stock from alerts.

        Returns:
            SQL subquery for stock in item status context
        """
        return """
            SELECT
                ib.item_id,
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
            GROUP BY ib.item_id
        """

    def get_item_status_stock_params(self) -> Tuple:
        """Get parameters for item status stock query."""
        return (
            MovementType.CONSUMPTION.value,
            MovementType.DISPOSAL.value,
            MovementType.RETURN.value,
        )

    def calculate_total_stock(self, item_id: int) -> int:
        """
        Calculate total stock for a single item.

        Args:
            item_id: The item ID

        Returns:
            Total stock quantity
        """
        try:
            query = """
            SELECT
                COALESCE(SUM(ib.quantity_received), 0) as original_stock,
                COALESCE(movements.consumed_qty, 0) as consumed_qty,
                COALESCE(movements.disposed_qty, 0) as disposed_qty,
                COALESCE(movements.returned_qty, 0) as returned_qty,
                COALESCE(SUM(ib.quantity_received), 0) -
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
                WHERE sm.item_id = ?
                GROUP BY sm.item_id
            ) movements ON ib.item_id = movements.item_id
            WHERE ib.item_id = ?
            """
            params = (
                MovementType.CONSUMPTION.value,
                MovementType.DISPOSAL.value,
                MovementType.RETURN.value,
                item_id,
                item_id,
            )
            rows = db.execute_query(query, params)
            return rows[0]["total_stock"] if rows else 0
        except Exception as e:
            logger.error(f"Failed to calculate total stock for item {item_id}: {e}")
            return 0

    def calculate_batch_stock(self, batch_id: int) -> int:
        """
        Calculate total stock for a single batch.

        Args:
            batch_id: The batch ID

        Returns:
            Total stock quantity for the batch
        """
        try:
            query = """
            SELECT
                ib.quantity_received,
                COALESCE(movements.consumed_qty, 0) as consumed_qty,
                COALESCE(movements.disposed_qty, 0) as disposed_qty,
                COALESCE(movements.returned_qty, 0) as returned_qty,
                ib.quantity_received -
                COALESCE(movements.consumed_qty, 0) -
                COALESCE(movements.disposed_qty, 0) +
                COALESCE(movements.returned_qty, 0) as total_stock
            FROM Item_Batches ib
            LEFT JOIN (
                SELECT
                    sm.batch_id,
                    SUM(CASE WHEN sm.movement_type = ? THEN sm.quantity ELSE 0 END) as consumed_qty,
                    SUM(CASE WHEN sm.movement_type = ? THEN sm.quantity ELSE 0 END) as disposed_qty,
                    SUM(CASE WHEN sm.movement_type = ? THEN sm.quantity ELSE 0 END) as returned_qty
                FROM Stock_Movements sm
                WHERE sm.batch_id = ?
                GROUP BY sm.batch_id
            ) movements ON ib.id = movements.batch_id
            WHERE ib.id = ?
            """
            params = (
                MovementType.CONSUMPTION.value,
                MovementType.DISPOSAL.value,
                MovementType.RETURN.value,
                batch_id,
                batch_id,
            )
            rows = db.execute_query(query, params)
            if not rows:
                return 0
            return rows[0]["total_stock"] or 0
        except Exception as e:
            logger.error(f"Failed to calculate stock for batch {batch_id}: {e}")
            return 0


stock_calculation_service = StockCalculationService()
