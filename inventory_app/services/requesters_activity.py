"""
Requesters Activity Manager - activity logging for requesters.

Provides activity descriptions that integrate with the existing Activity_Log system
for dashboard visibility and audit trails. Activity descriptions are immutable once created.
"""

from typing import List, Dict
from inventory_app.utils.activity_logger import activity_logger
from inventory_app.utils.logger import logger


class RequestersActivityManager:
    """
    Manages activity descriptions for requester operations.

    Integrates with the existing Activity_Log system to provide
    activity descriptions for dashboard display and audit purposes.
    """

    def __init__(self):
        """Initialize the requesters activity manager."""
        logger.info("RequestersActivityManager initialized")

    def log_requester_added(
        self,
        requester_name: str,
        user_name: str = "System",
    ) -> bool:
        """
        Log a requester creation activity.

        Args:
            requester_name: Name of the added requester
            user_name: Name of the user performing the action

        Returns:
            bool: True if logged successfully
        """
        try:
            # Create activity description
            description = self._format_addition_description(requester_name)

            # Log using existing activity logger
            success = activity_logger.log_activity(
                activity_type=activity_logger.REQUESTER_ADDED,
                description=description,
                entity_id=None,  # Will be set by caller if needed
                entity_type="requester",
                user_name=user_name,
            )

            if success:
                logger.info(
                    f"Logged requester addition activity for: {requester_name}"
                )
            else:
                logger.error(
                    f"Failed to log requester addition activity for: {requester_name}"
                )

            return success

        except Exception as e:
            logger.error(f"Error logging requester addition activity: {e}")
            return False

    def log_requester_updated(
        self,
        requester_name: str,
        user_name: str = "System",
    ) -> bool:
        """
        Log a requester update activity.

        Args:
            requester_name: Name of the updated requester
            user_name: Name of the user performing the action

        Returns:
            bool: True if logged successfully
        """
        try:
            # Create activity description
            description = self._format_update_description(requester_name)

            # Log using existing activity logger
            success = activity_logger.log_activity(
                activity_type=activity_logger.REQUESTER_EDITED,
                description=description,
                entity_id=None,  # Will be set by caller if needed
                entity_type="requester",
                user_name=user_name,
            )

            if success:
                logger.info(
                    f"Logged requester update activity for: {requester_name}"
                )
            else:
                logger.error(
                    f"Failed to log requester update activity for: {requester_name}"
                )

            return success

        except Exception as e:
            logger.error(f"Error logging requester update activity: {e}")
            return False

    def log_requester_deleted(
        self,
        requester_name: str,
        user_name: str = "System",
    ) -> bool:
        """
        Log a requester deletion activity.

        Args:
            requester_name: Name of the deleted requester
            user_name: Name of the user performing the action

        Returns:
            bool: True if logged successfully
        """
        try:
            # Create activity description
            description = self._format_deletion_description(requester_name)

            # Log using existing activity logger
            success = activity_logger.log_activity(
                activity_type=activity_logger.REQUESTER_DELETED,
                description=description,
                entity_id=None,  # Will be set by caller if needed
                entity_type="requester",
                user_name=user_name,
            )

            if success:
                logger.info(
                    f"Logged requester deletion activity for: {requester_name}"
                )
            else:
                logger.error(
                    f"Failed to log requester deletion activity for: {requester_name}"
                )

            return success

        except Exception as e:
            logger.error(f"Error logging requester deletion activity: {e}")
            return False

    def get_requesters_activities(self, limit: int = 50) -> List[Dict]:
        """
        Get recent requester-related activities.

        Args:
            limit: Maximum number of activities to return

        Returns:
            List of activity dictionaries with requester-specific details
        """
        try:
            # Get all recent activities
            all_activities = activity_logger.get_recent_activities(
                limit * 2
            )  # Get more to filter

            # Filter for requester activities
            requester_activities = [
                activity
                for activity in all_activities
                if activity.get("type", "").startswith("REQUESTER_")
            ]

            # Return only the requested number
            return requester_activities[:limit]

        except Exception as e:
            logger.error(f"Error getting requester activities: {e}")
            return []

    def _format_addition_description(self, requester_name: str) -> str:
        """
        Format a description for requester addition.

        Args:
            requester_name: Name of the requester

        Returns:
            Formatted description string
        """
        return f"added {requester_name} as a requester"

    def _format_update_description(self, requester_name: str) -> str:
        """
        Format a description for requester updates.

        Args:
            requester_name: Name of the requester

        Returns:
            Formatted description string
        """
        return f"{requester_name}'s details has been edited"

    def _format_deletion_description(self, requester_name: str) -> str:
        """
        Format a description for requester deletion.

        Args:
            requester_name: Name of the requester

        Returns:
            Formatted description string
        """
        return f"{requester_name} has been deleted as a requester"


# Global instance for easy access
requesters_activity_manager = RequestersActivityManager()
