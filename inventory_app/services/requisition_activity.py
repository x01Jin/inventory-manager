"""
Requisition Activity Manager - Enhanced activity logging for requisitions.

Provides rich activity descriptions that integrate with the existing Activity_Log system
for dashboard visibility and audit trails. Activity descriptions are immutable once created.
"""

from typing import List, Dict, Optional
from inventory_app.utils.activity_logger import activity_logger
from inventory_app.utils.logger import logger


class RequisitionActivityManager:
    """
    Manages rich activity descriptions for requisition operations.

    Integrates with the existing Activity_Log system to provide detailed,
    immutable activity descriptions for dashboard display and audit purposes.
    """

    def __init__(self):
        """Initialize the requisition activity manager."""
        logger.info("RequisitionActivityManager initialized")

    def log_requisition_created(
        self,
        requisition_id: int,
        requester_name: str,
        user_name: str = "System",
    ) -> bool:
        """
        Log a requisition creation activity.

        Args:
            requisition_id: ID of the created requisition
            requester_name: Name of the requester
            user_name: Name of the user performing the action

        Returns:
            bool: True if logged successfully
        """
        try:
            # Create rich activity description
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
    ) -> bool:
        """
        Log a requisition update activity.

        Args:
            requisition_id: ID of the updated requisition
            requester_name: Name of the requester
            user_name: Name of the user performing the action

        Returns:
            bool: True if logged successfully
        """
        try:
            # Create rich activity description
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
        requester_name: str,
        user_name: str = "System",
    ) -> bool:
        """
        Log a requisition return activity.

        Args:
            requisition_id: ID of the returned requisition
            requester_name: Name of the requester
            returned_items: Summary of returned items
            user_name: Name of the user performing the action

        Returns:
            bool: True if logged successfully
        """
        try:
            description = f"finalized requisition for {requester_name}"

            success = activity_logger.log_activity(
                activity_type=activity_logger.REQUISITION_RETURNED,
                description=description,
                entity_id=requisition_id,
                entity_type="requisition",
                user_name=user_name,
            )

            if success:
                logger.info(
                    f"Logged requisition return activity for ID: {requisition_id}"
                )

            return success

        except Exception as e:
            logger.error(f"Error logging requisition return activity: {e}")
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
        Format a rich description for requisition creation.

        Args:
            requisition_id: ID of the requisition
            requester_name: Name of the requester
            activity_name: Name of the activity
            activity_description: Detailed description
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
        Format a rich description for requisition updates.

        Args:
            requisition_id: ID of the requisition
            requester_name: Name of the requester
            activity_name: Name of the activity
            activity_description: Detailed description
            items_summary: Summary of items
            changes_summary: Summary of changes made

        Returns:
            Formatted description string
        """
        return f"edited requisition for {requester_name}"

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


# Global instance for easy access
requisition_activity_manager = RequisitionActivityManager()
