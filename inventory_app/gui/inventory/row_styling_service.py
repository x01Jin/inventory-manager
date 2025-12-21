"""
Row styling service for inventory table.
Handles row background color determination based on item status and criticality.
"""

from typing import Optional, Tuple
from inventory_app.services.item_status_service import ItemStatus


class RowStylingService:
    """
    Service for determining row styling based on item status.
    Applies single-purpose principle by handling only row styling logic.
    """

    # Status severity levels (higher is more critical)
    SEVERITY_LEVELS = {
        "EXPIRED": 4,
        "CAL_DUE": 3,
        "EXPIRING": 2,
        "CAL_WARNING": 1,
        "OK": 0,
    }

    def __init__(self):
        """Initialize the row styling service."""
        pass

    def get_row_style_class(self, item_status: Optional[ItemStatus]) -> str:
        """
        Determine the CSS class for row styling based on item status.

        For items with multiple status parts (e.g., "CAL_WARNING and EXPIRING"),
        the most critical status determines the row color.

        Args:
            item_status: ItemStatus object or None

        Returns:
            Style class name: 'row-overdue', 'row-warning', or ''
        """
        if not item_status or item_status.status == "OK":
            return ""

        # Parse status (may be combined like "CAL_WARNING and EXPIRING")
        status_parts = [s.strip() for s in item_status.status.split(" and ")]

        # Find the most critical status
        most_critical = self._get_most_critical_status(status_parts)

        # Map to style class
        if most_critical in ["EXPIRED", "CAL_DUE"]:
            return "row-overdue"
        elif most_critical in ["EXPIRING", "CAL_WARNING"]:
            return "row-warning"

        return ""

    def _get_most_critical_status(self, status_parts: list) -> str:
        """
        Get the most critical status from a list of status parts.

        Args:
            status_parts: List of status strings

        Returns:
            The most critical status string
        """
        max_severity = -1
        most_critical = "OK"

        for status in status_parts:
            severity = self.SEVERITY_LEVELS.get(status, 0)
            if severity > max_severity:
                max_severity = severity
                most_critical = status

        return most_critical

    def get_row_colors(self, style_class: str, theme: str = "dark") -> Tuple[str, str]:
        """
        Get background and text colors for a given style class and theme.

        Args:
            style_class: Style class name ('row-overdue', 'row-warning', or '')
            theme: Theme name ('dark' or 'light')

        Returns:
            Tuple of (background_color, text_color) as hex strings
        """
        if theme == "dark":
            if style_class == "row-overdue":
                # Reddish pink for overdues - darker shade for dark theme
                return ("#8A293E", "#FFFFFF")
            elif style_class == "row-warning":
                # Pale yellow for warnings - darker shade for dark theme
                return ("#A5A536", "#FFFFFF")
            else:
                # Default - no specific color
                return ("", "")
        else:  # light theme
            if style_class == "row-overdue":
                # Reddish pink for overdues - light theme
                return ("#D13A5B", "#000000")
            elif style_class == "row-warning":
                # Pale yellow for warnings - light theme
                return ("#EBEB41", "#000000")
            else:
                # Default - no specific color
                return ("", "")


# Global instance
row_styling_service = RowStylingService()
