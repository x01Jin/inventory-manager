"""
Activity logging utility for tracking user actions in the laboratory inventory system.
Provides centralized logging for dashboard recent activity display.
"""

from typing import Optional
from datetime import datetime, timedelta, timezone
from inventory_app.database.connection import db
from inventory_app.utils.logger import logger


class ActivityLogger:
    """Utility class for logging user activities throughout the application."""

    # Activity type constants
    ITEM_ADDED = "ITEM_ADDED"
    ITEM_EDITED = "ITEM_EDITED"
    ITEM_DELETED = "ITEM_DELETED"
    STOCK_RECEIVED = "STOCK_RECEIVED"
    STOCK_ADJUSTED = "STOCK_ADJUSTED"
    REQUISITION_CREATED = "REQUISITION_CREATED"
    REQUISITION_EDITED = "REQUISITION_EDITED"
    REQUISITION_RETURNED = "REQUISITION_RETURNED"
    REQUISITION_DELETED = "REQUISITION_DELETED"
    REQUESTER_ADDED = "REQUESTER_ADDED"
    REQUESTER_EDITED = "REQUESTER_EDITED"
    REQUESTER_DELETED = "REQUESTER_DELETED"
    REPORT_GENERATED = "REPORT_GENERATED"

    @staticmethod
    def log_activity(
        activity_type: str,
        description: str,
        entity_id: Optional[int] = None,
        entity_type: Optional[str] = None,
        user_name: str = "System",
    ) -> bool:
        """
        Log an activity to the database.

        Args:
            activity_type: Type of activity (use constants)
            description: Human-readable description
            entity_id: ID of related entity (optional)
            entity_type: Type of entity (optional)
            user_name: Name of user performing action

        Returns:
            bool: True if logged successfully
        """
        try:
            query = """
            INSERT INTO Activity_Log (activity_type, description, entity_id, entity_type, user_name, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """

            timestamp = datetime.now(timezone.utc).isoformat()
            db.execute_update(
                query,
                (
                    activity_type,
                    description,
                    entity_id,
                    entity_type,
                    user_name,
                    timestamp,
                ),
            )

            logger.debug(f"Logged activity: {activity_type} - {description}")

            # Maintain only the 20 most recent activities
            ActivityLogger.maintain_activity_limit()

            return True

        except Exception as e:
            logger.error(f"Failed to log activity {activity_type}: {e}")
            return False

    @staticmethod
    def get_recent_activities(limit: int = 20) -> list:
        """
        Get recent activities for dashboard display.

        Args:
            limit: Maximum number of activities to return

        Returns:
            List of activity dictionaries
        """
        try:
            query = """
            SELECT activity_type, description, entity_type, user_name, timestamp
            FROM Activity_Log
            ORDER BY timestamp DESC
            LIMIT ?
            """

            rows = db.execute_query(query, (limit,))
            activities = []

            for row in rows:
                # Parse timestamp to datetime object
                timestamp = row["timestamp"]
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp)
                    except (ValueError, TypeError):
                        dt = None
                else:
                    dt = None

                activities.append(
                    {
                        "type": row["activity_type"],
                        "description": row["description"],
                        "entity_type": row["entity_type"],
                        "user": row["user_name"] or "System",
                        "time": dt,
                    }
                )

            return activities

        except Exception as e:
            logger.error(f"Failed to get recent activities: {e}")
            return []

    @staticmethod
    def cleanup_old_activities(days_to_keep: int = 90) -> int:
        """
        Clean up old activity logs to prevent database bloat.

        Args:
            days_to_keep: Number of days of activities to keep

        Returns:
            Number of records deleted
        """
        try:
            # Compute cutoff timestamp in Python to allow parameterized queries
            cutoff = (
                datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            ).isoformat()

            # Get count before deletion
            count_query = (
                "SELECT COUNT(*) as count FROM Activity_Log WHERE timestamp < ?"
            )
            before_count = db.execute_query(count_query, (cutoff,))[0]["count"]

            delete_query = "DELETE FROM Activity_Log WHERE timestamp < ?"
            db.execute_update(delete_query, (cutoff,))

            logger.info(f"Cleaned up {before_count} old activity records")
            return before_count

        except Exception as e:
            logger.error(f"Failed to cleanup old activities: {e}")
            return 0

    @staticmethod
    def maintain_activity_limit(max_activities: int = 20) -> int:
        """
        Maintain only the most recent activities by deleting older ones beyond the limit.

        Args:
            max_activities: Maximum number of activities to keep

        Returns:
            Number of records deleted
        """
        try:
            # First, get the total count
            count_query = "SELECT COUNT(*) as count FROM Activity_Log"
            total_count = db.execute_query(count_query)[0]["count"]

            if total_count <= max_activities:
                return 0  # No cleanup needed

            # Delete older records beyond the limit in a parameterized, efficient way.
            # First, fetch the ids to keep (most recent `max_activities` entries).
            ids_query = "SELECT id FROM Activity_Log ORDER BY timestamp DESC LIMIT ?"
            ids_rows = db.execute_query(ids_query, (max_activities,))
            keep_ids = [r["id"] for r in ids_rows]

            # If we couldn't fetch the ids or there is nothing to delete, return 0.
            if not keep_ids:
                return 0

            # Build parameter placeholders for the NOT IN clause and pass values as params
            placeholders = ",".join("?" for _ in keep_ids)
            delete_query = f"DELETE FROM Activity_Log WHERE id NOT IN ({placeholders})"
            records_to_delete = total_count - max_activities
            db.execute_update(delete_query, tuple(keep_ids))

            logger.debug(
                f"Cleaned up {records_to_delete} old activity records to maintain limit of {max_activities}"
            )
            return records_to_delete

        except Exception as e:
            logger.error(f"Failed to maintain activity limit: {e}")
            return 0


# Global instance for easy access
activity_logger = ActivityLogger()
