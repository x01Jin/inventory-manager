"""
SQL Query Builder for report generation.
Extracts complex SQL construction logic into a dedicated, testable class.
"""

from typing import List, Tuple, Dict, Any
from datetime import date
from inventory_app.database.connection import db
from inventory_app.utils.logger import logger
from inventory_app.gui.reports.report_utils import date_formatter
from inventory_app.gui.reports.columns import report_base_columns_sql


class ReportQueryBuilder:
    """Builds SQL queries for dynamic report generation."""

    def __init__(self):
        """Initialize query builder."""
        # Maximum number of period columns before falling back to normalized query
        self.MAX_PERIOD_COLUMNS = 60
        # Reset after building each query; indicates if build used normalized fallback
        self.normalized_fallback = False

    def build_dynamic_report_query(
        self,
        start_date: date,
        end_date: date,
        granularity: str,
        category_filter: str = "",
        supplier_filter: str = "",
        include_consumables: bool = True,
        show_individual_only: bool = False,
    ) -> Tuple[str, Tuple]:
        """
        Build the complete dynamic report query.
        OPTIMIZED: Pre-compute period ranges and use indexed columns.

        Args:
            start_date: Report start date
            end_date: Report end date
            granularity: Time granularity ('daily', 'weekly', 'monthly', etc.)
            category_filter: Category filter
            supplier_filter: Supplier filter
            include_consumables: Whether to include consumable items
            show_individual_only: Whether to show only individual requests

        Returns:
            Tuple of (SQL query string, parameters tuple)
        """
        try:
            # Use optimized single query approach instead of CTEs
            query, params = self._build_optimized_report_query(
                start_date,
                end_date,
                granularity,
                category_filter,
                supplier_filter,
                include_consumables,
                show_individual_only,
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
        category_filter: str,
        supplier_filter: str,
        include_consumables: bool,
        show_individual_only: bool = False,
    ) -> Tuple[str, list]:
        """Build optimized single query without CTEs for better performance."""
        try:
            # Reset fallback mode for each query
            self.normalized_fallback = False
            # Base query with direct JOINs instead of CTEs
            query = (
                """
            SELECT
                """
                + report_base_columns_sql()
                + """
            """
            )

            # Add dynamic period columns (now returns SQL, params, flag, and optional CTE SQL)
            period_columns_sql, period_params, is_normalized, periods_cte = (
                self._build_optimized_period_columns(start_date, end_date, granularity)
            )
            if is_normalized:
                # Prepend CTE for normalized periods
                if periods_cte:
                    query = periods_cte + "\n" + query
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
            # If normalized, CROSS JOIN the periods CTE so each item/period row is produced
            if is_normalized:
                query += "\nCROSS JOIN periods p\n"

            # WHERE clause with filters. Use half-open range to avoid string
            # comparison issues when dates are stored as ISO date strings.
            # NOTE: Usage counting is based on lab_activity_date (when materials
            # are actually used) per beta test requirements, NOT expected_request.
            query += """
            WHERE r.lab_activity_date >= ? AND r.lab_activity_date < ?
            """

            if supplier_filter:
                query += " AND req.department = ?"
            if not include_consumables:
                query += " AND i.is_consumable = 0"
            if show_individual_only:
                query += " AND r.is_individual = 1"

            # GROUP BY clause
            group_by_columns = (
                "i.id, i.name, c.name, i.size, i.brand, i.other_specifications"
            )
            if is_normalized:
                group_by_columns += ", p.period_key"

            query += f"\nGROUP BY {group_by_columns}\nORDER BY c.name, i.name\n"

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
                # Extract ISO strings from the period param pairs or triples
                if is_normalized:
                    # params are [key, start, end, key, start, end, ...]
                    period_starts = [
                        period_params[i] for i in range(1, len(period_params), 3)
                    ]
                    period_ends = [
                        period_params[i] for i in range(2, len(period_params), 3)
                    ]
                else:
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
            if category_filter:
                params.append(category_filter)
            if supplier_filter:
                params.append(supplier_filter)

            return query, params

        except Exception as e:
            logger.error(f"Failed to build optimized report query: {e}")
            raise

    def _build_optimized_period_columns(
        self, start_date: date, end_date: date, granularity: str
    ) -> Tuple[str, list, bool, str]:
        """Build optimized period columns using correct logic from report_utils."""
        try:
            # Use the correct period generation from report_utils
            period_keys = date_formatter.get_period_keys(
                start_date, end_date, granularity
            )

            if not period_keys:
                return "", [], False, ""

            # If period count is too large, fall back to a normalized query
            # that returns rows for (item, period_key, value) instead of
            # producing wide pivot columns.
            if len(period_keys) > self.MAX_PERIOD_COLUMNS:
                self.normalized_fallback = True
                # Build a CTE with period values: (period_key, start, end)
                values_sql = ", ".join(["(?, ?, ?)" for _ in period_keys])
                cte_sql = (
                    f"WITH periods(period_key, start, end) AS (VALUES {values_sql})"
                )
                # Select p.period_key as PERIOD and a parameterized CASE that
                # aggregates values for each period via CROSS JOIN
                # Instead of returning a full SELECT snippet here, we provide
                # the normalized SELECT fragment for use in the caller.
                normalized_select = (
                    'p.period_key AS "PERIOD", '
                    "SUM(CASE WHEN r.lab_activity_date >= p.start "
                    "AND r.lab_activity_date < p.end THEN ri.quantity_requested ELSE 0 END) "
                    'AS "PERIOD_QUANTITY"'
                )

                params: list = []
                for k in period_keys:
                    # Validate and build param tuple (key, start, end)
                    import re

                    if not re.match(r"^[0-9A-Za-z\-]+(?:to[0-9A-Za-z\-]+)?$", k):
                        logger.warning(f"Skipping invalid period key: {k}")
                        continue
                    # compute start/end for the period
                    pstart, pend = self._parse_period_key_to_dates(
                        k, start_date, end_date, granularity
                    )
                    params.extend([k, pstart, pend])

                return normalized_select, params, True, cte_sql

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
                # NOTE: Usage counting based on lab_activity_date per beta test requirements
                safe_alias = period_key.replace('"', '""')
                column_parts.append(
                    "SUM(CASE WHEN r.lab_activity_date >= ? AND r.lab_activity_date < ? "
                    'THEN ri.quantity_requested ELSE 0 END) AS "{}"'.format(safe_alias)
                )
                params.extend([period_start, period_end])

            return ",".join(column_parts), params, False, ""

        except Exception as e:
            logger.error(f"Failed to build optimized period columns: {e}")
            return "", [], False, ""

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
                # Year: handle both full-year labels and partial ranges
                if "to" in period_key:
                    start_str, end_str = period_key.split("to")
                    start_date = date.fromisoformat(start_str)
                    end_date = date.fromisoformat(end_str)
                    return start_date.isoformat(), (
                        end_date + timedelta(days=1)
                    ).isoformat()

                # Full year: '2023'
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
        category_filter: str,
        supplier_filter: str,
        include_consumables: bool,
    ) -> Tuple:
        """Build optimized parameter list for the report query."""
        params: List[Any] = []

        # This method is retained for compatibility but callers now build params
        if category_filter:
            params.append(category_filter)
        if supplier_filter:
            params.append(supplier_filter)

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
        category_filter: str = "",
        supplier_filter: str = "",
    ) -> Tuple[str, Tuple]:
        """Build query to get usage statistics based on lab activity date."""
        # Total items used - counted by lab_activity_date (when materials are used)
        total_query = """
        SELECT SUM(ri.quantity_requested) as total_used
        FROM Requisition_Items ri
        JOIN Requisitions r ON r.id = ri.requisition_id
        JOIN Requesters req ON req.id = r.requester_id
        WHERE r.lab_activity_date BETWEEN ? AND ?
        """

        params: List[Any] = [start_date.isoformat(), end_date.isoformat()]

        # Add filters
        if supplier_filter:
            total_query += " AND req.department = ?"
            params.append(supplier_filter)

        return total_query, tuple(params)

    @staticmethod
    def build_category_statistics_query(
        start_date: date,
        end_date: date,
        category_filter: str = "",
        supplier_filter: str = "",
    ) -> Tuple[str, Tuple]:
        """Build query to get category statistics based on lab activity date."""
        category_query = """
        SELECT c.name as category, SUM(ri.quantity_requested) as qty
        FROM Requisition_Items ri
        JOIN Requisitions r ON r.id = ri.requisition_id
        JOIN Items i ON i.id = ri.item_id
        JOIN Categories c ON c.id = i.category_id
        JOIN Requesters req ON req.id = r.requester_id
        WHERE r.lab_activity_date BETWEEN ? AND ?
        """

        params: List[Any] = [start_date.isoformat(), end_date.isoformat()]

        # Add filters
        if supplier_filter:
            category_query += " AND req.department = ?"
            params.append(supplier_filter)

        category_query += " GROUP BY c.id, c.name ORDER BY qty DESC"

        return category_query, tuple(params)

    @staticmethod
    def build_top_items_query(
        start_date: date,
        end_date: date,
        category_filter: str = "",
        supplier_filter: str = "",
        limit: int = 10,
    ) -> Tuple[str, Tuple]:
        """Build query to get top used items based on lab activity date."""
        top_items_query = """
        SELECT i.name as item_name, SUM(ri.quantity_requested) as qty
        FROM Requisition_Items ri
        JOIN Requisitions r ON r.id = ri.requisition_id
        JOIN Items i ON i.id = ri.item_id
        JOIN Requesters req ON req.id = r.requester_id
        WHERE r.lab_activity_date BETWEEN ? AND ?
        """

        params: List[Any] = [start_date.isoformat(), end_date.isoformat()]

        # Add filters
        if supplier_filter:
            top_items_query += " AND req.department = ?"
            params.append(supplier_filter)

        top_items_query += " GROUP BY i.id, i.name ORDER BY qty DESC LIMIT ?"
        params.append(limit)

        return top_items_query, tuple(params)
