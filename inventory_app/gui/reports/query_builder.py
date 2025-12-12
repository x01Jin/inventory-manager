"""
SQL Query Builder for report generation.
Extracts complex SQL construction logic into a dedicated, testable class.
"""

from typing import List, Tuple, Dict, Any
from datetime import date
from inventory_app.database.connection import db
from inventory_app.utils.logger import logger
from inventory_app.gui.reports.report_utils import date_formatter


class ReportQueryBuilder:
    """Builds SQL queries for dynamic report generation."""

    def __init__(self):
        """Initialize query builder."""
        self.base_columns = [
            "item_name AS ITEMS",
            "category_name AS CATEGORIES",
            "(SELECT COALESCE(SUM(quantity_received), 0) FROM Item_Batches b WHERE b.item_id = dp.item_id) AS ACTUAL_INVENTORY",
            "size AS SIZE",
            "brand AS BRAND",
            'other_specifications AS "OTHER SPECIFICATIONS"',
        ]

    def build_dynamic_report_query(
        self,
        start_date: date,
        end_date: date,
        granularity: str,
        grade_filter: str = "",
        section_filter: str = "",
        include_consumables: bool = True,
    ) -> Tuple[str, Tuple]:
        """
        Build the complete dynamic report query.
        OPTIMIZED: Pre-compute period ranges and use indexed columns.

        Args:
            start_date: Report start date
            end_date: Report end date
            granularity: Time granularity ('daily', 'weekly', 'monthly', etc.)
            grade_filter: Grade level filter
            section_filter: Section filter
            include_consumables: Whether to include consumable items

        Returns:
            Tuple of (SQL query string, parameters tuple)
        """
        try:
            # Use optimized single query approach instead of CTEs
            query, params = self._build_optimized_report_query(
                start_date,
                end_date,
                granularity,
                grade_filter,
                section_filter,
                include_consumables,
            )

            return query, tuple(params)

        except Exception as e:
            logger.error(f"Failed to build dynamic report query: {e}")
            raise

    def _build_optimized_report_query(
        self,
        start_date: date,
        end_date: date,
        granularity: str,
        grade_filter: str,
        section_filter: str,
        include_consumables: bool,
    ) -> Tuple[str, list]:
        """Build optimized single query without CTEs for better performance."""
        try:
            # Base query with direct JOINs instead of CTEs
            query = """
            SELECT
                i.name AS ITEMS,
                c.name AS CATEGORIES,
                COALESCE(stock.total_stock, 0) AS ACTUAL_INVENTORY,
                i.size AS SIZE,
                i.brand AS BRAND,
                i.other_specifications AS "OTHER SPECIFICATIONS"
            """

            # Add dynamic period columns (now returns SQL and params)
            period_columns_sql, period_params = self._build_optimized_period_columns(
                start_date, end_date, granularity
            )
            if period_columns_sql:
                query += "," + period_columns_sql

            # Add TOTAL QUANTITY as the last column
            query += """,
                SUM(ri.quantity_requested) AS "TOTAL QUANTITY"
            """

            # FROM clause with optimized JOINs
            query += """
            FROM Requisition_Items ri
            JOIN Requisitions r ON r.id = ri.requisition_id
            JOIN Items i ON i.id = ri.item_id
            JOIN Categories c ON c.id = i.category_id
            JOIN Requesters req ON req.id = r.requester_id
            LEFT JOIN (
                SELECT
                    ib.item_id,
                    SUM(ib.quantity_received) as total_stock
                FROM Item_Batches ib
                GROUP BY ib.item_id
            ) stock ON i.id = stock.item_id
            """

            # WHERE clause with filters. Use half-open range to avoid string
            # comparison issues when datetimes are stored as ISO timestamps.
            query += """
            WHERE r.expected_request >= ? AND r.expected_request < ?
            """

            if grade_filter:
                query += " AND req.affiliation = ?"
            if section_filter:
                query += " AND req.group_name = ?"
            if not include_consumables:
                query += " AND i.is_consumable = 0"

            # GROUP BY clause
            query += """
            GROUP BY i.id, i.name, c.name, i.size, i.brand, i.other_specifications
            ORDER BY c.name, i.name
            """

            # Build params in stable order: period ranges, global date bounds, then filters
            # This ordering matches placeholders in the SQL where period scoped
            # columns come before the WHERE clause parameters.
            params: List[Any] = []
            params.extend(period_params)

            # Convert global date bounds to half-open range. When period ranges exist,
            # pick the min start and max end across generated period params to ensure
            # the global WHERE covers all period columns (including excess ranges).
            from datetime import timedelta

            if period_params:
                # Extract ISO strings from the period param pairs
                period_starts = [
                    period_params[i] for i in range(0, len(period_params), 2)
                ]
                period_ends = [
                    period_params[i] for i in range(1, len(period_params), 2)
                ]
                params.append(min(period_starts))
                params.append(max(period_ends))
            else:
                params.append(start_date.isoformat())
                params.append((end_date + timedelta(days=1)).isoformat())
            if grade_filter:
                params.append(grade_filter)
            if section_filter:
                params.append(section_filter)

            return query, params

        except Exception as e:
            logger.error(f"Failed to build optimized report query: {e}")
            raise

    def _build_optimized_period_columns(
        self, start_date: date, end_date: date, granularity: str
    ) -> Tuple[str, list]:
        """Build optimized period columns using correct logic from report_utils."""
        try:
            # Use the correct period generation from report_utils
            period_keys = date_formatter.get_period_keys(
                start_date, end_date, granularity
            )

            if not period_keys:
                return "", []

            column_parts = []
            params: list = []
            for period_key in period_keys:
                # Parse period key to get start and end dates
                period_start, period_end = self._parse_period_key_to_dates(
                    period_key, start_date, end_date, granularity
                )

                # Validate period_key to avoid injection via column alias
                import re

                if not re.match(r"^[0-9A-Za-z\-]+(?:to[0-9A-Za-z\-]+)?$", period_key):
                    logger.warning(f"Skipping invalid period key: {period_key}")
                    continue

                # Use parameter placeholders for dates; alias is quoted and validated
                safe_alias = period_key.replace('"', '""')
                column_parts.append(
                    "SUM(CASE WHEN r.expected_request >= ? AND r.expected_request < ? "
                    'THEN ri.quantity_requested ELSE 0 END) AS "{}"'.format(safe_alias)
                )
                params.extend([period_start, period_end])

            return ",".join(column_parts), params

        except Exception as e:
            logger.error(f"Failed to build optimized period columns: {e}")
            return "", []

    def _parse_period_key_to_dates(
        self, period_key: str, report_start: date, report_end: date, granularity: str
    ) -> Tuple[str, str]:
        """Parse a period key and return the corresponding start and end dates for SQL queries."""
        from datetime import timedelta

        try:
            if granularity == "daily":
                # Format: '2023-01-01'
                period_date = date.fromisoformat(period_key)
                next_date = period_date + timedelta(days=1)
                return period_date.isoformat(), next_date.isoformat()

            elif granularity == "weekly":
                if "to" in period_key:
                    # Excess period: '2023-01-01to2023-01-03'
                    start_str, end_str = period_key.split("to")
                    start_date = date.fromisoformat(start_str)
                    end_date = date.fromisoformat(end_str)
                    return start_date.isoformat(), (
                        end_date + timedelta(days=1)
                    ).isoformat()
                else:
                    # Main week: '2023-01-W1'
                    year_str, month_str, week_part = period_key.split("-")
                    year, month = int(year_str), int(month_str)
                    week_num = int(week_part.replace("W", ""))

                    # Find the Monday of the specified week
                    first_day_of_month = date(year, month, 1)
                    # Find first Monday of the month
                    days_to_first_monday = (7 - first_day_of_month.weekday()) % 7
                    first_monday = first_day_of_month + timedelta(
                        days=days_to_first_monday
                    )

                    # Calculate the Monday of the target week
                    week_monday = first_monday + timedelta(days=(week_num - 1) * 7)
                    week_sunday = week_monday + timedelta(days=6)

                    return week_monday.isoformat(), (
                        week_sunday + timedelta(days=1)
                    ).isoformat()

            elif granularity == "monthly":
                if "to" in period_key:
                    # Excess period: '2023-01-01to2023-01-15'
                    start_str, end_str = period_key.split("to")
                    start_date = date.fromisoformat(start_str)
                    end_date = date.fromisoformat(end_str)
                    return start_date.isoformat(), (
                        end_date + timedelta(days=1)
                    ).isoformat()
                else:
                    # Main month: '2023-01'
                    year_str, month_str = period_key.split("-")
                    year, month = int(year_str), int(month_str)
                    month_start = date(year, month, 1)
                    if month == 12:
                        month_end = date(year + 1, 1, 1)
                    else:
                        month_end = date(year, month + 1, 1)
                    return month_start.isoformat(), month_end.isoformat()

            elif granularity == "quarterly":
                if "to" in period_key:
                    # Excess period: '2023-01-01to2023-03-15'
                    start_str, end_str = period_key.split("to")
                    start_date = date.fromisoformat(start_str)
                    end_date = date.fromisoformat(end_str)
                    return start_date.isoformat(), (
                        end_date + timedelta(days=1)
                    ).isoformat()
                else:
                    # Main quarter: '2023-Q1'
                    year_str, quarter_str = period_key.split("-Q")
                    year, quarter = int(year_str), int(quarter_str)
                    quarter_start_month = (quarter - 1) * 3 + 1
                    quarter_start = date(year, quarter_start_month, 1)
                    quarter_end_month = quarter * 3 + 1
                    if quarter_end_month > 12:
                        quarter_end = date(year + 1, 1, 1)
                    else:
                        quarter_end = date(year, quarter_end_month, 1)
                    return quarter_start.isoformat(), quarter_end.isoformat()

            elif granularity in ["yearly", "multi_year"]:
                # Year: '2023'
                year = int(period_key)
                year_start = date(year, 1, 1)
                year_end = date(year + 1, 1, 1)
                return year_start.isoformat(), year_end.isoformat()

            else:
                # Default fallback
                return report_start.isoformat(), report_end.isoformat()

        except Exception as e:
            logger.error(f"Failed to parse period key '{period_key}': {e}")
            return report_start.isoformat(), report_end.isoformat()

    def _build_report_params(
        self,
        start_date: date,
        end_date: date,
        granularity: str,
        grade_filter: str,
        section_filter: str,
        include_consumables: bool,
    ) -> Tuple:
        """Build optimized parameter list for the report query."""
        params: List[Any] = []

        # This method is retained for compatibility but callers now build params
        if grade_filter:
            params.append(grade_filter)
        if section_filter:
            params.append(section_filter)

        return tuple(params)

    def execute_report_query(self, query: str, params: Tuple) -> List[Dict[str, Any]]:
        """Execute the report query and return results."""
        try:
            return db.execute_query(query, params) or []
        except Exception as e:
            logger.error(f"Failed to execute report query: {e}")
            return []


class ReportStatisticsBuilder:
    """Builds queries for report statistics and summaries."""

    @staticmethod
    def build_usage_statistics_query(
        start_date: date,
        end_date: date,
        grade_filter: str = "",
        section_filter: str = "",
    ) -> Tuple[str, Tuple]:
        """Build query to get usage statistics."""
        # Total items used
        total_query = """
        SELECT SUM(ri.quantity_requested) as total_used
        FROM Requisition_Items ri
        JOIN Requisitions r ON r.id = ri.requisition_id
        JOIN Requesters req ON req.id = r.requester_id
        WHERE r.expected_request BETWEEN ? AND ?
        """

        params: List[Any] = [start_date.isoformat(), end_date.isoformat()]

        # Add filters
        if grade_filter:
            total_query += " AND req.affiliation = ?"
            params.append(grade_filter)
        if section_filter:
            total_query += " AND req.group_name = ?"
            params.append(section_filter)

        return total_query, tuple(params)

    @staticmethod
    def build_category_statistics_query(
        start_date: date,
        end_date: date,
        grade_filter: str = "",
        section_filter: str = "",
    ) -> Tuple[str, Tuple]:
        """Build query to get category statistics."""
        category_query = """
        SELECT c.name as category, SUM(ri.quantity_requested) as qty
        FROM Requisition_Items ri
        JOIN Requisitions r ON r.id = ri.requisition_id
        JOIN Items i ON i.id = ri.item_id
        JOIN Categories c ON c.id = i.category_id
        JOIN Requesters req ON req.id = r.requester_id
        WHERE r.expected_request BETWEEN ? AND ?
        """

        params: List[Any] = [start_date.isoformat(), end_date.isoformat()]

        # Add filters
        if grade_filter:
            category_query += " AND req.affiliation = ?"
            params.append(grade_filter)
        if section_filter:
            category_query += " AND req.group_name = ?"
            params.append(section_filter)

        category_query += " GROUP BY c.id, c.name ORDER BY qty DESC"

        return category_query, tuple(params)

    @staticmethod
    def build_top_items_query(
        start_date: date,
        end_date: date,
        grade_filter: str = "",
        section_filter: str = "",
        limit: int = 10,
    ) -> Tuple[str, Tuple]:
        """Build query to get top used items."""
        top_items_query = """
        SELECT i.name as item_name, SUM(ri.quantity_requested) as qty
        FROM Requisition_Items ri
        JOIN Requisitions r ON r.id = ri.requisition_id
        JOIN Items i ON i.id = ri.item_id
        JOIN Requesters req ON req.id = r.requester_id
        WHERE r.expected_request BETWEEN ? AND ?
        """

        params: List[Any] = [start_date.isoformat(), end_date.isoformat()]

        # Add filters
        if grade_filter:
            top_items_query += " AND req.affiliation = ?"
            params.append(grade_filter)
        if section_filter:
            top_items_query += " AND req.group_name = ?"
            params.append(section_filter)

        top_items_query += " GROUP BY i.id, i.name ORDER BY qty DESC LIMIT ?"
        params.append(limit)

        return top_items_query, tuple(params)
