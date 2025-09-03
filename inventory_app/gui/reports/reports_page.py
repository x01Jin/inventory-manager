"""
Reports page for generating usage reports.
Provides UI for date range selection and Excel report generation. reports include all data.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QMessageBox
)
from PyQt6.QtCore import QDate

from inventory_app.gui.reports.report_config import ReportConfig, ReportMessages
from inventory_app.gui.reports.ui_components import ReportUIComponents, ReportStyler, ReportUIUpdater
from inventory_app.gui.reports.report_worker import ReportWorker
from inventory_app.utils.logger import logger
from inventory_app.gui.reports.report_utils import date_formatter

import os
from datetime import datetime


class ReportsPage(QWidget):
    """Reports page with date range selection and report generation capabilities."""

    def __init__(self):
        super().__init__()
        self.worker = None
        self.ui_updater = None  # Will be initialized in setup_ui
        self.setup_ui()

    def setup_ui(self):
        """Setup the user interface using modular components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header using UI component
        header = ReportUIComponents.create_header()
        layout.addWidget(header)

        # Create main splitter
        splitter = ReportUIComponents.create_main_splitter()
        layout.addWidget(splitter)

        # Left panel - Report Configuration
        config_widget = self.create_config_panel()
        splitter.addWidget(config_widget)

        # Right panel - Report Preview/Status
        status_widget, status_text, recent_reports_text = ReportUIComponents.create_status_panel()
        splitter.addWidget(status_widget)

        # Initialize UI updater
        self.ui_updater = ReportUIUpdater(status_text, recent_reports_text)
        self.status_text = status_text
        self.recent_reports_text = recent_reports_text

        # Set splitter proportions
        splitter.setSizes(ReportConfig.SPLITTER_PROPORTIONS)

    def create_config_panel(self):
        """Create the report configuration panel using modular components."""
        config_group = ReportUIComponents.create_config_panel()
        layout = QVBoxLayout(config_group)

        # Dynamic Granularity Info using UI components
        self.granularity_info = ReportUIComponents.create_granularity_info_section(layout)

        # Date Range Selection using UI components
        self.date_range_selector, self.date_range_info = ReportUIComponents.create_date_range_section(
            layout, self.update_granularity_info
        )

        # Generate Button using UI components
        self.generate_btn = ReportUIComponents.create_generate_button(layout, self.generate_report)

        # Progress Bar using UI components
        self.progress_bar = ReportUIComponents.create_progress_bar(layout)

        return config_group

    def load_available_date_range(self):
        """Load the available date range from requisition data and set date picker limits."""
        try:
            from inventory_app.database.connection import db

            # Query for min and max date_borrowed from requisitions
            query = """
            SELECT
                MIN(date_borrowed) as min_date,
                MAX(date_borrowed) as max_date
            FROM Requisitions
            WHERE date_borrowed IS NOT NULL
            """
            result = db.execute_query(query)

            if result and result[0]['min_date'] and result[0]['max_date']:
                min_date_str = result[0]['min_date']
                max_date_str = result[0]['max_date']

                # Convert to QDate
                min_qdate = QDate.fromString(min_date_str, "yyyy-MM-dd")
                max_qdate = QDate.fromString(max_date_str, "yyyy-MM-dd")

                # Set date range limits for the date selector
                self.date_range_selector.start_date_selector.setMinimumDate(min_qdate)
                self.date_range_selector.start_date_selector.setMaximumDate(max_qdate)
                self.date_range_selector.end_date_selector.setMinimumDate(min_qdate)
                self.date_range_selector.end_date_selector.setMaximumDate(max_qdate)

                # Set default dates to show recent data
                today = QDate.currentDate()
                default_start = today.addDays(-30)

                # Ensure default start is within available range
                if default_start < min_qdate:
                    default_start = min_qdate
                elif default_start > max_qdate:
                    default_start = max_qdate

                # Set default dates
                self.date_range_selector.set_date_range(default_start, max_qdate)

                # Update info label
                self.date_range_info.setText(f"Available: {min_qdate.toString('MM/dd/yyyy')} to {max_qdate.toString('MM/dd/yyyy')}")

                logger.info(f"Set date range limits: {min_date_str} to {max_date_str}")
            else:
                # No requisition data available
                self.date_range_info.setText("No requisition data available - date selection unrestricted")
                logger.warning("No requisition data found for date range limiting")

        except Exception as e:
            logger.error(f"Failed to load available date range: {e}")
            self.date_range_info.setText("Error loading date range - date selection unrestricted")

    def generate_report(self):
        """Generate the dynamic report using configuration and messaging."""
        try:
            # Get dates from the new date range selector
            start_date, end_date = self.date_range_selector.to_py_dates()

            if start_date > end_date:
                QMessageBox.warning(self, "Invalid Date Range", ReportMessages.invalid_date_range())
                return

            # Determine granularity for status message using new date formatter
            granularity = date_formatter.get_smart_granularity(start_date, end_date)

            # Disable generate button and show progress
            ReportStyler.apply_button_state(self.generate_btn, False, ReportConfig.GENERATE_BUTTON_LOADING)
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # Indeterminate progress

            # Update status using UI updater
            if self.ui_updater:
                self.ui_updater.clear_status()
                self.ui_updater.update_status(ReportMessages.generation_started(granularity))
                self.ui_updater.update_status(f"Date range: {start_date} to {end_date}")


                self.ui_updater.update_status(ReportMessages.generation_progress("Please wait..."))

            # Start background worker
            self.worker = ReportWorker(start_date, end_date)
            self.worker.progress.connect(self.update_progress)
            self.worker.finished.connect(self.on_report_finished)
            self.worker.error.connect(self.on_report_error)
            self.worker.start()

        except Exception as e:
            logger.error(f"Failed to start report generation: {e}")
            QMessageBox.critical(self, "Error", f"Failed to start report generation: {str(e)}")
            self.reset_ui()

    def update_progress(self, message):
        """Update progress message."""
        self.status_text.append(f"\n{message}")

    def on_report_finished(self, file_path):
        """Handle successful report generation using UI updater."""
        if self.ui_updater is None:
            return

        # Update status using UI updater
        self.ui_updater.update_status(ReportMessages.generation_progress("✅ Report generated successfully!"))
        self.ui_updater.update_status(ReportMessages.file_saved(file_path))

        # Update recent reports using UI updater
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.ui_updater.add_recent_report(os.path.basename(file_path), timestamp)

        # Try to open the file
        try:
            os.startfile(file_path)  # Windows specific
            self.ui_updater.update_status(ReportMessages.file_opening())
        except Exception as e:
            self.ui_updater.update_status(ReportMessages.generation_failed(f"Could not auto-open file: {str(e)}"))

        self.reset_ui()

    def on_report_error(self, error_message):
        """Handle report generation error using standardized messages."""
        if self.ui_updater is None:
            return

        self.ui_updater.update_status(ReportMessages.generation_failed(error_message))
        QMessageBox.critical(self, "Report Generation Failed", error_message)
        self.reset_ui()

    def reset_ui(self):
        """Reset UI after report generation completes."""
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText("📊 Generate Report")
        self.progress_bar.setVisible(False)
        self.worker = None

    def update_granularity_info(self):
        """Update the granularity information display using ReportStyler."""
        try:
            start_date, end_date = self.date_range_selector.to_py_dates()
            granularity = date_formatter.get_smart_granularity(start_date, end_date)
            description = date_formatter.get_date_range_description(start_date, end_date)

            # Update granularity display using styler (eliminates repetitive string manipulation)
            ReportStyler.update_granularity_display(self.granularity_info, granularity)

            # Update date range display
            ReportStyler.update_date_range_display(self.date_range_info, f"Selected: {description}")

        except Exception as e:
            logger.error(f"Failed to update granularity info: {e}")
            self.granularity_info.setText("Error calculating granularity")

    def refresh_data(self):
            """Refresh data on the reports page."""
            pass
