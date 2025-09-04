"""
Requisition Validator - Centralized validation logic for requisitions.

Provides consistent validation rules and error messaging across all
requisition dialogs (create and edit modes).
"""

from typing import List, Dict
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QDateTime

from inventory_app.database.models import Requester


class RequisitionValidator:
    """
    Centralized validation logic for requisitions.

    Handles all business rules validation and provides consistent
    error messages across create and edit dialogs.
    """

    def validate_requisition_data(self, requester: Requester,
                                selected_items: List[Dict],
                                expected_request: QDateTime,
                                expected_return: QDateTime,
                                activity_name: str) -> bool:
        """
        Comprehensive validation of requisition data.

        Args:
            requester: Selected requester
            selected_items: List of selected items
            expected_request: Expected request date/time
            expected_return: Expected return date/time
            activity_name: Activity name

        Returns:
            True if all validations pass
        """
        # Validate requester
        if not requester:
            QMessageBox.warning(None, "Validation Error", "Please select a requester.")
            return False

        # Validate activity name
        if not activity_name.strip():
            QMessageBox.warning(None, "Validation Error", "Please enter an activity name.")
            return False

        # Validate selected items
        if not selected_items:
            QMessageBox.warning(None, "Validation Error", "Please select at least one item.")
            return False

        # Validate dates
        if not self.validate_dates(expected_request, expected_return):
            return False

        return True

    def validate_dates(self, request_dt: QDateTime, return_dt: QDateTime) -> bool:
        """
        Validate request and return dates.

        Args:
            request_dt: Expected request date/time
            return_dt: Expected return date/time

        Returns:
            True if dates are valid
        """
        if return_dt <= request_dt:
            QMessageBox.warning(
                None,
                "Validation Error",
                "Expected return date/time must be after expected request date/time."
            )
            return False
        return True

    def validate_activity_date(self, activity_date: str, current_date: str) -> bool:
        """
        Validate activity date is not too far in the past.

        Args:
            activity_date: Activity date string
            current_date: Current date string

        Returns:
            True if activity date is valid
        """
        from datetime import date

        try:
            activity_dt = date.fromisoformat(activity_date)
            today = date.fromisoformat(current_date)

            if activity_dt < today:
                reply = QMessageBox.question(
                    None,
                    "Past Date Warning",
                    "The activity date is in the past. Continue anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return False
        except ValueError:
            QMessageBox.warning(None, "Validation Error", "Invalid activity date format.")
            return False

        return True

    def validate_item_quantities(self, selected_items: List[Dict],
                               available_stock_callback) -> bool:
        """
        Validate that selected quantities don't exceed available stock.

        Args:
            selected_items: List of selected items
            available_stock_callback: Function to get available stock for a batch

        Returns:
            True if all quantities are valid
        """
        for item in selected_items:
            batch_id = item['batch_id']
            requested_quantity = item['quantity']

            available_stock = available_stock_callback(batch_id)

            if requested_quantity > available_stock:
                QMessageBox.warning(
                    None,
                    "Stock Validation Error",
                    f"Requested quantity ({requested_quantity}) for {item['item_name']} "
                    f"exceeds available stock ({available_stock})."
                )
                return False

        return True

    def validate_requisition_changes(self, original_data: Dict,
                                   new_data: Dict) -> tuple[bool, str]:
        """
        Validate changes between original and new requisition data.

        Args:
            original_data: Original requisition data
            new_data: New requisition data

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if any changes were made
        changes_made = self._has_changes(original_data, new_data)

        if not changes_made:
            return False, "No changes detected. Please modify at least one field."

        # Extract data with proper type checking
        requester = new_data.get('requester')
        selected_items = new_data.get('selected_items', [])
        expected_request = new_data.get('expected_request')
        expected_return = new_data.get('expected_return')
        activity_name = new_data.get('activity_name', '')

        # Type validation before calling validate_requisition_data
        if not isinstance(requester, Requester) or requester is None:
            return False, "Invalid requester data."

        if not isinstance(expected_request, QDateTime) or expected_request is None:
            return False, "Invalid expected request date/time."

        if not isinstance(expected_return, QDateTime) or expected_return is None:
            return False, "Invalid expected return date/time."

        if not isinstance(activity_name, str):
            return False, "Invalid activity name."

        # Validate the new data
        if not self.validate_requisition_data(
            requester,
            selected_items,
            expected_request,
            expected_return,
            activity_name
        ):
            return False, "Validation failed for new data."

        return True, ""

    def _has_changes(self, original: Dict, new: Dict) -> bool:
        """
        Check if there are any changes between original and new data.

        Args:
            original: Original data
            new: New data

        Returns:
            True if changes are detected
        """
        # Compare simple fields
        fields_to_compare = [
            'activity_name', 'expected_request', 'expected_return',
            'activity_date', 'num_students', 'num_groups'
        ]

        for field in fields_to_compare:
            if original.get(field) != new.get(field):
                return True

        # Compare requester
        if original.get('requester_id') != new.get('requester_id'):
            return True

        # Compare items
        original_items = original.get('selected_items', [])
        new_items = new.get('selected_items', [])

        if len(original_items) != len(new_items):
            return True

        # Check each item
        for orig_item in original_items:
            found = False
            for new_item in new_items:
                if (new_item.get('item_id') == orig_item.get('item_id') and
                    new_item.get('batch_id') == orig_item.get('batch_id') and
                    new_item.get('quantity') == orig_item.get('quantity_requested', orig_item.get('quantity'))):
                    found = True
                    break
            if not found:
                return True

        return False
