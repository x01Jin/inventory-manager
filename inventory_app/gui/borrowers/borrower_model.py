"""
Borrower model - manages borrower data and filtering.
Provides data structure and filtering capabilities for borrower display.
Uses composition pattern with BorrowerController.
"""

from typing import List, Optional
from datetime import date
from dataclasses import dataclass

from inventory_app.database.models import Borrower as BorrowerDB
from inventory_app.database.connection import db
from inventory_app.utils.logger import logger


@dataclass
class BorrowerRow:
    """Data structure for displaying borrower information in tables."""
    id: Optional[int] = None
    name: str = ""
    affiliation: str = ""
    group_name: str = ""
    created_date: Optional[date] = None
    requisitions_count: int = 0


class BorrowerModel:
    """
    Model for managing borrower data and filtering.
    Handles data transformation and filtering logic.
    """

    def __init__(self):
        """Initialize the model."""
        self.all_borrowers: List[BorrowerDB] = []
        self.filtered_borrowers: List[BorrowerDB] = []
        self.search_term: str = ""

        logger.info("Borrower model initialized")

    def load_data(self) -> bool:
        """
        Load borrower data from the database.

        Returns:
            bool: True if successful
        """
        try:
            self.all_borrowers = BorrowerDB.get_all()
            self._apply_filters()
            logger.info(f"Loaded {len(self.all_borrowers)} borrowers")
            return True
        except Exception as e:
            logger.error(f"Failed to load borrower data: {e}")
            return False

    def get_filtered_rows(self) -> List[BorrowerRow]:
        """
        Get filtered borrowers as display rows.

        Returns:
            List of BorrowerRow objects for display
        """
        try:
            # Get requisition counts for all borrowers
            requisition_counts = self._get_requisition_counts()

            rows = []
            for borrower in self.filtered_borrowers:
                row = BorrowerRow(
                    id=borrower.id,
                    name=borrower.name,
                    affiliation=borrower.affiliation,
                    group_name=borrower.group_name,
                    created_date=None,  # We don't have this field in the current Borrower model
                    requisitions_count=requisition_counts.get(borrower.id, 0)
                )
                rows.append(row)

            return rows

        except Exception as e:
            logger.error(f"Failed to get filtered rows: {e}")
            return []

    def filter_by_search(self, search_term: str) -> None:
        """
        Filter borrowers by search term.

        Args:
            search_term: Term to search for in borrower name, affiliation, or group
        """
        self.search_term = search_term.lower()
        self._apply_filters()

    def clear_filters(self) -> None:
        """Clear all filters."""
        self.search_term = ""
        self._apply_filters()

    def get_borrower_by_id(self, borrower_id: int) -> Optional[BorrowerDB]:
        """
        Get a specific borrower by ID.

        Args:
            borrower_id: ID of the borrower

        Returns:
            Borrower or None if not found
        """
        for borrower in self.all_borrowers:
            if borrower.id == borrower_id:
                return borrower
        return None

    def get_statistics(self) -> dict:
        """
        Get statistics about current borrowers.

        Returns:
            Dictionary with various statistics
        """
        try:
            total_borrowers = len(self.filtered_borrowers)

            # Count borrowers by affiliation
            affiliations = {}
            for borrower in self.filtered_borrowers:
                affiliation = borrower.affiliation or "Unknown"
                affiliations[affiliation] = affiliations.get(affiliation, 0) + 1

            return {
                'total_borrowers': total_borrowers,
                'affiliation_breakdown': affiliations
            }

        except Exception as e:
            logger.error(f"Failed to calculate statistics: {e}")
            return {
                'total_borrowers': 0,
                'affiliation_breakdown': {}
            }

    def add_borrower(self, borrower_data: dict) -> bool:
        """
        Add a new borrower.

        Args:
            borrower_data: Borrower information

        Returns:
            bool: True if successful
        """
        try:
            borrower = BorrowerDB()
            borrower.name = borrower_data.get('name', '')
            borrower.affiliation = borrower_data.get('affiliation', '')
            borrower.group_name = borrower_data.get('group_name', '')

            success = borrower.save()
            if success:
                self.load_data()  # Refresh data
                logger.info(f"Added new borrower: {borrower.name}")
            return success

        except Exception as e:
            logger.error(f"Failed to add borrower: {e}")
            return False

    def update_borrower(self, borrower_id: int, borrower_data: dict) -> bool:
        """
        Update an existing borrower.

        Args:
            borrower_id: ID of borrower to update
            borrower_data: Updated borrower information

        Returns:
            bool: True if successful
        """
        try:
            borrower = self.get_borrower_by_id(borrower_id)
            if not borrower:
                return False

            borrower.name = borrower_data.get('name', borrower.name)
            borrower.affiliation = borrower_data.get('affiliation', borrower.affiliation)
            borrower.group_name = borrower_data.get('group_name', borrower.group_name)

            success = borrower.save()
            if success:
                self.load_data()  # Refresh data
                logger.info(f"Updated borrower {borrower_id}: {borrower.name}")
            return success

        except Exception as e:
            logger.error(f"Failed to update borrower {borrower_id}: {e}")
            return False

    def delete_borrower(self, borrower_id: int) -> bool:
        """
        Delete a borrower (not implemented in BorrowerDB model yet).

        Args:
            borrower_id: ID of borrower to delete

        Returns:
            bool: True if successful
        """
        # For now, just return False as deletion is not implemented
        logger.warning(f"Borrower deletion not implemented for ID: {borrower_id}")
        return False

    # Private methods

    def _apply_filters(self) -> None:
        """Apply all current filters to the borrower list."""
        try:
            filtered = self.all_borrowers.copy()

            # Apply search filter
            if self.search_term:
                filtered = self._filter_by_search_term(filtered)

            self.filtered_borrowers = filtered
            logger.debug(f"Applied filters: {len(filtered)} borrowers remaining")

        except Exception as e:
            logger.error(f"Failed to apply filters: {e}")
            self.filtered_borrowers = self.all_borrowers.copy()

    def _filter_by_search_term(self, borrowers: List[BorrowerDB]) -> List[BorrowerDB]:
        """Filter borrowers by search term across multiple fields."""
        search_term = self.search_term.lower()
        filtered = []

        for borrower in borrowers:
            # Search in borrower information
            if search_term in borrower.name.lower():
                filtered.append(borrower)
                continue

            if search_term in borrower.affiliation.lower():
                filtered.append(borrower)
                continue

            if search_term in borrower.group_name.lower():
                filtered.append(borrower)
                continue

        return filtered

    def _get_requisition_counts(self) -> dict:
        """
        Get the number of requisitions for each borrower.

        Returns:
            Dictionary mapping borrower_id to requisition count
        """
        try:
            query = """
            SELECT borrower_id, COUNT(*) as requisition_count
            FROM Requisitions
            GROUP BY borrower_id
            """
            rows = db.execute_query(query)
            return {row['borrower_id']: row['requisition_count'] for row in rows}
        except Exception as e:
            logger.error(f"Failed to get requisition counts: {e}")
            return {}
