"""
Requisitions filters - search and filter controls for requisitions.
Provides filtering by borrower, activity, status, and date range.
Uses composition pattern with RequisitionsModel.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QPushButton, QGroupBox,
    QDateEdit
)
from PyQt6.QtCore import pyqtSignal, QDate
from inventory_app.gui.requisitions.requisitions_model import RequisitionsModel
from inventory_app.utils.logger import logger


class RequisitionsFilters(QWidget):
    """
    Filter controls for requisitions.
    Allows filtering by various criteria to find specific requisitions.
    """

    # Signals emitted when filters change
    search_changed = pyqtSignal(str)  # Search term changed
    borrower_filter_changed = pyqtSignal(str)  # Borrower filter changed
    activity_filter_changed = pyqtSignal(str)  # Activity filter changed
    status_filter_changed = pyqtSignal(str)  # Status filter changed
    date_range_changed = pyqtSignal(object, object)  # Date range changed (from_date, to_date)
    clear_filters_requested = pyqtSignal()  # Clear all filters

    def __init__(self, parent=None):
        """Initialize the filters widget."""
        super().__init__(parent)
        self.model = None  # Will be set by parent

        self.setup_ui()
        logger.info("Requisitions filters initialized")

    def setup_ui(self):
        """Setup the filter UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Search section
        search_group = QGroupBox("Search & Filter")
        search_layout = QVBoxLayout(search_group)

        # Search by text
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by borrower name, activity, or items...")
        self.search_input.textChanged.connect(self._on_search_changed)
        search_row.addWidget(self.search_input)
        search_layout.addLayout(search_row)

        # Filter row 1: Borrower and Activity
        filter_row1 = QHBoxLayout()

        filter_row1.addWidget(QLabel("Borrower:"))
        self.borrower_combo = QComboBox()
        self.borrower_combo.addItem("All Borrowers", "")
        self.borrower_combo.currentTextChanged.connect(self._on_borrower_changed)
        filter_row1.addWidget(self.borrower_combo)

        filter_row1.addWidget(QLabel("Activity:"))
        self.activity_input = QLineEdit()
        self.activity_input.setPlaceholderText("Filter by activity name...")
        self.activity_input.textChanged.connect(self._on_activity_changed)
        filter_row1.addWidget(self.activity_input)

        search_layout.addLayout(filter_row1)

        # Filter row 2: Status and Date Range
        filter_row2 = QHBoxLayout()

        filter_row2.addWidget(QLabel("Status:"))
        self.status_combo = QComboBox()
        self.status_combo.addItem("All Statuses", "")
        self.status_combo.addItem("Active", "Active")
        self.status_combo.addItem("Returned", "Returned")
        self.status_combo.addItem("Overdue", "Overdue")
        self.status_combo.currentTextChanged.connect(self._on_status_changed)
        filter_row2.addWidget(self.status_combo)

        filter_row2.addWidget(QLabel("From:"))
        self.date_from = QDateEdit()
        self.date_from.setDate(QDate.currentDate().addDays(-30))  # Default to 30 days ago
        self.date_from.setCalendarPopup(True)
        self.date_from.dateChanged.connect(self._on_date_range_changed)
        filter_row2.addWidget(self.date_from)

        filter_row2.addWidget(QLabel("To:"))
        self.date_to = QDateEdit()
        self.date_to.setDate(QDate.currentDate().addDays(7))  # Default to 1 week ahead
        self.date_to.setCalendarPopup(True)
        self.date_to.dateChanged.connect(self._on_date_range_changed)
        filter_row2.addWidget(self.date_to)

        search_layout.addLayout(filter_row2)

        # Buttons row
        button_row = QHBoxLayout()
        button_row.addStretch()

        self.clear_button = QPushButton("🗑️ Clear Filters")
        self.clear_button.clicked.connect(self._on_clear_filters)
        button_row.addWidget(self.clear_button)

        self.apply_button = QPushButton("🔍 Apply Filters")
        self.apply_button.clicked.connect(self._on_apply_filters)
        button_row.addWidget(self.apply_button)

        search_layout.addLayout(button_row)

        layout.addWidget(search_group)

        # Filter summary
        self.summary_label = QLabel("Showing all requisitions")
        self.summary_label.setStyleSheet("font-size: 11pt; color: #666; font-style: italic;")
        layout.addWidget(self.summary_label)

    def set_model(self, model: RequisitionsModel):
        """Set the model reference for accessing data."""
        self.model = model
        self._load_borrower_options()

    def _load_borrower_options(self):
        """Load borrower names for the filter dropdown."""
        if not self.model:
            return

        try:
            # Clear existing items except "All Borrowers"
            while self.borrower_combo.count() > 1:
                self.borrower_combo.removeItem(1)

            # Add borrower names (only those with requisitions)
            borrowers = self.model.controller.get_borrowers_with_requisitions()
            for borrower in borrowers:
                display_text = f"{borrower.name} ({borrower.affiliation})"
                self.borrower_combo.addItem(display_text, borrower.name.lower())

        except Exception as e:
            logger.error(f"Failed to load borrower options: {e}")

    def update_summary(self, total_count: int, filtered_count: int):
        """Update the filter summary label."""
        try:
            if filtered_count == total_count:
                self.summary_label.setText(f"Showing all {total_count} requisitions")
            else:
                percentage = (filtered_count / total_count * 100) if total_count > 0 else 0
                self.summary_label.setText(
                    f"Showing {filtered_count} of {total_count} requisitions ({percentage:.1f}%)"
                )
        except Exception as e:
            logger.error(f"Failed to update filter summary: {e}")

    def get_current_filters(self) -> dict:
        """Get current filter settings as a dictionary."""
        try:
            return {
                'search_term': self.search_input.text().strip(),
                'borrower_filter': self.borrower_combo.currentData() or "",
                'activity_filter': self.activity_input.text().strip(),
                'status_filter': self.status_combo.currentData() or "",
                'date_from': self.date_from.date().toPyDate() if self.date_from.date().isValid() else None,
                'date_to': self.date_to.date().toPyDate() if self.date_to.date().isValid() else None
            }
        except Exception as e:
            logger.error(f"Failed to get current filters: {e}")
            return {}

    def set_filters(self, filters: dict):
        """Set filter values from a dictionary."""
        try:
            # Search term
            if 'search_term' in filters:
                self.search_input.setText(filters['search_term'])

            # Borrower filter
            if 'borrower_filter' in filters:
                index = self.borrower_combo.findData(filters['borrower_filter'])
                if index >= 0:
                    self.borrower_combo.setCurrentIndex(index)

            # Activity filter
            if 'activity_filter' in filters:
                self.activity_input.setText(filters['activity_filter'])

            # Status filter
            if 'status_filter' in filters:
                index = self.status_combo.findData(filters['status_filter'])
                if index >= 0:
                    self.status_combo.setCurrentIndex(index)

            # Date range
            if 'date_from' in filters and filters['date_from']:
                qdate = QDate(filters['date_from'].year, filters['date_from'].month, filters['date_from'].day)
                self.date_from.setDate(qdate)

            if 'date_to' in filters and filters['date_to']:
                qdate = QDate(filters['date_to'].year, filters['date_to'].month, filters['date_to'].day)
                self.date_to.setDate(qdate)

            logger.debug("Filter values set from dictionary")

        except Exception as e:
            logger.error(f"Failed to set filters: {e}")

    def clear_all_filters(self):
        """Clear all filter inputs."""
        try:
            self.search_input.clear()
            self.borrower_combo.setCurrentIndex(0)  # "All Borrowers"
            self.activity_input.clear()
            self.status_combo.setCurrentIndex(0)  # "All Statuses"

            # Reset date range to defaults
            self.date_from.setDate(QDate.currentDate().addDays(-30))
            self.date_to.setDate(QDate.currentDate().addDays(7))

            logger.debug("All filters cleared")

        except Exception as e:
            logger.error(f"Failed to clear filters: {e}")

    # Private event handlers

    def _on_search_changed(self, text: str):
        """Handle search input changes."""
        self.search_changed.emit(text)

    def _on_borrower_changed(self, borrower_name: str):
        """Handle borrower filter changes."""
        borrower_filter = self.borrower_combo.currentData() or ""
        self.borrower_filter_changed.emit(borrower_filter)

    def _on_activity_changed(self, text: str):
        """Handle activity filter changes."""
        self.activity_filter_changed.emit(text)

    def _on_status_changed(self, status: str):
        """Handle status filter changes."""
        status_filter = self.status_combo.currentData() or ""
        self.status_filter_changed.emit(status_filter)

    def _on_date_range_changed(self):
        """Handle date range changes."""
        from_date = self.date_from.date().toPyDate()
        to_date = self.date_to.date().toPyDate()
        self.date_range_changed.emit(from_date, to_date)

    def _on_clear_filters(self):
        """Handle clear filters button."""
        self.clear_all_filters()
        self.clear_filters_requested.emit()

    def _on_apply_filters(self):
        """Handle apply filters button."""
        # Emit all current filter values to ensure they're applied
        self._on_search_changed(self.search_input.text())
        self._on_borrower_changed(self.borrower_combo.currentText())
        self._on_activity_changed(self.activity_input.text())
        self._on_status_changed(self.status_combo.currentText())
        self._on_date_range_changed()
