"""
SQL Query Builder for report generation.
Extracts complex SQL construction logic into a dedicated, testable class.
"""

from typing import List, Tuple, Dict, Any, Optional
from datetime import date
from inventory_app.database.connection import db
from inventory_app.utils.logger import logger


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
            "other_specifications AS \"OTHER SPECIFICATIONS\""
        ]

    def build_dynamic_report_query(self, start_date: date, end_date: date,
                                  granularity: str,
                                  grade_filter: str = "",
                                  section_filter: str = "",
                                  include_consumables: bool = True) -> Tuple[str, Tuple]:
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
            query = self._build_optimized_report_query(
                start_date, end_date, granularity,
                grade_filter, section_filter, include_consumables
            )

            # Build parameters
            params = self._build_report_params(
                start_date, end_date, granularity,
                grade_filter, section_filter, include_consumables
            )

            return query, params

        except Exception as e:
            logger.error(f"Failed to build dynamic report query: {e}")
            raise

    def _build_optimized_report_query(self, start_date: date, end_date: date,
                                     granularity: str,
                                     grade_filter: str, section_filter: str,
                                     include_consumables: bool) -> str:
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

            # Add dynamic period columns
            period_columns = self._build_optimized_period_columns(start_date, end_date, granularity)
            if period_columns:
                query += "," + period_columns

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

            # WHERE clause with filters
            query += f"""
            WHERE r.datetime_requested BETWEEN '{start_date.isoformat()}' AND '{end_date.isoformat()}'
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

            return query

        except Exception as e:
            logger.error(f"Failed to build optimized report query: {e}")
            raise

    def _build_optimized_period_columns(self, start_date: date, end_date: date, granularity: str) -> str:
        """Build optimized period columns using pre-computed ranges."""
        try:
            # Pre-compute period ranges for better performance
            period_ranges = self._get_period_ranges(start_date, end_date, granularity)

            if not period_ranges:
                return ""

            column_parts = []
            for period_key, (period_start, period_end) in period_ranges.items():
                escaped_key = period_key.replace("'", "''")
                column_parts.append(f"""
                SUM(CASE WHEN r.datetime_requested >= '{period_start}' AND r.datetime_requested < '{period_end}'
                    THEN ri.quantity_requested ELSE 0 END) AS "{escaped_key}" """)

            return ",".join(column_parts)

        except Exception as e:
            logger.error(f"Failed to build optimized period columns: {e}")
            return ""

    def _get_period_ranges(self, start_date: date, end_date: date, granularity: str) -> Dict[str, Tuple[str, str]]:
        """Pre-compute period ranges for the given granularity."""
        from datetime import timedelta

        ranges = {}
        current = start_date

        while current <= end_date:
            if granularity == 'daily':
                period_key = current.isoformat()
                next_date = current + timedelta(days=1)
                ranges[period_key] = (current.isoformat(), next_date.isoformat())
                current = next_date

            elif granularity == 'weekly':
                # Calculate week start (Monday)
                week_start = current - timedelta(days=current.weekday())
                week_end = week_start + timedelta(days=7)
                week_num = (week_start.day - 1) // 7 + 1
                period_key = f"{week_start.year}-{week_start.month:02d}-W{week_num}"
                ranges[period_key] = (week_start.isoformat(), week_end.isoformat())
                current = week_end

            elif granularity == 'monthly':
                period_key = f"{current.year}-{current.month:02d}"
                if current.month == 12:
                    next_date = date(current.year + 1, 1, 1)
                else:
                    next_date = date(current.year, current.month + 1, 1)
                ranges[period_key] = (current.isoformat(), next_date.isoformat())
                current = next_date

            elif granularity == 'quarterly':
                # Calculate quarter start
                quarter = ((current.month - 1) // 3) + 1
                period_key = f"{current.year}-Q{quarter}"

                # Calculate next quarter start
                next_quarter_month = ((quarter) * 3) + 1
                if next_quarter_month > 12:
                    next_date = date(current.year + 1, 1, 1)
                else:
                    next_date = date(current.year, next_quarter_month, 1)

                ranges[period_key] = (current.isoformat(), next_date.isoformat())
                current = next_date

            elif granularity in ['yearly', 'multi_year']:
                period_key = str(current.year)
                next_date = date(current.year + 1, 1, 1)
                ranges[period_key] = (current.isoformat(), next_date.isoformat())
                current = next_date

            else:
                # Default to monthly
                period_key = f"{current.year}-{current.month:02d}"
                if current.month == 12:
                    next_date = date(current.year + 1, 1, 1)
                else:
                    next_date = date(current.year, current.month + 1, 1)
                ranges[period_key] = (current.isoformat(), next_date.isoformat())
                current = next_date

        return ranges

    def _build_report_params(self, start_date: date, end_date: date, granularity: str,
                           grade_filter: str, section_filter: str,
                           include_consumables: bool) -> Tuple:
        """Build optimized parameter list for the report query."""
        params = []

        # Add filter parameters
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
    def build_usage_statistics_query(start_date: date, end_date: date,
                                   grade_filter: str = "",
                                   section_filter: str = "") -> Tuple[str, Tuple]:
        """Build query to get usage statistics."""
        # Total items used
        total_query = """
        SELECT SUM(ri.quantity_requested) as total_used
        FROM Requisition_Items ri
        JOIN Requisitions r ON r.id = ri.requisition_id
        JOIN Requesters req ON req.id = r.requester_id
        WHERE r.datetime_requested BETWEEN ? AND ?
        """

        params = [start_date.isoformat(), end_date.isoformat()]

        # Add filters
        if grade_filter:
            total_query += " AND req.affiliation = ?"
            params.append(grade_filter)
        if section_filter:
            total_query += " AND req.group_name = ?"
            params.append(section_filter)

        return total_query, tuple(params)

    @staticmethod
    def build_category_statistics_query(start_date: date, end_date: date,
                                      grade_filter: str = "",
                                      section_filter: str = "") -> Tuple[str, Tuple]:
        """Build query to get category statistics."""
        category_query = """
        SELECT c.name as category, SUM(ri.quantity_requested) as qty
        FROM Requisition_Items ri
        JOIN Requisitions r ON r.id = ri.requisition_id
        JOIN Items i ON i.id = ri.item_id
        JOIN Categories c ON c.id = i.category_id
        JOIN Requesters req ON req.id = r.requester_id
        WHERE r.datetime_requested BETWEEN ? AND ?
        """

        params = [start_date.isoformat(), end_date.isoformat()]

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
    def build_top_items_query(start_date: date, end_date: date,
                            grade_filter: str = "",
                            section_filter: str = "",
                            limit: int = 10) -> Tuple[str, Tuple]:
        """Build query to get top used items."""
        top_items_query = """
        SELECT i.name as item_name, SUM(ri.quantity_requested) as qty
        FROM Requisition_Items ri
        JOIN Requisitions r ON r.id = ri.requisition_id
        JOIN Items i ON i.id = ri.item_id
        JOIN Requesters req ON req.id = r.requester_id
        WHERE r.datetime_requested BETWEEN ? AND ?
        """

        params = [start_date.isoformat(), end_date.isoformat()]

        # Add filters
        if grade_filter:
            top_items_query += " AND req.affiliation = ?"
            params.append(grade_filter)
        if section_filter:
            top_items_query += " AND req.group_name = ?"
            params.append(section_filter)

        top_items_query += f" GROUP BY i.id, i.name ORDER BY qty DESC LIMIT {limit}"

        return top_items_query, tuple(params)
