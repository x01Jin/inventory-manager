"""
Report worker thread for background report generation.
"""

from PyQt6.QtCore import QThread, pyqtSignal

from inventory_app.gui.reports.report_generator import report_generator
from inventory_app.utils.logger import logger


class ReportWorker(QThread):
    """Worker thread for dynamic report generation to prevent UI blocking."""

    finished = pyqtSignal(str)  # Signal emitted when report is generated (file path)
    error = pyqtSignal(str)     # Signal for progress updates
    progress = pyqtSignal(str)  # Signal for progress updates

    def __init__(self, report_type, start_date, end_date, **kwargs):
        super().__init__()
        self.report_type = report_type
        self.start_date = start_date
        self.end_date = end_date
        # Extract common parameters
        self.category_filter = kwargs.get('category_filter', '')
        self.supplier_filter = kwargs.get('supplier_filter', '')
        self.include_consumables = kwargs.get('include_consumables', True)
        # Inventory report specific parameters
        self.inventory_report_type = kwargs.get('inventory_report_type', 'Stock Levels Report')
        # Requisition report specific parameters
        self.req_report_type = kwargs.get('req_report_type', 'Requisition Summary')
        self.req_status_filter = kwargs.get('req_status_filter', '')
        # Statistics report specific parameters
        self.stat_report_type = kwargs.get('stat_report_type', 'Usage Statistics')
        self.top_n = kwargs.get('top_n', 25)

    def run(self):
        """Generate the dynamic report in background thread."""
        try:
            self.progress.emit(f"Starting {self.report_type} report generation...")

            # Dispatch to appropriate report generation method
            if self.report_type == "usage":
                file_path = self._generate_usage_report()
            elif self.report_type == "inventory":
                file_path = self._generate_inventory_report()
            elif self.report_type == "requisition":
                file_path = self._generate_requisition_report()
            elif self.report_type == "statistics":
                file_path = self._generate_statistics_report()
            else:
                file_path = f"Unknown report type: {self.report_type}"

            if file_path and not file_path.startswith("Failed to generate report"):
                self.progress.emit(f"{self.report_type.title()} report generated successfully!")
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

    def _generate_usage_report(self):
        """Generate usage report using existing functionality."""
        return report_generator.generate_report(
            self.start_date,
            self.end_date,
            grade_filter=self.category_filter,
            section_filter=self.supplier_filter,
            include_consumables=self.include_consumables
        )

    def _generate_inventory_report(self):
        """Generate inventory report."""
        return report_generator.generate_inventory_report(
            self.inventory_report_type,
            self.start_date,
            self.end_date,
            category_filter=self.category_filter
        )

    def _generate_requisition_report(self):
        """Generate requisition report."""
        # This will be implemented next
        return "Requisition reports not yet implemented"

    def _generate_statistics_report(self):
        """Generate statistics report."""
        # This will be implemented next
        return "Statistics reports not yet implemented"
