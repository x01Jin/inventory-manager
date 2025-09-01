"""
Stock movement service - handles stock movement operations.
Provides centralized stock tracking and movement recording.
"""

from typing import List, Dict
from datetime import date
from inventory_app.database.connection import db
from inventory_app.utils.logger import logger


class StockMovementService:
    """
    Service for stock movement operations.
    Handles recording consumption, returns, and stock queries.
    """

    def __init__(self):
        """Initialize the stock movement service."""
        logger.info("Stock movement service initialized")

    def record_consumption(self, item_id: int, quantity: int, source_id: int, note: str) -> None:
        """
        Record item consumption (borrowing).

        Args:
            item_id: ID of the item
            quantity: Quantity consumed
            source_id: Requisition ID
            note: Description/note for the movement
        """
        self._record_movement(item_id, 'CONSUMPTION', quantity, source_id, note)

    def record_return(self, item_id: int, quantity: int, source_id: int, note: str) -> None:
        """
        Record item return.

        Args:
            item_id: ID of the item
            quantity: Quantity returned
            source_id: Requisition ID
            note: Description/note for the movement
        """
        self._record_movement(item_id, 'RETURN', quantity, source_id, note)

    def process_return(self, requisition_id: int, return_data: List[Dict], editor_name: str) -> bool:
        """
        Process returns for multiple items in a requisition.

        Args:
            requisition_id: ID of the requisition
            return_data: List of dicts with item_id and quantity_returned
            editor_name: Name of person processing return

        Returns:
            bool: True if successful
        """
        try:
            for return_item in return_data:
                note = f"Items returned by {editor_name}"
                self.record_return(
                    return_item['item_id'],
                    return_item['quantity_returned'],
                    requisition_id,
                    note
                )

            logger.info(f"Processed return for requisition {requisition_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to process return for requisition {requisition_id}: {e}")
            return False

    def _record_movement(self, item_id: int, movement_type: str, quantity: int,
                        source_id: int, note: str) -> None:
        """
        Record a stock movement in the database.

        Args:
            item_id: ID of the item
            movement_type: Type of movement ('CONSUMPTION', 'RETURN', etc.)
            quantity: Quantity moved
            source_id: Source identifier (requisition ID)
            note: Descriptive note
        """
        try:
            query = """
            INSERT INTO Stock_Movements (item_id, movement_type, quantity, movement_date, source_id, note)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            db.execute_update(query, (
                item_id,
                movement_type,
                quantity,
                date.today().isoformat(),
                source_id,
                note
            ))
            logger.debug(f"Recorded {movement_type} movement for item {item_id}: {quantity} units")
        except Exception as e:
            logger.error(f"Failed to record stock movement: {e}")

    def get_current_stock_level(self, item_id: int) -> int:
        """
        Calculate current stock level for an item based on movements.

        Args:
            item_id: ID of the item

        Returns:
            Current stock level
        """
        try:
            # This would need to be implemented based on your stock movement logic
            # For now, return a placeholder
            query = """
            SELECT COALESCE(SUM(
                CASE
                    WHEN movement_type = 'RECEIPT' THEN quantity
                    WHEN movement_type = 'CONSUMPTION' THEN -quantity
                    WHEN movement_type = 'RETURN' THEN quantity
                    ELSE 0
                END
            ), 0) as current_stock
            FROM Stock_Movements
            WHERE item_id = ?
            """
            rows = db.execute_query(query, (item_id,))
            return rows[0]['current_stock'] if rows else 0
        except Exception as e:
            logger.error(f"Failed to get current stock level for item {item_id}: {e}")
            return 0
