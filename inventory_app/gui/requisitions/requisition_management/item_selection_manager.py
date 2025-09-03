"""
Item Selection Manager - Handles item selection logic with smart duplicate handling.

Provides centralized item management with proper stock calculations and
duplicate item combination to prevent multiple entries of the same item.
"""

from typing import Dict, List, Optional

from inventory_app.services.item_service import ItemService


class ItemSelectionManager:
    """
    Manages item selection with smart duplicate handling.

    Handles adding items, editing quantities, and stock calculations.
    Uses ItemService for proper data access and stock management.
    """

    def __init__(self, item_service: ItemService):
        """
        Initialize the item selection manager.

        Args:
            item_service: ItemService instance for data access
        """
        self.item_service = item_service

    def add_item_to_selection(
        self, selected_items: List[Dict], item_data: Dict, quantity: int
    ) -> bool:
        """
        Smart addition with duplicate combination.

        Checks for existing item (same item_id + batch_id) and combines
        quantities instead of creating duplicate entries.

        Args:
            selected_items: Current list of selected items
            item_data: Item data from the database
            quantity: Quantity to add

        Returns:
            True if addition was successful
        """
        # Check if item already exists (same item_id + batch_id)
        for existing_item in selected_items:
            if (
                existing_item["item_id"] == item_data["item_id"]
                and existing_item["batch_id"] == item_data["batch_id"]
            ):
                # Combine quantities instead of creating duplicate
                existing_item["quantity"] += quantity
                return True

        # Add as new item with standardized structure
        new_item = self._create_standard_item_structure(item_data, quantity)
        selected_items.append(new_item)
        return True

    def edit_item_quantity(self, selected_items: List[Dict], item_index: int) -> bool:
        """
        Edit quantity with current value as default.

        Uses current quantity as the default value in the dialog,
        fixing the issue where editing always started with 1.

        Args:
            selected_items: Current list of selected items
            item_index: Index of the item to edit

        Returns:
            True if quantity was successfully updated
        """
        if item_index >= len(selected_items):
            return False

        item = selected_items[item_index]

        # Get real-time available stock for this batch (including current selections)
        available_stock = self.get_real_time_available_stock_for_batch(
            item["batch_id"],
            selected_items,
            getattr(self, "exclude_requisition_id", None),
        )

        # Add back the current item's quantity since we're editing it
        available_stock += item["quantity"]

        # Use current quantity as default value
        new_quantity, ok = self._get_quantity_from_user(
            item["item_name"],
            available_stock,
            item["batch_number"],
            item["quantity"],  # ← Current quantity as default!
        )

        if ok and new_quantity != item["quantity"]:
            item["quantity"] = new_quantity
            return True

        return False

    def get_available_stock_for_batch(
        self, batch_id: int, exclude_requisition_id: Optional[int] = None
    ) -> int:
        """
        Get available stock for a specific batch.

        Uses ItemService instead of duplicating logic.

        Args:
            batch_id: ID of the batch
            exclude_requisition_id: Requisition ID to exclude from borrowed check

        Returns:
            Available stock for the batch
        """
        return self.item_service._get_available_stock_for_batch(
            batch_id, exclude_requisition_id
        )

    def get_real_time_available_stock_for_batch(
        self,
        batch_id: int,
        selected_items: List[Dict],
        exclude_requisition_id: Optional[int] = None,
    ) -> int:
        """
        Get real-time available stock for a batch, subtracting currently selected quantities.

        Real-time calculation: DB_available - currently_selected_quantities

        Args:
            batch_id: ID of the batch
            selected_items: Currently selected items in the dialog
            exclude_requisition_id: Requisition ID to exclude from borrowed check

        Returns:
            Real-time available stock for the batch
        """
        # Get database available stock
        db_available = self.item_service._get_available_stock_for_batch(
            batch_id, exclude_requisition_id
        )

        # Subtract quantities of the same batch that are currently selected
        selected_quantity = 0
        for item in selected_items:
            if item.get("batch_id") == batch_id:
                selected_quantity += item.get("quantity", 0)

        return max(0, db_available - selected_quantity)

    def _create_standard_item_structure(self, item_data: Dict, quantity: int) -> Dict:
        """
        Create standardized item data structure.

        Ensures consistent field names across all dialogs.

        Args:
            item_data: Raw item data from database
            quantity: Selected quantity

        Returns:
            Standardized item dictionary
        """
        return {
            "item_id": item_data["item_id"],
            "batch_id": item_data["batch_id"],
            "item_name": item_data["item_name"],
            "batch_number": item_data["batch_number"],
            "quantity": quantity,  # ← Standardized field name
            "category_name": item_data["category_name"],
        }

    def _get_quantity_from_user(
        self,
        item_name: str,
        max_quantity: int,
        batch_number: int,
        current_quantity: int = 1,
    ) -> tuple[int, bool]:
        """
        Get quantity from user with validation.

        Args:
            item_name: Name of the item
            max_quantity: Maximum available quantity
            batch_number: Batch number for display
            current_quantity: Current quantity (used as default)

        Returns:
            Tuple of (quantity, ok)
        """
        from PyQt6.QtWidgets import QInputDialog

        quantity, ok = QInputDialog.getInt(
            None,  # No parent dialog needed
            "Select Quantity",
            f"Enter quantity for {item_name} (Batch #{batch_number}):\n"
            f"Available: {max_quantity}",
            value=current_quantity,  # ← Use current quantity as default!
            min=1,
            max=max_quantity,
        )

        return quantity, ok if ok is not None else False
