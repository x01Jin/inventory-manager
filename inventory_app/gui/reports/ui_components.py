"""
UI Components for the reports page.
Extracts UI creation logic into reusable, focused components.
"""

from typing import Tuple, Optional
from PyQt6.QtWidgets import (
    QVBoxLayout,
    QLabel,
    QPushButton,
    QGroupBox,
    QProgressBar,
    QTextEdit,
    QSplitter,
    QListWidget,
)

from inventory_app.gui.styles import DarkTheme
from inventory_app.gui.reports.report_config import ReportConfig
from inventory_app.gui.widgets.date_selector import DateRangeSelector


class ReportUIComponents:
    """Reusable UI components for the reports page."""

    @staticmethod
    def create_header() -> QLabel:
        """Create the page header."""
        header = QLabel(ReportConfig.WINDOW_TITLE)
        header.setStyleSheet(
            f"font-size: {DarkTheme.FONT_SIZE_TITLE}pt; "
            f"font-weight: bold; "
            f"color: {DarkTheme.TEXT_PRIMARY}; "
            "margin-bottom: 10px;"
        )
        return header

    @staticmethod
    def create_main_splitter() -> QSplitter:
        """Create the main splitter for the page layout."""
        splitter = QSplitter()
        splitter.setSizes(ReportConfig.SPLITTER_PROPORTIONS)
        return splitter

    @staticmethod
    def create_config_panel() -> QGroupBox:
        """Create the report configuration panel."""
        return QGroupBox(ReportConfig.GROUP_TITLES["config"])

    @staticmethod
    def create_granularity_info_section(parent_layout):
        """Create the dynamic granularity info section."""
        granularity_layout = QVBoxLayout()

        granularity_label = QLabel(
            "Report will automatically determine optimal granularity based on date range:"
        )
        granularity_label.setWordWrap(True)
        granularity_label.setStyleSheet(
            f"color: {DarkTheme.TEXT_SECONDARY}; "
            f"font-size: {DarkTheme.FONT_SIZE_NORMAL}pt;"
        )
        granularity_layout.addWidget(granularity_label)

        granularity_info = QLabel()
        granularity_info.setStyleSheet(
            f"color: {DarkTheme.TEXT_SECONDARY}; "
            f"font-size: {DarkTheme.FONT_SIZE_NORMAL}pt;"
        )
        granularity_layout.addWidget(granularity_info)

        parent_layout.addLayout(granularity_layout)
        return granularity_info

    @staticmethod
    def create_date_range_section(
        parent_layout, callback=None
    ) -> Tuple[DateRangeSelector, QLabel]:
        """Create the date range selection section."""
        date_group = QGroupBox(ReportConfig.GROUP_TITLES["date_range"])
        layout = QVBoxLayout(date_group)

        # Available date range info
        date_range_info = QLabel("Loading available date range...")
        date_range_info.setStyleSheet(
            f"color: {DarkTheme.TEXT_SECONDARY}; "
            f"font-size: {DarkTheme.FONT_SIZE_NORMAL}pt;"
        )
        layout.addWidget(date_range_info)

        # Date Range Selector
        date_range_selector = DateRangeSelector()
        layout.addWidget(date_range_selector)

        # Connect callback if provided
        if callback:
            date_range_selector.dateRangeChanged.connect(callback)

        parent_layout.addWidget(date_group)
        return date_range_selector, date_range_info

    # Filtering methods removed - filtering functionality has been disabled

    @staticmethod
    def create_generate_button(parent_layout, callback=None) -> QPushButton:
        """Create the generate report button."""
        generate_btn = QPushButton(ReportConfig.GENERATE_BUTTON_TEXT)
        generate_btn.setStyleSheet(ReportConfig.BUTTON_STYLES["generate"])

        if callback:
            generate_btn.clicked.connect(callback)

        parent_layout.addWidget(generate_btn)
        return generate_btn

    @staticmethod
    def create_progress_bar(parent_layout) -> QProgressBar:
        """Create the progress bar."""
        progress_bar = QProgressBar()
        progress_bar.setMaximumHeight(12)
        progress_bar.setVisible(False)
        progress_bar.setStyleSheet(ReportConfig.BUTTON_STYLES["progress_bar"])
        parent_layout.addWidget(progress_bar)
        return progress_bar

    @staticmethod
    def create_status_panel() -> Tuple[QGroupBox, QTextEdit, QTextEdit]:
        """Create the status and preview panel."""
        status_group = QGroupBox(ReportConfig.GROUP_TITLES["status"])
        layout = QVBoxLayout(status_group)

        # Status Text Area
        status_text = QTextEdit()
        status_text.setReadOnly(True)
        status_text.setMaximumHeight(ReportConfig.STATUS_TEXT_MAX_HEIGHT)
        status_text.setPlainText(ReportConfig.STATUS_READY)
        layout.addWidget(status_text)

        # Recent Reports
        recent_group = QGroupBox(ReportConfig.GROUP_TITLES["recent_reports"])
        recent_layout = QVBoxLayout(recent_group)

        recent_reports_text = QTextEdit()
        recent_reports_text.setReadOnly(True)
        recent_reports_text.setMaximumHeight(ReportConfig.RECENT_REPORTS_MAX_HEIGHT)
        recent_reports_text.setPlainText("No recent reports generated.")
        recent_layout.addWidget(recent_reports_text)

        layout.addWidget(recent_group)

        return status_group, status_text, recent_reports_text


class ReportStyler:
    """Styling utilities for report components."""

    @staticmethod
    def apply_button_state(
        button: QPushButton, enabled: bool, text: Optional[str] = None
    ):
        """Apply enabled/disabled state to a button."""
        button.setEnabled(enabled)
        if text:
            button.setText(text)

    @staticmethod
    def update_granularity_display(
        info_label: QLabel, current_granularity: Optional[str] = None
    ):
        """Update the granularity information display."""
        granularity_text = ReportConfig.get_all_granularity_descriptions(
            current_granularity
        )
        info_label.setText(granularity_text)

    @staticmethod
    def update_date_range_display(info_label: QLabel, date_range_text: str):
        """Update the date range information display."""
        info_label.setText(date_range_text)


class ReportUIUpdater:
    """Handles UI updates for the reports page."""

    def __init__(
        self,
        status_text: QTextEdit,
        results_list: Optional[QListWidget] = None,
        recent_reports_text: Optional[QTextEdit] = None,
    ):
        """Initialize with UI components."""
        self.status_text = status_text
        self.results_list = results_list
        self.recent_reports_text = recent_reports_text

    def update_status(self, message: str):
        """Update the status text area."""
        self.status_text.append(message)

    def clear_status(self):
        """Clear the status text area."""
        self.status_text.clear()

    def add_recent_report(self, file_path: str, timestamp: str):
        """Add a report to the recent reports list."""
        if self.recent_reports_text:
            report_info = f"[{timestamp}] {file_path}\n"
            current_text = self.recent_reports_text.toPlainText()

            if current_text == "No recent reports generated.":
                self.recent_reports_text.setPlainText(report_info)
            else:
                self.recent_reports_text.setPlainText(report_info + current_text)

    def add_to_results(self, result_text: str):
        """Add a result to the results list."""
        if self.results_list:
            self.results_list.addItem(result_text)
