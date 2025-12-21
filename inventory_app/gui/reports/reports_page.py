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
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

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

        # Report Type Tabs
        self.tab_widget = QTabWidget()
        self.tab_widget.currentChanged.connect(self.on_report_type_changed)

        # Usage Reports Tab
        usage_tab = self.create_usage_tab()
        self.tab_widget.addTab(usage_tab, "📈 Usage Reports")

        # Inventory Reports Tab
        inventory_tab = self.create_inventory_tab()
        self.tab_widget.addTab(inventory_tab, "📦 Inventory Reports")

        # Trends Reports Tab
        trends_tab = self.create_trends_tab()
        self.tab_widget.addTab(trends_tab, "📉 Trends Reports")

        config_layout.addWidget(self.tab_widget)

        # Generate Button
        self.generate_btn = QPushButton("🚀 Generate Report")
        self.generate_btn.clicked.connect(self.generate_report)
        config_layout.addWidget(self.generate_btn)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        config_layout.addWidget(self.progress_bar)

        return config_widget

    def create_usage_tab(self) -> QWidget:
        """Create usage reports configuration tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Date Range Section
        date_group = QGroupBox("📅 Date Range")
        date_layout = QVBoxLayout(date_group)

        self.date_range_selector = DateRangeSelector()
        date_layout.addWidget(self.date_range_selector)

        # Preset date ranges
        preset_layout = QHBoxLayout()
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
        layout.addWidget(date_group)

        # Filters Section
        filters_group = QGroupBox("🔍 Filters")
        filters_layout = QVBoxLayout(filters_group)

        # Category filter
        category_layout = QHBoxLayout()
        from inventory_app.gui.reports.report_config import ReportConfig

        category_layout.addWidget(QLabel(ReportConfig.LABELS["category"]))
        self.category_combo = QComboBox()
        self.category_combo.addItem("All Categories")
        self.load_categories()
        category_layout.addWidget(self.category_combo)
        filters_layout.addLayout(category_layout)

        # Supplier filter
        supplier_layout = QHBoxLayout()
        supplier_layout.addWidget(QLabel(ReportConfig.LABELS["supplier"]))
        self.supplier_combo = QComboBox()
        self.supplier_combo.addItem("All Suppliers")
        self.load_suppliers()
        supplier_layout.addWidget(self.supplier_combo)
        filters_layout.addLayout(supplier_layout)

        # Consumable filter
        self.consumable_check = QCheckBox("Include consumable items")
        self.consumable_check.setChecked(True)
        filters_layout.addWidget(self.consumable_check)

        layout.addWidget(filters_group)

        layout.addStretch()
        return tab

    def create_inventory_tab(self) -> QWidget:
        """Create inventory reports configuration tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Report Type Selection
        type_group = QGroupBox("📋 Report Type")
        type_layout = QVBoxLayout(type_group)

        self.inventory_report_type = QComboBox()
        self.inventory_report_type.addItems(
            [
                "Stock Levels Report",
                "Expiration Report",
                "Low Stock Alert",
                "Acquisition History",
                "Calibration Due Report",
            ]
        )
        type_layout.addWidget(self.inventory_report_type)
        layout.addWidget(type_group)

        # Date Range (for acquisition history)
        date_group = QGroupBox("📅 Date Range (for History Reports)")
        date_layout = QVBoxLayout(date_group)

        self.inventory_date_selector = DateRangeSelector()
        date_layout.addWidget(self.inventory_date_selector)
        layout.addWidget(date_group)

        # Filters
        filters_group = QGroupBox("🔍 Filters")
        filters_layout = QVBoxLayout(filters_group)

        # Category filter
        category_layout = QHBoxLayout()
        category_layout.addWidget(QLabel("Category:"))
        self.inv_category_combo = QComboBox()
        self.inv_category_combo.addItem("All Categories")
        self.load_categories(self.inv_category_combo)
        category_layout.addWidget(self.inv_category_combo)
        filters_layout.addLayout(category_layout)

        layout.addWidget(filters_group)

        # Low stock threshold input (for Low Stock Alert report)
        threshold_group = QGroupBox("⚠️ Low Stock Threshold")
        threshold_layout = QHBoxLayout(threshold_group)
        self.low_stock_spin = QSpinBox()
        self.low_stock_spin.setRange(1, 10000)
        from inventory_app.gui.reports.report_config import ReportConfig

        # If configured to use percentage defaults (None), show spin disabled
        if ReportConfig.DEFAULT_LOW_STOCK_THRESHOLD is None:
            # Show a sensible default but keep disabled to indicate percentage mode
            self.low_stock_spin.setValue(10)
            self.low_stock_spin.setEnabled(False)
        else:
            self.low_stock_spin.setValue(ReportConfig.DEFAULT_LOW_STOCK_THRESHOLD)

        # Checkbox to choose percentage-based thresholds vs absolute units
        self.use_percentage_thresholds = QCheckBox(
            "Use percentage thresholds (Consumables 20% / Non-consumables 10%)"
        )
        self.use_percentage_thresholds.setChecked(
            ReportConfig.DEFAULT_LOW_STOCK_THRESHOLD is None
        )
        self.use_percentage_thresholds.toggled.connect(
            lambda checked: self.low_stock_spin.setEnabled(not checked)
        )
        threshold_layout.addWidget(QLabel(ReportConfig.LABELS["threshold"]))
        threshold_layout.addWidget(self.low_stock_spin)
        threshold_layout.addWidget(self.use_percentage_thresholds)
        layout.addWidget(threshold_group)

        layout.addStretch()
        return tab

    def create_trends_tab(self) -> QWidget:
        """Create the trends reports configuration tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Date Range
        date_group = QGroupBox("📅 Date Range")
        date_layout = QVBoxLayout(date_group)
        self.trends_date_selector = DateRangeSelector()
        date_layout.addWidget(self.trends_date_selector)
        layout.addWidget(date_group)

        # Granularity
        gran_group = QGroupBox("📈 Granularity")
        gran_layout = QHBoxLayout(gran_group)
        self.trends_granularity = QComboBox()
        self.trends_granularity.addItems(
            ["Auto", "Daily", "Weekly", "Monthly", "Quarterly"]
        )
        from inventory_app.gui.reports.report_config import ReportConfig

        self.trends_granularity.setToolTip(ReportConfig.GRANULARITY_TOOLTIP)
        gran_layout.addWidget(self.trends_granularity)
        layout.addWidget(gran_group)

        # Group By and Top N
        options_group = QGroupBox("⚙️ Options")
        options_layout = QVBoxLayout(options_group)

        group_layout = QHBoxLayout()
        group_layout.addWidget(QLabel(ReportConfig.LABELS["group_by"]))
        self.trends_group_by = QComboBox()
        self.trends_group_by.addItems(["Item", "Category"])
        group_layout.addWidget(self.trends_group_by)
        options_layout.addLayout(group_layout)

        top_layout = QHBoxLayout()
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

        # Status Section
        status_group = QGroupBox("📝 Status")
        status_layout_inner = QVBoxLayout(status_group)

        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(150)
        self.status_text.setPlainText(
            "Ready to generate reports.\n\nSelect your parameters and click 'Generate Report'."
        )
        status_layout_inner.addWidget(self.status_text)

        status_layout.addWidget(status_group)

        # Results Section
        results_group = QGroupBox("📄 Generated Reports")
        results_layout = QVBoxLayout(results_group)

        self.results_list = QListWidget()
        self.results_list.setMaximumHeight(200)
        results_layout.addWidget(self.results_list)

        status_layout.addWidget(results_group)

        # Recent Reports
        recent_group = QGroupBox("🕒 Recent Reports")
        recent_layout = QVBoxLayout(recent_group)

        self.recent_reports_text = QTextEdit()
        self.recent_reports_text.setReadOnly(True)
        self.recent_reports_text.setMaximumHeight(150)
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
            if categories:
                for cat in categories:
                    combo_box.addItem(cat["name"])
        except Exception as e:
            logger.error(f"Failed to load categories: {e}")

    def load_suppliers(self):
        """Load suppliers from database."""
        try:
            from inventory_app.database.connection import db

            suppliers = db.execute_query("SELECT name FROM Suppliers ORDER BY name")
            if suppliers:
                for sup in suppliers:
                    self.supplier_combo.addItem(sup["name"])
        except Exception as e:
            logger.error(f"Failed to load suppliers: {e}")

    def on_report_type_changed(self, index):
        """Handle report type tab changes."""
        report_types = ["usage", "inventory", "trends"]
        self.current_report_type = report_types[index]

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

        supplier_filter = self.supplier_combo.currentText()
        if supplier_filter == "All Suppliers":
            supplier_filter = ""

        include_consumables = self.consumable_check.isChecked()

        # Start background worker
        self.worker = ReportWorker(
            "usage",
            start_date,
            end_date,
            category_filter=category_filter,
            supplier_filter=supplier_filter,
            include_consumables=include_consumables,
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

        # Get filter values
        category_filter = self.inv_category_combo.currentText()
        if category_filter == "All Categories":
            category_filter = ""

        inventory_report_type = self.inventory_report_type.currentText()

        # Start background worker
        low_stock_threshold = (
            None
            if getattr(self, "use_percentage_thresholds", False)
            and self.use_percentage_thresholds.isChecked()
            else self.low_stock_spin.value()
        )

        self.worker = ReportWorker(
            "inventory",
            start_date,
            end_date,
            category_filter=category_filter,
            inventory_report_type=inventory_report_type,
            low_stock_threshold=low_stock_threshold,
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
