"""
Report generator for the inventory application.
Handles Excel report generation for dynamic reports based on date range.
Refactored to use QueryBuilder for SQL operations and eliminate redundancy.
"""

from typing import List, Dict, Optional
from datetime import date, datetime
from pathlib import Path

from inventory_app.utils.logger import logger
from inventory_app.gui.reports.report_utils import date_formatter
# Query builders and movement types used in data_sources

# Move Excel and header logic to dedicated modules
from inventory_app.gui.reports.excel_utils import create_excel_report
from inventory_app.gui.reports.header_utils import (
    format_excel_headers,
    parse_and_format_period_key,
)
from inventory_app.gui.reports.data_sources import (
    get_dynamic_report_data,
    get_stock_levels_data,
    get_trends_data,
    get_expiration_data,
    get_low_stock_data,
    get_acquisition_history_data,
    get_calibration_due_data,
    get_usage_statistics as ds_get_usage_statistics,
)

# Inline header mapping moved to header_utils


class ReportGenerator:
    """
    Handles report generation and Excel export.
    Uses composition with DatabaseConnection and openpyxl.
    """

    def __init__(self):
        """Initialize report generator."""

    def get_granularity(self, start_date: date, end_date: date) -> str:
        """
        Determine the appropriate reporting granularity based on date range.

        Args:
            start_date (datetime.date): Start date of the reporting period
            end_date (datetime.date): End date of the reporting period

        Returns:
            str: Granularity level ('daily', 'weekly', 'monthly', 'quarterly', 'yearly', 'multi_year')
        """
        return date_formatter.get_smart_granularity(start_date, end_date)

    def generate_report(
        self,
        start_date: date,
        end_date: date,
        output_path: Optional[str] = None,
        category_filter: str = "",
        supplier_filter: str = "",
        include_consumables: bool = True,
    ) -> str:
        """
        Generate dynamic usage report in Excel format based on date range.

        Args:
            start_date: Start date for the report period
            end_date: End date for the report period
            output_path: Optional output file path
            category_filter: Filter by category
            supplier_filter: Filter by supplier
            include_consumables: Whether to include consumable items

        Returns:
            Path to generated Excel file
        """
        # Determine granularity and report title
        granularity = self.get_granularity(start_date, end_date)

        try:
            logger.info(
                f"Generating {granularity} report from {start_date} to {end_date}"
            )

            # Get report data with dynamic granularity
            report_data = self._get_dynamic_report_data(
                start_date,
                end_date,
                granularity,
                category_filter=category_filter,
                supplier_filter=supplier_filter,
                include_consumables=include_consumables,
            )

            if not report_data:
                error_msg = "Failed to generate report\nReason: No data found for the specified period"
                logger.warning("No data found for the specified period")
                return error_msg

            # Create Excel file
            if not output_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"{granularity}_report_{timestamp}.xlsx"

            output_path_obj = Path(output_path)
            title = f"{granularity.title()} Usage Report"
            self._create_excel_report(
                report_data, output_path_obj, title, start_date, end_date
            )

            logger.info(f"{granularity.title()} report generated: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"Failed to generate {granularity} report: {e}")
            return ""

    def _get_dynamic_report_data(
        self,
        start_date: date,
        end_date: date,
        granularity: str,
        category_filter: str = "",
        supplier_filter: str = "",
        include_consumables: bool = True,
    ) -> List[Dict]:
        """Wrapper over data_sources.get_dynamic_report_data"""
        try:
            return get_dynamic_report_data(
                start_date,
                end_date,
                granularity,
                category_filter=category_filter,
                supplier_filter=supplier_filter,
                include_consumables=include_consumables,
            )
        except Exception as e:
            logger.error(f"Failed to get dynamic report data: {e}")
            return []

    def _format_excel_headers(
        self, headers: List[str], start_date: date, end_date: date
    ) -> List[str]:
        """
        Format Excel headers by converting period keys to user-friendly format.

        Args:
            headers: Raw headers from database
            start_date: Report start date
            end_date: Report end date

        Returns:
            List of formatted headers
        """
        # Delegate to header_utils.format_excel_headers
        try:
            return format_excel_headers(headers, start_date, end_date)
        except Exception as e:
            logger.error(f"Failed to format Excel headers: {e}")
            return headers

    def _parse_and_format_period_key(self, period_key: str, granularity: str) -> str:
        """Delegate parsing to header_utils.parse_and_format_period_key"""
        try:
            return parse_and_format_period_key(period_key, granularity)
        except Exception as e:
            logger.error(f"Failed to parse period key '{period_key}': {e}")
            return period_key

    def _create_excel_report(
        self,
        data: List[Dict],
        output_path: Path,
        title: str,
        start_date: date,
        end_date: date,
    ) -> None:
        """
        Create Excel file with report data.

        Args:
            data: Report data rows
            output_path: Output file path
            title: Report title
            start_date: Report start date
            end_date: Report end date
        """
        # Delegate to excel_utils
        try:
            create_excel_report(data, output_path, title, start_date, end_date)
        except Exception as e:
            logger.error(f"Failed to create Excel report: {e}")
            raise

    def get_usage_statistics(self, start_date: date, end_date: date) -> Dict:
        """
        Get usage statistics for a date range using ReportStatisticsBuilder.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            Dictionary with usage statistics
        """
        try:
            return ds_get_usage_statistics(start_date, end_date)
        except Exception as e:
            logger.error(f"Failed to get usage statistics: {e}")
            return {
                "total_items_used": 0,
                "categories": [],
                "top_items": [],
                "date_range": f"{start_date} to {end_date}",
            }

    def generate_inventory_report(
        self,
        report_type: str,
        start_date: date,
        end_date: date,
        category_filter: str = "",
        output_path: Optional[str] = None,
    ) -> str:
        """
        Generate inventory report based on type.

        Args:
            report_type: Type of inventory report ('stock_levels', 'expiration', 'low_stock', 'acquisition_history', 'calibration_due')
            start_date: Start date for the report period
            end_date: End date for the report period
            category_filter: Category filter
            output_path: Optional output file path

        Returns:
            Path to generated Excel file
        """
        try:
            logger.info(
                f"Generating {report_type} report from {start_date} to {end_date}"
            )

            # Get report data based on type
            if report_type == "Stock Levels Report":
                report_data = self._get_stock_levels_data(category_filter)
                title = "Stock Levels Report"
            elif report_type == "Expiration Report":
                report_data = self._get_expiration_data(
                    start_date, end_date, category_filter
                )
                title = "Expiration Report"
            elif report_type == "Low Stock Alert":
                report_data = self._get_low_stock_data(category_filter)
                title = "Low Stock Alert Report"
            elif report_type == "Acquisition History":
                report_data = self._get_acquisition_history_data(
                    start_date, end_date, category_filter
                )
                title = "Acquisition History Report"
            elif report_type == "Calibration Due Report":
                report_data = self._get_calibration_due_data(
                    start_date, end_date, category_filter
                )
                title = "Calibration Due Report"
            else:
                return f"Unknown inventory report type: {report_type}"

            if not report_data:
                error_msg = f"Failed to generate {report_type}\nReason: No data found for the specified criteria"
                logger.warning(f"No data found for {report_type}")
                return error_msg

            # Create Excel file
            if not output_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"inventory_{report_type.lower().replace(' ', '_')}_{timestamp}.xlsx"

            output_path_obj = Path(output_path)
            self._create_excel_report(
                report_data, output_path_obj, title, start_date, end_date
            )

            logger.info(f"{report_type} report generated: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"Failed to generate {report_type} report: {e}")
            return ""

    def generate_trends_report(
        self,
        start_date: date,
        end_date: date,
        granularity: str = "monthly",
        group_by: str = "item",
        top_n: Optional[int] = None,
        include_consumables: bool = True,
        output_path: Optional[str] = None,
    ) -> str:
        """
        Generate a trends report (time-series) grouped by item or category.

        Args:
            start_date, end_date: Date range
            granularity: daily/weekly/monthly/quarterly
            group_by: 'item' or 'category'
            top_n: Limit to top N rows by total quantity (None for all)
            include_consumables: whether to include consumable items
            output_path: optional output path

        Returns:
            Path to generated Excel file or error string
        """
        try:
            logger.info(f"Generating trends report from {start_date} to {end_date}")

            report_data = self._get_trends_data(
                start_date,
                end_date,
                granularity,
                group_by=group_by,
                top_n=top_n,
                include_consumables=include_consumables,
            )

            if not report_data:
                logger.warning("No data found for trends report")
                return "Failed to generate trends report\nReason: No data found"

            # Create Excel file
            if not output_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"trends_report_{group_by}_{timestamp}.xlsx"

            output_path_obj = Path(output_path)
            title = f"Trends Report - {group_by.title()}"
            self._create_excel_report(
                report_data, output_path_obj, title, start_date, end_date
            )

            logger.info(f"Trends report generated: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"Failed to generate trends report: {e}")
            return ""

    def _get_stock_levels_data(self, category_filter: str = "") -> List[Dict]:
        """Get current stock levels data.

        Parameters:
            category_filter: Optional category filter
            min_stock: If provided, return only items with current stock < min_stock
        """
        try:
            return get_stock_levels_data(category_filter=category_filter)
        except Exception as e:
            logger.error(f"Failed to get stock levels data: {e}")
            return []

    def _get_trends_data(
        self,
        start_date: date,
        end_date: date,
        granularity: str = "monthly",
        group_by: str = "item",
        top_n: Optional[int] = None,
        include_consumables: bool = True,
        category_filter: str = "",
    ) -> List[Dict]:
        """Return time-series pivot data for trends reports.

        The method leverages existing dynamic report pivoting and then optionally
        aggregates by category and applies top-N filtering.
        """
        try:
            return get_trends_data(
                start_date,
                end_date,
                granularity,
                group_by=group_by,
                top_n=top_n,
                include_consumables=include_consumables,
                category_filter=category_filter,
            )
        except Exception as e:
            logger.error(f"Failed to get trends data: {e}")
            return []

    def _get_expiration_data(
        self, start_date: date, end_date: date, category_filter: str = ""
    ) -> List[Dict]:
        """Get items expiring within date range."""
        try:
            return get_expiration_data(start_date, end_date, category_filter)
        except Exception as e:
            logger.error(f"Failed to get expiration data: {e}")
            return []

    def _get_low_stock_data(
        self, category_filter: str = "", threshold: int = 10
    ) -> List[Dict]:
        """Get items with low stock (< threshold). Re-uses stock levels query to avoid duplication."""
        try:
            return get_low_stock_data(
                category_filter=category_filter, threshold=threshold
            )
        except Exception as e:
            logger.error(f"Failed to get low stock data: {e}")
            return []

    def _get_acquisition_history_data(
        self, start_date: date, end_date: date, category_filter: str = ""
    ) -> List[Dict]:
        """Get acquisition history within date range."""
        try:
            return get_acquisition_history_data(start_date, end_date, category_filter)
        except Exception as e:
            logger.error(f"Failed to get acquisition history data: {e}")
            return []

    def _get_calibration_due_data(
        self, start_date: date, end_date: date, category_filter: str = ""
    ) -> List[Dict]:
        """Get items needing calibration within date range."""
        try:
            return get_calibration_due_data(start_date, end_date, category_filter)
        except Exception as e:
            logger.error(f"Failed to get calibration due data: {e}")
            return []


# Global report generator instance
report_generator = ReportGenerator()
