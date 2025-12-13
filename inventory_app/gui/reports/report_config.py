"""
Configuration and constants for the reports module.
Centralizes all UI strings, styling, and business logic constants.
"""

from typing import Optional
from inventory_app.gui.styles import DarkTheme


class ReportConfig:
    """Configuration constants for report generation and UI."""

    # UI Text Constants
    WINDOW_TITLE = "📊 Laboratory Usage Reports"
    GENERATE_BUTTON_TEXT = "📊 Generate Report"
    GENERATE_BUTTON_LOADING = "Generating Report..."
    STATUS_READY = "Ready to generate report.\n\nSelect your parameters and click 'Generate Report'."
    STATUS_SUCCESS = "✅ Report generated successfully!"
    STATUS_ERROR = "❌ Error: {}"
    STATUS_OPENING_FILE = "📂 Opening Excel file..."
    STATUS_FILE_SAVED = "📁 File saved to: {}"

    # Granularity definitions - single source of truth
    GRANULARITY_RANGES = {
        "daily": {"max_days": 7, "description": "≤7 days: Daily breakdown"},
        "weekly": {"max_days": 30, "description": "8-30 days: Weekly breakdown"},
        "monthly": {"max_days": 180, "description": "31-180 days: Monthly breakdown"},
        "quarterly": {
            "max_days": 365,
            "description": "181-365 days: Quarterly breakdown",
        },
        "yearly": {"max_days": 730, "description": "366-730 days: Yearly breakdown"},
        "multi_year": {
            "max_days": float("inf"),
            "description": ">730 days: Multi-year breakdown",
        },
    }

    # UI Layout Constants
    SPLITTER_PROPORTIONS = [400, 400]
    STATUS_TEXT_MAX_HEIGHT = 200
    RECENT_REPORTS_MAX_HEIGHT = 150
    PROGRESS_BAR_HEIGHT = 25

    # Date Range Constants
    DEFAULT_DATE_RANGE_DAYS = 30

    # Styling Constants
    BUTTON_STYLES = {
        "generate": f"""
            QPushButton {{
                font-size: {DarkTheme.FONT_SIZE_LARGE}pt;
                padding: 15px;
                min-height: 50px;
                background-color: {DarkTheme.SUCCESS_COLOR};
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #059669;
            }}
            QPushButton:pressed {{
                background-color: #047857;
            }}
            QPushButton:disabled {{
                background-color: {DarkTheme.TEXT_MUTED};
            }}
        """,
        "progress_bar": f"""
            QProgressBar {{
                border: 1px solid {DarkTheme.BORDER_COLOR};
                border-radius: 4px;
                text-align: center;
                background-color: {DarkTheme.SECONDARY_DARK};
                height: {PROGRESS_BAR_HEIGHT}px;
            }}
            QProgressBar::chunk {{
                background-color: {DarkTheme.SUCCESS_COLOR};
                border-radius: 2px;
            }}
        """,
    }

    # Group Box Titles
    GROUP_TITLES = {
        "config": "Report Configuration",
        "date_range": "Date Range",
        "filters": "Filters",
        "status": "Report Status",
        "recent_reports": "Recent Reports",
    }

    # Filter Labels
    FILTER_LABELS = {
        "grade": "Grade Level:",
        "section": "Section:",
        "consumables": "Include consumable items",
    }

    # Default Values
    DEFAULT_FILTER_VALUES = {
        "grade": "All Grades",
        "section": "All Sections",
        "include_consumables": True,
    }
    # Low stock threshold (units) visible to the UI
    DEFAULT_LOW_STOCK_THRESHOLD = 10

    @classmethod
    def get_granularity_description(
        cls, granularity: str, is_current: bool = False
    ) -> str:
        """Get formatted granularity description with optional current indicator."""
        desc = cls.GRANULARITY_RANGES[granularity]["description"]
        return f"{desc} ← Current" if is_current else desc

    @classmethod
    def get_all_granularity_descriptions(
        cls, current_granularity: Optional[str] = None
    ) -> str:
        """Get all granularity descriptions formatted for display."""
        descriptions = []
        for granularity in cls.GRANULARITY_RANGES.keys():
            is_current = (
                granularity == current_granularity if current_granularity else False
            )
            descriptions.append(
                cls.get_granularity_description(granularity, is_current)
            )
        return "\n".join(descriptions)

    @classmethod
    def get_granularity_for_days(cls, days: int) -> str:
        """Determine granularity based on number of days."""
        for granularity, config in cls.GRANULARITY_RANGES.items():
            if days <= config["max_days"]:
                return granularity
        return "multi_year"


class ReportMessages:
    """Standardized messages for report operations."""

    @staticmethod
    def generation_started(granularity: str) -> str:
        return f"Generating {granularity} report..."

    @staticmethod
    def generation_progress(message: str) -> str:
        return f"\n{message}"

    @staticmethod
    def file_saved(file_path: str) -> str:
        return f"📁 File saved to: {file_path}"

    @staticmethod
    def file_opening() -> str:
        return "📂 Opening Excel file..."

    @staticmethod
    def generation_failed(error: str) -> str:
        return f"❌ Error: {error}"

    @staticmethod
    def invalid_date_range() -> str:
        return "Start date cannot be after end date."

    @staticmethod
    def no_data_found() -> str:
        return (
            "Failed to generate report\nReason: No data found for the specified period"
        )

    @staticmethod
    def filter_applied(filter_name: str, value: str) -> str:
        return f"{filter_name}: {value}"

    @staticmethod
    def include_consumables(value: bool) -> str:
        return f"Include consumables: {value}"


class ReportFilters:
    """Constants for report filtering options."""

    GRADE_ALL = ""
    SECTION_ALL = ""
    INCLUDE_CONSUMABLES_DEFAULT = True

    @staticmethod
    def get_grade_display_value(value: str) -> str:
        """Convert filter value to display string."""
        return "All Grades" if not value else value

    @staticmethod
    def get_section_display_value(value: str) -> str:
        """Convert filter value to display string."""
        return "All Sections" if not value else value

    @classmethod
    def get_low_stock_threshold(cls) -> int:
        """Return the default low stock threshold as configured."""
        return ReportConfig.DEFAULT_LOW_STOCK_THRESHOLD
