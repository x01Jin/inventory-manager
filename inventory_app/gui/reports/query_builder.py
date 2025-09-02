"""
SQL Query Builder for report generation.
Extracts complex SQL construction logic into a dedicated, testable class.
"""

from typing import List, Tuple, Dict, Any, Optional
from datetime import date, timedelta
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
            SUM(ri.quantity_borrowed) AS qty,
            r.date_borrowed
          FROM Requisition_Items ri
          JOIN Requisitions r ON r.id = ri.requisition_id
          JOIN Items i ON i.id = ri.item_id
          JOIN Categories c ON c.id = i.category_id
          WHERE r.date_borrowed BETWEEN ? AND ?
        """

        # Start with base parameters (date range will be added later)
        params = []

        # Add filters
        if grade_filter:
            base_query += " AND r.borrower_id IN (SELECT id FROM Borrowers WHERE affiliation = ?)"
            params.append(grade_filter)
        if section_filter:
            base_query += " AND r.borrower_id IN (SELECT id FROM Borrowers WHERE group_name = ?)"
            params.append(section_filter)
        if not include_consumables:
            base_query += " AND i.is_consumable = 0"

        base_query += " GROUP BY i.id, r.date_borrowed)"
        return base_query, params

    def _build_period_query(self, granularity: str, start_date: Optional[date] = None, end_date: Optional[date] = None) -> str:
        """Build the period calculation CTE with comprehensive excess period handling."""
        if granularity == 'weekly' and start_date and end_date:
            # For weekly, generate date range mappings based on Python logic
            period_mappings = self._generate_weekly_period_mappings(start_date, end_date)

            # Build SQL CASE statement for date ranges
            case_conditions = []
            for period_key, date_ranges in period_mappings.items():
                conditions = []
                for start_range, end_range in date_ranges:
                    conditions.append(f"(date_borrowed BETWEEN '{start_range}' AND '{end_range}')")
                if conditions:
                    case_conditions.append(f"WHEN {' OR '.join(conditions)} THEN '{period_key}'")

            case_statement = "\n                      ".join(case_conditions)

            period_queries = {
                'daily': """
                    ,dynamic_periods AS (
                      SELECT *, strftime('%Y-%m-%d', date_borrowed) AS period_key FROM base
                    )
                """,
                'weekly': f"""
                    ,dynamic_periods AS (
                      SELECT
                        *,
                        CASE
                          {case_statement}
                          ELSE 'UNKNOWN_PERIOD'
                        END AS period_key
                      FROM base
                    )
                """,
                'monthly': """
                    ,dynamic_periods AS (
                      SELECT *, strftime('%Y-%m', date_borrowed) AS period_key FROM base
                    )
                """,
                'quarterly': """
                    ,dynamic_periods AS (
                      SELECT
                        *,
                        strftime('%Y', date_borrowed) || '-Q' ||
                        CAST(((CAST(strftime('%m', date_borrowed) AS INTEGER) - 1) / 3) + 1 AS TEXT) AS period_key
                      FROM base
                    )
                """,
                'yearly': """
                    ,dynamic_periods AS (
                      SELECT *, strftime('%Y', date_borrowed) AS period_key FROM base
                    )
                """,
                'multi_year': """
                    ,dynamic_periods AS (
                      SELECT *, strftime('%Y', date_borrowed) AS period_key FROM base
                    )
                """
            }
        else:
            # Fallback for other granularities or when dates not provided
            period_queries = {
                'daily': """
                    ,dynamic_periods AS (
                      SELECT *, strftime('%Y-%m-%d', date_borrowed) AS period_key FROM base
                    )
                """,
                'weekly': """
                    ,dynamic_periods AS (
                      SELECT *, strftime('%Y-%W', date_borrowed) AS period_key FROM base
                    )
                """,
                'monthly': """
                    ,dynamic_periods AS (
                      SELECT *, strftime('%Y-%m', date_borrowed) AS period_key FROM base
                    )
                """,
                'quarterly': """
                    ,dynamic_periods AS (
                      SELECT
                        *,
                        strftime('%Y', date_borrowed) || '-Q' ||
                        CAST(((CAST(strftime('%m', date_borrowed) AS INTEGER) - 1) / 3) + 1 AS TEXT) AS period_key
                      FROM base
                    )
                """,
                'yearly': """
                    ,dynamic_periods AS (
                      SELECT *, strftime('%Y', date_borrowed) AS period_key FROM base
                    )
                """,
                'multi_year': """
                    ,dynamic_periods AS (
                      SELECT *, strftime('%Y', date_borrowed) AS period_key FROM base
                    )
                """
            }

        return period_queries.get(granularity, period_queries['monthly'])

    def _generate_weekly_period_mappings(self, start_date: date, end_date: date) -> Dict[str, List[Tuple[str, str]]]:
        """Generate period key to date range mappings using Python logic."""
        from inventory_app.utils.date_utils import date_formatter

        # Get period keys from Python logic - this gives us the expected output format
        period_keys = date_formatter.get_period_keys(start_date, end_date, 'weekly')

        # Create mapping of date -> period_key by simulating the Python logic
        date_to_period = {}

        # For each date in our range, determine which period it belongs to
        current = start_date
        while current <= end_date:
            # Find the period key for this date using the same logic as Python
            period_key = self._find_period_key_for_date(current, start_date, end_date, period_keys)
            if period_key:
                date_to_period[current.isoformat()] = period_key
            current += timedelta(days=1)

        # Group dates by period key
        mappings = {}
        for date_str, period_key in date_to_period.items():
            if period_key not in mappings:
                mappings[period_key] = []
            mappings[period_key].append((date_str, date_str))  # Each date maps to itself

        return mappings

    def _find_period_key_for_date(self, target_date: date, start_date: date, end_date: date, period_keys: List[str]) -> Optional[str]:
        """Find which period key a specific date belongs to."""
        # Check excess periods first (format: YYYY-MM-DDtoYYYY-MM-DD)
        for period_key in period_keys:
            if 'to' in period_key:
                try:
                    start_str, end_str = period_key.split('to')
                    period_start = date.fromisoformat(start_str)
                    period_end = date.fromisoformat(end_str)
                    if period_start <= target_date <= period_end:
                        return period_key
                except ValueError:
                    continue

        # Check regular week periods (format: YYYY-MM-W#)
        for period_key in period_keys:
            if '-W' in period_key:
                try:
                    _, week_part = period_key.split('-W')
                    week_num = int(week_part)

                    # Calculate the date range for this week using the same logic as Python
                    first_monday = start_date - timedelta(days=(start_date.weekday() - 0) % 7)
                    if first_monday < start_date:
                        first_monday = start_date - timedelta(days=(start_date.weekday() - 0) % 7)

                    week_start = first_monday + timedelta(days=(week_num - 1) * 7)
                    week_end = week_start + timedelta(days=6)

                    if week_start <= target_date <= week_end:
                        return period_key
                except (ValueError, IndexError):
                    continue

        return None

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

    def _build_parameters(self, start_date: date, end_date: date, include_yearly: bool) -> Tuple:
        """Build parameter tuple for the query."""
        params = [start_date.isoformat(), end_date.isoformat()]

        if include_yearly:
            params.extend([start_date.isoformat(), end_date.isoformat()])

        return tuple(params)

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
        SELECT SUM(ri.quantity_borrowed) as total_used
        FROM Requisition_Items ri
        JOIN Requisitions r ON r.id = ri.requisition_id
        WHERE r.date_borrowed BETWEEN ? AND ?
        """

        params = [start_date.isoformat(), end_date.isoformat()]

        # Add filters
        if grade_filter:
            total_query += " AND r.borrower_id IN (SELECT id FROM Borrowers WHERE affiliation = ?)"
            params.append(grade_filter)
        if section_filter:
            total_query += " AND r.borrower_id IN (SELECT id FROM Borrowers WHERE group_name = ?)"
            params.append(section_filter)

        return total_query, tuple(params)

    @staticmethod
    def build_category_statistics_query(start_date: date, end_date: date,
                                      grade_filter: str = "",
                                      section_filter: str = "") -> Tuple[str, Tuple]:
        """Build query to get category statistics."""
        category_query = """
        SELECT c.name as category, SUM(ri.quantity_borrowed) as qty
        FROM Requisition_Items ri
        JOIN Requisitions r ON r.id = ri.requisition_id
        JOIN Items i ON i.id = ri.item_id
        JOIN Categories c ON c.id = i.category_id
        WHERE r.date_borrowed BETWEEN ? AND ?
        """

        params = [start_date.isoformat(), end_date.isoformat()]

        # Add filters
        if grade_filter:
            category_query += " AND r.borrower_id IN (SELECT id FROM Borrowers WHERE affiliation = ?)"
            params.append(grade_filter)
        if section_filter:
            category_query += " AND r.borrower_id IN (SELECT id FROM Borrowers WHERE group_name = ?)"
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
        SELECT i.name as item_name, SUM(ri.quantity_borrowed) as qty
        FROM Requisition_Items ri
        JOIN Requisitions r ON r.id = ri.requisition_id
        JOIN Items i ON i.id = ri.item_id
        WHERE r.date_borrowed BETWEEN ? AND ?
        """

        params = [start_date.isoformat(), end_date.isoformat()]

        # Add filters
        if grade_filter:
            top_items_query += " AND r.borrower_id IN (SELECT id FROM Borrowers WHERE affiliation = ?)"
            params.append(grade_filter)
        if section_filter:
            top_items_query += " AND r.borrower_id IN (SELECT id FROM Borrowers WHERE group_name = ?)"
            params.append(section_filter)

        top_items_query += f" GROUP BY i.id, i.name ORDER BY qty DESC LIMIT {limit}"

        return top_items_query, tuple(params)
