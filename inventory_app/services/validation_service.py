"""
Validation service - handles data validation operations.
Provides centralized validation logic for requisitions and items.
"""

from typing import List, Dict
from inventory_app.utils.logger import logger


class ValidationService:
    """
    Service for validation operations.
    Handles validation of requisition data, requester data, and items.
    """

    def __init__(self):
        """Initialize the validation service."""
        logger.info("Validation service initialized")

    def validate_requisition_data(self, requester_data: Dict, requisition_data: Dict,
                                 items_data: List[Dict]) -> bool:
        """
        Validate complete requisition data.

        Args:
            requester_data: Requester information
            requisition_data: Requisition details
            items_data: List of items with quantities

        Returns:
            bool: True if all data is valid
        """
        # Validate requester data
        if not self._validate_requester_data(requester_data):
            return False

        # Validate requisition data
        if not self._validate_requisition_details(requisition_data):
            return False

        # Validate items data
        if not self._validate_items_data(items_data):
            return False

        return True

    def validate_requisition_creation(self, requester_id: int, requisition_data: Dict,
                                     items_data: List[Dict]) -> bool:
        """
        Validate requisition creation with existing requester.

        Args:
            requester_id: ID of existing requester
            requisition_data: Requisition details
            items_data: List of items with quantities

        Returns:
            bool: True if valid
        """
        # Validate requester exists (basic check)
        if not requester_id:
            logger.error("Requester ID is required")
            return False

        # Validate requisition data
        if not self._validate_requisition_details(requisition_data):
            return False

        # Validate items data
        if not self._validate_items_data(items_data):
            return False

        return True

    def _validate_requester_data(self, requester_data: Dict) -> bool:
        """Validate requester information."""
        required_fields = ['name', 'affiliation', 'group_name']

        for field in required_fields:
            value = requester_data.get(field, '').strip()
            if not value:
                logger.error(f"Missing required requester field: {field}")
                return False

        return True

    def _validate_requisition_details(self, requisition_data: Dict) -> bool:
        """Validate requisition details."""
        required_fields = ['date_requested', 'lab_activity_name', 'lab_activity_date']

        for field in required_fields:
            value = requisition_data.get(field, '').strip()
            if not value:
                logger.error(f"Missing required requisition field: {field}")
                return False

        return True

    def _validate_items_data(self, items_data: List[Dict]) -> bool:
        """Validate items data."""
        if not items_data:
            logger.error("No items specified for requisition")
            return False

        for item in items_data:
            if not item.get('item_id') or not item.get('quantity_requested'):
                logger.error(f"Invalid item data: {item}")
                return False

            if item['quantity_requested'] <= 0:
                logger.error(f"Invalid quantity for item {item['item_id']}: {item['quantity_requested']}")
                return False

        return True

    def validate_return_data(self, return_data: List[Dict]) -> bool:
        """
        Validate return data.

        Args:
            return_data: List of items being returned

        Returns:
            bool: True if valid
        """
        if not return_data:
            logger.error("No items specified for return")
            return False

        for return_item in return_data:
            if not return_item.get('item_id') or not return_item.get('quantity_returned'):
                logger.error(f"Invalid return data: {return_item}")
                return False

            if return_item['quantity_returned'] <= 0:
                logger.error(f"Invalid return quantity for item {return_item['item_id']}: {return_item['quantity_returned']}")
                return False

        return True
