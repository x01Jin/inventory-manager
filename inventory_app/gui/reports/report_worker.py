"""
Report worker thread for background report generation.
"""

from PyQt6.QtCore import QThread, pyqtSignal

from inventory_app.gui.reports.report_generator import report_generator
from inventory_app.utils.logger import logger


class ReportWorker(QThread):
    """Worker thread for dynamic report generation to prevent UI blocking."""

    finished = pyqtSignal(str)  # Signal emitted when report is generated (file path)
    error = pyqtSignal(str)     # Signal emitted on error
    progress = pyqtSignal(str)  # Signal for progress updates

    def __init__(self, start_date, end_date):
        super().__init__()
        self.start_date = start_date
        self.end_date = end_date
        # Use default filter values (no filtering)
        self.grade_filter = ""
        self.section_filter = ""
        self.include_consumables = True

    def run(self):
        """Generate the dynamic report in background thread."""
        try:
            self.progress.emit("Starting dynamic report generation...")

            # Use the new unified report generation method
            file_path = report_generator.generate_report(
                self.start_date,
                self.end_date,
                grade_filter=self.grade_filter,
                section_filter=self.section_filter,
                include_consumables=self.include_consumables
            )

            if file_path and not file_path.startswith("Failed to generate report"):
                # Determine granularity for status message
                granularity = report_generator.get_granularity(self.start_date, self.end_date)
                self.progress.emit(f"{granularity.title()} report generated successfully!")
                self.finished.emit(file_path)
            else:
                # Handle error messages from report generator
                if file_path:
                    self.error.emit(file_path)
                else:
                    self.error.emit("Failed to generate report")

        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            self.error.emit(f"Report generation failed: {str(e)}")
