"""
Reports Page for Laboratory Inventory Management.
Provides comprehensive reporting with multiple report types and modern UI.
"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QProgressBar,
    QTextEdit,
    QComboBox,
    QCheckBox,
    QListWidget,
    QSpinBox,
    QSplitter,
    QMessageBox,
    QTabWidget,
    QSizePolicy,
    QLineEdit,
)
from PyQt6.QtCore import Qt, QDate

from inventory_app.gui.reports.ui_components import ReportUIUpdater
from inventory_app.gui.reports.report_worker import ReportWorker
from inventory_app.utils.logger import logger
from inventory_app.gui.widgets.date_selector import DateRangeSelector
from inventory_app.gui.styles import ThemeManager

import os
from datetime import datetime, date, timedelta


class ReportsPage(QWidget):
    """Reports page with multiple report types and modern UI."""

    def __init__(self):
        super().__init__()
        self.worker = None
        self.ui_updater = None
        self.current_report_type = "usage"
        self.apply_theme()
        self.setup_ui()

    def apply_theme(self):
        """Apply current theme to the reports page."""
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance()
        if app and isinstance(app, QApplication):
            theme_manager = ThemeManager.instance()
            theme_manager.apply_theme(app)

    # Keep old method name for backward compatibility
    def apply_dark_theme(self):
        """Apply dark theme to the reports page (deprecated, use apply_theme)."""
        self.apply_theme()

    def setup_ui(self):
        """Setup the modern interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 20)
        layout.setSpacing(10)

        # Header
        header = self.create_header()
        layout.addWidget(header, 0)  # Stretch factor 0: header stays compact

        # Main content with splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - Report Configuration
        config_panel = self.create_config_panel()
        main_splitter.addWidget(config_panel)

        # Right panel - Status and Results
        status_panel = self.create_status_panel()
        main_splitter.addWidget(status_panel)

        main_splitter.setCollapsible(0, False)
        main_splitter.setCollapsible(1, False)

        main_splitter.setSizes([500, 500])
        layout.addWidget(
            main_splitter, 1
        )  # Stretch factor 1: splitter takes remaining space

        # Initialize UI updater
        self.ui_updater = ReportUIUpdater(
            self.status_text, self.results_list, self.recent_reports_text
        )

    def create_header(self) -> QWidget:
        """Create the page header."""
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)

        title = QLabel("📊 Reports")
        title.setStyleSheet("font-size: 16pt; font-weight: bold;")

        header_layout.addWidget(title)

        return header_widget

    def create_config_panel(self) -> QWidget:
        """Create the configuration panel with tabs."""
        config_widget = QWidget()
        config_layout = QVBoxLayout(config_widget)
        config_layout.setSpacing(8)  # Reduce spacing between items
        config_layout.setContentsMargins(0, 0, 0, 0)  # Minimize margins

        # Report Type Tabs
        self.tab_widget = QTabWidget()
        self.tab_widget.currentChanged.connect(self.on_report_type_changed)

        # Usage Reports Tab (merged monthly and date range)
        usage_tab = self.create_usage_tab()
        self.tab_widget.addTab(usage_tab, "📈 Usage Reports")

        # Inventory Reports Tab
        inventory_tab = self.create_inventory_tab()
        self.tab_widget.addTab(inventory_tab, "📦 Inventory Reports")

        # Trends Reports Tab
        trends_tab = self.create_trends_tab()
        self.tab_widget.addTab(trends_tab, "📉 Trends Reports")

        config_layout.addWidget(
            self.tab_widget, 1
        )  # Stretch factor 1: takes remaining space

        # Generate Button
        self.generate_btn = QPushButton("🚀 Generate Report")
        self.generate_btn.clicked.connect(self.generate_report)
        config_layout.addWidget(self.generate_btn, 0)  # Stretch factor 0: stays compact

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        config_layout.addWidget(self.progress_bar, 0)  # Stretch factor 0: stays compact

        return config_widget

    def create_usage_tab(self) -> QWidget:
        """Create merged usage reports configuration tab.

        Provides both monthly usage report and date range usage report
        with separate UI for each type.
        """
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(6)  # Reduce spacing between sections
        layout.setContentsMargins(0, 0, 0, 0)  # Minimize margins

        # Usage Report Type Selection
        type_group = QGroupBox("📋 Report Type")
        type_layout = QVBoxLayout(type_group)
        type_layout.setSpacing(4)  # Reduce spacing in groupbox
        type_layout.setContentsMargins(8, 8, 8, 8)  # Minimal padding

        self.usage_report_type = QComboBox()
        self.usage_report_type.addItem("Monthly Usage Report", "monthly")
        self.usage_report_type.addItem("Date Range Usage Report", "date_range")
        self.usage_report_type.addItem("Usage by Grade Level", "grade_level")
        self.usage_report_type.setCurrentIndex(0)  # Default to Monthly
        self.usage_report_type.currentIndexChanged.connect(
            self.on_usage_report_type_changed
        )
        type_layout.addWidget(self.usage_report_type)
        layout.addWidget(type_group)

        # Monthly Report Configuration Section
        self.monthly_config_widget = QWidget()
        monthly_layout = QVBoxLayout(self.monthly_config_widget)
        monthly_layout.setSpacing(6)  # Reduce spacing
        monthly_layout.setContentsMargins(0, 0, 0, 0)

        # Month Selection
        month_group = QGroupBox("📅 Select Month")
        month_layout = QVBoxLayout(month_group)
        month_layout.setSpacing(4)
        month_layout.setContentsMargins(8, 8, 8, 8)

        # Year selection
        year_layout = QHBoxLayout()
        year_layout.addWidget(QLabel("Year:"))
        self.monthly_year_spin = QSpinBox()
        self.monthly_year_spin.setRange(2020, 2100)
        self.monthly_year_spin.setValue(date.today().year)
        year_layout.addWidget(self.monthly_year_spin)
        month_layout.addLayout(year_layout)

        # Month selection
        month_select_layout = QHBoxLayout()
        month_select_layout.addWidget(QLabel("Month:"))
        self.monthly_month_combo = QComboBox()
        months = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
        self.monthly_month_combo.addItems(months)
        self.monthly_month_combo.setCurrentIndex(date.today().month - 1)
        month_select_layout.addWidget(self.monthly_month_combo)
        month_layout.addLayout(month_select_layout)

        monthly_layout.addWidget(month_group)

        # Category Filter
        filters_group = QGroupBox("🔍 Filters")
        filters_layout = QVBoxLayout(filters_group)
        filters_layout.setSpacing(4)
        filters_layout.setContentsMargins(8, 8, 8, 8)

        category_layout = QHBoxLayout()
        category_layout.addWidget(QLabel("Category:"))
        self.monthly_category_combo = QComboBox()
        self.monthly_category_combo.addItem("All Categories")
        self.load_categories(self.monthly_category_combo)
        category_layout.addWidget(self.monthly_category_combo)
        filters_layout.addLayout(category_layout)

        monthly_layout.addWidget(filters_group)

        # Info box for Monthly
        monthly_info_text = QTextEdit()
        monthly_info_text.setReadOnly(True)
        monthly_info_text.setMinimumHeight(70)
        monthly_info_text.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        monthly_info_text.setPlainText(
            "Monthly Usage Report generates an Excel file with:\n"
            "• Items grouped by category (Apparatus, Equipment, etc.)\n"
            "• Weekly breakdown within the selected month (PRE, WEEK 1-4, POST)\n"
            "• Total usage per item and category\n"
            "• Matches sample Excel format for lab activity reporting"
        )
        monthly_layout.addWidget(monthly_info_text)
        monthly_layout.addStretch()

        layout.addWidget(self.monthly_config_widget)

        # Date Range Report Configuration Section
        self.date_range_config_widget = QWidget()
        date_range_layout = QVBoxLayout(self.date_range_config_widget)
        date_range_layout.setSpacing(6)  # Reduce spacing
        date_range_layout.setContentsMargins(0, 0, 0, 0)

        # Date Range Section
        date_group = QGroupBox("📅 Date Range")
        date_layout = QVBoxLayout(date_group)
        date_layout.setSpacing(4)
        date_layout.setContentsMargins(8, 8, 8, 8)

        self.date_range_selector = DateRangeSelector()
        date_layout.addWidget(self.date_range_selector)

        # Preset date ranges
        preset_layout = QHBoxLayout()
        preset_layout.setSpacing(4)
        from inventory_app.gui.reports.report_config import ReportConfig

        preset_layout.addWidget(QLabel(ReportConfig.LABELS["quick_select"]))

        self.preset_combo = QComboBox()
        self.preset_combo.addItems(
            [
                "Custom Range",
                "Last 7 Days",
                "Last 30 Days",
                "Last 90 Days",
                "This Month",
                "Last Month",
                "This Year",
                "Last Year",
            ]
        )
        self.preset_combo.currentTextChanged.connect(self.on_preset_changed)
        preset_layout.addWidget(self.preset_combo)

        date_layout.addLayout(preset_layout)
        date_range_layout.addWidget(date_group)

        # Filters Section
        filters_group = QGroupBox("🔍 Filters")
        filters_layout = QVBoxLayout(filters_group)
        filters_layout.setSpacing(4)
        filters_layout.setContentsMargins(8, 8, 8, 8)

        # Category filter
        category_layout = QHBoxLayout()
        category_layout.setSpacing(4)
        category_layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItem("All Categories")
        self.load_categories()
        category_layout.addWidget(self.category_combo)
        filters_layout.addLayout(category_layout)

        # Individual requests filter
        self.show_individual_only_check = QCheckBox("Show only individual requests")
        filters_layout.addWidget(self.show_individual_only_check)

        # Grade/Section simplified filter (for Usage by Grade Level report)
        self.usage_grade_section_widget = QWidget()
        grade_section_layout = QHBoxLayout(self.usage_grade_section_widget)
        grade_section_layout.setSpacing(4)
        grade_section_layout.setContentsMargins(0, 0, 0, 0)

        grade_section_layout.addWidget(QLabel("Filter by:"))
        self.usage_filter_type_combo = QComboBox()
        # Provide an explicit 'All' option and choices for Grade Level or Section
        self.usage_filter_type_combo.addItems(
            ["All Grades & Sections", "Grade Level", "Section"]
        )
        self.usage_filter_type_combo.setCurrentIndex(0)
        self.usage_filter_type_combo.currentIndexChanged.connect(
            self.on_usage_filter_type_changed
        )
        grade_section_layout.addWidget(self.usage_filter_type_combo)

        self.usage_filter_value_combo = QComboBox()
        # Hidden by default; appears when Grade Level or Section is selected
        self.usage_filter_value_combo.setVisible(False)
        grade_section_layout.addWidget(self.usage_filter_value_combo)

        self.usage_grade_section_widget.setVisible(False)
        filters_layout.addWidget(self.usage_grade_section_widget)

        # Consumable filter
        self.consumable_check = QCheckBox("Include consumable items")
        self.consumable_check.setChecked(True)
        filters_layout.addWidget(self.consumable_check)

        date_range_layout.addWidget(filters_group)

        # Info box for Date Range
        date_range_info_text = QTextEdit()
        date_range_info_text.setReadOnly(True)
        date_range_info_text.setMinimumHeight(70)
        date_range_info_text.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        date_range_info_text.setPlainText(
            "Date Range Usage Report generates an Excel file with:\n"
            "• Time-series analysis for any date range\n"
            "• Automatic granularity selection (Daily, Weekly, Monthly, Yearly)\n"
            "• Filterable by category\n"
            "• Includes or excludes consumable items based on selection"
        )
        date_range_layout.addWidget(date_range_info_text)
        date_range_layout.addStretch()

        layout.addWidget(self.date_range_config_widget)

        # Initially show monthly config, hide date range
        self.date_range_config_widget.setVisible(False)

        return tab

    def create_inventory_tab(self) -> QWidget:
        """Create inventory reports configuration tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)

        # Report Type Selection
        type_group = QGroupBox("📋 Report Type")
        type_layout = QVBoxLayout(type_group)
        type_layout.setSpacing(4)
        type_layout.setContentsMargins(8, 8, 8, 8)

        self.inventory_report_type = QComboBox()
        self.inventory_report_type.addItems(
            [
                "Stock Levels Report",
                "Expiration Report",
                "Calibration Due Report",
                "Update History Report",
                "Disposal History Report",
                "Defective Items Report",
                "Low Stock Alert",
                "Acquisition History",
                "Item Usage Details",
                "Batch Summary",
            ]
        )
        self.inventory_report_type.currentTextChanged.connect(
            self._on_inventory_report_type_changed
        )
        type_layout.addWidget(self.inventory_report_type)
        layout.addWidget(type_group)

        # Date Range (for acquisition history)
        date_group = QGroupBox("📅 Date Range (for History Reports)")
        date_layout = QVBoxLayout(date_group)
        date_layout.setSpacing(4)
        date_layout.setContentsMargins(8, 8, 8, 8)

        self.inventory_date_selector = DateRangeSelector()
        date_layout.addWidget(self.inventory_date_selector)
        layout.addWidget(date_group)

        # Filters
        filters_group = QGroupBox("🔍 Filters")
        filters_layout = QVBoxLayout(filters_group)
        filters_layout.setSpacing(4)
        filters_layout.setContentsMargins(8, 8, 8, 8)

        # Category filter
        category_layout = QHBoxLayout()
        category_layout.setSpacing(4)
        category_layout.addWidget(QLabel("Category:"))
        self.inv_category_combo = QComboBox()
        self.inv_category_combo.addItem("All Categories")
        self.load_categories(self.inv_category_combo)
        category_layout.addWidget(self.inv_category_combo)
        filters_layout.addLayout(category_layout)

        # Low stock threshold container (for Low Stock Alert)
        self.threshold_widget = QWidget()
        threshold_layout = QHBoxLayout(self.threshold_widget)
        threshold_layout.setSpacing(4)
        threshold_layout.setContentsMargins(0, 0, 0, 0)
        threshold_layout.addWidget(QLabel("Threshold (units):"))
        self.low_stock_threshold = QSpinBox()
        self.low_stock_threshold.setRange(0, 9999)
        self.low_stock_threshold.setValue(5)
        threshold_layout.addWidget(self.low_stock_threshold)
        self.threshold_widget.setVisible(False)
        filters_layout.addWidget(self.threshold_widget)

        # Item name filter container (for Item Usage Details and Batch Summary)
        self.item_name_widget = QWidget()
        item_name_layout = QHBoxLayout(self.item_name_widget)
        item_name_layout.setSpacing(4)
        item_name_layout.setContentsMargins(0, 0, 0, 0)
        item_name_layout.addWidget(QLabel("Item Name:"))
        self.item_name_filter = QLineEdit()
        self.item_name_filter.setPlaceholderText("Search by item name...")
        item_name_layout.addWidget(self.item_name_filter)
        self.item_name_widget.setVisible(False)
        filters_layout.addWidget(self.item_name_widget)

        layout.addWidget(filters_group)

        layout.addStretch()
        return tab

    def create_trends_tab(self) -> QWidget:
        """Create the trends reports configuration tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)

        # Date Range
        date_group = QGroupBox("📅 Date Range")
        date_layout = QVBoxLayout(date_group)
        date_layout.setSpacing(4)
        date_layout.setContentsMargins(8, 8, 8, 8)
        self.trends_date_selector = DateRangeSelector()
        date_layout.addWidget(self.trends_date_selector)
        layout.addWidget(date_group)

        # Granularity
        gran_group = QGroupBox("📈 Granularity")
        gran_layout = QHBoxLayout(gran_group)
        gran_layout.setSpacing(4)
        gran_layout.setContentsMargins(8, 8, 8, 8)
        self.trends_granularity = QComboBox()
        self.trends_granularity.addItems(
            ["Auto", "Daily", "Weekly", "Monthly", "Yearly"]
        )
        from inventory_app.gui.reports.report_config import ReportConfig

        self.trends_granularity.setToolTip(ReportConfig.GRANULARITY_TOOLTIP)
        gran_layout.addWidget(self.trends_granularity)
        layout.addWidget(gran_group)

        # Group By and Top N
        options_group = QGroupBox("⚙️ Options")
        options_layout = QVBoxLayout(options_group)
        options_layout.setSpacing(4)
        options_layout.setContentsMargins(8, 8, 8, 8)

        group_layout = QHBoxLayout()
        group_layout.setSpacing(4)
        group_layout.addWidget(QLabel(ReportConfig.LABELS["group_by"]))
        self.trends_group_by = QComboBox()
        self.trends_group_by.addItems(["Item", "Category"])
        group_layout.addWidget(self.trends_group_by)
        options_layout.addLayout(group_layout)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(4)
        top_layout.addWidget(QLabel(ReportConfig.LABELS["top_items"]))
        self.trends_top_combo = QComboBox()
        self.trends_top_combo.addItems(["Top 10", "Top 20", "Top 50", "All"])
        top_layout.addWidget(self.trends_top_combo)
        options_layout.addLayout(top_layout)

        # Consumable filter
        self.trends_include_consumables = QCheckBox("Include consumable items")
        self.trends_include_consumables.setChecked(True)
        options_layout.addWidget(self.trends_include_consumables)

        layout.addWidget(options_group)

        layout.addStretch()
        return tab

    def create_status_panel(self) -> QWidget:
        """Create the status and results panel."""
        status_widget = QWidget()
        status_layout = QVBoxLayout(status_widget)
        status_layout.setSpacing(8)
        status_layout.setContentsMargins(0, 0, 0, 0)

        # Status Section
        status_group = QGroupBox("📝 Status")
        status_layout_inner = QVBoxLayout(status_group)
        status_layout_inner.setSpacing(4)
        status_layout_inner.setContentsMargins(8, 8, 8, 8)

        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setPlainText(
            "Ready to generate reports.\n\nSelect your parameters and click 'Generate Report'."
        )
        status_layout_inner.addWidget(self.status_text)

        status_layout.addWidget(status_group)

        # Results Section
        results_group = QGroupBox("📄 Generated Reports")
        results_layout = QVBoxLayout(results_group)
        results_layout.setSpacing(4)
        results_layout.setContentsMargins(8, 8, 8, 8)

        self.results_list = QListWidget()
        results_layout.addWidget(self.results_list)

        status_layout.addWidget(results_group)

        # Recent Reports
        recent_group = QGroupBox("🕒 Recent Reports")
        recent_layout = QVBoxLayout(recent_group)
        recent_layout.setSpacing(4)
        recent_layout.setContentsMargins(8, 8, 8, 8)

        self.recent_reports_text = QTextEdit()
        self.recent_reports_text.setReadOnly(True)
        self.recent_reports_text.setPlainText("No recent reports generated.")
        recent_layout.addWidget(self.recent_reports_text)

        status_layout.addWidget(recent_group)

        return status_widget

    def load_categories(self, combo_box=None):
        """Load categories from database."""
        if combo_box is None:
            combo_box = self.category_combo

        try:
            from inventory_app.database.connection import db

            categories = db.execute_query("SELECT name FROM Categories ORDER BY name")
            if combo_box.count() == 0:
                combo_box.addItem("All Categories")
            if categories:
                for cat in categories:
                    combo_box.addItem(cat["name"])
        except Exception as e:
            logger.error(f"Failed to load categories: {e}")

    def load_grade_levels_combo(self, combo: QComboBox):
        """Load grade levels from database into a given combo box."""
        try:
            from inventory_app.database.connection import db

            grades = db.execute_query(
                "SELECT DISTINCT grade_level FROM Requesters WHERE grade_level IS NOT NULL AND grade_level != '' ORDER BY grade_level"
            )
            if grades:
                for row in grades:
                    combo.addItem(row["grade_level"])
        except Exception as e:
            logger.error(f"Failed to load grade levels: {e}")

    def load_sections_combo(self, combo: QComboBox):
        """Load sections from database into a given combo box."""
        try:
            from inventory_app.database.connection import db

            sections = db.execute_query(
                "SELECT DISTINCT section FROM Requesters WHERE section IS NOT NULL AND section != '' ORDER BY section"
            )
            if sections:
                for row in sections:
                    combo.addItem(row["section"])
        except Exception as e:
            logger.error(f"Failed to load sections: {e}")

    def _on_inventory_report_type_changed(self, report_type: str):
        """Handle inventory report type dropdown changes to show/hide appropriate inputs."""
        self.threshold_widget.setVisible(report_type == "Low Stock Alert")

        self.item_name_widget.setVisible(
            report_type in {"Item Usage Details", "Batch Summary"}
        )

        self.inv_category_combo.setEnabled(
            report_type
            not in {"Item Usage Details", "Batch Summary", "Low Stock Alert"}
        )

        if report_type in {
            "Stock Levels Report",
            "Low Stock Alert",
            "Item Usage Details",
            "Batch Summary",
        }:
            self.inventory_date_selector.setEnabled(False)
        else:
            self.inventory_date_selector.setEnabled(True)

    def load_suppliers(self):
        """Load suppliers from database (deprecated - no longer used)."""
        pass

    def on_report_type_changed(self, index):
        """Handle report type tab changes."""
        report_types = ["usage", "inventory", "trends"]
        self.current_report_type = report_types[index]

    def on_usage_report_type_changed(self):
        """Handle usage report type dropdown changes."""
        report_type = self.usage_report_type.currentData()
        if report_type == "monthly":
            self.monthly_config_widget.setVisible(True)
            self.date_range_config_widget.setVisible(False)
            self.usage_grade_section_widget.setVisible(False)
        elif report_type == "grade_level":
            self.monthly_config_widget.setVisible(False)
            self.date_range_config_widget.setVisible(True)
            self.usage_grade_section_widget.setVisible(True)
        else:  # date_range
            self.monthly_config_widget.setVisible(False)
            self.date_range_config_widget.setVisible(True)
            self.usage_grade_section_widget.setVisible(False)

    def on_usage_filter_type_changed(self):
        """Handle filter type selection changes (Grade Level/Section or All)."""
        filter_type = self.usage_filter_type_combo.currentText()
        self.usage_filter_value_combo.clear()
        if filter_type == "Grade Level":
            self.usage_filter_value_combo.addItem("All Grades")
            self.load_grade_levels_combo(self.usage_filter_value_combo)
            self.usage_filter_value_combo.setVisible(True)
            self.usage_filter_value_combo.setEnabled(True)
        elif filter_type == "Section":
            self.usage_filter_value_combo.addItem("All Sections")
            self.load_sections_combo(self.usage_filter_value_combo)
            self.usage_filter_value_combo.setVisible(True)
            self.usage_filter_value_combo.setEnabled(True)
        else:
            # 'All Grades & Sections' selected - hide the detail selector
            self.usage_filter_value_combo.setVisible(False)
            self.usage_filter_value_combo.setEnabled(False)

    def on_preset_changed(self, preset):
        """Handle preset date range selection."""
        today = date.today()
        if preset == "Last 7 Days":
            start_date = today - timedelta(days=7)
            self.date_range_selector.set_date_range(
                QDate(start_date.year, start_date.month, start_date.day),
                QDate(today.year, today.month, today.day),
            )
        elif preset == "Last 30 Days":
            start_date = today - timedelta(days=30)
            self.date_range_selector.set_date_range(
                QDate(start_date.year, start_date.month, start_date.day),
                QDate(today.year, today.month, today.day),
            )
        elif preset == "Last 90 Days":
            start_date = today - timedelta(days=90)
            self.date_range_selector.set_date_range(
                QDate(start_date.year, start_date.month, start_date.day),
                QDate(today.year, today.month, today.day),
            )
        elif preset == "This Month":
            start_date = today.replace(day=1)
            self.date_range_selector.set_date_range(
                QDate(start_date.year, start_date.month, start_date.day),
                QDate(today.year, today.month, today.day),
            )
        elif preset == "Last Month":
            # Get first day of last month
            first_of_this_month = today.replace(day=1)
            last_month_end = first_of_this_month - timedelta(days=1)
            start_date = last_month_end.replace(day=1)
            self.date_range_selector.set_date_range(
                QDate(start_date.year, start_date.month, start_date.day),
                QDate(last_month_end.year, last_month_end.month, last_month_end.day),
            )
        elif preset == "This Year":
            start_date = today.replace(month=1, day=1)
            self.date_range_selector.set_date_range(
                QDate(start_date.year, start_date.month, start_date.day),
                QDate(today.year, today.month, today.day),
            )
        elif preset == "Last Year":
            start_date = today.replace(year=today.year - 1, month=1, day=1)
            end_date = start_date.replace(month=12, day=31)
            self.date_range_selector.set_date_range(
                QDate(start_date.year, start_date.month, start_date.day),
                QDate(end_date.year, end_date.month, end_date.day),
            )

    def generate_report(self):
        """Generate the selected report type."""
        try:
            # Disable generate button and show progress
            self.generate_btn.setEnabled(False)
            self.generate_btn.setText("Generating Report...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # Indeterminate progress

            # Clear previous status
            if self.ui_updater:
                self.ui_updater.clear_status()
                self.ui_updater.update_status(
                    f"Generating {self.current_report_type} report..."
                )

            # Generate based on current tab
            if self.current_report_type == "usage":
                # Check which usage report type is selected
                usage_type = self.usage_report_type.currentData()
                if usage_type == "monthly":
                    self.generate_monthly_usage_report()
                elif usage_type == "grade_level":
                    self.generate_usage_by_grade_level_report()
                else:  # date_range
                    self.generate_usage_report()
            elif self.current_report_type == "inventory":
                self.generate_inventory_report()
            elif self.current_report_type == "trends":
                self.generate_trends_report()
            else:
                QMessageBox.critical(
                    self, "Error", f"Unknown report type: {self.current_report_type}"
                )
                self.reset_ui()

        except Exception as e:
            logger.error(f"Failed to start report generation: {e}")
            QMessageBox.critical(
                self, "Error", f"Failed to start report generation: {str(e)}"
            )
            self.reset_ui()

    def generate_monthly_usage_report(self):
        """Generate monthly usage report in the beta test format.

        Per beta test requirements #20, #21:
        - Report format matches sample Excel files
        - Items grouped by category (Apparatus, Equipment, etc.)
        - Weekly breakdown within selected month
        """
        try:
            year = self.monthly_year_spin.value()
            month = self.monthly_month_combo.currentIndex() + 1

            category_filter = self.monthly_category_combo.currentText()
            if category_filter == "All Categories":
                category_filter = ""

            report_style = "detailed"  # Default to full title

            # Update status
            if self.ui_updater:
                month_name = self.monthly_month_combo.currentText()
                self.ui_updater.update_status(
                    f"Generating monthly report for {month_name} {year}..."
                )

            # Import and generate the monthly report
            from inventory_app.gui.reports.monthly_usage_report import (
                generate_monthly_usage_report,
            )

            result = generate_monthly_usage_report(
                year=year,
                month=month,
                category_filter=category_filter,
                report_style=report_style,
            )

            if result.startswith("Error") or result.startswith("No data"):
                self.on_report_error(result)
            else:
                self.on_report_finished(result)

        except Exception as e:
            logger.error(f"Failed to generate monthly usage report: {e}")
            self.on_report_error(str(e))

    def generate_usage_report(self):
        """Generate usage report with current configuration."""
        start_date, end_date = self.date_range_selector.to_py_dates()

        if start_date > end_date:
            QMessageBox.warning(
                self, "Invalid Date Range", "Start date cannot be after end date."
            )
            self.reset_ui()
            return

        # Get filter values
        category_filter = self.category_combo.currentText()
        if category_filter == "All Categories":
            category_filter = ""

        include_consumables = self.consumable_check.isChecked()
        show_individual_only = self.show_individual_only_check.isChecked()

        # Start background worker
        self.worker = ReportWorker(
            "usage",
            start_date,
            end_date,
            category_filter=category_filter,
            include_consumables=include_consumables,
            show_individual_only=show_individual_only,
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_report_finished)
        self.worker.error.connect(self.on_report_error)
        self.worker.start()

    def generate_usage_by_grade_level_report(self):
        """Generate usage by grade level report with current configuration."""
        start_date, end_date = self.date_range_selector.to_py_dates()

        if start_date > end_date:
            QMessageBox.warning(
                self, "Invalid Date Range", "Start date cannot be after end date."
            )
            self.reset_ui()
            return

        category_filter = self.category_combo.currentText()
        if category_filter == "All Categories":
            category_filter = ""

        filter_type = self.usage_filter_type_combo.currentText()
        filter_value = ""
        if filter_type == "Grade Level":
            filter_value = self.usage_filter_value_combo.currentText()
            if filter_value == "All Grades":
                filter_value = ""
        elif filter_type == "Section":
            filter_value = self.usage_filter_value_combo.currentText()
            if filter_value == "All Sections":
                filter_value = ""

        show_individual_only = self.show_individual_only_check.isChecked()

        grade_filter = filter_value if filter_type == "Grade Level" else ""
        section_filter = filter_value if filter_type == "Section" else ""

        self.worker = ReportWorker(
            "usage",
            start_date,
            end_date,
            category_filter=category_filter,
            usage_report_type="grade_level",
            grade_filter=grade_filter,
            section_filter=section_filter,
            show_individual_only=show_individual_only,
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_report_finished)
        self.worker.error.connect(self.on_report_error)
        self.worker.start()

    def generate_inventory_report(self):
        """Generate inventory report."""
        start_date, end_date = self.inventory_date_selector.to_py_dates()

        if start_date > end_date:
            QMessageBox.warning(
                self, "Invalid Date Range", "Start date cannot be after end date."
            )
            self.reset_ui()
            return

        inventory_report_type = self.inventory_report_type.currentText()

        # Build kwargs based on report type
        kwargs: dict[str, object] = {
            "inventory_report_type": inventory_report_type,
        }

        # Category filter (used differently for some reports)
        category_filter = self.inv_category_combo.currentText()
        if category_filter == "All Categories":
            category_filter = ""

        # Report-specific filters
        if inventory_report_type == "Low Stock Alert":
            kwargs["low_stock_threshold"] = self.low_stock_threshold.value()
        elif inventory_report_type in {"Item Usage Details", "Batch Summary"}:
            kwargs["item_name_filter"] = self.item_name_filter.text().strip()

        # Only pass category filter for reports that use it
        if inventory_report_type not in {
            "Item Usage Details",
            "Batch Summary",
            "Low Stock Alert",
        }:
            kwargs["category_filter"] = category_filter

        # Start background worker
        self.worker = ReportWorker(
            "inventory",
            start_date,
            end_date,
            **kwargs,
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_report_finished)
        self.worker.error.connect(self.on_report_error)
        self.worker.start()

    def generate_trends_report(self):
        """Generate trends report based on current selection."""
        start_date, end_date = self.trends_date_selector.to_py_dates()

        if start_date > end_date:
            QMessageBox.warning(
                self, "Invalid Date Range", "Start date cannot be after end date."
            )
            self.reset_ui()
            return

        group_by = self.trends_group_by.currentText()
        group_by_key = "item" if group_by == "Item" else "category"

        top_text = self.trends_top_combo.currentText()
        top_n = None
        if top_text.startswith("Top"):
            try:
                top_n = int(top_text.split()[1])
            except Exception:
                top_n = None

        include_consumables = self.trends_include_consumables.isChecked()

        gran_text = self.trends_granularity.currentText().lower()
        granularity = None if gran_text == "auto" else gran_text

        # Start background worker
        self.worker = ReportWorker(
            "trends",
            start_date,
            end_date,
            granularity=granularity,
            group_by=group_by_key,
            top_n=top_n,
            include_consumables=include_consumables,
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_report_finished)
        self.worker.error.connect(self.on_report_error)
        self.worker.start()

    def update_progress(self, message):
        """Update progress message."""
        if self.ui_updater:
            self.ui_updater.update_status(message)

    def on_report_finished(self, file_path):
        """Handle successful report generation."""
        if self.ui_updater is None:
            return

        # Update status
        self.ui_updater.update_status("✅ Report generated successfully!")
        self.ui_updater.update_status(f"📁 File saved to: {file_path}")

        # Add to results list
        self.results_list.addItem(f"✅ {os.path.basename(file_path)}")

        # Update recent reports
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.ui_updater.add_recent_report(os.path.basename(file_path), timestamp)

        # Try to open the file
        try:
            os.startfile(file_path)  # Windows specific
            self.ui_updater.update_status("📂 Opening Excel file...")
        except Exception as e:
            self.ui_updater.update_status(f"Could not auto-open file: {str(e)}")

        self.reset_ui()

    def on_report_error(self, error_message):
        """Handle report generation error."""
        if self.ui_updater is None:
            return

        self.ui_updater.update_status(f"❌ Error: {error_message}")
        QMessageBox.critical(self, "Report Generation Failed", error_message)
        self.reset_ui()

    def reset_ui(self):
        """Reset UI after report generation completes."""
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText("🚀 Generate Report")
        self.progress_bar.setVisible(False)
        self.worker = None
