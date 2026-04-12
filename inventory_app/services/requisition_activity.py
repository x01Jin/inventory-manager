"""
Requisition Activity Manager - Enhanced activity logging for requisitions.

Provides activity descriptions that integrate with the existing Activity_Log system
for dashboard visibility and audit trails. Activity descriptions are immutable once created.
"""

from typing import List, Dict, Optional
from inventory_app.utils.activity_logger import activity_logger
from inventory_app.utils.logger import logger


class RequisitionActivityManager:
    """
    Manages activity descriptions for requisition operations.

    Integrates with the existing Activity_Log system to provide
    activity descriptions for dashboard display and audit purposes.
    """

    def __init__(self):
        """Initialize the requisition activity manager."""
        logger.info("RequisitionActivityManager initialized")

    def log_requisition_created(
        self,
        requisition_id: int,
        requester_name: str,
        user_name: str = "System",
        timestamp: str | None = None,
    ) -> bool:
        """
        Log a requisition creation activity.

        Args:
            requisition_id: ID of the created requisition
            requester_name: Name of the requester
            user_name: Name of the user performing the action
            timestamp: Optional ISO timestamp override

        Returns:
            bool: True if logged successfully
        """
        try:
            # Create activity description
            description = self._format_creation_description(
                requester_name,
            )

            # Log using existing activity logger
            success = activity_logger.log_activity(
                activity_type=activity_logger.REQUISITION_CREATED,
                description=description,
                entity_id=requisition_id,
                entity_type="requisition",
                user_name=user_name,
                timestamp=timestamp,
            )

            if success:
                logger.info(
                    f"Logged requisition creation activity for ID: {requisition_id}"
                )
            else:
                logger.error(
                    f"Failed to log requisition creation activity for ID: {requisition_id}"
                )

            return success

        except Exception as e:
            logger.error(f"Error logging requisition creation activity: {e}")
            return False

    def log_requisition_updated(
        self,
        requisition_id: int,
        requester_name: str,
        user_name: str = "System",
        timestamp: str | None = None,
    ) -> bool:
        """
        Log a requisition update activity.

        Args:
            requisition_id: ID of the updated requisition
            requester_name: Name of the requester
            user_name: Name of the user performing the action
            timestamp: Optional ISO timestamp override

        Returns:
            bool: True if logged successfully
        """
        try:
            # Create activity description
            description = self._format_update_description(
                requester_name,
            )

            # Log using existing activity logger
            success = activity_logger.log_activity(
                activity_type=activity_logger.REQUISITION_EDITED,
                description=description,
                entity_id=requisition_id,
                entity_type="requisition",
                user_name=user_name,
                timestamp=timestamp,
            )

            if success:
                logger.info(
                    f"Logged requisition update activity for ID: {requisition_id}"
                )
            else:
                logger.error(
                    f"Failed to log requisition update activity for ID: {requisition_id}"
                )

            return success

        except Exception as e:
            logger.error(f"Error logging requisition update activity: {e}")
            return False

    def log_requisition_returned(
        self,
        requisition_id: int,
        user_name: str = "System",
        timestamp: str | None = None,
    ) -> bool:
        """
        Log a requisition return activity.

        Args:
            requisition_id: ID of the returned requisition
            user_name: Name of the user performing the action
            timestamp: Optional ISO timestamp override

        Returns:
            bool: True if logged successfully
        """
        try:
            # Get requester name from database
            requester_name = self._get_requester_name(requisition_id)

            description = f"finalized requisition for {requester_name}"

            success = activity_logger.log_activity(
                activity_type=activity_logger.REQUISITION_RETURNED,
                description=description,
                entity_id=requisition_id,
                entity_type="requisition",
                user_name=user_name,
                timestamp=timestamp,
            )

            if success:
                logger.info(
                    f"Logged requisition return activity for ID: {requisition_id}"
                )

            return success

        except Exception as e:
            logger.error(f"Error logging requisition return activity: {e}")
            return False

    def log_requisition_deleted(
        self,
        requisition_id: int,
        requester_name: str,
        user_name: str = "System",
        timestamp: str | None = None,
    ) -> bool:
        """
        Log a requisition deletion activity.

        Args:
            requisition_id: ID of the deleted requisition
            requester_name: Name of the requester
            user_name: Name of the user performing the action
            timestamp: Optional ISO timestamp override

        Returns:
            bool: True if logged successfully
        """
        try:
            # Create activity description
            description = self._format_deletion_description(
                requester_name,
            )

            # Log using existing activity logger
            success = activity_logger.log_activity(
                activity_type=activity_logger.REQUISITION_DELETED,
                description=description,
                entity_id=requisition_id,
                entity_type="requisition",
                user_name=user_name,
                timestamp=timestamp,
            )

            if success:
                logger.info(
                    f"Logged requisition deletion activity for ID: {requisition_id}"
                )
            else:
                logger.error(
                    f"Failed to log requisition deletion activity for ID: {requisition_id}"
                )

            return success

        except Exception as e:
            logger.error(f"Error logging requisition deletion activity: {e}")
            return False

    def log_defective_recorded(
        self,
        requisition_id: int,
        item_id: int,
        quantity: int,
        user_name: str = "System",
        timestamp: str | None = None,
    ) -> bool:
        """Log a defective item recording activity from return processing."""
        try:
            requester_name = self._get_requester_name(requisition_id)
            item_name = self._get_item_name(item_id)
            description = (
                f"recorded {quantity} defective unit(s) of {item_name} "
                f"for {requester_name}"
            )

            success = activity_logger.log_activity(
                activity_type=activity_logger.ITEM_MARKED_DEFECTIVE,
                description=description,
                entity_id=item_id,
                entity_type="item",
                user_name=user_name,
                timestamp=timestamp,
            )

            if success:
                logger.info(
                    "Logged defective item activity for requisition %s (item %s)",
                    requisition_id,
                    item_id,
                )
            else:
                logger.error(
                    "Failed to log defective item activity for requisition %s (item %s)",
                    requisition_id,
                    item_id,
                )

            return success

        except Exception as e:
            logger.error(f"Error logging defective item activity: {e}")
            return False

    def get_requisition_activities(self, limit: int = 50) -> List[Dict]:
        """
        Get recent requisition-related activities.

        Args:
            limit: Maximum number of activities to return

        Returns:
            List of activity dictionaries with requisition-specific details
        """
        try:
            # Get all recent activities
            all_activities = activity_logger.get_recent_activities(
                limit * 2
            )  # Get more to filter

            # Filter for requisition activities
            requisition_activities = [
                activity
                for activity in all_activities
                if activity.get("type", "").startswith("REQUISITION_")
            ]

            # Return only the requested number
            return requisition_activities[:limit]

        except Exception as e:
            logger.error(f"Error getting requisition activities: {e}")
            return []

    def get_activity_for_requisition(self, requisition_id: int) -> Optional[str]:
        """
        Get the activity description for a specific requisition.

        Args:
            requisition_id: ID of the requisition

        Returns:
            Activity description string or None if not found
        """
        try:
            # This would require a custom query to get the latest activity for a specific requisition
            # For now, return None as this would need additional database schema support
            logger.debug(
                f"Activity retrieval for requisition {requisition_id} not implemented yet"
            )
            return None

        except Exception as e:
            logger.error(
                f"Error getting activity for requisition {requisition_id}: {e}"
            )
            return None

    def _format_creation_description(
        self,
        requester_name: str,
    ) -> str:
        """
        Format a description for requisition creation.

        Args:
            requisition_id: ID of the requisition
            requester_name: Name of the requester
            activity_name: Name of the activity
            activity_description: description
            items_summary: Summary of items

        Returns:
            Formatted description string
        """
        return f"added requisition for {requester_name}"

    def _format_update_description(
        self,
        requester_name: str,
    ) -> str:
        """
        Format a description for requisition updates.

        Args:
            requisition_id: ID of the requisition
            requester_name: Name of the requester
            activity_name: Name of the activity
            activity_description: description
            items_summary: Summary of items
            changes_summary: Summary of changes made

        Returns:
            Formatted description string
        """
        return f"edited requisition for {requester_name}"

    def _format_deletion_description(
        self,
        requester_name: str,
    ) -> str:
        """
        Format a description for requisition deletion.

        Args:
            requester_name: Name of the requester

        Returns:
            Formatted description string
        """
        return f"deleted requisition for {requester_name}"

    def format_items_summary(self, selected_items: List[Dict]) -> str:
        """
        Format a summary of selected items for activity logging.

        Args:
            selected_items: List of selected item dictionaries

        Returns:
            Formatted items summary string
        """
        if not selected_items:
            return "No items"

        # Group items by category and name
        item_groups = {}
        for item in selected_items:
            key = f"{item['item_name']} ({item['category_name']})"
            if key in item_groups:
                item_groups[key] += item["quantity"]
            else:
                item_groups[key] = item["quantity"]

        # Format as readable string
        item_parts = []
        for item_name, quantity in item_groups.items():
            item_parts.append(f"{item_name} (x{quantity})")

        return ", ".join(item_parts)

    def _get_requester_name(self, requisition_id: int) -> str:
        """
        Get requester name for activity logging.

        Args:
            requisition_id: ID of the requisition

        Returns:
            str: Requester name or "Unknown" if not found
        """
        try:
            from inventory_app.database.connection import db

            query = """
            SELECT r.name
            FROM Requesters r
            JOIN Requisitions req ON r.id = req.requester_id
            WHERE req.id = ?
            """
            rows = db.execute_query(query, (requisition_id,))
            return rows[0]["name"] if rows else "Unknown"
        except Exception as e:
            logger.error(
                f"Failed to get requester name for requisition {requisition_id}: {e}"
            )
            return "Unknown"

    def _get_item_name(self, item_id: int) -> str:
        """Get item name for activity logging."""
        try:
            from inventory_app.database.connection import db

            rows = db.execute_query("SELECT name FROM Items WHERE id = ?", (item_id,))
            if rows and (rows[0].get("name") or "").strip():
                return rows[0]["name"].strip()
            return "item"
        except Exception as e:
            logger.error(f"Failed to get item name for item {item_id}: {e}")
            return "item"


# Global instance for easy access
requisition_activity_manager = RequisitionActivityManager()
