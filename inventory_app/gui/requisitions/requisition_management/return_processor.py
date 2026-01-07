"""
Return Processor - Simplified one-time return process for requisitions.

Handles final return processing where all items are processed at once.
No partial returns, no editing after processing.

Per beta test requirements:
- Add info for defective/broken items returned
"""

from typing import List, Optional

from inventory_app.services.stock_movement_service import StockMovementService
from inventory_app.services.movement_types import MovementType
from inventory_app.services.requisition_activity import requisition_activity_manager
from inventory_app.database.connection import db
from inventory_app.utils.logger import logger


class ReturnItem:
    """Simple data structure for one-time return processing.

    Per beta test: Added defective/broken quantity tracking for non-consumables.
    """

    def __init__(
        self,
        item_id: int,
        batch_id: Optional[int],
        quantity_requested: int,
        quantity_returned: int = 0,
        quantity_lost: int = 0,
        quantity_defective: int = 0,  # Beta test: track defective/broken items
        is_consumable: bool = False,
        defective_notes: str = "",  # Beta test: notes about defective items
    ):
        self.item_id = item_id
        self.batch_id = batch_id
        self.quantity_requested = quantity_requested
        self.quantity_returned = quantity_returned  # For consumables only
        self.quantity_lost = quantity_lost  # For non-consumables only
        self.quantity_defective = quantity_defective  # Defective/broken items
        self.is_consumable = is_consumable
        self.defective_notes = defective_notes  # Reason/description for defective

    @property
    def quantity_processed(self) -> int:
        """Total quantity that has been processed."""
        if self.is_consumable:
            return self.quantity_returned
        else:
            return self.quantity_lost

    def is_fully_processed(self) -> bool:
        """Check if all requested quantity has been processed."""
        # For consumables: user has made a decision by setting quantity_returned
        # For non-consumables: user has made a decision by setting quantity_lost
        # Both are initialized to valid defaults (0 for lost, requested for returned)
        # But we consider it processed if the user has explicitly interacted with it
        # Since the UI initializes with valid values, we need to track if user changed anything
        # For now, consider it processed if quantities are within valid ranges
        if self.is_consumable:
            return 0 <= self.quantity_returned <= self.quantity_requested
        else:
            return 0 <= self.quantity_lost <= self.quantity_requested


class ReturnProcessor:
    """
    Simplified processor for one-time return processing.

    Handles final return processing for all items in a requisition.
    Once processed, the requisition is locked and cannot be edited.
    """

    def __init__(self):
        """Initialize the return processor with composed services."""
        self.stock_service = StockMovementService()
        logger.info("Return processor initialized")

    def process_returns(
        self,
        requisition_id: int,
        return_items: List[ReturnItem],
        editor_name: str,
    ) -> bool:
        """
        Process all returns for a requisition in one final operation.

        Args:
            requisition_id: ID of the requisition
            return_items: List of ReturnItem objects with final return/loss information
            editor_name: Name of person processing the returns

        Returns:
            bool: True if processing successful
        """
        try:
            logger.info(f"Processing final returns for requisition {requisition_id}")

            # Validate that all items are fully processed
            if not self._validate_all_processed(return_items):
                return False

            # Run the entire final return processing inside an IMMEDIATE transaction
            # to prevent concurrent modifications while we're updating stock and status.
            from inventory_app.database.connection import db as global_db

            with global_db.transaction(immediate=True):
                # Process each item (one-time final processing)
                returned_items = []
                lost_items = []
                consumed_items = []

                for return_item in return_items:
                    if return_item.is_consumable:
                        self._process_consumable_return(
                            requisition_id, return_item, editor_name
                        )
                        # Track returned and consumed quantities for logging
                        if return_item.quantity_returned > 0:
                            returned_items.append(
                                f"{return_item.quantity_returned}x (ID: {return_item.item_id})"
                            )
                        consumed_quantity = (
                            return_item.quantity_requested
                            - return_item.quantity_returned
                        )
                        if consumed_quantity > 0:
                            consumed_items.append(
                                f"{consumed_quantity}x (ID: {return_item.item_id})"
                            )
                    elif not return_item.is_consumable:
                        self._process_non_consumable_loss(
                            requisition_id, return_item, editor_name
                        )
                        # Track returned and lost quantities for logging
                        returned_quantity = (
                            return_item.quantity_requested - return_item.quantity_lost
                        )
                        if returned_quantity > 0:
                            returned_items.append(
                                f"{returned_quantity}x (ID: {return_item.item_id})"
                            )
                        if return_item.quantity_lost > 0:
                            lost_items.append(
                                f"{return_item.quantity_lost}x (ID: {return_item.item_id})"
                            )

                        # Record defective items (per beta test B.2)
                        if return_item.quantity_defective > 0:
                            self._record_defective_item(
                                requisition_id,
                                return_item.item_id,
                                return_item.quantity_defective,
                                return_item.defective_notes,
                                editor_name,
                            )

                # Update requisition status to final "returned"
                self._update_requisition_status_final(requisition_id)

                # Log final activity
                success = requisition_activity_manager.log_requisition_returned(
                    requisition_id=requisition_id, user_name=editor_name
                )

                if success:
                    logger.info(
                        f"Logged final return activity for requisition {requisition_id}"
                    )
                else:
                    logger.warning(
                        f"Failed to log final return activity for requisition {requisition_id}"
                    )

            logger.info(
                f"Successfully processed final returns for requisition {requisition_id}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to process returns for requisition {requisition_id}: {e}"
            )
            return False

    def _validate_all_processed(self, return_items: List[ReturnItem]) -> bool:
        """
        Validate that all items are fully processed (no partial processing allowed).

        Args:
            return_items: List of ReturnItem to validate

        Returns:
            bool: True if all items are fully processed
        """
        for item in return_items:
            if item.quantity_returned < 0 or item.quantity_lost < 0:
                logger.error(f"Negative quantities not allowed for item {item.item_id}")
                return False

            if not item.is_fully_processed():
                logger.error(
                    f"Item {item.item_id} is not fully processed. "
                    f"Requested: {item.quantity_requested}, Processed: {item.quantity_processed}"
                )
                return False

        return True

    def _process_consumable_return(
        self, requisition_id: int, return_item: ReturnItem, editor_name: str
    ) -> None:
        """Process consumable item return - replace RESERVATION with final movements."""
        # Phase 2: Replace the initial RESERVATION movement with final movements

        # Remove the original RESERVATION movement first to avoid trigger conflicts
        # (the DB trigger prevents adding a CONSUMPTION if a RESERVATION is still present
        # and would cause the sum to exceed the batch's quantity). Deleting first is
        # safe because the entire operation is performed inside a single transaction
        # so failures will rollback both operations.
        self._remove_reservation_movement(
            requisition_id, return_item.item_id, return_item.batch_id
        )

        # Record CONSUMPTION movement for consumed quantity (requested - returned)
        consumed_quantity = (
            return_item.quantity_requested - return_item.quantity_returned
        )
        if consumed_quantity > 0:
            consumption_note = f"Consumable consumed by {editor_name} (used quantity)"
            self.stock_service.record_consumption(
                return_item.item_id,
                consumed_quantity,
                requisition_id,
                consumption_note,
                return_item.batch_id,
            )

    def _remove_reservation_movement(
        self, requisition_id: int, item_id: int, batch_id: Optional[int]
    ) -> None:
        """Remove the original RESERVATION movement to prevent double-counting in stock calculations."""
        if batch_id is not None:
            query = """
            DELETE FROM Stock_Movements
            WHERE item_id = ? AND batch_id = ? AND source_id = ? AND movement_type = ?
            """
            params = (item_id, batch_id, requisition_id, MovementType.RESERVATION.value)
        else:
            query = """
            DELETE FROM Stock_Movements
            WHERE item_id = ? AND source_id = ? AND movement_type = ?
            """
            params = (item_id, requisition_id, MovementType.RESERVATION.value)

        db.execute_update(query, params)
        logger.debug(
            f"Removed RESERVATION movement for item {item_id} in requisition {requisition_id}"
        )

    def _remove_request_movement(
        self, requisition_id: int, item_id: int, batch_id: Optional[int]
    ) -> None:
        """Remove the original REQUEST movement to prevent double-counting in stock calculations."""
        if batch_id is not None:
            query = """
            DELETE FROM Stock_Movements
            WHERE item_id = ? AND batch_id = ? AND source_id = ? AND movement_type = ?
            """
            params = (item_id, batch_id, requisition_id, MovementType.REQUEST.value)
        else:
            query = """
            DELETE FROM Stock_Movements
            WHERE item_id = ? AND source_id = ? AND movement_type = ?
            """
            params = (item_id, requisition_id, MovementType.REQUEST.value)

        db.execute_update(query, params)
        logger.debug(
            f"Removed REQUEST movement for item {item_id} in requisition {requisition_id}"
        )

    def _process_non_consumable_loss(
        self, requisition_id: int, return_item: ReturnItem, editor_name: str
    ) -> None:
        """Process non-consumable item loss - record disposed quantities."""
        # Remove the original REQUEST movement first to avoid trigger conflicts and
        # then record the DISPOSAL. As above, this is safe inside the surrounding
        # transaction which will rollback on failure.
        self._remove_request_movement(
            requisition_id, return_item.item_id, return_item.batch_id
        )

        # Record DISPOSAL movement for lost quantity
        if return_item.quantity_lost > 0:
            disposal_note = f"Non-consumable marked as lost by {editor_name}"
            self.stock_service.record_disposal(
                return_item.item_id,
                return_item.quantity_lost,
                requisition_id,
                disposal_note,
                return_item.batch_id,
            )

    def _update_requisition_status_final(self, requisition_id: int) -> None:
        """Update requisition status to final 'returned' state."""
        try:
            query = "UPDATE Requisitions SET status = ? WHERE id = ?"
            db.execute_update(query, ("returned", requisition_id))
            logger.info(
                f"Updated requisition {requisition_id} status to final 'returned'"
            )
        except Exception as e:
            logger.error(f"Failed to update requisition {requisition_id} status: {e}")

    def _record_defective_item(
        self,
        requisition_id: int,
        item_id: int,
        quantity: int,
        notes: str,
        reported_by: str,
    ) -> None:
        """
        Record defective/broken items in the Defective_Items table.

        Per beta test requirement B.2: Add info for defective/broken items returned.

        Args:
            requisition_id: ID of the requisition
            item_id: ID of the item
            quantity: Number of defective items
            notes: Description of the defect
            reported_by: Name of person reporting
        """
        try:
            query = """
            INSERT INTO Defective_Items (item_id, requisition_id, quantity, notes, reported_by)
            VALUES (?, ?, ?, ?, ?)
            """
            db.execute_update(
                query,
                (
                    item_id,
                    requisition_id,
                    quantity,
                    notes or "",
                    reported_by,
                ),
            )
            logger.info(
                f"Recorded {quantity} defective items (ID: {item_id}) "
                f"for requisition {requisition_id}"
            )
        except Exception as e:
            logger.error(
                f"Failed to record defective item {item_id} for requisition {requisition_id}: {e}"
            )
            # Don't raise - defective recording failure shouldn't block return processing

    def get_requisition_items_for_return(self, requisition_id: int) -> List[ReturnItem]:
        """
        Get items for a requisition that need return processing.
        Only returns items that haven't been processed yet.

        Args:
            requisition_id: ID of the requisition

        Returns:
            List of ReturnItem objects for return processing
        """
        try:
            # Get all requisition items with consumable info
            query = """
            SELECT ri.item_id, ri.quantity_requested, ib.id as batch_id, i.is_consumable
            FROM Requisition_Items ri
            LEFT JOIN Item_Batches ib ON ri.item_id = ib.item_id
            JOIN Items i ON ri.item_id = i.id
            WHERE ri.requisition_id = ?
            """
            rows = db.execute_query(query, (requisition_id,))

            return_items = []
            for row in rows:
                return_item = ReturnItem(
                    item_id=row["item_id"],
                    batch_id=row["batch_id"],
                    quantity_requested=row["quantity_requested"],
                    quantity_returned=0,
                    quantity_lost=0,
                    is_consumable=bool(row["is_consumable"]),
                )
                return_items.append(return_item)

            return return_items

        except Exception as e:
            logger.error(
                f"Failed to get return items for requisition {requisition_id}: {e}"
            )
            return []

    def is_requisition_processed(self, requisition_id: int) -> bool:
        """
        Check if a requisition has been fully processed (final return state).

        Args:
            requisition_id: ID of the requisition

        Returns:
            bool: True if fully processed and locked
        """
        try:
            query = "SELECT status FROM Requisitions WHERE id = ?"
            rows = db.execute_query(query, (requisition_id,))
            if rows:
                return rows[0]["status"] == "returned"
            return False
        except Exception as e:
            logger.error(
                f"Failed to check if requisition {requisition_id} is processed: {e}"
            )
            return False

    def get_requisition_return_summary(self, requisition_id: int) -> dict:
        """
        Get summary of final return processing for a requisition.
        Calculates returned quantities based on original requested amounts minus consumed/lost amounts.

        Args:
            requisition_id: ID of the requisition

        Returns:
            Dictionary with return summary data
        """
        try:
            # Get original requisition items with requested quantities
            requisition_items_query = """
            SELECT ri.item_id, ri.quantity_requested, i.is_consumable, i.name as item_name
            FROM Requisition_Items ri
            JOIN Items i ON ri.item_id = i.id
            WHERE ri.requisition_id = ?
            """
            requisition_rows = db.execute_query(
                requisition_items_query, (requisition_id,)
            )

            # Get all stock movements for this requisition (CONSUMPTION and DISPOSAL only)
            movements_query = """
            SELECT sm.item_id, sm.movement_type, sm.quantity
            FROM Stock_Movements sm
            WHERE sm.source_id = ? AND sm.movement_type IN (?, ?)
            """
            movement_rows = db.execute_query(
                movements_query,
                (
                    requisition_id,
                    MovementType.CONSUMPTION.value,
                    MovementType.DISPOSAL.value,
                ),
            )

            # Create lookup for movements by item_id and type
            movements_lookup = {}
            for row in movement_rows:
                item_id = row["item_id"]
                movement_type = row["movement_type"]
                quantity = row["quantity"]

                if item_id not in movements_lookup:
                    movements_lookup[item_id] = {"CONSUMPTION": 0, "DISPOSAL": 0}

                movements_lookup[item_id][movement_type] = quantity

            summary = {
                "returned_consumables": [],
                "consumed_items": [],
                "returned_non_consumables": [],
                "lost_non_consumables": [],
                "total_returned": 0,
                "total_consumed": 0,
                "total_lost": 0,
            }

            # Process each original requisition item
            for row in requisition_rows:
                item_id = row["item_id"]
                item_name = row["item_name"]
                quantity_requested = row["quantity_requested"]
                is_consumable = bool(row["is_consumable"])

                # Get movements for this item (default to 0 if no movement recorded)
                item_movements = movements_lookup.get(
                    item_id, {"CONSUMPTION": 0, "DISPOSAL": 0}
                )

                if is_consumable:
                    # For consumables: consumed = CONSUMPTION quantity, returned = requested - consumed
                    consumed_quantity = item_movements["CONSUMPTION"]
                    returned_quantity = quantity_requested - consumed_quantity

                    if consumed_quantity > 0:
                        summary["consumed_items"].append(
                            {"item_name": item_name, "quantity": consumed_quantity}
                        )
                        summary["total_consumed"] += consumed_quantity

                    if returned_quantity > 0:
                        summary["returned_consumables"].append(
                            {"item_name": item_name, "quantity": returned_quantity}
                        )
                        summary["total_returned"] += returned_quantity

                else:
                    # For non-consumables: lost = DISPOSAL quantity, returned = requested - lost
                    lost_quantity = item_movements["DISPOSAL"]
                    returned_quantity = quantity_requested - lost_quantity

                    if lost_quantity > 0:
                        summary["lost_non_consumables"].append(
                            {"item_name": item_name, "quantity": lost_quantity}
                        )
                        summary["total_lost"] += lost_quantity

                    if returned_quantity > 0:
                        summary["returned_non_consumables"].append(
                            {"item_name": item_name, "quantity": returned_quantity}
                        )
                        summary["total_returned"] += returned_quantity

            return summary

        except Exception as e:
            logger.error(
                f"Failed to get return summary for requisition {requisition_id}: {e}"
            )
            return {}

    def get_requisition_defective_items(self, requisition_id: int) -> list:
        """
        Get all defective items recorded for a requisition.

        Args:
            requisition_id: ID of the requisition

        Returns:
            List of defective items with details (item name, quantity, notes, reported by)
        """
        try:
            query = """
            SELECT
                i.name AS item_name,
                di.quantity,
                di.notes,
                di.reported_by,
                di.reported_date,
                c.name AS category
            FROM Defective_Items di
            JOIN Items i ON i.id = di.item_id
            JOIN Categories c ON c.id = i.category_id
            WHERE di.requisition_id = ?
            ORDER BY di.reported_date DESC, i.name
            """
            return db.execute_query(query, (requisition_id,)) or []

        except Exception as e:
            logger.error(
                f"Failed to get defective items for requisition {requisition_id}: {e}"
            )
            return []


# Global instance for easy access
return_processor = ReturnProcessor()
