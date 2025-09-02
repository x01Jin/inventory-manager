"""
Enhanced date utilities for the inventory management system.
Provides comprehensive date formatting, granularity calculation, and period handling.
"""

from datetime import date, timedelta
from typing import List, Tuple
from calendar import monthrange


class EnhancedDateFormatter:
    """Advanced date formatting utilities with smart granularity."""

    # Constants for month and day names
    MONTH_NAMES = {
        1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
        7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
    }

    DAY_NAMES = {
        0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"
    }

    @staticmethod
    def get_smart_granularity(start_date: date, end_date: date) -> str:
        """
        Determine the optimal reporting granularity based on date range.

        Args:
            start_date: Start date of the period
            end_date: End date of the period

        Returns:
            Granularity level: 'daily', 'weekly', 'monthly', 'quarterly', 'yearly', 'multi_year'
        """
        days_diff = (end_date - start_date).days + 1

        if days_diff <= 7:
            return 'daily'
        elif days_diff <= 30:
            return 'weekly'
        elif days_diff <= 180:
            return 'monthly'
        elif days_diff <= 365:
            return 'quarterly'
        elif days_diff <= 730:
            return 'yearly'
        else:
            return 'multi_year'

    @staticmethod
    def format_period_header(date_obj: date, granularity: str) -> str:
        """
        Format a date according to the specified granularity.

        Args:
            date_obj: Date to format
            granularity: Granularity level

        Returns:
            Formatted period header string
        """
        if granularity == 'daily':
            # Format: (Mon - Jan 01, 2020)
            day_name = EnhancedDateFormatter.DAY_NAMES.get(date_obj.weekday(), "Mon")
            month_name = EnhancedDateFormatter.MONTH_NAMES.get(date_obj.month, "Jan")
            return f"({day_name} - {month_name} {date_obj.day:02d}, {date_obj.year})"
        elif granularity == 'weekly':
            # Format: (W1 - Jan/2020) - Month-based weeks
            week_num = ((date_obj.day - 1) // 7) + 1
            month_name = EnhancedDateFormatter.MONTH_NAMES.get(date_obj.month, "Jan")
            return f"(W{week_num} - {month_name}/{date_obj.year})"
        elif granularity == 'monthly':
            # Format: (Jan/2020)
            month_name = EnhancedDateFormatter.MONTH_NAMES.get(date_obj.month, "Jan")
            return f"({month_name}/{date_obj.year})"
        elif granularity == 'quarterly':
            # Format: (Jan-Mar/2020)
            quarter = ((date_obj.month - 1) // 3) + 1
            # Calculate quarter start and end months
            quarter_start_month = (quarter - 1) * 3 + 1
            quarter_end_month = quarter * 3

            start_month_name = EnhancedDateFormatter.MONTH_NAMES.get(quarter_start_month, "Jan")
            end_month_name = EnhancedDateFormatter.MONTH_NAMES.get(quarter_end_month, "Mar")
            return f"({start_month_name}-{end_month_name}/{date_obj.year})"
        elif granularity in ['yearly', 'multi_year']:
            # Format: (2020)
            return f"({date_obj.year})"
        else:
            return date_obj.strftime('%Y-%m-%d')

    @staticmethod
    def calculate_periods_with_excess(start_date: date, end_date: date, granularity: str) -> Tuple[List[date], List[date]]:
        """
        Calculate main periods and any excess time that doesn't fit the granularity.

        Args:
            start_date: Start date of the period
            end_date: End date of the period
            granularity: Granularity level

        Returns:
            Tuple of (main_periods, excess_periods)
        """
        main_periods = []
        excess_periods = []
        current = start_date

        while current <= end_date:
            main_periods.append(current)

            if granularity == 'daily':
                current += timedelta(days=1)
            elif granularity == 'weekly':
                current += timedelta(weeks=1)
            elif granularity == 'monthly':
                # Move to next month
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1)
                else:
                    current = current.replace(month=current.month + 1)
            elif granularity == 'quarterly':
                # Move to next quarter
                quarter_months = 3
                new_month = current.month + quarter_months
                if new_month > 12:
                    current = current.replace(year=current.year + 1, month=new_month - 12)
                else:
                    current = current.replace(month=new_month)
            elif granularity == 'yearly':
                current = current.replace(year=current.year + 1)
            else:  # multi_year
                current = current.replace(year=current.year + 1)

        # Check for excess periods
        if current <= end_date:
            excess_periods.append(current)

        return main_periods, excess_periods

    @staticmethod
    def get_period_keys(start_date: date, end_date: date, granularity: str) -> List[str]:
        """
        Generate comprehensive period keys including excess periods for complete data coverage.

        Args:
            start_date: Start date
            end_date: End date
            granularity: Granularity level

        Returns:
            List of period key strings for SQL queries
        """
        period_keys = []

        if granularity == 'daily':
            # Daily: Just include all individual days
            current_date = start_date
            while current_date <= end_date:
                period_keys.append(current_date.strftime('%Y-%m-%d'))
                current_date += timedelta(days=1)

        elif granularity == 'weekly':
            # Weekly: Include excess days + main weeks + excess days
            period_keys.extend(EnhancedDateFormatter._get_weekly_period_keys(start_date, end_date))

        elif granularity == 'monthly':
            # Monthly: Include excess days + main months + excess days
            period_keys.extend(EnhancedDateFormatter._get_monthly_period_keys(start_date, end_date))

        elif granularity == 'quarterly':
            # Quarterly: Include excess days + main quarters + excess days
            period_keys.extend(EnhancedDateFormatter._get_quarterly_period_keys(start_date, end_date))

        elif granularity in ['yearly', 'multi_year']:
            # Yearly: Just include the years
            current_year = start_date.year
            while current_year <= end_date.year:
                period_keys.append(str(current_year))
                current_year += 1

        return period_keys

    @staticmethod
    def _get_weekly_period_keys(start_date: date, end_date: date) -> List[str]:
        """Generate weekly period keys with excess handling."""
        period_keys = []

        # Find the first Monday on or before start_date
        first_monday = start_date - timedelta(days=(start_date.weekday() - 0) % 7)
        if first_monday < start_date:
            # Add excess days before first Monday
            excess_start = start_date
            excess_end = first_monday + timedelta(days=6)  # Sunday before first Monday
            if excess_start <= excess_end:
                period_keys.append(f"{excess_start.strftime('%Y-%m-%d')}to{excess_end.strftime('%Y-%m-%d')}")

        # Add main weeks (Monday to Sunday)
        current_monday = first_monday
        while current_monday <= end_date:
            week_sunday = current_monday + timedelta(days=6)
            if current_monday >= start_date or week_sunday >= start_date:
                # Only include weeks that have days in our range
                week_year = current_monday.year
                week_month = current_monday.month
                # Calculate week number within month
                first_monday_of_month = current_monday.replace(day=1)
                while first_monday_of_month.weekday() != 0:  # Find first Monday of month
                    first_monday_of_month += timedelta(days=1)
                if first_monday_of_month > current_monday:
                    first_monday_of_month -= timedelta(days=7)  # Go to previous Monday

                week_num = ((current_monday - first_monday_of_month).days // 7) + 1
                period_keys.append(f"{week_year}-{week_month:02d}-W{week_num}")

            current_monday += timedelta(days=7)

        # Add excess days after last Sunday
        # Find the last Sunday that was actually processed in the loop
        last_sunday = current_monday - timedelta(days=8)  # Go back to the last processed Sunday
        if last_sunday < end_date:
            excess_start = last_sunday + timedelta(days=1)
            excess_end = end_date
            if excess_start <= excess_end:
                period_keys.append(f"{excess_start.strftime('%Y-%m-%d')}to{excess_end.strftime('%Y-%m-%d')}")

        return list(dict.fromkeys(period_keys))  # Remove duplicates

    @staticmethod
    def _get_monthly_period_keys(start_date: date, end_date: date) -> List[str]:
        """Generate monthly period keys with excess handling."""
        period_keys = []

        # Add excess days before first day of month
        if start_date.day > 1:
            month_start = start_date.replace(day=1)
            excess_start = month_start
            excess_end = start_date - timedelta(days=1)
            period_keys.append(f"{excess_start.strftime('%Y-%m-%d')}to{excess_end.strftime('%Y-%m-%d')}")

        # Add main months
        current_month = start_date.replace(day=1)
        while current_month <= end_date:
            period_keys.append(current_month.strftime('%Y-%m'))
            if current_month.month == 12:
                current_month = current_month.replace(year=current_month.year + 1, month=1)
            else:
                current_month = current_month.replace(month=current_month.month + 1)

        # Add excess days after last day of month
        last_month_end = current_month - timedelta(days=1)
        if last_month_end < end_date:
            excess_start = last_month_end + timedelta(days=1)
            excess_end = end_date
            if excess_start <= excess_end:
                period_keys.append(f"{excess_start.strftime('%Y-%m-%d')}to{excess_end.strftime('%Y-%m-%d')}")

        return list(dict.fromkeys(period_keys))  # Remove duplicates

    @staticmethod
    def _get_quarterly_period_keys(start_date: date, end_date: date) -> List[str]:
        """Generate quarterly period keys with excess handling."""
        period_keys = []

        # Find quarter start
        quarter_start_month = ((start_date.month - 1) // 3) * 3 + 1
        quarter_start = start_date.replace(month=quarter_start_month, day=1)

        # Add excess days before quarter start
        if start_date > quarter_start:
            excess_start = quarter_start
            excess_end = start_date - timedelta(days=1)
            period_keys.append(f"{excess_start.strftime('%Y-%m-%d')}to{excess_end.strftime('%Y-%m-%d')}")

        # Add main quarters
        current_quarter_start = quarter_start
        while current_quarter_start <= end_date:
            quarter = ((current_quarter_start.month - 1) // 3) + 1
            period_keys.append(f"{current_quarter_start.year}-Q{quarter}")

            # Move to next quarter
            next_month = current_quarter_start.month + 3
            if next_month > 12:
                current_quarter_start = current_quarter_start.replace(year=current_quarter_start.year + 1, month=1)
            else:
                current_quarter_start = current_quarter_start.replace(month=next_month)

        # Add excess days after quarter end
        quarter_end = current_quarter_start - timedelta(days=1)
        if quarter_end < end_date:
            excess_start = quarter_end + timedelta(days=1)
            excess_end = end_date
            if excess_start <= excess_end:
                period_keys.append(f"{excess_start.strftime('%Y-%m-%d')}to{excess_end.strftime('%Y-%m-%d')}")

        return list(dict.fromkeys(period_keys))  # Remove duplicates

    @staticmethod
    def get_days_in_period(date_obj: date, granularity: str) -> int:
        """
        Get the number of days in a period for accurate calculations.

        Args:
            date_obj: Date within the period
            granularity: Granularity level

        Returns:
            Number of days in the period
        """
        if granularity == 'daily':
            return 1
        elif granularity == 'weekly':
            # Calculate days until end of week (Sunday)
            days_to_end = 6 - date_obj.weekday()
            return days_to_end + 1
        elif granularity == 'monthly':
            return monthrange(date_obj.year, date_obj.month)[1]
        elif granularity == 'quarterly':
            # Calculate days in quarter
            quarter_start_month = ((date_obj.month - 1) // 3) * 3 + 1
            days = 0
            for month in range(quarter_start_month, quarter_start_month + 3):
                days += monthrange(date_obj.year, month)[1]
            return days
        elif granularity in ['yearly', 'multi_year']:
            return 365 + (1 if date_obj.year % 4 == 0 and (date_obj.year % 100 != 0 or date_obj.year % 400 == 0) else 0)
        else:
            return 1

    @staticmethod
    def validate_date_range(start_date: date, end_date: date) -> bool:
        """
        Validate that the date range is logical.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            True if valid, False otherwise
        """
        return start_date <= end_date

    @staticmethod
    def get_date_range_description(start_date: date, end_date: date) -> str:
        """
        Get a human-readable description of the date range.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            Description string
        """
        days_diff = (end_date - start_date).days + 1
        granularity = EnhancedDateFormatter.get_smart_granularity(start_date, end_date)

        if days_diff == 1:
            return f"Single day: {start_date.strftime('%B %d, %Y')}"
        elif days_diff <= 7:
            return f"{days_diff} days ({granularity} view)"
        elif days_diff <= 30:
            weeks = days_diff // 7
            extra_days = days_diff % 7
            desc = f"{weeks} week{'s' if weeks > 1 else ''}"
            if extra_days > 0:
                desc += f" {extra_days} day{'s' if extra_days > 1 else ''}"
            return f"{desc} ({granularity} view)"
        elif days_diff <= 365:
            months = days_diff // 30
            return f"~{months} month{'s' if months > 1 else ''} ({granularity} view)"
        else:
            years = days_diff // 365
            return f"~{years} year{'s' if years > 1 else ''} ({granularity} view)"


# Global instance for convenience
date_formatter = EnhancedDateFormatter()
