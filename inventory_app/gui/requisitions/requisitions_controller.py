"""
Requisitions controller - handles business logic for requisition management.
Provides CRUD operations for requisitions, requesters, and requisition items.
Uses composition pattern with DatabaseConnection.
"""

from typing import List, Dict, Optional
from datetime import date
from dataclasses import dataclass
import time

from inventory_app.database.connection import db
from inventory_app.database.models import Requester, Requisition
from inventory_app.services import ItemService
from inventory_app.utils.logger import logger


@dataclass
class RequisitionSummary:
    """Summary data for a requisition including requester and items."""
    requisition: Requisition
    requester: Requester
    items: List[Dict]  # List of item details with quantities
    total_items: int
    status: str  # 'Active', 'Returned', 'Overdue'

class RequisitionsController:
    """
    Controller for requisition management operations.
    Handles business logic for requesting workflow.
    """

    def __init__(self):
        """Initialize controller with composed services."""
        # Compose with services using composition pattern
        self.item_service = ItemService()

        logger.info("Requisitions controller initialized with services")

    def get_all_requisitions(self) -> List[RequisitionSummary]:
        """
        Get all requisitions with requester and item details.

        Returns:
            List of requisition summaries
        """
        try:
            # Get all requisitions
            requisitions = Requisition.get_all()
            summaries = []

            for req in requisitions:
                if not req.id:
                    continue

                # Get requester details
                requester = Requester.get_by_id(req.requester_id)
                if not requester:
                    logger.warning(f"Requester {req.requester_id} not found for requisition {req.id}")
                    continue

                # Get requisition items with details using ItemService
                items = self.item_service.get_requisition_items_with_details(req.id)

                # Get status directly from database (real-time monitor updates this)
                status = req.status if req.status else "Active"

                summary = RequisitionSummary(
                    requisition=req,
                    requester=requester,
                    items=items,
                    total_items=sum(item['quantity_requested'] for item in items),
                    status=status
                )
                summaries.append(summary)

            logger.info(f"Retrieved {len(summaries)} requisitions")
            return summaries

        except Exception as e:
            logger.error(f"Failed to get requisitions: {e}")
            return []

    def delete_requisition(self, requisition_id: int, editor_name: str) -> bool:
        """
        Delete a requisition and all its dependent records in proper order.

        Args:
            requisition_id: ID of requisition to delete
            editor_name: Name of person deleting

        Returns:
            bool: True if successful
        """
        try:
            # Step 1: Delete requisition history records first (simple DELETE)
            self._delete_requisition_history(requisition_id)
            time.sleep(0.1)

            # Step 2: Delete requisition items (removes FK references to requisition)
            db.execute_update("DELETE FROM Requisition_Items WHERE requisition_id = ?", (requisition_id,))
            time.sleep(0.1)

            # Step 3: Delete ALL stock movements for this requisition
            db.execute_update("DELETE FROM Stock_Movements WHERE source_id = ?", (requisition_id,))
            time.sleep(0.1)

            # Step 4: Finally delete the requisition itself
            success = db.execute_update("DELETE FROM Requisitions WHERE id = ?", (requisition_id,))

            if success:
                logger.info(f"Successfully deleted requisition {requisition_id} and all dependencies")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to delete requisition {requisition_id}: {e}")
            return False

    def get_requesters(self) -> List[Requester]:
        """
        Get all requesters.

        Returns:
            List of requesters
        """
        try:
            return Requester.get_all()
        except Exception as e:
            logger.error(f"Failed to get requesters: {e}")
            return []

    def get_requesters_with_requisitions(self) -> List[Requester]:
        """
        Get only requesters that have created requisitions.

        Returns:
            List of requesters who have active requisitions
        """
        try:
            query = """
            SELECT DISTINCT b.* FROM Requesters b
            JOIN Requisitions r ON b.id = r.requester_id
            ORDER BY b.name
            """
            rows = db.execute_query(query)
            requesters = []
            for row in rows:
                requesters.append(Requester(**dict(row)))
            logger.info(f"Retrieved {len(requesters)} requesters with requisitions")
            return requesters
        except Exception as e:
            logger.error(f"Failed to get requesters with requisitions: {e}")
            return []

    def _get_requisition_by_id(self, requisition_id: int) -> Optional[Requisition]:
        """Get a single requisition by ID."""
        try:
            query = "SELECT * FROM Requisitions WHERE id = ?"
            rows = db.execute_query(query, (requisition_id,))
            if not rows:
                return None

            req_dict = dict(rows[0])
            # Convert dates
            if req_dict.get('date_requested'):
                req_dict['date_requested'] = date.fromisoformat(req_dict['date_requested'])
            if req_dict.get('lab_activity_date'):
                req_dict['lab_activity_date'] = date.fromisoformat(req_dict['lab_activity_date'])

            return Requisition(**req_dict)
        except Exception as e:
            logger.error(f"Failed to get requisition {requisition_id}: {e}")
            return None

    def _delete_requisition_history(self, requisition_id: int) -> None:
        """Delete all history records for a requisition."""
        try:
            query = "DELETE FROM Requisition_History WHERE requisition_id = ?"
            db.execute_update(query, (requisition_id,))
            logger.debug(f"Deleted history records for requisition {requisition_id}")
        except Exception as e:
            logger.error(f"Failed to delete requisition history for {requisition_id}: {e}")

    def _clear_requisition_items(self, requisition_id: int) -> None:
        """Remove all items from a requisition."""
        try:
            db.execute_update("DELETE FROM Requisition_Items WHERE requisition_id = ?", (requisition_id,))
        except Exception as e:
            logger.error(f"Failed to clear requisition items: {e}")
