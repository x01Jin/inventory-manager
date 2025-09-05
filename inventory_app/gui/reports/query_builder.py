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
                                  granularity: str, include_yearly: bool,
                                  grade_filter: str = "",
                                  section_filter: str = "",
                                  include_consumables: bool = True) -> Tuple[str, Tuple]:
        """
        Build the complete dynamic report query.

        Args:
            start_date: Report start date
            end_date: Report end date
            granularity: Time granularity ('daily', 'weekly', 'monthly', etc.)
            include_yearly: Whether to include yearly acquisitions column
            grade_filter: Grade level filter
            section_filter: Section filter
            include_consumables: Whether to include consumable items

        Returns:
            Tuple of (SQL query string, parameters tuple)
        """
        try:
            # Build base query
            base_query, base_params = self._build_base_query(grade_filter, section_filter, include_consumables)

            # Add dynamic period calculation
            period_query = self._build_period_query(granularity, start_date, end_date)

            # Build main query with dynamic columns
            main_query = self._build_main_query(include_yearly)

            # Combine all parts
            full_query = base_query + period_query + main_query

            # Build parameters - date params first, then filter params
            date_params = [start_date.isoformat(), end_date.isoformat()]
            if include_yearly:
                date_params.extend([start_date.isoformat(), end_date.isoformat()])

            params = tuple(date_params + base_params)

            return full_query, params

        except Exception as e:
            logger.error(f"Failed to build dynamic report query: {e}")
            raise

    def _build_base_query(self, grade_filter: str, section_filter: str, include_consumables: bool) -> Tuple[str, List]:
        """Build the base CTE query with filters."""
        base_query = """
        WITH base AS (
          SELECT
            i.id AS item_id,
            i.name AS item_name,
            c.name AS category_name,
            i.size,
            i.brand,
            i.other_specifications,
            SUM(ri.quantity_requested) AS qty,
            r.datetime_requested
          FROM Requisition_Items ri
          JOIN Requisitions r ON r.id = ri.requisition_id
          JOIN Items i ON i.id = ri.item_id
          JOIN Categories c ON c.id = i.category_id
          JOIN Requesters req ON req.id = r.requester_id
          WHERE r.datetime_requested BETWEEN ? AND ?
        """

        # Start with base parameters (date range will be added later)
        params = []

        # Add filters
        if grade_filter:
            base_query += " AND req.affiliation = ?"
            params.append(grade_filter)
        if section_filter:
            base_query += " AND req.group_name = ?"
            params.append(section_filter)
        if not include_consumables:
            base_query += " AND i.is_consumable = 0"

        base_query += " GROUP BY i.id, r.datetime_requested)"
        return base_query, params

    def _build_period_query(self, granularity: str, start_date: Optional[date] = None, end_date: Optional[date] = None) -> str:
        """Build the period calculation CTE with simplified weekly handling."""
        period_queries = {
            'daily': """
                ,dynamic_periods AS (
                  SELECT *, strftime('%Y-%m-%d', datetime_requested) AS period_key FROM base
                )
            """,
            'weekly': """
                ,dynamic_periods AS (
                  SELECT
                    *,
                    strftime('%Y-%m', datetime_requested) || '-W' ||
                    CAST(((strftime('%d', datetime_requested) - 1) / 7) + 1 AS TEXT) AS period_key
                  FROM base
                )
            """,
            'monthly': """
                ,dynamic_periods AS (
                  SELECT *, strftime('%Y-%m', datetime_requested) AS period_key FROM base
                )
            """,
            'quarterly': """
                ,dynamic_periods AS (
                  SELECT
                    *,
                    strftime('%Y', datetime_requested) || '-Q' ||
                    CAST(((CAST(strftime('%m', datetime_requested) AS INTEGER) - 1) / 3) + 1 AS TEXT) AS period_key
                  FROM base
                )
            """,
            'yearly': """
                ,dynamic_periods AS (
                  SELECT *, strftime('%Y', datetime_requested) AS period_key FROM base
                )
            """,
            'multi_year': """
                ,dynamic_periods AS (
                  SELECT *, strftime('%Y', datetime_requested) AS period_key FROM base
                )
            """
        }

        return period_queries.get(granularity, period_queries['monthly'])

    def _build_main_query(self, include_yearly: bool) -> str:
        """Build the main SELECT query with dynamic columns."""
        # Start with fixed columns
        query_parts = ["SELECT", ",\n".join(self.base_columns)]

        # Add placeholder for dynamic period columns (will be replaced)
        query_parts.append("{period_columns}")

        # Add yearly acquisitions if needed
        if include_yearly:
            query_parts.append("""
                ,(SELECT COALESCE(SUM(quantity_received), 0)
                 FROM Item_Batches b
                 WHERE b.item_id = dp.item_id
                 AND strftime('%Y', b.date_received) >= strftime('%Y', ?)
                 AND strftime('%Y', b.date_received) <= strftime('%Y', ?)) AS "YEARLY ACQUISITIONS"
            """)

        # Add total quantity and FROM clause
        query_parts.append(',SUM(qty) AS "TOTAL QUANTITY"')
        query_parts.extend([
            'FROM dynamic_periods dp',
            'GROUP BY item_id',
            'ORDER BY category_name, item_name'
        ])

        return "\n".join(query_parts)



    def build_dynamic_columns(self, period_keys: List[str]) -> str:
        """Build dynamic period columns for the query."""
        if not period_keys:
            return ""

        column_parts = []
        for period_key in period_keys:
            # Escape single quotes in period_key for SQL
            escaped_key = period_key.replace("'", "''")
            column_parts.append(f'SUM(CASE WHEN period_key = \'{escaped_key}\' THEN qty ELSE 0 END) AS "{escaped_key}"')

        # Add leading comma for the first column
        return ",\n".join([""] + column_parts)

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
