"""
Requisitions model - manages requisition data and filtering.
Provides data structure and filtering capabilities for requisition display.
Uses composition pattern with RequisitionsController.
"""

from typing import List, Dict, Optional
from datetime import date, datetime
from dataclasses import dataclass

from inventory_app.gui.requisitions.requisitions_controller import RequisitionsController, RequisitionSummary
from inventory_app.utils.logger import logger


@dataclass
class RequisitionRow:
    """Data structure for displaying requisition information in tables."""
    id: Optional[int] = None
    requester_name: str = ""
    requester_affiliation: str = ""
    requester_group: str = ""
    expected_request: Optional[datetime] = None
    expected_return: Optional[datetime] = None
    lab_activity_name: str = ""
    lab_activity_date: Optional[date] = None
    num_students: Optional[int] = None
    num_groups: Optional[int] = None
    total_items: int = 0
    status: str = ""
    items_list: str = ""  # Comma-separated list of items for display


class RequisitionsModel:
    """
    Model for managing requisition data and filtering.
    Handles data transformation and filtering logic.
    """

    def __init__(self):
        """Initialize the model."""
        self.controller = RequisitionsController()
        self.all_requisitions: List[RequisitionSummary] = []
        self.filtered_requisitions: List[RequisitionSummary] = []
        self.search_term: str = ""
        self.requester_filter: str = ""
        self.activity_filter: str = ""
        self.status_filter: str = ""
        self.workflow_status_filter: str = ""
        self.processed_status_filter: str = ""
        self.date_from: Optional[date] = None
        self.date_to: Optional[date] = None

        logger.info("Requisitions model initialized")

    def load_data(self) -> bool:
        """
        Load requisition data from the database.

        Returns:
            bool: True if successful
        """
        try:
            self.all_requisitions = self.controller.get_all_requisitions()
            self._apply_filters()
            logger.info(f"Loaded {len(self.all_requisitions)} requisitions")
            return True
        except Exception as e:
            logger.error(f"Failed to load requisition data: {e}")
            return False

    def get_filtered_rows(self) -> List[RequisitionRow]:
        """
        Get filtered requisitions as display rows.

        Returns:
            List of RequisitionRow objects for display
        """
        try:
            rows = []
            for summary in self.filtered_requisitions:
                # Create comma-separated list of items
                items_list = ", ".join([
                    f"{item['name']} (x{item['quantity_requested']})"
                    for item in summary.items
                ])

                row = RequisitionRow(
                    id=summary.requisition.id,
                    requester_name=summary.requester.name,
                    requester_affiliation=summary.requester.affiliation,
                    requester_group=summary.requester.group_name,
                    expected_request=summary.requisition.expected_request,
                    expected_return=summary.requisition.expected_return,
                    lab_activity_name=summary.requisition.lab_activity_name,
                    lab_activity_date=summary.requisition.lab_activity_date,
                    num_students=summary.requisition.num_students,
                    num_groups=summary.requisition.num_groups,
                    total_items=summary.total_items,
                    status=summary.status,
                    items_list=items_list
                )
                rows.append(row)

            return rows

        except Exception as e:
            logger.error(f"Failed to get filtered rows: {e}")
            return []

    def filter_by_search(self, search_term: str) -> None:
        """
        Filter requisitions by search term.

        Args:
            search_term: Term to search for in requester name, activity, or items
        """
        self.search_term = search_term.lower()
        self._apply_filters()

    def filter_by_requester(self, requester_name: str) -> None:
        """
        Filter by requester name.

        Args:
            requester_name: Requester name to filter by
        """
        self.requester_filter = requester_name.lower()
        self._apply_filters()

    def filter_by_activity(self, activity_name: str) -> None:
        """
        Filter by lab activity name.

        Args:
            activity_name: Activity name to filter by
        """
        self.activity_filter = activity_name.lower()
        self._apply_filters()

    def filter_by_status(self, status: str) -> None:
        """
        Filter by requisition status.

        Args:
            status: Status to filter by ('active', 'returned', 'overdue', 'partially returned', etc.)
        """
        self.status_filter = status
        self._apply_filters()

    def filter_by_workflow_status(self, workflow_status: str) -> None:
        """
        Filter by workflow status only (requested, active, overdue).

        Args:
            workflow_status: Workflow status to filter by
        """
        self.workflow_status_filter = workflow_status
        self._apply_filters()

    def filter_by_processed_status(self, processed_status: str) -> None:
        """
        Filter by processed status (returned, partially returned, used, lost).

        Args:
            processed_status: Processed status to filter by
        """
        self.processed_status_filter = processed_status
        self._apply_filters()

    def filter_by_date_range(self, date_from: Optional[date], date_to: Optional[date]) -> None:
        """
        Filter by date range.

        Args:
            date_from: Start date for filtering
            date_to: End date for filtering
        """
        self.date_from = date_from
        self.date_to = date_to
        self._apply_filters()

    def clear_filters(self) -> None:
        """Clear all filters."""
        self.search_term = ""
        self.requester_filter = ""
        self.activity_filter = ""
        self.status_filter = ""
        self.workflow_status_filter = ""
        self.processed_status_filter = ""
        self.date_from = None
        self.date_to = None
        self._apply_filters()

    def get_requisition_by_id(self, requisition_id: int) -> Optional[RequisitionSummary]:
        """
        Get a specific requisition by ID.

        Args:
            requisition_id: ID of the requisition

        Returns:
            RequisitionSummary or None if not found
        """
        for summary in self.all_requisitions:
            if summary.requisition.id == requisition_id:
                return summary
        return None

    def get_statistics(self) -> Dict[str, int]:
        """
        Get statistics about current requisitions.

        Returns:
            Dictionary with various statistics
        """
        try:
            total_requisitions = len(self.filtered_requisitions)
            active_count = sum(1 for r in self.filtered_requisitions if r.status == "active")
            returned_count = sum(1 for r in self.filtered_requisitions if r.status == "returned")
            overdue_count = sum(1 for r in self.filtered_requisitions if r.status == "overdue")
            partially_returned_count = sum(1 for r in self.filtered_requisitions if "partially returned" in r.status)
            consumed_count = sum(1 for r in self.filtered_requisitions if r.status == "consumed")
            lost_count = sum(1 for r in self.filtered_requisitions if r.status == "lost")
            returned_and_lost_count = sum(1 for r in self.filtered_requisitions if r.status == "returned and lost")
            returned_and_consumed_count = sum(1 for r in self.filtered_requisitions if r.status == "returned and consumed")

            # Calculate total items requested
            total_items = sum(r.total_items for r in self.filtered_requisitions)

            # Count unique requesters
            unique_requesters = len(set(r.requester.id for r in self.filtered_requisitions if r.requester.id))

            return {
                'total_requisitions': total_requisitions,
                'active_requisitions': active_count,
                'returned_requisitions': returned_count,
                'overdue_requisitions': overdue_count,
                'partially_returned_requisitions': partially_returned_count,
                'consumed_requisitions': consumed_count,
                'lost_requisitions': lost_count,
                'returned_and_lost_requisitions': returned_and_lost_count,
                'returned_and_consumed_requisitions': returned_and_consumed_count,
                'total_items_requested': total_items,
                'unique_requesters': unique_requesters
            }

        except Exception as e:
            logger.error(f"Failed to calculate statistics: {e}")
            return {
                'total_requisitions': 0,
                'active_requisitions': 0,
                'returned_requisitions': 0,
                'overdue_requisitions': 0,
                'partially_returned_requisitions': 0,
                'consumed_requisitions': 0,
                'lost_requisitions': 0,
                'returned_and_lost_requisitions': 0,
                'returned_and_consumed_requisitions': 0,
                'total_items_requested': 0,
                'unique_requesters': 0
            }

    def delete_requisition(self, requisition_id: int, editor_name: str) -> bool:
        """
        Delete a requisition.

        Args:
            requisition_id: ID of requisition to delete
            editor_name: Name of person deleting

        Returns:
            bool: True if successful
        """
        if self.controller.delete_requisition(requisition_id, editor_name):
            self.load_data()  # Refresh data
            return True
        return False
    # Private methods

    def _apply_filters(self) -> None:
        """Apply all current filters to the requisition list."""
        try:
            filtered = self.all_requisitions.copy()

            # Apply search filter
            if self.search_term:
                filtered = self._filter_by_search_term(filtered)

            # Apply requester filter
            if self.requester_filter:
                filtered = [r for r in filtered if self.requester_filter in r.requester.name.lower()]

            # Apply activity filter
            if self.activity_filter:
                filtered = [r for r in filtered if self.activity_filter in r.requisition.lab_activity_name.lower()]

            # Apply status filters
            if self.workflow_status_filter:
                filtered = [r for r in filtered if self._matches_workflow_status(r.status, self.workflow_status_filter)]

            if self.processed_status_filter:
                filtered = [r for r in filtered if self._matches_processed_status(r.status, self.processed_status_filter)]

            # Legacy status filter (for backward compatibility)
            if self.status_filter:
                if self.status_filter == "partially returned":
                    filtered = [r for r in filtered if "partially returned" in r.status]
                elif self.status_filter in ["requested", "active", "overdue"]:
                    filtered = [r for r in filtered if self._matches_workflow_status(r.status, self.status_filter)]
                else:
                    filtered = [r for r in filtered if self.status_filter in r.status]

            # Apply date range filter
            if self.date_from or self.date_to:
                filtered = self._filter_by_date_range(filtered)

            self.filtered_requisitions = filtered
            logger.debug(f"Applied filters: {len(filtered)} requisitions remaining")

        except Exception as e:
            logger.error(f"Failed to apply filters: {e}")
            self.filtered_requisitions = self.all_requisitions.copy()

    def _filter_by_search_term(self, requisitions: List[RequisitionSummary]) -> List[RequisitionSummary]:
        """Filter requisitions by search term across multiple fields."""
        search_term = self.search_term.lower()
        filtered = []

        for req in requisitions:
            # Search in requester information
            if search_term in req.requester.name.lower():
                filtered.append(req)
                continue

            if search_term in req.requester.affiliation.lower():
                filtered.append(req)
                continue

            if search_term in req.requester.group_name.lower():
                filtered.append(req)
                continue

            # Search in activity information
            if search_term in req.requisition.lab_activity_name.lower():
                filtered.append(req)
                continue

            # Search in items
            for item in req.items:
                if search_term in item['name'].lower():
                    filtered.append(req)
                    break

        return filtered

    def _filter_by_date_range(self, requisitions: List[RequisitionSummary]) -> List[RequisitionSummary]:
        """Filter requisitions by date range."""
        filtered = []

        for req in requisitions:
            req_date = req.requisition.lab_activity_date

            if req_date:
                # Check if date is within range
                if self.date_from and req_date < self.date_from:
                    continue
                if self.date_to and req_date > self.date_to:
                    continue

            filtered.append(req)

        return filtered

    def _matches_workflow_status(self, status_string: str, workflow_status: str) -> bool:
        """Check if status string contains the specified workflow status."""
        # Status format: "workflow_status, processed_status1 (X%), processed_status2 (Y%)"
        # Or just "workflow_status" if no processed status
        workflow_part = status_string.split(',')[0].strip()
        return workflow_part == workflow_status

    def _matches_processed_status(self, status_string: str, processed_status: str) -> bool:
        """Check if status string contains the specified processed status."""
        # Status format: "workflow_status, processed_status1 (X%), processed_status2 (Y%)"
        parts = status_string.split(',')
        if len(parts) < 2:
            return False  # No processed status

        # Check each processed status part
        for part in parts[1:]:
            part = part.strip()
            # Extract the status name (remove percentage)
            status_name = part.split(' (')[0] if ' (' in part else part
            if status_name == processed_status:
                return True
        return False
