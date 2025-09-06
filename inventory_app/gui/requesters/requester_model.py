"""
Requester model - manages requester data and filtering.
Provides data structure and filtering capabilities for requester display.
Uses composition pattern with RequesterController.
"""

from typing import List, Optional
from datetime import datetime
from dataclasses import dataclass

from inventory_app.database.models import Requester as RequesterDB
from inventory_app.database.connection import db
from inventory_app.services.requesters_activity import requesters_activity_manager
from inventory_app.utils.logger import logger


@dataclass
class RequesterRow:
    """Data structure for displaying requester information in tables."""
    id: Optional[int] = None
    name: str = ""
    affiliation: str = ""
    group_name: str = ""
    created_datetime: Optional[datetime] = None
    requisitions_count: int = 0


class RequesterModel:
    """
    Model for managing requester data and filtering.
    Handles data transformation and filtering logic.
    """

    def __init__(self):
        """Initialize the model."""
        self.all_requesters: List[RequesterDB] = []
        self.filtered_requesters: List[RequesterDB] = []
        self.search_term: str = ""

        logger.info("Requester model initialized")

    def load_data(self) -> bool:
        """
        Load requester data from the database.

        Returns:
            bool: True if successful
        """
        try:
            self.all_requesters = RequesterDB.get_all()
            self._apply_filters()
            logger.info(f"Loaded {len(self.all_requesters)} requesters")
            return True
        except Exception as e:
            logger.error(f"Failed to load requester data: {e}")
            return False

    def get_filtered_rows(self) -> List[RequesterRow]:
        """
        Get filtered requesters as display rows.

        Returns:
            List of RequesterRow objects for display
        """
        try:
            # Get requisition counts for all requesters
            requisition_counts = self._get_requisition_counts()

            rows = []
            for requester in self.filtered_requesters:
                row = RequesterRow(
                    id=requester.id,
                    name=requester.name,
                    affiliation=requester.affiliation,
                    group_name=requester.group_name,
                    created_datetime=requester.created_at,
                    requisitions_count=requisition_counts.get(requester.id, 0)
                )
                rows.append(row)

            return rows

        except Exception as e:
            logger.error(f"Failed to get filtered rows: {e}")
            return []

    def filter_by_search(self, search_term: str) -> None:
        """
        Filter requesters by search term.

        Args:
            search_term: Term to search for in requester name, affiliation, or group
        """
        self.search_term = search_term.lower()
        self._apply_filters()

    def clear_filters(self) -> None:
        """Clear all filters."""
        self.search_term = ""
        self._apply_filters()

    def get_requester_by_id(self, requester_id: int) -> Optional[RequesterDB]:
        """
        Get a specific requester by ID.

        Args:
            requester_id: ID of the requester

        Returns:
            Requester or None if not found
        """
        for requester in self.all_requesters:
            if requester.id == requester_id:
                return requester
        return None

    def get_statistics(self) -> dict:
        """
        Get statistics about current requesters.

        Returns:
            Dictionary with various statistics
        """
        try:
            total_requesters = len(self.filtered_requesters)

            # Count requesters by affiliation
            affiliations = {}
            for requester in self.filtered_requesters:
                affiliation = requester.affiliation or "Unknown"
                affiliations[affiliation] = affiliations.get(affiliation, 0) + 1

            return {
                'total_requesters': total_requesters,
                'affiliation_breakdown': affiliations
            }

        except Exception as e:
            logger.error(f"Failed to calculate statistics: {e}")
            return {
                'total_requesters': 0,
                'affiliation_breakdown': {}
            }

    def add_requester(self, requester_data: dict) -> bool:
        """
        Add a new requester.

        Args:
            requester_data: Requester information

        Returns:
            bool: True if successful
        """
        try:
            requester = RequesterDB()
            requester.name = requester_data.get('name', '')
            requester.affiliation = requester_data.get('affiliation', '')
            requester.group_name = requester_data.get('group_name', '')

            success = requester.save()
            if success:
                self.load_data()  # Refresh data
                logger.info(f"Added new requester: {requester.name}")
            return success

        except Exception as e:
            logger.error(f"Failed to add requester: {e}")
            return False

    def update_requester(self, requester_id: int, requester_data: dict) -> bool:
        """
        Update an existing requester.

        Args:
            requester_id: ID of requester to update
            requester_data: Updated requester information

        Returns:
            bool: True if successful
        """
        try:
            requester = self.get_requester_by_id(requester_id)
            if not requester:
                return False

            requester.name = requester_data.get('name', requester.name)
            requester.affiliation = requester_data.get('affiliation', requester.affiliation)
            requester.group_name = requester_data.get('group_name', requester.group_name)

            success = requester.save()
            if success:
                self.load_data()  # Refresh data
                logger.info(f"Updated requester {requester_id}: {requester.name}")
            return success

        except Exception as e:
            logger.error(f"Failed to update requester {requester_id}: {e}")
            return False

    def delete_requester(self, requester_id: int, editor_name: str = "System") -> bool:
        """
        Delete a requester.

        Args:
            requester_id: ID of requester to delete
            editor_name: Name of the user performing the deletion

        Returns:
            bool: True if successful
        """
        try:
            requester = self.get_requester_by_id(requester_id)
            if not requester:
                logger.error(f"Requester {requester_id} not found")
                return False

            # Attempt deletion
            success = requester.delete()
            if success:
                # Refresh data after successful deletion
                self.load_data()

                # Log activity
                requesters_activity_manager.log_requester_deleted(
                    requester_name=requester.name,
                    user_name=editor_name
                )

                logger.info(f"Successfully deleted requester {requester_id}: {requester.name}")
            else:
                logger.warning(f"Failed to delete requester {requester_id}: requester has associated requisitions")

            return success

        except Exception as e:
            logger.error(f"Failed to delete requester {requester_id}: {e}")
            return False

    def requester_has_requisitions(self, requester_id: int) -> bool:
        """
        Check if a requester has any associated requisitions.

        Args:
            requester_id: ID of requester to check

        Returns:
            bool: True if requester has requisitions, False otherwise
        """
        try:
            query = """
            SELECT COUNT(*) as count
            FROM Requisitions
            WHERE requester_id = ?
            """
            result = db.execute_query(query, (requester_id,))
            if result and len(result) > 0:
                count = result[0]['count']
                return count > 0
            return False
        except Exception as e:
            logger.error(f"Failed to check requisitions for requester {requester_id}: {e}")
            return True  # Return True to be safe (disable deletion if we can't check)

    # Private methods

    def _apply_filters(self) -> None:
        """Apply all current filters to the requester list."""
        try:
            filtered = self.all_requesters.copy()

            # Apply search filter
            if self.search_term:
                filtered = self._filter_by_search_term(filtered)

            self.filtered_requesters = filtered
            logger.debug(f"Applied filters: {len(filtered)} requesters remaining")

        except Exception as e:
            logger.error(f"Failed to apply filters: {e}")
            self.filtered_requesters = self.all_requesters.copy()

    def _filter_by_search_term(self, requesters: List[RequesterDB]) -> List[RequesterDB]:
        """Filter requesters by search term across multiple fields."""
        search_term = self.search_term.lower()
        filtered = []

        for requester in requesters:
            # Search in requester information
            if search_term in requester.name.lower():
                filtered.append(requester)
                continue

            if search_term in requester.affiliation.lower():
                filtered.append(requester)
                continue

            if search_term in requester.group_name.lower():
                filtered.append(requester)
                continue

        return filtered

    def _get_requisition_counts(self) -> dict:
        """
        Get the number of requisitions for each requester.

        Returns:
            Dictionary mapping requester_id to requisition count
        """
        try:
            query = """
            SELECT requester_id, COUNT(*) as requisition_count
            FROM Requisitions
            GROUP BY requester_id
            """
            rows = db.execute_query(query)
            return {row['requester_id']: row['requisition_count'] for row in rows}
        except Exception as e:
            logger.error(f"Failed to get requisition counts: {e}")
            return {}
