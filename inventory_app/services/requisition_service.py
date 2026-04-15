"""
Requisition Service - Core business logic for requisition management.

This service centralizes requisition operations that were previously
handled in the GUI layer, providing a clean API for backend operations
and testing.
"""

from typing import List, Dict, Optional
from datetime import date, datetime
from inventory_app.database.connection import db
from inventory_app.database.models import Requisition, RequisitionItem
from inventory_app.services.stock_movement_service import StockMovementService
from inventory_app.services.movement_types import MovementType
from inventory_app.services.requisition_activity import requisition_activity_manager
from inventory_app.utils.logger import logger


class RequisitionService:
    """
    Service for managing requisition lifecycle and related stock movements.
    """

    def __init__(self):
        self.stock_service = StockMovementService()

    def create_requisition(
        self,
        requester_id: int,
        items: List[Dict],
        expected_request: datetime,
        expected_return: datetime,
        lab_activity_name: str,
        lab_activity_description: str = "",
        lab_activity_date: Optional[date] = None,
        num_students: Optional[int] = None,
        num_groups: Optional[int] = None,
        user_name: str = "System",
    ) -> Optional[int]:
        """
        Create a new requisition with items and initial stock movements.

        Args:
            requester_id: ID of the requester
            items: List of dicts with 'item_id', 'batch_id', and 'quantity'
            expected_request: Expected date/time of request
            expected_return: Expected date/time of return
            lab_activity_name: Name of the lab activity
            lab_activity_description: Description of the activity
            lab_activity_date: Date of the activity
            num_students: Number of students
            num_groups: Number of groups
            user_name: User performing the action

        Returns:
            int: ID of the created requisition, or None if failed
        """
        try:
            with db.transaction(immediate=True):
                # Create main requisition
                requisition = Requisition()
                requisition.requester_id = requester_id
                requisition.expected_request = expected_request
                requisition.expected_return = expected_return
                requisition.status = "requested"
                requisition.lab_activity_name = lab_activity_name
                requisition.lab_activity_description = lab_activity_description
                requisition.lab_activity_date = lab_activity_date or date.today()
                requisition.num_students = num_students
                requisition.num_groups = num_groups

                if not requisition.save(user_name):
                    raise Exception("Failed to save requisition model")

                requisition_id = requisition.id
                if requisition_id is None:
                    raise Exception("Failed to retrieve requisition ID after save")

                # Create items and movements
                for item in items:
                    # Save requisition item record
                    req_item = RequisitionItem()
                    req_item.requisition_id = requisition_id
                    req_item.item_id = item["item_id"]
                    req_item.quantity_requested = item["quantity"]
                    if not req_item.save():
                        raise Exception(
                            f"Failed to save RequisitionItem for item {item['item_id']}"
                        )

                    # Determine movement type based on item consumability
                    item_query = "SELECT is_consumable FROM Items WHERE id = ?"
                    item_result = db.execute_query(item_query, (item["item_id"],))
                    is_consumable = (
                        item_result[0]["is_consumable"] if item_result else 1
                    )
                    movement_type = (
                        MovementType.RESERVATION
                        if is_consumable
                        else MovementType.REQUEST
                    )

                    # Record movement
                    self._record_initial_movement(
                        item["item_id"],
                        item["batch_id"],
                        movement_type,
                        item["quantity"],
                        requisition_id,
                    )

                # Log activity
                from inventory_app.database.models import Requester

                requester = Requester.get_by_id(requester_id)
                requester_name = requester.name if requester else "Unknown"
                requisition_activity_manager.log_requisition_created(
                    requisition_id, requester_name, user_name
                )

                return requisition_id
        except Exception as e:
            logger.error(f"RequisitionService: Failed to create requisition: {e}")
            return None

    def update_status(
        self,
        requisition_id: int,
        new_status: str,
        user_name: str = "System",
        reason: Optional[str] = None,
    ) -> bool:
        """
        Update the status of a requisition.

        Args:
            requisition_id: ID of the requisition
            new_status: New status (requested, active, overdue, returned)
            user_name: User performing the action
            reason: Optional reason text for audit history

        Returns:
            bool: True if successful
        """
        try:
            if db.in_transaction():
                return self._update_status_logic(
                    requisition_id,
                    new_status,
                    user_name,
                    reason,
                )
            else:
                with db.transaction():
                    return self._update_status_logic(
                        requisition_id,
                        new_status,
                        user_name,
                        reason,
                    )
        except Exception as e:
            logger.error(f"RequisitionService: Failed to update status: {e}")
            return False

    def _update_status_logic(
        self,
        requisition_id: int,
        new_status: str,
        user_name: str = "System",
        reason: Optional[str] = None,
    ) -> bool:
        """Internal logic for status update without transaction wrapper."""
        current_rows = db.execute_query(
            "SELECT status FROM Requisitions WHERE id = ?",
            (requisition_id,),
            use_cache=False,
        )
        if not current_rows:
            logger.warning(
                f"RequisitionService: requisition {requisition_id} not found for status update"
            )
            return False

        previous_status = (current_rows[0].get("status") or "").strip()
        if previous_status == new_status:
            return True

        query = "UPDATE Requisitions SET status = ? WHERE id = ?"
        db.execute_update(query, (new_status, requisition_id))

        # Log to history
        history_query = """
        INSERT INTO Requisition_History (requisition_id, editor_name, reason)
        VALUES (?, ?, ?)
        """
        history_reason = reason or (
            f"Status transition: {previous_status or 'unknown'} -> {new_status}"
        )
        db.execute_update(history_query, (requisition_id, user_name, history_reason))
        return True

    def process_return(
        self, requisition_id: int, return_items: List[Dict], user_name: str = "System"
    ) -> bool:
        """
        Process the final return of a requisition.

        Args:
            requisition_id: ID of the requisition
            return_items: List of dicts with:
                'item_id', 'batch_id', 'quantity_requested', 'quantity_returned' (consumables),
                'quantity_lost' (non-consumables), 'is_consumable'
            user_name: User performing the action

        Returns:
            bool: True if successful
        """
        try:
            with db.transaction(immediate=True):
                for item in return_items:
                    item_id = item["item_id"]
                    batch_id = item.get("batch_id")
                    qty_requested = item["quantity_requested"]
                    is_consumable = item["is_consumable"]

                    if is_consumable:
                        # Remove reservation
                        self._remove_movement(
                            requisition_id, item_id, batch_id, MovementType.RESERVATION
                        )

                        # Record consumption if any
                        qty_returned = item.get("quantity_returned", qty_requested)
                        consumed = qty_requested - qty_returned
                        if consumed > 0:
                            self.stock_service.record_consumption(
                                item_id,
                                consumed,
                                requisition_id,
                                f"Consumed during requisition {requisition_id}",
                                batch_id,
                            )
                    else:
                        # Remove request
                        self._remove_movement(
                            requisition_id, item_id, batch_id, MovementType.REQUEST
                        )

                        # Record disposal for lost items
                        qty_lost = item.get("quantity_lost", 0)
                        if qty_lost > 0:
                            self.stock_service.record_disposal(
                                item_id,
                                qty_lost,
                                requisition_id,
                                f"Lost during requisition {requisition_id}",
                                batch_id,
                            )

                # Final status update
                if not self.update_status(requisition_id, "returned", user_name):
                    raise Exception("Failed to update status to returned")
                requisition_activity_manager.log_requisition_returned(
                    requisition_id, user_name
                )

            return True
        except Exception as e:
            logger.error(f"RequisitionService: Failed to process return: {e}")
            return False

    def _record_initial_movement(
        self,
        item_id: int,
        batch_id: int,
        m_type: MovementType,
        qty: int,
        source_id: int,
    ):
        """Internal helper to record initial movements."""
        query = """
        INSERT INTO Stock_Movements (item_id, batch_id, movement_type, quantity, movement_date, source_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        db.execute_update(
            query,
            (item_id, batch_id, m_type.value, qty, date.today().isoformat(), source_id),
        )

    def _remove_movement(
        self,
        requisition_id: int,
        item_id: int,
        batch_id: Optional[int],
        m_type: MovementType,
    ):
        """Internal helper to remove movements."""
        if batch_id is not None:
            query = """
            DELETE FROM Stock_Movements
            WHERE item_id = ? AND batch_id = ? AND source_id = ? AND movement_type = ?
            """
            params = (item_id, batch_id, requisition_id, m_type.value)
        else:
            query = """
            DELETE FROM Stock_Movements
            WHERE item_id = ? AND source_id = ? AND movement_type = ?
            """
            params = (item_id, requisition_id, m_type.value)
        db.execute_update(query, params)
