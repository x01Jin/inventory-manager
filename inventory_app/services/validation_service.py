"""
Validation service - handles data validation operations.
Provides centralized validation logic for requisitions and items.
"""

from typing import List, Dict, Optional
from datetime import datetime, date
from inventory_app.utils.logger import logger


class ValidationService:
    """
    Service for validation operations.
    Handles validation of requisition data, requester data, and items.
    """

    def __init__(self):
        """Initialize the validation service."""
        logger.info("Validation service initialized")
        # Last validation error message, useful for callers to present user feedback
        self._last_error: Optional[str] = None
        # Application-wide limits
        self.MAX_QUANTITY = 10000  # upper bound for requested/returned quantities
        self.MAX_STR_LEN = 500  # max length for freeform text fields

    def validate_requisition_data(
        self, requester_data: Dict, requisition_data: Dict, items_data: List[Dict]
    ) -> bool:
        """
        Validate complete requisition data.

        Args:
            requester_data: Requester information
            requisition_data: Requisition details
            items_data: List of items with quantities

        Returns:
            bool: True if all data is valid
        """
        # Clear last error and validate requester data
        self._last_error = None
        if not self._validate_requester_data(requester_data):
            return False

        # Validate requisition data
        if not self._validate_requisition_details(requisition_data):
            return False

        # Validate items data
        if not self._validate_items_data(items_data):
            return False

        return True

    def validate_requisition_creation(
        self, requester_id: int, requisition_data: Dict, items_data: List[Dict]
    ) -> bool:
        """
        Validate requisition creation with existing requester.

        Args:
            requester_id: ID of existing requester
            requisition_data: Requisition details
            items_data: List of items with quantities

        Returns:
            bool: True if valid
        """
        # Clear last error and validate requester exists (basic check)
        self._last_error = None
        if not requester_id or not isinstance(requester_id, int) or requester_id <= 0:
            self._last_error = "Invalid requester ID"
            logger.error(self._last_error)
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
        required_fields = ["name", "affiliation", "group_name"]

        if not isinstance(requester_data, dict):
            self._last_error = "Invalid requester data"
            logger.error(self._last_error)
            return False

        for field in required_fields:
            value = requester_data.get(field, "")
            if not isinstance(value, str) or not value.strip():
                self._last_error = (
                    f"Missing or invalid required requester field: {field}"
                )
                logger.error(self._last_error)
                return False
            if len(value) > self.MAX_STR_LEN:
                self._last_error = f"Requester field {field} is too long"
                logger.error(self._last_error)
                return False

        return True

    def _validate_requisition_details(self, requisition_data: Dict) -> bool:
        """Validate requisition details."""
        required_fields = ["date_requested", "lab_activity_name", "lab_activity_date"]

        if not isinstance(requisition_data, dict):
            self._last_error = "Invalid requisition data"
            logger.error(self._last_error)
            return False

        for field in required_fields:
            value = requisition_data.get(field, "")
            if not isinstance(value, str) or not value.strip():
                self._last_error = (
                    f"Missing or invalid required requisition field: {field}"
                )
                logger.error(self._last_error)
                return False
            if field in ("lab_activity_name",) and len(value) > self.MAX_STR_LEN:
                self._last_error = f"Requisition field {field} is too long"
                logger.error(self._last_error)
                return False

        # Validate dates in ISO format
        try:
            date_requested = datetime.fromisoformat(requisition_data["date_requested"])
        except Exception:
            self._last_error = "Invalid date_requested format"
            logger.error(self._last_error)
            return False

        try:
            # Parse to validate format - value not needed beyond validation
            date.fromisoformat(requisition_data["lab_activity_date"])
        except Exception:
            self._last_error = "Invalid lab_activity_date format"
            logger.error(self._last_error)
            return False

        # If expected_return exists, validate it and ensure it is after date_requested
        expected_return = requisition_data.get(
            "expected_return"
        ) or requisition_data.get("date_return")
        if expected_return:
            try:
                expected_return_dt = datetime.fromisoformat(expected_return)
                if expected_return_dt <= date_requested:
                    self._last_error = "Expected return must be after date_requested"
                    logger.error(self._last_error)
                    return False
            except Exception:
                self._last_error = "Invalid expected_return format"
                logger.error(self._last_error)
                return False

        return True

    def _validate_items_data(self, items_data: List[Dict]) -> bool:
        """Validate items data."""
        if not items_data:
            self._last_error = "No items specified for requisition"
            logger.error(self._last_error)
            return False

        if not isinstance(items_data, list):
            self._last_error = "Invalid items data"
            logger.error(self._last_error)
            return False

        for item in items_data:
            if not isinstance(item, dict):
                self._last_error = "Invalid item entry"
                logger.error(self._last_error)
                return False

            item_id = item.get("item_id")
            qty = item.get("quantity_requested")
            if not isinstance(item_id, int) or item_id <= 0:
                self._last_error = f"Invalid item_id: {item_id}"
                logger.error(self._last_error)
                return False
            if not isinstance(qty, int):
                self._last_error = (
                    f"Invalid quantity type for item {item_id}: {type(qty)}"
                )
                logger.error(self._last_error)
                return False
            if qty <= 0:
                self._last_error = f"Invalid quantity for item {item_id}: {qty}"
                logger.error(self._last_error)
                return False
            if qty > self.MAX_QUANTITY:
                self._last_error = (
                    f"Quantity for item {item_id} exceeds maximum ({self.MAX_QUANTITY})"
                )
                logger.error(self._last_error)
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
        self._last_error = None
        if not return_data:
            self._last_error = "No items specified for return"
            logger.error(self._last_error)
            return False

        if not isinstance(return_data, list):
            self._last_error = "Invalid return data"
            logger.error(self._last_error)
            return False

        for return_item in return_data:
            if not isinstance(return_item, dict):
                self._last_error = "Invalid return entry"
                logger.error(self._last_error)
                return False
            item_id = return_item.get("item_id")
            qty = return_item.get("quantity_returned")
            if not isinstance(item_id, int) or item_id <= 0:
                self._last_error = f"Invalid item_id in return: {item_id}"
                logger.error(self._last_error)
                return False
            if not isinstance(qty, int):
                self._last_error = (
                    f"Invalid return quantity type for item {item_id}: {type(qty)}"
                )
                logger.error(self._last_error)
                return False
            if qty <= 0:
                self._last_error = f"Invalid return quantity for item {item_id}: {qty}"
                logger.error(self._last_error)
                return False
            if qty > self.MAX_QUANTITY:
                self._last_error = f"Return quantity for item {item_id} exceeds maximum ({self.MAX_QUANTITY})"
                logger.error(self._last_error)
                return False

        return True

    def get_last_error(self) -> Optional[str]:
        """Return the last validation error message."""
        return self._last_error
