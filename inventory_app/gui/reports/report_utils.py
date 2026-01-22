"""
Report utilities for the inventory management system.
Uses centralized date utilities from inventory_app.utils.date_utils.
"""

from datetime import date, timedelta
from typing import List
from inventory_app.utils.date_utils import (
    format_date_long,
    get_month_name,
    get_day_name,
)


class ReportDateFormatter:
    """Date formatting utilities for reports using centralized date utilities."""

    @staticmethod
    def get_smart_granularity(start_date: date, end_date: date) -> str:
        """
        Determine the optimal reporting granularity based on date range.

        Args:
            start_date: Start date of the period
            end_date: End date of the period

        Returns:
            Granularity level: 'daily', 'weekly', 'monthly', 'yearly', 'multi_year'
        """
        # Use explicit, human-friendly thresholds based on the user's
        # requirement: granularity should switch after more than 2 units of
        # the smaller magnitude. In plain terms:
        # - <= 2 weeks -> daily
        # - > 2 weeks and <= 2 months -> weekly
        # - > 2 months and <= 1 year -> monthly
        # - > 1 year -> yearly
        days_diff = (end_date - start_date).days + 1

        # helper to add months safely
        def _add_months(d: date, months: int) -> date:
            month = d.month - 1 + months
            year = d.year + month // 12
            month = month % 12 + 1
            # clamp day to month's end when necessary
            from inventory_app.utils.date_utils import get_days_in_month

            day = min(d.day, get_days_in_month(year, month))
            return date(year, month, day)

        if days_diff <= 14:
            return "daily"

        # more than 2 weeks -> weekly until (and including) 2 months from start
        if end_date <= _add_months(start_date, 2):
            return "weekly"

        # more than 2 months -> monthly until (and including) 1 year
        if end_date <= _add_months(start_date, 12):
            return "monthly"

        # more than 1 year -> yearly
        return "yearly"

    @staticmethod
    def format_period_header(date_obj: date, granularity: str) -> str:
        """
        Format a date according to the specified granularity using centralized utilities.

        Args:
            date_obj: Date to format
            granularity: Granularity level

        Returns:
            Formatted period header string
        """
        if granularity == "daily":
            # Format: (Mon - Jan 01, 2020)
            day_name = get_day_name(date_obj.weekday())
            month_name = get_month_name(date_obj.month)
            return f"({day_name} - {month_name} {date_obj.day:02d}, {date_obj.year})"
        elif granularity == "weekly":
            # Format: (W1 - Jan/2020) - Month-based weeks
            week_num = ((date_obj.day - 1) // 7) + 1
            month_name = get_month_name(date_obj.month)
            return f"(W{week_num} - {month_name}/{date_obj.year})"
        elif granularity == "monthly":
            # Format: (Jan/2020)
            month_name = get_month_name(date_obj.month)
            return f"({month_name}/{date_obj.year})"
        elif granularity in ["yearly", "multi_year"]:
            # Format: (2020)
            return f"({date_obj.year})"
        else:
            return date_obj.strftime("%Y-%m-%d")

    @staticmethod
    def get_period_keys(
        start_date: date, end_date: date, granularity: str
    ) -> List[str]:
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

        if granularity == "daily":
            # Daily: Just include all individual days
            current_date = start_date
            while current_date <= end_date:
                period_keys.append(current_date.strftime("%Y-%m-%d"))
                current_date += timedelta(days=1)

        elif granularity == "weekly":
            # Weekly: Include excess days + main weeks + excess days
            period_keys.extend(
                ReportDateFormatter._get_weekly_period_keys(start_date, end_date)
            )

        elif granularity == "monthly":
            # Monthly: Include excess days + main months + excess days
            period_keys.extend(
                ReportDateFormatter._get_monthly_period_keys(start_date, end_date)
            )

        elif granularity in ["yearly", "multi_year"]:
            # Yearly: Include partial start/year and full years in the middle and partial end
            # If entirely within one year, return a single partial year range
            if start_date.year == end_date.year:
                period_keys.append(
                    f"{start_date.strftime('%Y-%m-%d')}to{end_date.strftime('%Y-%m-%d')}"
                )
                return period_keys

            # If start is mid-year, add partial start year (start_date -> end_of_year)
            if not (start_date.month == 1 and start_date.day == 1):
                end_of_start_year = date(start_date.year, 12, 31)
                period_keys.append(
                    f"{start_date.strftime('%Y-%m-%d')}to{end_of_start_year.strftime('%Y-%m-%d')}"
                )

            # Add full years
            current_year = start_date.year + (
                0 if start_date.month == 1 and start_date.day == 1 else 1
            )
            while current_year <= end_date.year - 1:
                period_keys.append(str(current_year))
                current_year += 1

            # If end is mid-year, add a partial end-year after the loop
            if not (end_date.month == 12 and end_date.day == 31):
                start_of_end_year = date(end_date.year, 1, 1)
                period_keys.append(
                    f"{start_of_end_year.strftime('%Y-%m-%d')}to{end_date.strftime('%Y-%m-%d')}"
                )

        return period_keys

    @staticmethod
    def _get_weekly_period_keys(start_date: date, end_date: date) -> List[str]:
        """Generate weekly period keys with excess handling."""
        period_keys = []
        # Find the Monday on or before start_date
        first_monday = start_date - timedelta(days=start_date.weekday())

        # If range starts mid-week (not Monday), create a first partial range from start_date to that week's Sunday
        if start_date.weekday() != 0:
            excess_start = start_date
            excess_end = first_monday + timedelta(days=6)
            if excess_start <= excess_end:
                period_keys.append(
                    f"{excess_start.strftime('%Y-%m-%d')}to{excess_end.strftime('%Y-%m-%d')}"
                )
            # Start main weeks from the Monday after that week to avoid duplication
            current_monday = first_monday + timedelta(days=7)
        else:
            current_monday = first_monday
        while current_monday <= end_date:
            week_sunday = current_monday + timedelta(days=6)
            if week_sunday <= end_date:
                # Full week included within the range: add a week label
                week_year = current_monday.year
                week_month = current_monday.month
                # Calculate week number within month
                first_monday_of_month = current_monday.replace(day=1)
                while (
                    first_monday_of_month.weekday() != 0
                ):  # Find first Monday of month
                    first_monday_of_month += timedelta(days=1)
                if first_monday_of_month > current_monday:
                    first_monday_of_month -= timedelta(days=7)  # Go to previous Monday

                week_num = ((current_monday - first_monday_of_month).days // 7) + 1
                period_keys.append(f"{week_year}-{week_month:02d}-W{week_num}")
                current_monday += timedelta(days=7)
                continue

            # If the week spans beyond end_date, add a tail partial and exit
            if current_monday <= end_date:
                period_keys.append(
                    f"{current_monday.strftime('%Y-%m-%d')}to{end_date.strftime('%Y-%m-%d')}"
                )
            break

        # Add excess days after last processed Sunday (if any)
        last_sunday = current_monday - timedelta(days=1)
        if last_sunday < end_date:
            excess_start = last_sunday + timedelta(days=1)
            excess_end = end_date
            if excess_start <= excess_end:
                period_keys.append(
                    f"{excess_start.strftime('%Y-%m-%d')}to{excess_end.strftime('%Y-%m-%d')}"
                )

        return list(dict.fromkeys(period_keys))  # Remove duplicates

    @staticmethod
    def _get_monthly_period_keys(start_date: date, end_date: date) -> List[str]:
        """Generate monthly period keys with excess handling."""
        period_keys = []
        # Edge case: range entirely within one month -> single partial range
        if start_date.year == end_date.year and start_date.month == end_date.month:
            period_keys.append(
                f"{start_date.strftime('%Y-%m-%d')}to{end_date.strftime('%Y-%m-%d')}"
            )
            return period_keys

        # Helper to get first day of next month
        def _first_day_next_month(d: date) -> date:
            if d.month == 12:
                return d.replace(year=d.year + 1, month=1, day=1)
            return d.replace(month=d.month + 1, day=1)

        # If the range starts mid-month, add the first partial (start_date -> end_of_start_month)
        if start_date.day > 1:
            next_month_first = _first_day_next_month(start_date)
            end_of_start_month = next_month_first - timedelta(days=1)
            period_keys.append(
                f"{start_date.strftime('%Y-%m-%d')}to{end_of_start_month.strftime('%Y-%m-%d')}"
            )
            current_month = next_month_first
        else:
            current_month = start_date.replace(day=1)

        # Add full months as long as the entire month fits in the range
        while current_month <= end_date:
            next_month_first = _first_day_next_month(current_month)
            last_day_of_month = next_month_first - timedelta(days=1)

            if last_day_of_month <= end_date:
                period_keys.append(current_month.strftime("%Y-%m"))
                current_month = next_month_first
                continue

            # Tail partial month: from first day of this month to end_date
            if current_month <= end_date:
                period_keys.append(
                    f"{current_month.strftime('%Y-%m-%d')}to{end_date.strftime('%Y-%m-%d')}"
                )
            break

        return list(dict.fromkeys(period_keys))  # Remove duplicates

    @staticmethod
    def get_date_range_description(start_date: date, end_date: date) -> str:
        """
        Get a human-readable description of the date range using centralized utilities.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            Description string
        """
        days_diff = (end_date - start_date).days + 1
        granularity = ReportDateFormatter.get_smart_granularity(start_date, end_date)

        if days_diff == 1:
            return f"Single day: {format_date_long(start_date)}"
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

    @staticmethod
    def get_fixed_weekly_period_keys(start_date: date, end_date: date) -> List[str]:
        """
        Generate fixed weekly period keys (Week 1, Week 2, etc.) for beta test compliance.

        This generates columns like:
        - Week 1 (with date range)
        - Week 2 (with date range)
        - Week 3 (with date range)
        - Week 4 (with date range)
        - Week 5 (if applicable)

        Per beta test requirements, reports should show fixed weekly columns for
        tracking usage by grade levels.

        Args:
            start_date: Start date of the report period
            end_date: End date of the report period

        Returns:
            List of period keys in format ["WEEK1", "WEEK2", "WEEK3", "WEEK4", "WEEK5"]
        """
        period_keys = []
        current_start = start_date
        week_num = 1

        while current_start <= end_date:
            # Each week is 7 days from current start
            week_end = current_start + timedelta(days=6)

            # Cap week_end at the report end_date
            if week_end > end_date:
                week_end = end_date

            # Use simple WEEK1, WEEK2 format for column keys
            period_keys.append(f"WEEK{week_num}")

            # Move to next week
            current_start = week_end + timedelta(days=1)
            week_num += 1

            # Cap at 5 weeks maximum (as per beta test spec: Week 1-4 or 5)
            if week_num > 5:
                break

        return period_keys

    @staticmethod
    def get_fixed_weekly_date_ranges(start_date: date, end_date: date) -> List[tuple]:
        """
        Get the date ranges corresponding to fixed weekly periods.

        Args:
            start_date: Start date of the report period
            end_date: End date of the report period

        Returns:
            List of tuples [(week_key, start_date, end_date), ...]
        """
        ranges = []
        current_start = start_date
        week_num = 1

        while current_start <= end_date:
            week_end = current_start + timedelta(days=6)

            if week_end > end_date:
                week_end = end_date

            ranges.append((f"WEEK{week_num}", current_start, week_end))

            current_start = week_end + timedelta(days=1)
            week_num += 1

            if week_num > 5:
                break

        return ranges


# Global instance for convenience
date_formatter = ReportDateFormatter()
