"""
Stock movement service - handles stock movement operations.
Provides centralized stock tracking and movement recording.
"""

from typing import List, Dict, Optional, Union
from datetime import date
from inventory_app.database.connection import db
from inventory_app.utils.logger import logger
from inventory_app.services.movement_types import MovementType, sql_values_in_clause


class StockMovementService:
    """
    Service for stock movement operations.
    Handles recording consumption, returns, and stock queries.
    """

    def __init__(self):
        """Initialize the stock movement service."""
        logger.info("Stock movement service initialized")

    def record_consumption(
        self,
        item_id: int,
        quantity: int,
        source_id: int,
        note: str,
        batch_id: Optional[int] = None,
    ) -> None:
        """
        Record item consumption (requesting).

        Args:
            item_id: ID of the item
            quantity: Quantity consumed
            source_id: Requisition ID
            note: Description/note for the movement
            batch_id: Specific batch being consumed (optional)
        """
        self._record_movement(
            item_id, MovementType.CONSUMPTION, quantity, source_id, note, batch_id
        )

    def record_reservation(
        self,
        item_id: int,
        quantity: int,
        source_id: int,
        note: str,
        batch_id: Optional[int] = None,
    ) -> None:
        """
        Record item reservation (temporary hold for active requisitions).

        Args:
            item_id: ID of the item
            quantity: Quantity reserved
            source_id: Requisition ID
            note: Description/note for the movement
            batch_id: Specific batch being reserved (optional)
        """
        self._record_movement(
            item_id, MovementType.RESERVATION, quantity, source_id, note, batch_id
        )

    def record_return(
        self,
        item_id: int,
        quantity: int,
        source_id: int,
        note: str,
        batch_id: Optional[int] = None,
    ) -> None:
        """
        Record item return.

        Args:
            item_id: ID of the item
            quantity: Quantity returned
            source_id: Requisition ID
            note: Description/note for the movement
            batch_id: Specific batch being returned (optional)
        """
        self._record_movement(
            item_id, MovementType.RETURN, quantity, source_id, note, batch_id
        )

    def record_disposal(
        self,
        item_id: int,
        quantity: int,
        source_id: int,
        note: str,
        batch_id: Optional[int] = None,
    ) -> None:
        """
        Record item disposal (lost or damaged non-consumable items).

        Args:
            item_id: ID of the item
            quantity: Quantity disposed
            source_id: Requisition ID
            note: Description/note for the movement
            batch_id: Specific batch being disposed (optional)
        """
        self._record_movement(
            item_id, MovementType.DISPOSAL, quantity, source_id, note, batch_id
        )

    def process_return(
        self, requisition_id: int, return_data: List[Dict], editor_name: str
    ) -> bool:
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
            # Run returns in a transaction so that all movements are created
            # atomically and we can rollback on error.
            from inventory_app.database.connection import db as global_db

            def _process():
                for return_item in return_data:
                    note = f"Items returned by {editor_name}"
                    self.record_return(
                        return_item["item_id"],
                        return_item["quantity_returned"],
                        requisition_id,
                        note,
                    )
                return True

            if global_db.in_transaction():
                return _process()

            with global_db.transaction(immediate=True):
                return _process()

        except Exception as e:
            logger.error(
                f"Failed to process return for requisition {requisition_id}: {e}"
            )
            return False

    def _record_movement(
        self,
        item_id: int,
        movement_type: Union[MovementType, str],
        quantity: int,
        source_id: int,
        note: str,
        batch_id: Optional[int] = None,
    ) -> None:
        """
        Record a stock movement in the database.

        Args:
            item_id: ID of the item
            movement_type: Type of movement ('CONSUMPTION', 'RETURN', etc.)
            quantity: Quantity moved
            source_id: Source identifier (requisition ID)
            note: Descriptive note
            batch_id: Specific batch ID (optional)
        """
        # Accept MovementType enum or raw string; normalize to string value
        mv = (
            movement_type.value
            if isinstance(movement_type, MovementType)
            else str(movement_type)
        )

        if batch_id is not None:
            query = """
            INSERT INTO Stock_Movements (item_id, batch_id, movement_type, quantity, movement_date, source_id, note)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                item_id,
                batch_id,
                mv,
                quantity,
                date.today().isoformat(),
                source_id,
                note,
            )
        else:
            query = """
            INSERT INTO Stock_Movements (item_id, movement_type, quantity, movement_date, source_id, note)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            params = (
                item_id,
                mv,
                quantity,
                date.today().isoformat(),
                source_id,
                note,
            )

        db.execute_update(query, params)
        batch_info = f" (batch {batch_id})" if batch_id else ""
        logger.debug(
            f"Recorded {mv} movement for item {item_id}{batch_info}: {quantity} units"
        )

    def get_current_stock_level(self, item_id: int) -> int:
        """
        Calculate current stock level for an item based on movements.
        RESERVATION: Temporary hold (reduces available stock)
        CONSUMPTION/DISPOSAL: Permanent reduction (reduces total stock)

        Args:
            item_id: ID of the item

        Returns:
            Current stock level
        """
        try:
            # Get total stock from batches first
            batch_query = """
            SELECT COALESCE(SUM(quantity_received), 0) as total_received
            FROM Item_Batches
            WHERE item_id = ?
            """
            batch_rows = db.execute_query(batch_query, (item_id,))
            total_received = batch_rows[0]["total_received"] if batch_rows else 0

            # Get net movement adjustments
            movement_query = """
            SELECT COALESCE(SUM(
                CASE
                    WHEN movement_type = ? THEN -quantity
                    WHEN movement_type = ? THEN -quantity
                    WHEN movement_type = ? THEN quantity

                    ELSE 0
                END
            ), 0) as net_adjustment
            FROM Stock_Movements
            WHERE item_id = ?
            """
            params = (
                MovementType.CONSUMPTION.value,
                MovementType.DISPOSAL.value,
                MovementType.RETURN.value,
                item_id,
            )
            movement_rows = db.execute_query(movement_query, params)
            net_adjustment = movement_rows[0]["net_adjustment"] if movement_rows else 0

            return max(0, total_received + net_adjustment)
        except Exception as e:
            logger.error(f"Failed to get current stock level for item {item_id}: {e}")
            return 0

    def get_reserved_stock(self, item_id: int) -> int:
        """
        Get total reserved stock for an item (temporary holds).

        Args:
            item_id: ID of the item

        Returns:
            Total reserved quantity
        """
        try:
            query = """
            SELECT COALESCE(SUM(quantity), 0) as reserved_qty
            FROM Stock_Movements
            WHERE item_id = ? AND movement_type IN %s
            """ % sql_values_in_clause()
            rows = db.execute_query(query, (item_id,))
            return rows[0]["reserved_qty"] if rows else 0
        except Exception as e:
            logger.error(f"Failed to get reserved stock for item {item_id}: {e}")
            return 0

    def delete_movements_for_requisition(self, requisition_id: int) -> bool:
        """
        Delete all stock movements associated with a specific requisition.
        Used when editing requisitions to remove old movements before creating new ones.

        Args:
            requisition_id: ID of the requisition

        Returns:
            True if movements were successfully deleted
        """
        query = """
        DELETE FROM Stock_Movements
        WHERE source_id = ?
        """
        db.execute_update(query, (requisition_id,))
        logger.info(f"Deleted stock movements for requisition {requisition_id}")
        return True
