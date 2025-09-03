"""
Pure date and time utilities for consistent formatting and display across the application.

This module provides reusable functions for date/time formatting, parsing, and conversion
without any business logic or feature-specific code.
"""

from datetime import datetime, date, time
from typing import Optional, Union, List
import calendar

# Constants for month and day names
MONTH_NAMES = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
}

DAY_NAMES = {
    0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"
}

# Full month and day names for detailed formatting
FULL_MONTH_NAMES = {
    1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
    7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"
}

FULL_DAY_NAMES = {
    0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday",
    4: "Friday", 5: "Saturday", 6: "Sunday"
}


def get_month_name(month_num: int, full: bool = False) -> str:
    """Get month name from month number (1-12).

    Args:
        month_num: Month number (1-12)
        full: If True, return full month name, otherwise abbreviated

    Returns:
        Month name string
    """
    if full:
        return FULL_MONTH_NAMES.get(month_num, "")
    return MONTH_NAMES.get(month_num, "")


def get_day_name(day_num: int, full: bool = False) -> str:
    """Get day name from weekday number (0-6, where 0=Monday).

    Args:
        day_num: Weekday number (0=Monday, 6=Sunday)
        full: If True, return full day name, otherwise abbreviated

    Returns:
        Day name string
    """
    if full:
        return FULL_DAY_NAMES.get(day_num, "")
    return DAY_NAMES.get(day_num, "")


def format_date_short(date_obj: Union[date, datetime]) -> str:
    """Format date in short format: 'Jan 15, 2025'.

    Args:
        date_obj: Date or datetime object

    Returns:
        Formatted date string
    """
    if isinstance(date_obj, datetime):
        date_obj = date_obj.date()

    month_name = get_month_name(date_obj.month)
    return f"{month_name} {date_obj.day}, {date_obj.year}"


def format_date_long(date_obj: Union[date, datetime]) -> str:
    """Format date in long format: 'Monday, January 15, 2025'.

    Args:
        date_obj: Date or datetime object

    Returns:
        Formatted date string
    """
    if isinstance(date_obj, datetime):
        date_obj = date_obj.date()

    day_name = get_day_name(date_obj.weekday(), full=True)
    month_name = get_month_name(date_obj.month, full=True)
    return f"{day_name}, {month_name} {date_obj.day}, {date_obj.year}"


def format_datetime_12h(dt_obj: datetime) -> str:
    """Format datetime in 12-hour format: 'Jan 15, 2025 2:30 PM'.

    Args:
        dt_obj: Datetime object

    Returns:
        Formatted datetime string
    """
    date_str = format_date_short(dt_obj)
    time_str = format_time_12h(dt_obj.time())
    return f"{date_str} {time_str}"


def format_time_12h(time_obj: time) -> str:
    """Format time in 12-hour format: '2:30 PM'.

    Args:
        time_obj: Time object

    Returns:
        Formatted time string
    """
    hour = time_obj.hour
    minute = time_obj.minute

    if hour == 0:
        hour_12 = 12
        am_pm = "AM"
    elif hour < 12:
        hour_12 = hour
        am_pm = "AM"
    elif hour == 12:
        hour_12 = 12
        am_pm = "PM"
    else:
        hour_12 = hour - 12
        am_pm = "PM"

    return f"{hour_12}:{minute:02d} {am_pm}"


def parse_date_iso(date_str: str) -> Optional[date]:
    """Parse ISO date string (YYYY-MM-DD) to date object.

    Args:
        date_str: Date string in ISO format

    Returns:
        Date object or None if parsing fails
    """
    try:
        return date.fromisoformat(date_str)
    except (ValueError, TypeError):
        return None


def parse_datetime_iso(dt_str: str) -> Optional[datetime]:
    """Parse ISO datetime string to datetime object.

    Args:
        dt_str: Datetime string in ISO format

    Returns:
        Datetime object or None if parsing fails
    """
    try:
        return datetime.fromisoformat(dt_str)
    except (ValueError, TypeError):
        return None


def parse_time_12h(time_str: str) -> Optional[time]:
    """Parse 12-hour time string to time object.

    Args:
        time_str: Time string in 12-hour format (e.g., "2:30 PM")

    Returns:
        Time object or None if parsing fails
    """
    try:
        # Split time and AM/PM
        time_part, am_pm = time_str.strip().rsplit(' ', 1)
        hour_str, minute_str = time_part.split(':')

        hour = int(hour_str)
        minute = int(minute_str)

        # Convert to 24-hour format
        if am_pm.upper() == "AM":
            if hour == 12:
                hour = 0
        elif am_pm.upper() == "PM":
            if hour != 12:
                hour += 12

        return time(hour=hour, minute=minute)

    except (ValueError, TypeError, AttributeError):
        return None


def format_relative_date(date_obj: date) -> str:
    """Format date as relative string: 'Today', 'Yesterday', 'Tomorrow', or formatted date.

    Args:
        date_obj: Date object

    Returns:
        Relative date string
    """
    today = date.today()
    diff = (date_obj - today).days

    if diff == 0:
        return "Today"
    elif diff == -1:
        return "Yesterday"
    elif diff == 1:
        return "Tomorrow"
    else:
        return format_date_short(date_obj)


def datetime_to_qdatetime(dt_obj: datetime):
    """Convert Python datetime to QDateTime.

    Args:
        dt_obj: Python datetime object

    Returns:
        QDateTime object
    """
    try:
        from PyQt6.QtCore import QDateTime, QDate, QTime
        qdate = QDate(dt_obj.year, dt_obj.month, dt_obj.day)
        qtime = QTime(dt_obj.hour, dt_obj.minute, dt_obj.second)
        return QDateTime(qdate, qtime)
    except ImportError:
        return None


def qdatetime_to_datetime(qdt) -> Optional[datetime]:
    """Convert QDateTime to Python datetime.

    Args:
        qdt: QDateTime object

    Returns:
        Python datetime object or None if conversion fails
    """
    try:
        if hasattr(qdt, 'toPyDateTime'):
            return qdt.toPyDateTime()
        return None
    except (AttributeError, TypeError):
        return None


def date_to_qdate(date_obj: date):
    """Convert Python date to QDate.

    Args:
        date_obj: Python date object

    Returns:
        QDate object
    """
    try:
        from PyQt6.QtCore import QDate
        return QDate(date_obj.year, date_obj.month, date_obj.day)
    except ImportError:
        return None


def qdate_to_date(qdate) -> Optional[date]:
    """Convert QDate to Python date.

    Args:
        qdate: QDate object

    Returns:
        Python date object or None if conversion fails
    """
    try:
        if hasattr(qdate, 'toPyDate'):
            return qdate.toPyDate()
        return None
    except (AttributeError, TypeError):
        return None


def get_current_datetime() -> datetime:
    """Get current datetime.

    Returns:
        Current datetime object
    """
    return datetime.now()


def get_current_date() -> date:
    """Get current date.

    Returns:
        Current date object
    """
    return date.today()


def format_date_iso(date_obj: Union[date, datetime]) -> str:
    """Format date/datetime to ISO string (YYYY-MM-DD).

    Args:
        date_obj: Date or datetime object

    Returns:
        ISO formatted date string
    """
    if isinstance(date_obj, datetime):
        return date_obj.date().isoformat()
    return date_obj.isoformat()


def format_datetime_iso(dt_obj: datetime) -> str:
    """Format datetime to ISO string (YYYY-MM-DDTHH:MM:SS).

    Args:
        dt_obj: Datetime object

    Returns:
        ISO formatted datetime string
    """
    return dt_obj.isoformat()


def is_valid_date_format(date_str: str, format_pattern: str = "%Y-%m-%d") -> bool:
    """Validate date string format.

    Args:
        date_str: Date string to validate
        format_pattern: Expected format pattern (default: YYYY-MM-DD)

    Returns:
        True if format is valid, False otherwise
    """
    try:
        datetime.strptime(date_str, format_pattern)
        return True
    except (ValueError, TypeError):
        return False


def get_days_in_month(year: int, month: int) -> int:
    """Get the number of days in a specific month and year.

    Automatically handles leap years and different month lengths.

    Args:
        year: Year (e.g., 2025)
        month: Month number (1-12)

    Returns:
        Number of days in the month (28, 29, 30, or 31)
    """
    return calendar.monthrange(year, month)[1]


def get_valid_days_for_month(year: int, month: int) -> List[int]:
    """Get list of valid day numbers for a specific month and year.

    Args:
        year: Year (e.g., 2025)
        month: Month number (1-12)

    Returns:
        List of valid day numbers for the month
    """
    days_in_month = get_days_in_month(year, month)
    return list(range(1, days_in_month + 1))


def is_leap_year(year: int) -> bool:
    """Check if a year is a leap year.

    Args:
        year: Year to check

    Returns:
        True if leap year, False otherwise
    """
    return calendar.isleap(year)


def get_year_range(current_year: Optional[int] = None, years_before: int = 5, years_after: int = 5) -> List[int]:
    """Get a range of years for dropdown selection.

    Args:
        current_year: Center year (defaults to current year)
        years_before: Number of years before current year
        years_after: Number of years after current year

    Returns:
        List of years for dropdown
    """
    if current_year is None:
        current_year = date.today().year

    start_year = current_year - years_before
    end_year = current_year + years_after

    return list(range(start_year, end_year + 1))


def convert_12h_to_24h(hour_12: int, am_pm: str) -> int:
    """Convert 12-hour format hour to 24-hour format.

    Args:
        hour_12: Hour in 12-hour format (1-12)
        am_pm: "AM" or "PM"

    Returns:
        Hour in 24-hour format (0-23)
    """
    if am_pm.upper() == "AM":
        return 0 if hour_12 == 12 else hour_12
    else:  # PM
        return 12 if hour_12 == 12 else hour_12 + 12


def convert_24h_to_12h(hour_24: int) -> tuple[int, str]:
    """Convert 24-hour format hour to 12-hour format.

    Args:
        hour_24: Hour in 24-hour format (0-23)

    Returns:
        Tuple of (hour_12, am_pm) where hour_12 is 1-12 and am_pm is "AM" or "PM"
    """
    if hour_24 == 0:
        return 12, "AM"
    elif hour_24 < 12:
        return hour_24, "AM"
    elif hour_24 == 12:
        return 12, "PM"
    else:
        return hour_24 - 12, "PM"


def get_minutes_options() -> List[str]:
    """Get formatted minute options for dropdown selection.

    Returns:
        List of minute strings with leading zeros: ["01", "02", ..., "59"]
    """
    return [f"{minute:02d}" for minute in range(0, 60)]


def get_hour_options_12h() -> List[int]:
    """Get 12-hour format hour options for dropdown selection.

    Returns:
        List of hours 1-12
    """
    return list(range(1, 13))


def get_ampm_options() -> List[str]:
    """Get AM/PM options for dropdown selection.

    Returns:
        List of ["AM", "PM"]
    """
    return ["AM", "PM"]
