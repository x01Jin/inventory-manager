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
    QListWidgetItem,
    QSpinBox,
    QSplitter,
    QMessageBox,
    QTabWidget,
    QSizePolicy,
    QLineEdit,
    QInputDialog,
    QApplication,
)
from PyQt6.QtCore import Qt, QDate, QTimer, QMimeData, QUrl

from inventory_app.gui.reports.ui_components import ReportUIUpdater
from inventory_app.gui.reports.report_worker import ReportWorker
from inventory_app.gui.utils.worker import Worker, worker_pool
from inventory_app.gui.reports.report_paths import (
    get_reports_directory,
    list_report_files,
)
from inventory_app.services.category_config import get_all_category_names
from inventory_app.utils.activity_logger import activity_logger
from inventory_app.utils.logger import logger
from inventory_app.gui.widgets.date_selector import DateRangeSelector
from inventory_app.gui.styles import ThemeManager

import os
from pathlib import Path
from datetime import datetime, date, timedelta


class ReportsPage(QWidget):
    """Reports page with multiple report types and modern UI."""

    def __init__(self):
        super().__init__()
        self.worker = None
        self._selector_refresh_worker = None
        self._category_refresh_worker = None
        self._report_files_worker = None
        self._pending_report_selection = ""
        self._is_disposing = False
        self.ui_updater = None
        self.current_report_type = "usage"
        self._generated_report_paths: list[str] = []
        self._reports_poll_timer = QTimer(self)
        self._reports_poll_timer.setInterval(3000)
        self._reports_poll_timer.timeout.connect(self.schedule_report_files_refresh)
        self.destroyed.connect(self._on_destroyed)
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
        self.refresh_data()

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

        # Audit Log Reports Tab
        audit_tab = self.create_audit_tab()
        self.tab_widget.addTab(audit_tab, "📋 Audit Log")

        config_layout.addWidget(
            self.tab_widget, 1
        )  # Stretch factor 1: takes remaining space

        # Generate Button
        self.generate_btn = QPushButton("🚀 Generate Report")
        self.generate_btn.clicked.connect(self.generate_report)
        config_layout.addWidget(self.generate_btn, 0)  # Stretch factor 0: stays compact

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(12)
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
            "• Grade 7-10 tally columns per item\n"
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

        category_layout = QHBoxLayout()
        category_layout.setSpacing(4)
        category_layout.addWidget(QLabel("Category:"))
        self.trends_category_combo = QComboBox()
        self.trends_category_combo.addItem("All Categories")
        category_layout.addWidget(self.trends_category_combo)
        options_layout.addLayout(category_layout)

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

    def create_audit_tab(self) -> QWidget:
        """Create dedicated Task 9 audit log report configuration tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)

        date_group = QGroupBox("📅 Date Range")
        date_layout = QVBoxLayout(date_group)
        date_layout.setSpacing(4)
        date_layout.setContentsMargins(8, 8, 8, 8)
        self.audit_date_selector = DateRangeSelector()
        date_layout.addWidget(self.audit_date_selector)
        layout.addWidget(date_group)

        filters_group = QGroupBox("🔍 Audit Filters")
        filters_layout = QVBoxLayout(filters_group)
        filters_layout.setSpacing(4)
        filters_layout.setContentsMargins(8, 8, 8, 8)

        editor_layout = QHBoxLayout()
        editor_layout.setSpacing(4)
        editor_layout.addWidget(QLabel("Editor Name/Initials:"))
        self.audit_editor_filter = QLineEdit()
        self.audit_editor_filter.setPlaceholderText("Optional: filter by editor")
        editor_layout.addWidget(self.audit_editor_filter)
        filters_layout.addLayout(editor_layout)

        action_layout = QHBoxLayout()
        action_layout.setSpacing(4)
        action_layout.addWidget(QLabel("Action Type:"))
        self.audit_action_filter = QComboBox()
        self.audit_action_filter.addItems(
            [
                "All Actions",
                "ITEM_UPDATE",
                "REQUISITION_UPDATE",
                "ITEM_DISPOSAL",
                "DEFECTIVE_RECORDED",
                "DEFECTIVE_DISPOSED",
                "DEFECTIVE_NOT_DEFECTIVE",
                "ITEM_ADDED",
                "ITEM_EDITED",
                "ITEM_DELETED",
                "SDS_UPLOADED",
                "SDS_REMOVED",
                "REQUISITION_CREATED",
                "REQUISITION_EDITED",
                "REQUISITION_RETURNED",
                "REQUISITION_DELETED",
                "REQUESTER_ADDED",
                "REQUESTER_EDITED",
                "REQUESTER_DELETED",
                "REPORT_GENERATED",
                "REPORT_DELETED",
                "STOCK_RECEIVED",
                "STOCK_ADJUSTED",
            ]
        )
        action_layout.addWidget(self.audit_action_filter)
        filters_layout.addLayout(action_layout)

        entity_layout = QHBoxLayout()
        entity_layout.setSpacing(4)
        entity_layout.addWidget(QLabel("Entity Type:"))
        self.audit_entity_filter = QComboBox()
        self.audit_entity_filter.addItems(
            ["All Entities", "item", "requisition", "requester", "stock", "report"]
        )
        entity_layout.addWidget(self.audit_entity_filter)
        filters_layout.addLayout(entity_layout)

        layout.addWidget(filters_group)

        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setMinimumHeight(80)
        info_text.setPlainText(
            "Audit Log Report provides centralized change history across item edits,\n"
            "requisition updates, disposals, defective recordings, and activity events.\n"
            "Use filters to isolate editor actions and verify field-level old/new values."
        )
        layout.addWidget(info_text)
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

        actions_layout = QHBoxLayout()
        self.refresh_reports_btn = QPushButton("🔄 Refresh")
        self.refresh_reports_btn.clicked.connect(
            lambda: self.schedule_report_files_refresh(force=True)
        )
        actions_layout.addWidget(self.refresh_reports_btn)

        self.open_report_btn = QPushButton("📂 Open Report")
        self.open_report_btn.setEnabled(False)
        self.open_report_btn.clicked.connect(self.open_selected_report)
        actions_layout.addWidget(self.open_report_btn)

        self.open_report_folder_btn = QPushButton("🗂️ Open Folder")
        self.open_report_folder_btn.setEnabled(True)
        self.open_report_folder_btn.clicked.connect(self.open_selected_report_folder)
        actions_layout.addWidget(self.open_report_folder_btn)

        self.copy_report_btn = QPushButton("📋 Copy File")
        self.copy_report_btn.setEnabled(False)
        self.copy_report_btn.clicked.connect(self.copy_selected_report)
        actions_layout.addWidget(self.copy_report_btn)

        self.delete_report_btn = QPushButton("🗑️ Delete")
        self.delete_report_btn.setEnabled(False)
        self.delete_report_btn.clicked.connect(self.delete_selected_report)
        actions_layout.addWidget(self.delete_report_btn)

        actions_layout.addStretch()
        results_layout.addLayout(actions_layout)

        self.results_list.currentRowChanged.connect(self._on_results_selection_changed)
        self.results_list.itemDoubleClicked.connect(
            lambda _item: self.open_selected_report()
        )

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
        """Load canonical categories into a combo box."""
        if combo_box is None:
            combo_box = self.category_combo

        try:
            while combo_box.count() > 1:
                combo_box.removeItem(1)

            if combo_box.count() == 0:
                combo_box.addItem("All Categories")

            for category in get_all_category_names():
                combo_box.addItem(category)
        except Exception as e:
            logger.error(f"Failed to load categories: {e}")

    def _get_category_combos(self) -> list[QComboBox]:
        """Return all category filter combo boxes managed by this page."""
        return [
            self.monthly_category_combo,
            self.category_combo,
            self.inv_category_combo,
            self.trends_category_combo,
        ]

    @staticmethod
    def _load_category_names() -> list[str]:
        """Load category names in a worker thread."""
        return list(get_all_category_names())

    @staticmethod
    def _scan_report_files() -> list[str]:
        """Scan report directory and return absolute Excel file paths."""
        return [str(path.resolve()) for path in list_report_files()]

    def _refresh_categories_async(self):
        """Refresh category dropdown values without blocking GUI."""
        if self._is_disposing:
            return

        if self._category_refresh_worker is not None:
            self._category_refresh_worker.cancel()
            self._category_refresh_worker = None

        worker = Worker(self._load_category_names)
        self._category_refresh_worker = worker
        worker.signals.result.connect(self._on_categories_loaded)
        worker.signals.error.connect(self._on_categories_error)
        worker.signals.finished.connect(self._clear_category_refresh_worker)
        worker_pool.start(worker)

    def _on_categories_loaded(self, categories: list[str]):
        """Populate all category combos with latest category values."""
        if self._is_disposing:
            return

        for combo in self._get_category_combos():
            selected_text = combo.currentText().strip()
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("All Categories")
            for category in categories:
                combo.addItem(category)

            if selected_text and combo.findText(selected_text) >= 0:
                combo.setCurrentText(selected_text)
            else:
                combo.setCurrentText("All Categories")
            combo.blockSignals(False)

    def _on_categories_error(self, error_info):
        """Handle category worker failure."""
        logger.error(f"Failed to refresh report categories: {error_info}")

    def _clear_category_refresh_worker(self):
        """Release category worker reference after completion."""
        self._category_refresh_worker = None

    def schedule_report_files_refresh(self, force: bool = False):
        """Schedule asynchronous refresh of generated report files list."""
        if self._is_disposing:
            return

        if self._report_files_worker is not None and not force:
            return

        if self._report_files_worker is not None:
            self._report_files_worker.cancel()
            self._report_files_worker = None

        worker = Worker(self._scan_report_files)
        self._report_files_worker = worker
        worker.signals.result.connect(self._on_report_files_loaded)
        worker.signals.error.connect(self._on_report_files_error)
        worker.signals.finished.connect(self._clear_report_files_worker)
        worker_pool.start(worker)

    def _on_report_files_loaded(self, file_paths: list[str]):
        """Render generated report list from actual files in reports directory."""
        if self._is_disposing:
            return

        selected_path = (
            self._pending_report_selection or self._get_selected_report_path()
        )
        self._pending_report_selection = ""

        self._generated_report_paths = file_paths

        self.results_list.blockSignals(True)
        self.results_list.clear()
        for file_path in file_paths:
            self.results_list.addItem(QListWidgetItem(f"✅ {Path(file_path).name}"))
        self.results_list.blockSignals(False)

        new_row = -1
        if selected_path and selected_path in self._generated_report_paths:
            new_row = self._generated_report_paths.index(selected_path)

        if new_row >= 0:
            self.results_list.setCurrentRow(new_row)
        else:
            self.results_list.setCurrentRow(-1)

        self._on_results_selection_changed(self.results_list.currentRow())

    def _on_report_files_error(self, error_info):
        """Handle file list refresh failures."""
        logger.error(f"Failed to refresh report files: {error_info}")

    def _clear_report_files_worker(self):
        """Release report files worker reference after completion."""
        self._report_files_worker = None

    @staticmethod
    def _normalized_combo_value(combo_box: QComboBox, all_label: str) -> str:
        """Return normalized combo value where sentinel "all" becomes empty."""
        current_text = combo_box.currentText().strip()
        if current_text == all_label:
            return ""
        return current_text

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
        report_types = ["usage", "inventory", "trends", "audit"]
        self.current_report_type = report_types[index]

    def refresh_data(self):
        """Refresh report page dynamic selector data."""
        try:
            self._refresh_categories_async()
            self.on_usage_report_type_changed()
            self.on_usage_filter_type_changed()
            self.schedule_report_files_refresh(force=True)
            if not self._reports_poll_timer.isActive():
                self._reports_poll_timer.start()
        except Exception as e:
            logger.error(f"Failed to refresh reports page data: {e}")

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
            self.usage_filter_value_combo.setVisible(True)
            self.usage_filter_value_combo.setEnabled(False)
            self._refresh_usage_filter_values_async()
        elif filter_type == "Section":
            self.usage_filter_value_combo.addItem("All Sections")
            self.usage_filter_value_combo.setVisible(True)
            self.usage_filter_value_combo.setEnabled(False)
            self._refresh_usage_filter_values_async()
        else:
            # 'All Grades & Sections' selected - hide the detail selector
            self.usage_filter_value_combo.setVisible(False)
            self.usage_filter_value_combo.setEnabled(False)

    @staticmethod
    def _load_usage_filter_values(filter_type: str) -> list[str]:
        """Load usage filter options from DB in a worker thread."""
        from inventory_app.database.connection import db

        if filter_type == "Grade Level":
            rows = db.execute_query(
                "SELECT DISTINCT grade_level FROM Requesters WHERE grade_level IS NOT NULL AND grade_level != '' ORDER BY grade_level",
                use_cache=False,
            )
            return [row["grade_level"] for row in rows if row.get("grade_level")]

        if filter_type == "Section":
            rows = db.execute_query(
                "SELECT DISTINCT section FROM Requesters WHERE section IS NOT NULL AND section != '' ORDER BY section",
                use_cache=False,
            )
            return [row["section"] for row in rows if row.get("section")]

        return []

    def _refresh_usage_filter_values_async(self):
        """Refresh usage filter values without blocking the GUI thread."""
        if self._is_disposing:
            return

        filter_type = self.usage_filter_type_combo.currentText()
        if filter_type not in {"Grade Level", "Section"}:
            return

        if self._selector_refresh_worker is not None:
            self._selector_refresh_worker.cancel()
            self._selector_refresh_worker = None

        worker = Worker(self._load_usage_filter_values, filter_type)
        self._selector_refresh_worker = worker
        worker.signals.result.connect(
            lambda values, expected=filter_type: self._on_usage_filter_values_loaded(
                expected, values
            )
        )
        worker.signals.error.connect(
            lambda error_info, expected=filter_type: self._on_usage_filter_values_error(
                expected, error_info
            )
        )
        worker.signals.finished.connect(self._clear_selector_refresh_worker)
        worker_pool.start(worker)

    def _on_usage_filter_values_loaded(
        self, expected_filter_type: str, values: list[str]
    ):
        """Apply asynchronously loaded usage filter values to the UI."""
        if self._is_disposing:
            return

        if self.usage_filter_type_combo.currentText() != expected_filter_type:
            return

        all_label = (
            "All Grades" if expected_filter_type == "Grade Level" else "All Sections"
        )
        self.usage_filter_value_combo.clear()
        self.usage_filter_value_combo.addItem(all_label)
        for value in values:
            self.usage_filter_value_combo.addItem(value)
        self.usage_filter_value_combo.setVisible(True)
        self.usage_filter_value_combo.setEnabled(True)

    def _on_usage_filter_values_error(self, expected_filter_type: str, error_info):
        """Handle usage filter loading errors without freezing the UI."""
        if self._is_disposing:
            return

        if self.usage_filter_type_combo.currentText() != expected_filter_type:
            return

        all_label = (
            "All Grades" if expected_filter_type == "Grade Level" else "All Sections"
        )
        self.usage_filter_value_combo.clear()
        self.usage_filter_value_combo.addItem(all_label)
        self.usage_filter_value_combo.setVisible(True)
        self.usage_filter_value_combo.setEnabled(True)

        logger.error(
            f"Failed to load {expected_filter_type} filter values: {error_info}"
        )

    def _clear_selector_refresh_worker(self):
        """Drop stale worker reference when refresh completes."""
        self._selector_refresh_worker = None

    def showEvent(self, a0):
        """Resume live report-list polling when page becomes visible."""
        super().showEvent(a0)
        if not self._is_disposing:
            self.schedule_report_files_refresh(force=True)
            if not self._reports_poll_timer.isActive():
                self._reports_poll_timer.start()

    def hideEvent(self, a0):
        """Pause polling when page is hidden to reduce background work."""
        super().hideEvent(a0)
        self._reports_poll_timer.stop()

    def _on_destroyed(self, *_args):
        """Cancel pending selector refresh worker during widget teardown."""
        self._is_disposing = True
        self._reports_poll_timer.stop()
        if self._selector_refresh_worker is not None:
            self._selector_refresh_worker.cancel()
            self._selector_refresh_worker = None
        if self._category_refresh_worker is not None:
            self._category_refresh_worker.cancel()
            self._category_refresh_worker = None
        if self._report_files_worker is not None:
            self._report_files_worker.cancel()
            self._report_files_worker = None

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
            elif self.current_report_type == "audit":
                self.generate_audit_report()
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

            category_filter = self._normalized_combo_value(
                self.monthly_category_combo, "All Categories"
            )

            report_style = "detailed"  # Default to full title

            # Update status
            if self.ui_updater:
                month_name = self.monthly_month_combo.currentText()
                self.ui_updater.update_status(
                    f"Generating monthly report for {month_name} {year}..."
                )

            # Run on background thread to keep UI responsive on heavy datasets.
            month_start = date(year, month, 1)
            if month == 12:
                month_end = date(year, 12, 31)
            else:
                month_end = date(year, month + 1, 1) - timedelta(days=1)

            self.worker = ReportWorker(
                "usage",
                month_start,
                month_end,
                usage_report_type="monthly",
                monthly_year=year,
                monthly_month=month,
                category_filter=category_filter,
                report_style=report_style,
            )
            self.worker.progress.connect(self.update_progress)
            self.worker.finished.connect(self.on_report_finished)
            self.worker.error.connect(self.on_report_error)
            self.worker.start()

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
        category_filter = self._normalized_combo_value(
            self.category_combo, "All Categories"
        )

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

        category_filter = self._normalized_combo_value(
            self.category_combo, "All Categories"
        )

        filter_type = self.usage_filter_type_combo.currentText()
        filter_value = ""
        if filter_type == "Grade Level":
            filter_value = self._normalized_combo_value(
                self.usage_filter_value_combo, "All Grades"
            )
        elif filter_type == "Section":
            filter_value = self._normalized_combo_value(
                self.usage_filter_value_combo, "All Sections"
            )

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
        category_filter = self._normalized_combo_value(
            self.inv_category_combo, "All Categories"
        )

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

        category_filter = self._normalized_combo_value(
            self.trends_category_combo, "All Categories"
        )

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
            category_filter=category_filter,
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_report_finished)
        self.worker.error.connect(self.on_report_error)
        self.worker.start()

    def generate_audit_report(self):
        """Generate centralized Task 9 audit log report."""
        start_date, end_date = self.audit_date_selector.to_py_dates()

        if start_date > end_date:
            QMessageBox.warning(
                self, "Invalid Date Range", "Start date cannot be after end date."
            )
            self.reset_ui()
            return

        editor_filter = self.audit_editor_filter.text().strip()
        action_filter = self._normalized_combo_value(
            self.audit_action_filter, "All Actions"
        )
        entity_filter = self._normalized_combo_value(
            self.audit_entity_filter, "All Entities"
        )

        self.worker = ReportWorker(
            "inventory",
            start_date,
            end_date,
            inventory_report_type="Audit Log Report",
            editor_filter=editor_filter,
            action_filter=action_filter,
            entity_filter=entity_filter,
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

        self._pending_report_selection = os.path.abspath(file_path)
        self.schedule_report_files_refresh(force=True)

        # Update recent reports
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.ui_updater.add_recent_report(os.path.basename(file_path), timestamp)

        self.ui_updater.update_status(
            "✅ Report ready. Use Open Report or Open Folder."
        )

        self.reset_ui()

    def _on_results_selection_changed(self, row: int):
        """Enable/disable report action buttons based on current selection."""
        has_valid_selection = 0 <= row < len(self._generated_report_paths)
        self.open_report_btn.setEnabled(has_valid_selection)
        self.copy_report_btn.setEnabled(has_valid_selection)
        self.delete_report_btn.setEnabled(has_valid_selection)

    def _get_selected_report_path(self) -> str:
        """Return selected generated report path, or empty string if invalid."""
        row = self.results_list.currentRow()
        if 0 <= row < len(self._generated_report_paths):
            return self._generated_report_paths[row]
        return ""

    def open_selected_report(self):
        """Open selected report file with the operating system default handler."""
        file_path = self._get_selected_report_path()
        if not file_path:
            return

        if not os.path.exists(file_path):
            QMessageBox.warning(
                self,
                "Report Missing",
                "The selected report file no longer exists. The list will now refresh.",
            )
            self.schedule_report_files_refresh(force=True)
            return

        try:
            os.startfile(file_path)
            if self.ui_updater:
                self.ui_updater.update_status(
                    f"📂 Opened report: {os.path.basename(file_path)}"
                )
        except Exception as e:
            QMessageBox.warning(
                self, "Open Report Failed", f"Could not open report: {str(e)}"
            )

    def open_selected_report_folder(self):
        """Open folder containing the selected generated report."""
        file_path = self._get_selected_report_path()
        folder_path = (
            os.path.dirname(file_path)
            if file_path
            else str(get_reports_directory(create=True))
        )
        try:
            os.startfile(folder_path)
            if self.ui_updater:
                self.ui_updater.update_status(f"🗂️ Opened folder: {folder_path}")
        except Exception as e:
            QMessageBox.warning(
                self, "Open Folder Failed", f"Could not open folder: {str(e)}"
            )

    def copy_selected_report(self):
        """Copy selected report file to clipboard as an Explorer-compatible file object."""
        file_path = self._get_selected_report_path()
        if not file_path:
            return

        if not os.path.exists(file_path):
            QMessageBox.warning(
                self,
                "Report Missing",
                "The selected report file no longer exists. The list will now refresh.",
            )
            self.schedule_report_files_refresh(force=True)
            return

        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(file_path)])
        mime_data.setText(file_path)
        clipboard = QApplication.clipboard()
        if clipboard is None:
            QMessageBox.warning(
                self,
                "Clipboard Unavailable",
                "Could not access clipboard to copy the selected report.",
            )
            return
        clipboard.setMimeData(mime_data)

        if self.ui_updater:
            self.ui_updater.update_status(
                f"📋 Copied report file: {os.path.basename(file_path)}"
            )

    def delete_selected_report(self):
        """Delete selected report file after confirmation and audit logging."""
        file_path = self._get_selected_report_path()
        if not file_path:
            return

        if not os.path.exists(file_path):
            QMessageBox.warning(
                self,
                "Report Missing",
                "The selected report file no longer exists. The list will now refresh.",
            )
            self.schedule_report_files_refresh(force=True)
            return

        file_name = os.path.basename(file_path)
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete report '{file_name}'?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        editor_name, ok = QInputDialog.getText(
            self,
            "Editor Information",
            "Please enter your name/initials for audit logging:",
        )
        editor_name = editor_name.strip() if ok else ""
        if not editor_name:
            QMessageBox.warning(
                self,
                "Delete Cancelled",
                "Name/initials are required to delete a report file.",
            )
            return

        try:
            Path(file_path).unlink()
            activity_logger.log_activity(
                activity_logger.REPORT_DELETED,
                f"Deleted report file: {file_name} || Deleted file path: {file_path}",
                entity_type="report",
                user_name=editor_name,
            )
            if self.ui_updater:
                self.ui_updater.update_status(f"🗑️ Deleted report: {file_name}")
            self.schedule_report_files_refresh(force=True)
        except FileNotFoundError:
            QMessageBox.warning(
                self,
                "Report Missing",
                "The selected report file was already removed.",
            )
            self.schedule_report_files_refresh(force=True)
        except Exception as e:
            logger.error(f"Failed to delete report file {file_path}: {e}")
            QMessageBox.warning(
                self, "Delete Failed", f"Could not delete report file: {str(e)}"
            )

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
