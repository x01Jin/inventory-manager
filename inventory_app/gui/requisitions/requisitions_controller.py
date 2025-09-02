"""
Requisitions controller - handles business logic for requisition management.
Provides CRUD operations for requisitions, borrowers, and requisition items.
Uses composition pattern with DatabaseConnection.
"""

from typing import List, Dict, Optional
from datetime import date
from dataclasses import dataclass
import time

from inventory_app.database.connection import db
from inventory_app.database.models import Borrower, Requisition
from inventory_app.services import ItemService
from inventory_app.utils.logger import logger


@dataclass
class RequisitionSummary:
    """Summary data for a requisition including borrower and items."""
    requisition: Requisition
    borrower: Borrower
    items: List[Dict]  # List of item details with quantities
    total_items: int
    status: str  # 'Active', 'Returned', 'Overdue'

class RequisitionsController:
    """
    Controller for requisition management operations.
    Handles business logic for borrowing workflow.
    """

    def __init__(self):
        """Initialize controller with composed services."""
        # Compose with services using composition pattern
        self.item_service = ItemService()

        logger.info("Requisitions controller initialized with services")

    def get_all_requisitions(self) -> List[RequisitionSummary]:
        """
        Get all requisitions with borrower and item details.

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

                # Get borrower details
                borrower = Borrower.get_by_id(req.borrower_id)
                if not borrower:
                    logger.warning(f"Borrower {req.borrower_id} not found for requisition {req.id}")
                    continue

                # Get requisition items with details using ItemService
                items = self.item_service.get_requisition_items_with_details(req.id)

                # Determine status
                status = self._determine_requisition_status(req, items)

                summary = RequisitionSummary(
                    requisition=req,
                    borrower=borrower,
                    items=items,
                    total_items=sum(item['quantity_borrowed'] for item in items),
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

    def get_borrowers(self) -> List[Borrower]:
        """
        Get all borrowers.

        Returns:
            List of borrowers
        """
        try:
            return Borrower.get_all()
        except Exception as e:
            logger.error(f"Failed to get borrowers: {e}")
            return []

    def get_borrowers_with_requisitions(self) -> List[Borrower]:
        """
        Get only borrowers that have created requisitions.

        Returns:
            List of borrowers who have active requisitions
        """
        try:
            query = """
            SELECT DISTINCT b.* FROM Borrowers b
            JOIN Requisitions r ON b.id = r.borrower_id
            ORDER BY b.name
            """
            rows = db.execute_query(query)
            borrowers = []
            for row in rows:
                borrowers.append(Borrower(**dict(row)))
            logger.info(f"Retrieved {len(borrowers)} borrowers with requisitions")
            return borrowers
        except Exception as e:
            logger.error(f"Failed to get borrowers with requisitions: {e}")
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
            if req_dict.get('date_borrowed'):
                req_dict['date_borrowed'] = date.fromisoformat(req_dict['date_borrowed'])
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

    def _determine_requisition_status(self, requisition: Requisition, items: List[Dict]) -> str:
        """Determine the status of a requisition based on return records."""
        try:
            # Check if requisition ID exists
            if not requisition.id:
                logger.warning("Requisition ID is None, cannot determine status")
                return "Active"

            # Check if all items in the requisition have been returned
            all_returned = True
            current_date = date.today()

            for item in items:
                item_id = item['item_id']
                borrowed_qty = item['quantity_borrowed']

                # Get total returned quantity for this item in this requisition
                returned_qty = self._get_returned_quantity_for_item(item_id, requisition.id)

                if returned_qty < borrowed_qty:
                    all_returned = False
                    break

            if all_returned:
                return "Returned"
            elif requisition.lab_activity_date < current_date:
                # Past due date and not fully returned
                return "Overdue"
            else:
                # Not past due and not fully returned
                return "Active"

        except Exception as e:
            logger.error(f"Failed to determine requisition status: {e}")
            return "Active"  # Default fallback

    def _get_returned_quantity_for_item(self, item_id: int, requisition_id: int) -> int:
        """Get the total quantity returned for a specific item in a requisition."""
        try:
            query = """
            SELECT COALESCE(SUM(quantity), 0) as returned_qty
            FROM Stock_Movements
            WHERE item_id = ? AND source_id = ? AND movement_type = 'RETURN'
            """
            rows = db.execute_query(query, (item_id, requisition_id))
            return rows[0]['returned_qty'] if rows else 0
        except Exception as e:
            logger.error(f"Failed to get returned quantity for item {item_id}: {e}")
            return 0
