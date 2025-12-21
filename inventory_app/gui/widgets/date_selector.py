"""
Custom date selector widget using QDateEdit for accurate date entry.
Provides calendar popup for intuitive date selection.
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QDateEdit, QVBoxLayout
from PyQt6.QtCore import QDate, pyqtSignal
from datetime import date
from typing import Tuple

from inventory_app.gui.styles import get_current_theme


class DateSelector(QWidget):
    """Date selector using QDateEdit with calendar popup for accurate date entry."""

    # Signal emitted when date changes
    dateChanged = pyqtSignal(QDate)

    def __init__(self, label_text: str = "", parent=None):
        super().__init__(parent)
        self._current_date = QDate.currentDate()

        self.setup_ui(label_text)
        self.connect_signals()

    def setup_ui(self, label_text: str):
        """Setup the user interface with QDateEdit."""
        Theme = get_current_theme()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Label
        if label_text:
            self.label = QLabel(label_text)
            self.label.setStyleSheet(
                f"color: {Theme.TEXT_PRIMARY}; font-size: {Theme.FONT_SIZE_NORMAL}pt;"
            )
            layout.addWidget(self.label)

        # Date selector layout
        date_layout = QHBoxLayout()
        date_layout.setSpacing(10)

        # QDateEdit widget with calendar popup
        self.date_edit = QDateEdit()
        self.date_edit.setDate(self._current_date)
        self.date_edit.setCalendarPopup(True)  # Enable calendar popup
        self.date_edit.setDisplayFormat("MMM dd, yyyy")  # User-friendly format
        self.date_edit.setFixedWidth(140)

        # Apply theme styling
        self.date_edit.setStyleSheet(f"""
            QDateEdit {{
                background-color: {Theme.SECONDARY_DARK};
                color: {Theme.TEXT_PRIMARY};
                border: 1px solid {Theme.BORDER_COLOR};
                border-radius: 6px;
                padding: 6px 8px;
                font-size: {Theme.FONT_SIZE_NORMAL}pt;
                min-width: 140px;
            }}
            QDateEdit:hover {{
                border-color: {Theme.ACCENT_HOVER};
            }}
            QDateEdit:focus {{
                border-color: {Theme.ACCENT_COLOR};
            }}
            QDateEdit::drop-down {{
                border: none;
                background-color: transparent;
            }}
            QDateEdit::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid {Theme.TEXT_SECONDARY};
                margin-right: 8px;
            }}
            QDateEdit::up-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-bottom: 4px solid {Theme.TEXT_SECONDARY};
                margin-left: 8px;
            }}
            QCalendarWidget {{
                background-color: {Theme.SECONDARY_DARK};
                color: {Theme.TEXT_PRIMARY};
                border: 1px solid {Theme.BORDER_COLOR};
                border-radius: 6px;
            }}
            QCalendarWidget QTableView {{
                background-color: {Theme.SECONDARY_DARK};
                color: {Theme.TEXT_PRIMARY};
                selection-background-color: {Theme.ACCENT_COLOR};
                selection-color: {Theme.TEXT_PRIMARY};
            }}
            QCalendarWidget QHeaderView::section {{
                background-color: {Theme.PRIMARY_DARK};
                color: {Theme.TEXT_PRIMARY};
                border: none;
                padding: 8px;
            }}
            QCalendarWidget QAbstractItemView:enabled {{
                color: {Theme.TEXT_PRIMARY};
                selection-background-color: {Theme.ACCENT_COLOR};
                selection-color: white;
            }}
            QCalendarWidget QWidget {{
                background-color: {Theme.SECONDARY_DARK};
                color: {Theme.TEXT_PRIMARY};
            }}
            QCalendarWidget QToolButton {{
                color: {Theme.TEXT_PRIMARY};
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 4px;
            }}
            QCalendarWidget QToolButton:hover {{
                background-color: {Theme.ACCENT_HOVER};
            }}
        """)

        # Add date edit to layout
        date_layout.addWidget(self.date_edit)
        date_layout.addStretch()

        layout.addLayout(date_layout)

    def connect_signals(self):
        """Connect date edit signal to update handler."""
        self.date_edit.dateChanged.connect(self.on_date_changed)

    def on_date_changed(self, qdate: QDate):
        """Handle date changes from QDateEdit."""
        if qdate.isValid():
            self._current_date = qdate
            self.dateChanged.emit(self._current_date)

    def set_date(self, qdate: QDate):
        """Set the date programmatically."""
        if qdate.isValid():
            self._current_date = qdate
            self.date_edit.setDate(qdate)

    def get_date(self) -> QDate:
        """Get the current date."""
        return self.date_edit.date()

    def set_date_range(self, min_date: QDate, max_date: QDate):
        """Set the allowable date range."""
        if min_date.isValid() and max_date.isValid() and min_date <= max_date:
            self.date_edit.setMinimumDate(min_date)
            self.date_edit.setMaximumDate(max_date)

    def setMinimumDate(self, min_date: QDate):
        """Set minimum allowable date."""
        if min_date.isValid():
            self.date_edit.setMinimumDate(min_date)

    def setMaximumDate(self, max_date: QDate):
        """Set maximum allowable date."""
        if max_date.isValid():
            self.date_edit.setMaximumDate(max_date)

    def toPyDate(self) -> date:
        """Convert to Python date object."""
        return self.date_edit.date().toPyDate()

    # Legacy compatibility methods (for backward compatibility)
    def update_day_range(self):
        """Legacy method - no longer needed with QDateEdit."""
        pass

    def on_date_component_changed(self):
        """Legacy method - no longer needed with QDateEdit."""
        pass


class DateRangeSelector(QWidget):
    """Widget for selecting a date range with start and end dates."""

    # Signal emitted when date range changes
    dateRangeChanged = pyqtSignal(QDate, QDate)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        """Setup the date range selector UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Start date selector
        self.start_date_selector = DateSelector("Start Date")

        # End date selector
        self.end_date_selector = DateSelector("End Date")

        layout.addWidget(self.start_date_selector)
        layout.addWidget(self.end_date_selector)

    def connect_signals(self):
        """Connect date selector signals."""
        self.start_date_selector.dateChanged.connect(self.on_date_range_changed)
        self.end_date_selector.dateChanged.connect(self.on_date_range_changed)

    def on_date_range_changed(self):
        """Handle date range changes."""
        start_date = self.start_date_selector.get_date()
        end_date = self.end_date_selector.get_date()

        # Ensure start date is not after end date
        if start_date > end_date:
            if self.sender() == self.start_date_selector:
                self.end_date_selector.set_date(start_date)
            else:
                self.start_date_selector.set_date(end_date)
            return

        self.dateRangeChanged.emit(start_date, end_date)

    def set_date_range(self, start_date: QDate, end_date: QDate):
        """Set both start and end dates."""
        self.start_date_selector.set_date(start_date)
        self.end_date_selector.set_date(end_date)

    def get_start_date(self) -> QDate:
        """Get start date."""
        return self.start_date_selector.get_date()

    def get_end_date(self) -> QDate:
        """Get end date."""
        return self.end_date_selector.get_date()

    def get_date_range(self) -> Tuple[QDate, QDate]:
        """Get date range as tuple."""
        return self.get_start_date(), self.get_end_date()

    def to_py_dates(self) -> Tuple[date, date]:
        """Convert to Python date objects."""
        return self.start_date_selector.toPyDate(), self.end_date_selector.toPyDate()
