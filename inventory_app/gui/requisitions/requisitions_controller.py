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
from inventory_app.database.models import Borrower, Requisition, RequisitionItem, Item, Category, Supplier
from inventory_app.services import ItemService, StockMovementService, ValidationService
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
        self.stock_service = StockMovementService()
        self.validation_service = ValidationService()

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

    def create_requisition(self, borrower_id: int, requisition_data: Dict,
                          items_data: List[Dict], editor_name: str) -> bool:
        """
        Create a new requisition with existing borrower.

        Args:
            borrower_id: ID of existing borrower (selected via BorrowerSelector)
            requisition_data: Dict with requisition details
            items_data: List of dicts with item_id and quantity_borrowed
            editor_name: Name of person creating the requisition

        Returns:
            bool: True if successful
        """
        try:
            # Validate required fields using ValidationService
            if not self.validation_service.validate_requisition_creation(borrower_id, requisition_data, items_data):
                return False

            # Verify borrower exists
            borrower = Borrower.get_by_id(borrower_id)
            if not borrower:
                logger.error(f"Borrower {borrower_id} not found")
                return False

            # Step 1: Create requisition
            requisition = Requisition(
                borrower_id=borrower_id,
                date_borrowed=requisition_data['date_borrowed'],
                lab_activity_name=requisition_data['lab_activity_name'],
                lab_activity_date=requisition_data['lab_activity_date'],
                num_students=requisition_data.get('num_students'),
                num_groups=requisition_data.get('num_groups')
            )

            if not requisition.save(editor_name):
                logger.error("Failed to save requisition")
                return False
            time.sleep(0.5)  # Allow requisition save to complete

            # Step 2: Add items to requisition and update stock
            for item_data in items_data:
                if not requisition.id:
                    logger.error("Requisition ID is None after save")
                    return False

                req_item = RequisitionItem(
                    requisition_id=requisition.id,
                    item_id=item_data['item_id'],
                    quantity_borrowed=item_data['quantity_borrowed']
                )

                if not req_item.save():
                    logger.error(f"Failed to save requisition item: {item_data}")
                    return False
                time.sleep(0.5)  # Allow requisition item save to complete

                # Step 3: Record stock movement (consumption) using StockMovementService
                self.stock_service.record_consumption(
                    item_data['item_id'],
                    item_data['quantity_borrowed'],
                    requisition.id,
                    f"Borrowed for activity: {requisition.lab_activity_name}"
                )
                time.sleep(0.5)  # Allow stock movement to complete

            logger.info(f"Created requisition {requisition.id} for borrower {borrower.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to create requisition: {e}")
            return False

    def create_requisition_with_existing_borrower(self, requisition_data: Dict,
                                                items_data: List[Dict], editor_name: str) -> bool:
        """
        Create a new requisition with an existing borrower.

        Args:
            requisition_data: Dict with requisition details (must include borrower_id)
            items_data: List of dicts with item_id and quantity_borrowed
            editor_name: Name of person creating the requisition

        Returns:
            bool: True if successful
        """
        try:
            # Validate required fields using ValidationService
            borrower_id = requisition_data.get('borrower_id')
            if not borrower_id:
                logger.error("Borrower ID is required for existing borrower requisition")
                return False

            if not self.validation_service.validate_requisition_creation(borrower_id, requisition_data, items_data):
                return False

            # Verify borrower exists
            borrower = Borrower.get_by_id(borrower_id)
            if not borrower:
                logger.error(f"Borrower {borrower_id} not found")
                return False

            # Create requisition
            requisition = Requisition(
                borrower_id=borrower_id,
                date_borrowed=requisition_data['date_borrowed'],
                lab_activity_name=requisition_data['lab_activity_name'],
                lab_activity_date=requisition_data['lab_activity_date'],
                num_students=requisition_data.get('num_students'),
                num_groups=requisition_data.get('num_groups')
            )

            if not requisition.save(editor_name):
                logger.error("Failed to save requisition")
                return False
            time.sleep(0.5)  # Allow requisition save to complete

            # Add items to requisition and update stock
            for item_data in items_data:
                if not requisition.id:
                    logger.error("Requisition ID is None after save")
                    return False

                req_item = RequisitionItem(
                    requisition_id=requisition.id,
                    item_id=item_data['item_id'],
                    quantity_borrowed=item_data['quantity_borrowed']
                )

                if not req_item.save():
                    logger.error(f"Failed to save requisition item: {item_data}")
                    return False
                time.sleep(0.5)  # Allow requisition item save to complete

                # Record stock movement (consumption) using StockMovementService
                self.stock_service.record_consumption(
                    item_data['item_id'],
                    item_data['quantity_borrowed'],
                    requisition.id,
                    f"Borrowed for activity: {requisition.lab_activity_name}"
                )
                time.sleep(0.5)  # Allow stock movement to complete

            logger.info(f"Created requisition {requisition.id} for existing borrower {borrower.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to create requisition with existing borrower: {e}")
            return False

    def update_requisition(self, requisition_id: int, borrower_id: int,
                          requisition_data: Dict, items_data: List[Dict],
                          editor_name: str) -> bool:
        """
        Update an existing requisition.

        Args:
            requisition_id: ID of requisition to update
            borrower_id: ID of borrower (borrower changes should be handled via BorrowerEditor)
            requisition_data: Updated requisition details
            items_data: Updated list of items
            editor_name: Name of person making changes

        Returns:
            bool: True if successful
        """
        try:
            # Get existing requisition
            existing_req = self._get_requisition_by_id(requisition_id)
            if not existing_req:
                logger.error(f"Requisition {requisition_id} not found")
                return False

            # Verify borrower exists
            borrower = Borrower.get_by_id(borrower_id)
            if not borrower:
                logger.error(f"Borrower {borrower_id} not found")
                return False

            # Update requisition
            existing_req.borrower_id = borrower_id
            existing_req.date_borrowed = requisition_data['date_borrowed']
            existing_req.lab_activity_name = requisition_data['lab_activity_name']
            existing_req.lab_activity_date = requisition_data['lab_activity_date']
            existing_req.num_students = requisition_data.get('num_students')
            existing_req.num_groups = requisition_data.get('num_groups')

            if not existing_req.save(editor_name):
                return False

            # Update items (remove old, add new)
            self._clear_requisition_items(requisition_id)
            for item_data in items_data:
                req_item = RequisitionItem(
                    requisition_id=requisition_id,
                    item_id=item_data['item_id'],
                    quantity_borrowed=item_data['quantity_borrowed']
                )
                if not req_item.save():
                    return False

            logger.info(f"Updated requisition {requisition_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update requisition {requisition_id}: {e}")
            return False

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

    def get_inventory_items(self) -> List[Dict]:
        """
        Get all inventory items for selection in requisitions.
        Excludes items that are currently borrowed (have unreturned requisitions).

        Returns:
            List of item dictionaries with relevant fields
        """
        return self.item_service.get_inventory_items_for_selection()

    def get_inventory_items_for_editing(self, current_requisition_id: int) -> List[Dict]:
        """
        Get all inventory items for editing a requisition.
        Includes items borrowed by the current requisition, excludes items borrowed by others.

        Args:
            current_requisition_id: ID of the requisition being edited

        Returns:
            List of item dictionaries with relevant fields
        """
        return self.item_service.get_inventory_items_for_selection(
            exclude_borrowed=True,
            exclude_requisition_id=current_requisition_id
        )

    def search_items(self, search_term: str) -> List[Dict]:
        """
        Search inventory items by name.
        Excludes items that are currently borrowed (have unreturned requisitions).

        Args:
            search_term: Term to search for

        Returns:
            List of matching items
        """
        return self.item_service.get_inventory_items_for_selection(
            search_term=search_term,
            exclude_borrowed=True
        )

    def return_items(self, requisition_id: int, return_data: List[Dict], editor_name: str) -> bool:
        """
        Process return of items from a requisition.

        Args:
            requisition_id: ID of requisition
            return_data: List of dicts with item_id and quantity_returned
            editor_name: Name of person processing return

        Returns:
            bool: True if successful
        """
        try:
            # Process returns using StockMovementService
            if not self.stock_service.process_return(requisition_id, return_data, editor_name):
                return False

            # Log the return in requisition history
            requisition = self._get_requisition_by_id(requisition_id)
            if requisition:
                history_query = """
                INSERT INTO Requisition_History (requisition_id, editor_name, reason)
                VALUES (?, ?, ?)
                """
                db.execute_update(history_query, (
                    requisition_id,
                    editor_name,
                    f"Items returned: {sum(r['quantity_returned'] for r in return_data)} items"
                ))

            logger.info(f"Processed return for requisition {requisition_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to process return for requisition {requisition_id}: {e}")
            return False

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
        """Determine the status of a requisition."""
        # Check if all items have been returned
        # This is a simplified check - in practice, you'd track returns more precisely
        current_date = date.today()

        if requisition.lab_activity_date < current_date:
            # Activity is in the past, assume items returned
            return "Returned"
        else:
            # Activity is upcoming or today
            return "Active"
