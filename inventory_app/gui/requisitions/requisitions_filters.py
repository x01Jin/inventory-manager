"""
Requisitions filters - search and filter controls for requisitions.
Provides filtering by requester, activity, status, and date range.
Uses composition pattern with RequisitionsModel.
"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QGroupBox,
    QDateEdit,
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
    requester_filter_changed = pyqtSignal(str)  # Requester filter changed
    status_filter_changed = pyqtSignal(str)  # Status filter changed
    date_range_changed = pyqtSignal(
        object, object
    )  # Date range changed (from_date, to_date)
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
        layout.setSpacing(8)

        # Search section
        search_group = QGroupBox("Search & Filter")
        search_layout = QVBoxLayout(search_group)
        search_layout.setContentsMargins(8, 8, 8, 8)
        search_layout.setSpacing(8)

        # Search by text
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Search by requester name, activity, or items..."
        )
        self.search_input.textChanged.connect(self._on_search_changed)
        search_row.addWidget(self.search_input)
        search_layout.addLayout(search_row)

        # Filter row 1: Requester and Status
        filter_row1 = QHBoxLayout()

        filter_row1.addWidget(QLabel("Requester:"))
        self.requester_combo = QComboBox()
        self.requester_combo.addItem("All Requesters", "")
        self.requester_combo.currentTextChanged.connect(self._on_requester_changed)
        filter_row1.addWidget(self.requester_combo)

        filter_row1.addWidget(QLabel("Status:"))
        self.status_combo = QComboBox()
        self.status_combo.addItem("All Statuses", "")
        self.status_combo.addItem("Requested", "requested")
        self.status_combo.addItem("Active", "active")
        self.status_combo.addItem("Returned", "returned")
        self.status_combo.addItem("Overdue", "overdue")
        self.status_combo.currentTextChanged.connect(self._on_status_changed)
        filter_row1.addWidget(self.status_combo)

        search_layout.addLayout(filter_row1)

        # Filter row 2: Date Range and Clear Filters
        filter_row2 = QHBoxLayout()

        filter_row2.addWidget(QLabel("From:"))
        self.date_from = QDateEdit()
        self.date_from.setDate(
            QDate.currentDate().addDays(-30)
        )  # Default to 30 days ago
        self.date_from.setCalendarPopup(True)
        self.date_from.dateChanged.connect(self._on_date_range_changed)
        filter_row2.addWidget(self.date_from)

        filter_row2.addWidget(QLabel("To:"))
        self.date_to = QDateEdit()
        self.date_to.setDate(QDate.currentDate().addDays(7))  # Default to 1 week ahead
        self.date_to.setCalendarPopup(True)
        self.date_to.dateChanged.connect(self._on_date_range_changed)
        filter_row2.addWidget(self.date_to)

        filter_row2.addStretch()

        self.clear_button = QPushButton("🗑️ Clear Filters")
        self.clear_button.clicked.connect(self._on_clear_filters)
        filter_row2.addWidget(self.clear_button)

        search_layout.addLayout(filter_row2)

        layout.addWidget(search_group)

        # Filter summary
        self.summary_label = QLabel("Showing all requisitions")
        self.summary_label.setStyleSheet(
            "font-size: 11pt; color: #666; font-style: italic;"
        )
        layout.addWidget(self.summary_label)

    def set_model(self, model: "RequisitionsModel"):
        """Set the model reference for accessing data."""
        self.model = model

    @staticmethod
    def _format_requester_display(requester) -> str:
        """Build requester display text for dropdown."""
        display_text = requester.name
        if requester.requester_type == "student":
            display_text = (
                f"{requester.name} ({requester.grade_level} - {requester.section})"
            )
        elif requester.requester_type == "teacher":
            display_text = f"{requester.name} ({requester.department})"
        return display_text

    def set_requester_options(self, requesters: list):
        """Populate requester dropdown using already-loaded requester objects."""
        try:
            while self.requester_combo.count() > 1:
                self.requester_combo.removeItem(1)

            for requester in requesters:
                display_text = self._format_requester_display(requester)
                self.requester_combo.addItem(display_text, requester.name.lower())
        except Exception as e:
            logger.error(f"Failed to set requester options: {e}")

    def _load_requester_options(self):
        """Load requester names for the filter dropdown."""
        if not self.model:
            return

        try:
            requesters = self.model.controller.get_requesters_with_requisitions()
            self.set_requester_options(requesters)

        except Exception as e:
            logger.error(f"Failed to load requester options: {e}")

    def update_summary(self, total_count: int, filtered_count: int):
        """Update the filter summary label."""
        try:
            if filtered_count == total_count:
                self.summary_label.setText(f"Showing all {total_count} requisitions")
            else:
                percentage = (
                    (filtered_count / total_count * 100) if total_count > 0 else 0
                )
                self.summary_label.setText(
                    f"Showing {filtered_count} of {total_count} requisitions ({percentage:.1f}%)"
                )
        except Exception as e:
            logger.error(f"Failed to update filter summary: {e}")

    def get_current_filters(self) -> dict:
        """Get current filter settings as a dictionary."""
        try:
            return {
                "search_term": self.search_input.text().strip(),
                "requester_filter": self.requester_combo.currentData() or "",
                "status_filter": self.status_combo.currentData() or "",
                "date_from": self.date_from.date().toPyDate()
                if self.date_from.date().isValid()
                else None,
                "date_to": self.date_to.date().toPyDate()
                if self.date_to.date().isValid()
                else None,
            }
        except Exception as e:
            logger.error(f"Failed to get current filters: {e}")
            return {}

    def set_filters(self, filters: dict):
        """Set filter values from a dictionary."""
        try:
            # Search term
            if "search_term" in filters:
                self.search_input.setText(filters["search_term"])

            # Requester filter
            if "requester_filter" in filters:
                index = self.requester_combo.findData(filters["requester_filter"])
                if index >= 0:
                    self.requester_combo.setCurrentIndex(index)

            # Status filter
            if "status_filter" in filters:
                index = self.status_combo.findData(filters["status_filter"])
                if index >= 0:
                    self.status_combo.setCurrentIndex(index)

            # Date range
            if "date_from" in filters and filters["date_from"]:
                qdate = QDate(
                    filters["date_from"].year,
                    filters["date_from"].month,
                    filters["date_from"].day,
                )
                self.date_from.setDate(qdate)

            if "date_to" in filters and filters["date_to"]:
                qdate = QDate(
                    filters["date_to"].year,
                    filters["date_to"].month,
                    filters["date_to"].day,
                )
                self.date_to.setDate(qdate)

            logger.debug("Filter values set from dictionary")

        except Exception as e:
            logger.error(f"Failed to set filters: {e}")

    def clear_all_filters(self):
        """Clear all filter inputs."""
        try:
            self.search_input.clear()
            self.requester_combo.setCurrentIndex(0)  # "All Requesters"
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

    def _on_requester_changed(self, requester_name: str):
        """Handle requester filter changes."""
        requester_filter = self.requester_combo.currentData() or ""
        self.requester_filter_changed.emit(requester_filter)

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
