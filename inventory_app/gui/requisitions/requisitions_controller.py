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
        """Initialize controller."""
        logger.info("Requisitions controller initialized")

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

                # Get requisition items with details
                items = self._get_requisition_items_with_details(req.id)

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

    def create_requisition(self, borrower_data: Dict, requisition_data: Dict,
                          items_data: List[Dict], editor_name: str) -> bool:
        """
        Create a new requisition with borrower and items.

        Args:
            borrower_data: Dict with borrower information
            requisition_data: Dict with requisition details
            items_data: List of dicts with item_id and quantity_borrowed
            editor_name: Name of person creating the requisition

        Returns:
            bool: True if successful
        """
        try:
            # Validate required fields (Spec #1)
            if not self._validate_requisition_data(borrower_data, requisition_data, items_data):
                return False

            # Step 1: Handle borrower (create if new)
            borrower = self._get_or_create_borrower(borrower_data)
            if not borrower or not borrower.id:
                logger.error("Failed to create/retrieve borrower")
                return False
            time.sleep(0.5)  # Allow borrower operation to complete

            # Step 2: Create requisition
            requisition = Requisition(
                borrower_id=borrower.id,
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

            # Step 3: Add items to requisition and update stock
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

                # Step 4: Record stock movement (consumption)
                self._record_stock_movement(
                    item_data['item_id'],
                    'CONSUMPTION',
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
            # Validate required fields
            borrower_id = requisition_data.get('borrower_id')
            if not borrower_id:
                logger.error("Borrower ID is required for existing borrower requisition")
                return False

            # Validate other required fields
            required_fields = ['date_borrowed', 'lab_activity_name', 'lab_activity_date']
            for field in required_fields:
                if not requisition_data.get(field):
                    logger.error(f"Missing required field: {field}")
                    return False

            if not items_data:
                logger.error("No items specified for requisition")
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

                # Record stock movement (consumption)
                self._record_stock_movement(
                    item_data['item_id'],
                    'CONSUMPTION',
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

    def update_requisition(self, requisition_id: int, borrower_data: Dict,
                          requisition_data: Dict, items_data: List[Dict],
                          editor_name: str) -> bool:
        """
        Update an existing requisition.

        Args:
            requisition_id: ID of requisition to update
            borrower_data: Updated borrower information
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

            # Handle borrower updates
            borrower = self._get_or_create_borrower(borrower_data)
            if not borrower or not borrower.id:
                return False

            # Update requisition
            existing_req.borrower_id = borrower.id
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
        Delete a requisition and handle stock returns.

        Args:
            requisition_id: ID of requisition to delete
            editor_name: Name of person deleting

        Returns:
            bool: True if successful
        """
        try:
            requisition = self._get_requisition_by_id(requisition_id)
            if not requisition:
                return False

            # Return items to stock before deleting
            items = RequisitionItem.get_by_requisition(requisition_id)
            for req_item in items:
                if not requisition.id:
                    continue
                self._record_stock_movement(
                    req_item.item_id,
                    'RETURN',
                    req_item.quantity_borrowed,
                    requisition.id,
                    f"Returned from deleted requisition: {requisition.lab_activity_name}"
                )

            # Delete requisition (will cascade to items)
            if requisition.delete(editor_name):
                logger.info(f"Deleted requisition {requisition_id}")
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
        try:
            items = Item.get_all()

            # Get IDs of currently borrowed items
            borrowed_item_ids = self._get_borrowed_item_ids()

            result = []

            for item in items:
                if not item.id:
                    continue

                # Skip items that are currently borrowed
                if item.id in borrowed_item_ids:
                    continue

                # Get category and supplier names
                category_name = self._get_category_name(item.category_id)
                supplier_name = self._get_supplier_name(item.supplier_id) if item.supplier_id else None

                item_dict = {
                    'id': item.id,
                    'unique_code': item.unique_code,
                    'name': item.name,
                    'category_name': category_name,
                    'supplier_name': supplier_name,
                    'size': item.size,
                    'brand': item.brand,
                    'other_specifications': item.other_specifications,
                    'is_consumable': item.is_consumable,
                    'available_quantity': self._get_available_quantity(item.id)
                }
                result.append(item_dict)

            return result

        except Exception as e:
            logger.error(f"Failed to get inventory items: {e}")
            return []

    def get_inventory_items_for_editing(self, current_requisition_id: int) -> List[Dict]:
        """
        Get all inventory items for editing a requisition.
        Includes items borrowed by the current requisition, excludes items borrowed by others.

        Args:
            current_requisition_id: ID of the requisition being edited

        Returns:
            List of item dictionaries with relevant fields
        """
        try:
            items = Item.get_all()

            # Get IDs of items borrowed by OTHER requisitions (exclude current one)
            borrowed_item_ids = self._get_borrowed_item_ids(exclude_requisition_id=current_requisition_id)

            result = []

            for item in items:
                if not item.id:
                    continue

                # Skip items that are currently borrowed by OTHER requisitions
                if item.id in borrowed_item_ids:
                    continue

                # Get category and supplier names
                category_name = self._get_category_name(item.category_id)
                supplier_name = self._get_supplier_name(item.supplier_id) if item.supplier_id else None

                item_dict = {
                    'id': item.id,
                    'unique_code': item.unique_code,
                    'name': item.name,
                    'category_name': category_name,
                    'supplier_name': supplier_name,
                    'size': item.size,
                    'brand': item.brand,
                    'other_specifications': item.other_specifications,
                    'is_consumable': item.is_consumable,
                    'available_quantity': self._get_available_quantity(item.id)
                }
                result.append(item_dict)

            return result

        except Exception as e:
            logger.error(f"Failed to get inventory items for editing: {e}")
            return []

    def search_items(self, search_term: str) -> List[Dict]:
        """
        Search inventory items by name.
        Excludes items that are currently borrowed (have unreturned requisitions).

        Args:
            search_term: Term to search for

        Returns:
            List of matching items
        """
        try:
            items = Item.search(search_term)

            # Get IDs of currently borrowed items
            borrowed_item_ids = self._get_borrowed_item_ids()

            result = []

            for item in items:
                if not item.id:
                    continue

                # Skip items that are currently borrowed
                if item.id in borrowed_item_ids:
                    continue

                category_name = self._get_category_name(item.category_id)
                supplier_name = self._get_supplier_name(item.supplier_id) if item.supplier_id else None

                item_dict = {
                    'id': item.id,
                    'unique_code': item.unique_code,
                    'name': item.name,
                    'category_name': category_name,
                    'supplier_name': supplier_name,
                    'size': item.size,
                    'brand': item.brand,
                    'other_specifications': item.other_specifications,
                    'is_consumable': item.is_consumable,
                    'available_quantity': self._get_available_quantity(item.id)
                }
                result.append(item_dict)

            return result

        except Exception as e:
            logger.error(f"Failed to search items: {e}")
            return []

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
            for return_item in return_data:
                self._record_stock_movement(
                    return_item['item_id'],
                    'RETURN',
                    return_item['quantity_returned'],
                    requisition_id,
                    f"Items returned by {editor_name}"
                )

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

    # Private helper methods

    def _get_requisition_items_with_details(self, requisition_id: int) -> List[Dict]:
        """Get detailed item information for a requisition."""
        try:
            query = """
            SELECT ri.item_id, ri.quantity_borrowed, i.name, i.category_id, i.size, i.brand,
                   c.name as category_name, s.name as supplier_name
            FROM Requisition_Items ri
            JOIN Items i ON ri.item_id = i.id
            LEFT JOIN Categories c ON i.category_id = c.id
            LEFT JOIN Suppliers s ON i.supplier_id = s.id
            WHERE ri.requisition_id = ?
            """
            rows = db.execute_query(query, (requisition_id,))
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get requisition items for {requisition_id}: {e}")
            return []

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

    def _validate_requisition_data(self, borrower_data: Dict, requisition_data: Dict,
                                  items_data: List[Dict]) -> bool:
        """Validate requisition data according to specs."""
        # Check mandatory borrower fields
        required_borrower = ['name', 'affiliation', 'group_name']
        for field in required_borrower:
            if not borrower_data.get(field, '').strip():
                logger.error(f"Missing required borrower field: {field}")
                return False

        # Check mandatory requisition fields
        required_req = ['date_borrowed', 'lab_activity_name', 'lab_activity_date']
        for field in required_req:
            if not requisition_data.get(field):
                logger.error(f"Missing required requisition field: {field}")
                return False

        # Check items
        if not items_data:
            logger.error("No items specified for requisition")
            return False

        for item in items_data:
            if not item.get('item_id') or not item.get('quantity_borrowed') or item['quantity_borrowed'] <= 0:
                logger.error(f"Invalid item data: {item}")
                return False

        return True

    def _get_or_create_borrower(self, borrower_data: Dict) -> Optional[Borrower]:
        """Get existing borrower or create new one."""
        try:
            # Try to find existing borrower by name and affiliation
            query = """
            SELECT * FROM Borrowers
            WHERE name = ? AND affiliation = ? AND group_name = ?
            """
            rows = db.execute_query(query, (
                borrower_data['name'],
                borrower_data['affiliation'],
                borrower_data['group_name']
            ))

            if rows:
                return Borrower(**dict(rows[0]))

            # Create new borrower
            borrower = Borrower(
                name=borrower_data['name'],
                affiliation=borrower_data['affiliation'],
                group_name=borrower_data['group_name']
            )

            if borrower.save():
                return borrower

            return None

        except Exception as e:
            logger.error(f"Failed to get/create borrower: {e}")
            return None

    def _record_stock_movement(self, item_id: int, movement_type: str, quantity: int,
                             source_id: int, note: str) -> None:
        """Record a stock movement."""
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
        except Exception as e:
            logger.error(f"Failed to record stock movement: {e}")

    def _clear_requisition_items(self, requisition_id: int) -> None:
        """Remove all items from a requisition."""
        try:
            db.execute_update("DELETE FROM Requisition_Items WHERE requisition_id = ?", (requisition_id,))
        except Exception as e:
            logger.error(f"Failed to clear requisition items: {e}")

    def _get_category_name(self, category_id: int) -> str:
        """Get category name by ID."""
        try:
            category = Category.get_by_id(category_id)
            return category.name if category else "Unknown"
        except Exception:
            return "Unknown"

    def _get_supplier_name(self, supplier_id: int) -> str:
        """Get supplier name by ID."""
        try:
            supplier = Supplier.get_by_id(supplier_id)
            return supplier.name if supplier else "Unknown"
        except Exception:
            return "Unknown"

    def _get_available_quantity(self, item_id: int) -> int:
        """Get available quantity for an item (simplified calculation)."""
        try:
            # This is a simplified calculation - in practice, you'd use the Stock_Movements
            # table to calculate current stock levels
            query = """
            SELECT COALESCE(SUM(quantity_received), 0) as total_received
            FROM Item_Batches
            WHERE item_id = ?
            """
            rows = db.execute_query(query, (item_id,))
            total_received = rows[0]['total_received'] if rows else 0

            # For now, return total received (would need to subtract consumed items)
            return total_received

        except Exception as e:
            logger.error(f"Failed to get available quantity for item {item_id}: {e}")
            return 0

    def _get_borrowed_item_ids(self, exclude_requisition_id: Optional[int] = None) -> set:
        """
        Get IDs of items that are currently borrowed (have unreturned requisitions).

        Args:
            exclude_requisition_id: Optional requisition ID to exclude from results

        Returns:
            Set of item IDs that are currently borrowed
        """
        try:
            # Query for items that have requisition items but no corresponding RETURN stock movements
            query = """
            SELECT DISTINCT ri.item_id
            FROM Requisition_Items ri
            JOIN Requisitions r ON ri.requisition_id = r.id
            WHERE NOT EXISTS (
                SELECT 1 FROM Stock_Movements sm
                WHERE sm.item_id = ri.item_id
                AND sm.movement_type = 'RETURN'
                AND sm.source_id = r.id
            )
            """
            params = []

            # Add exclusion condition if specified
            if exclude_requisition_id is not None:
                query += " AND r.id != ?"
                params.append(exclude_requisition_id)

            rows = db.execute_query(query, tuple(params))
            return {row['item_id'] for row in rows}
        except Exception as e:
            logger.error(f"Failed to get borrowed item IDs: {e}")
            return set()

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
