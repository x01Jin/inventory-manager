"""
Report worker thread for background report generation.
"""

from PyQt6.QtCore import QThread, pyqtSignal

from inventory_app.gui.reports.report_generator import report_generator
from inventory_app.utils.logger import logger
from inventory_app.gui.reports.report_config import ReportConfig


class ReportWorker(QThread):
    """Worker thread for dynamic report generation to prevent UI blocking."""

    finished = pyqtSignal(str)  # Signal emitted when report is generated (file path)
    error = pyqtSignal(str)  # Signal for progress updates
    progress = pyqtSignal(str)  # Signal for progress updates

    def __init__(self, report_type, start_date, end_date, **kwargs):
        super().__init__()
        self.report_type = report_type
        self.start_date = start_date
        self.end_date = end_date
        # Extract common parameters
        self.category_filter = kwargs.get("category_filter", "")
        self.supplier_filter = kwargs.get("supplier_filter", "")
        self.include_consumables = kwargs.get("include_consumables", True)
        self.show_individual_only = kwargs.get("show_individual_only", False)
        # Usage report specific parameters
        self.usage_report_type = kwargs.get("usage_report_type", "date_range")
        self.monthly_year = kwargs.get("monthly_year")
        self.monthly_month = kwargs.get("monthly_month")
        self.report_style = kwargs.get("report_style", "detailed")
        # Inventory report specific parameters
        self.inventory_report_type = kwargs.get(
            "inventory_report_type", "Stock Levels Report"
        )
        # Low stock threshold (for Low Stock Alert)
        self.low_stock_threshold = kwargs.get(
            "low_stock_threshold", ReportConfig.DEFAULT_LOW_STOCK_THRESHOLD
        )
        # Item name filter (for Item Usage Details and Batch Summary)
        self.item_name_filter = kwargs.get("item_name_filter", "")
        # Audit report filters
        self.editor_filter = kwargs.get("editor_filter", "")
        self.action_filter = kwargs.get("action_filter", "")
        self.entity_filter = kwargs.get("entity_filter", "")
        # Grade and Section filters (for Usage by Grade Level)
        self.grade_filter = kwargs.get("grade_filter", "")
        self.section_filter = kwargs.get("section_filter", "")
        # Trends report params
        self.granularity = kwargs.get("granularity", None)
        self.group_by = kwargs.get("group_by", "item")
        self.top_n = kwargs.get("top_n", None)

    def run(self):
        """Generate the dynamic report in background thread."""
        try:
            self.progress.emit(f"Starting {self.report_type} report generation...")

            # Dispatch to appropriate report generation method
            if self.report_type == "usage":
                file_path = self._generate_usage_report()
            elif self.report_type == "inventory":
                file_path = self._generate_inventory_report()
            elif self.report_type == "trends":
                file_path = self._generate_trends_report()
            else:
                file_path = f"Unknown report type: {self.report_type}"

            # Support structured dict returns as well as legacy strings
            if isinstance(file_path, dict):
                if file_path.get("success"):
                    self.progress.emit(
                        f"{self.report_type.title()} report generated successfully!"
                    )
                    self.finished.emit(file_path.get("path") or "")
                else:
                    self.error.emit(
                        file_path.get("error") or "Failed to generate report"
                    )
            else:
                if self._is_successful_path(file_path):
                    self.progress.emit(
                        f"{self.report_type.title()} report generated successfully!"
                    )
                    self.finished.emit(file_path)
                else:
                    # Handle error messages
                    if file_path:
                        self.error.emit(file_path)
                    else:
                        self.error.emit("Failed to generate report")

        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            self.error.emit(f"Report generation failed: {str(e)}")

    @staticmethod
    def _is_successful_path(result) -> bool:
        """Return True only for likely valid output-path strings."""
        if not isinstance(result, str):
            return False

        normalized = result.strip()
        if not normalized:
            return False

        lowered = normalized.lower()
        failure_markers = (
            "failed to generate",
            "unknown report type",
            "reason:",
            "traceback",
            "error",
        )
        if any(marker in lowered for marker in failure_markers):
            return False

        return lowered.endswith(".xlsx")

    def _generate_usage_report(self):
        """Generate usage report using existing functionality."""
        if self.usage_report_type == "monthly":
            from inventory_app.gui.reports.monthly_usage_report import (
                generate_monthly_usage_report,
            )

            if self.monthly_year is None or self.monthly_month is None:
                return "Failed to generate report: missing monthly period"

            return generate_monthly_usage_report(
                year=int(self.monthly_year),
                month=int(self.monthly_month),
                category_filter=self.category_filter,
                report_style=self.report_style,
            )

        if self.usage_report_type == "grade_level":
            return report_generator.generate_usage_by_grade_level_report(
                self.start_date,
                self.end_date,
                category_filter=self.category_filter,
                grade_filter=self.grade_filter,
                section_filter=self.section_filter,
                show_individual_only=self.show_individual_only,
            )
        return report_generator.generate_report(
            self.start_date,
            self.end_date,
            category_filter=self.category_filter,
            supplier_filter=self.supplier_filter,
            include_consumables=self.include_consumables,
            show_individual_only=self.show_individual_only,
        )

    def _generate_inventory_report(self):
        """Generate inventory report."""
        return report_generator.generate_inventory_report(
            self.inventory_report_type,
            self.start_date,
            self.end_date,
            category_filter=self.category_filter,
            low_stock_threshold=self.low_stock_threshold,
            item_name_filter=self.item_name_filter,
            editor_filter=self.editor_filter,
            action_filter=self.action_filter,
            entity_filter=self.entity_filter,
            grade_filter=self.grade_filter,
            section_filter=self.section_filter,
            show_individual_only=self.show_individual_only,
        )

    def _generate_trends_report(self):
        """Generate trends report using ReportGenerator."""
        granularity = getattr(self, "granularity", None)
        group_by = getattr(self, "group_by", "item")
        top_n = getattr(self, "top_n", None)
        include_consumables = getattr(self, "include_consumables", True)

        return report_generator.generate_trends_report(
            self.start_date,
            self.end_date,
            granularity=granularity,
            group_by=group_by,
            top_n=top_n,
            include_consumables=include_consumables,
        )

    # end of class
