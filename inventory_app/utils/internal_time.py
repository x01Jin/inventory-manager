"""
Clean date/time utilities for the inventory application.
Provides simple date/time display functionality.
"""

from datetime import datetime


def get_current_datetime_string() -> str:
    """Get current date and time as formatted string for navigation display."""
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")


def get_current_date_string() -> str:
    """Get current date as formatted string."""
    now = datetime.now()
    return now.strftime("%Y-%m-%d")


def get_current_time_string() -> str:
    """Get current time as formatted string."""
    now = datetime.now()
    return now.strftime("%H:%M:%S")
