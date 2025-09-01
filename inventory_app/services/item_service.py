"""
Item service - handles item-related business logic operations.
Provides centralized item management with composition pattern.
"""

from typing import List, Dict, Optional, Set
from inventory_app.database.connection import db
from inventory_app.database.models import Item, Category, Supplier
from inventory_app.utils.logger import logger


class ItemService:
    """
    Service for item-related operations.
    Handles item queries, availability checks, and dictionary building.
    """

    def __init__(self):
        """Initialize the item service."""
        logger.info("Item service initialized")

    def build_item_dict(self, item: Item, exclude_borrowed: bool = True,
                       exclude_requisition_id: Optional[int] = None) -> Dict:
        """
        Build a standardized item dictionary for display/selection.

        Args:
            item: Item model instance
            exclude_borrowed: Whether to exclude currently borrowed items
            exclude_requisition_id: Requisition ID to exclude from borrowed check

        Returns:
            Dictionary with item details
        """
        try:
            if not item.id:
                return {}

            # Check if item is currently borrowed (if exclusion requested)
            if exclude_borrowed:
                borrowed_ids = self._get_borrowed_item_ids(exclude_requisition_id)
                if item.id in borrowed_ids:
                    return {}

            # Get category and supplier names
            category_name = self._get_category_name(item.category_id)
            supplier_name = self._get_supplier_name(item.supplier_id)

            return {
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

        except Exception as e:
            logger.error(f"Failed to build item dict for item {item.id}: {e}")
            return {}

    def get_inventory_items_for_selection(self, search_term: Optional[str] = None,
                                       exclude_borrowed: bool = True,
                                       exclude_requisition_id: Optional[int] = None) -> List[Dict]:
        """
        Get inventory items formatted for selection in requisitions.

        Args:
            search_term: Optional search term to filter items
            exclude_borrowed: Whether to exclude currently borrowed items
            exclude_requisition_id: Requisition ID to exclude from borrowed check

        Returns:
            List of item dictionaries
        """
        try:
            # Get items (search or all)
            if search_term:
                items = Item.search(search_term)
            else:
                items = Item.get_all()

            result = []
            for item in items:
                item_dict = self.build_item_dict(item, exclude_borrowed, exclude_requisition_id)
                if item_dict:  # Only add if not empty (not excluded)
                    result.append(item_dict)

            return result

        except Exception as e:
            logger.error(f"Failed to get inventory items: {e}")
            return []

    def get_requisition_items_with_details(self, requisition_id: int) -> List[Dict]:
        """
        Get detailed item information for a specific requisition.

        Args:
            requisition_id: ID of the requisition

        Returns:
            List of item details with quantities
        """
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

    def _get_borrowed_item_ids(self, exclude_requisition_id: Optional[int] = None) -> Set[int]:
        """
        Get IDs of items that are currently borrowed.

        Args:
            exclude_requisition_id: Optional requisition ID to exclude

        Returns:
            Set of borrowed item IDs
        """
        try:
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

            if exclude_requisition_id is not None:
                query += " AND r.id != ?"
                params.append(exclude_requisition_id)

            rows = db.execute_query(query, tuple(params))
            return {row['item_id'] for row in rows}
        except Exception as e:
            logger.error(f"Failed to get borrowed item IDs: {e}")
            return set()

    def _get_category_name(self, category_id: int) -> str:
        """Get category name by ID."""
        try:
            category = Category.get_by_id(category_id)
            return category.name if category else "Unknown"
        except Exception:
            return "Unknown"

    def _get_supplier_name(self, supplier_id: Optional[int]) -> str:
        """Get supplier name by ID."""
        try:
            if supplier_id is None:
                return "Unknown"
            supplier = Supplier.get_by_id(supplier_id)
            return supplier.name if supplier else "Unknown"
        except Exception:
            return "Unknown"

    def _get_available_quantity(self, item_id: int) -> int:
        """Get available quantity for an item."""
        try:
            query = """
            SELECT COALESCE(SUM(quantity_received), 0) as total_received
            FROM Item_Batches
            WHERE item_id = ?
            """
            rows = db.execute_query(query, (item_id,))
            return rows[0]['total_received'] if rows else 0
        except Exception as e:
            logger.error(f"Failed to get available quantity for item {item_id}: {e}")
            return 0
