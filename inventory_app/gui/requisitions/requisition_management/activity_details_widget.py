"""
Activity Details Widget - Reusable component for activity form fields.

Extracted from BaseRequisitionDialog to eliminate code duplication
between create and edit requisition dialogs.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QGroupBox,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
)
from PyQt6.QtCore import pyqtSignal

from inventory_app.utils.logger import logger


class ActivityDetailsWidget(QGroupBox):
    """
    Reusable widget for activity details form fields.

    Provides consistent UI for activity name, description, date, and student/group fields.
    """

    # Signals emitted when fields change
    activity_name_changed = pyqtSignal(str)
    field_changed = pyqtSignal()  # Generic signal for any field change

    def __init__(self, title="📝 Activity Details", parent=None):
        """
        Initialize the activity details widget.

        Args:
            title: Title for the group box
            parent: Parent widget
        """
        super().__init__(title, parent)
        self.datetime_manager = None  # Will be set by parent
        self._setup_ui()

    def _setup_ui(self):
        """Setup the widget UI."""
        from PyQt6.QtWidgets import QSizePolicy
        
        # Set size policy to expand and fill available space
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        # Activity name
        activity_name_layout = QHBoxLayout()
        activity_name_layout.addWidget(QLabel("Activity Name:"))
        self.activity_name = QLineEdit()
        self.activity_name.setPlaceholderText("(REQUIRED)")
        self.activity_name.setFixedHeight(25)
        self.activity_name.textChanged.connect(self._on_activity_name_changed)
        activity_name_layout.addWidget(self.activity_name)
        layout.addLayout(activity_name_layout)

        # Activity description - give it stretch to expand
        layout.addWidget(QLabel("Description:"))
        self.activity_description = QTextEdit()
        self.activity_description.setPlaceholderText("Activity description")
        self.activity_description.setMinimumHeight(60)
        self.activity_description.textChanged.connect(self._on_field_changed)
        layout.addWidget(self.activity_description, 1)  # Stretch factor 1

        # Activity date - will be populated by parent
        self.date_layout = QHBoxLayout()
        self.date_layout.addWidget(QLabel("Activity Date:"))
        # Placeholder for date selector - will be added by parent
        layout.addLayout(self.date_layout)

        # Number of students/groups
        numbers_layout = QHBoxLayout()

        students_layout = QVBoxLayout()
        students_layout.addWidget(QLabel("Number of Students:"))
        self.num_students = QLineEdit()
        self.num_students.setPlaceholderText("---")
        self.num_students.textChanged.connect(self._on_field_changed)
        students_layout.addWidget(self.num_students)

        groups_layout = QVBoxLayout()
        groups_layout.addWidget(QLabel("Number of Groups:"))
        self.num_groups = QLineEdit()
        self.num_groups.setPlaceholderText("---")
        self.num_groups.textChanged.connect(self._on_field_changed)
        groups_layout.addWidget(self.num_groups)

        numbers_layout.addLayout(students_layout)
        numbers_layout.addLayout(groups_layout)
        layout.addLayout(numbers_layout)

    def set_datetime_manager(self, datetime_manager):
        """Set the datetime manager and add date selector to layout."""
        self.datetime_manager = datetime_manager
        if self.datetime_manager:
            selector = self.datetime_manager.create_selector(self)
            self.date_layout.addWidget(selector)
            self.datetime_manager.set_defaults()

    def _on_activity_name_changed(self, text: str):
        """Handle activity name changes."""
        self.activity_name_changed.emit(text)
        self.field_changed.emit()

    def _on_field_changed(self):
        """Handle any field changes."""
        self.field_changed.emit()

    def get_activity_name(self) -> str:
        """Get the activity name."""
        return self.activity_name.text().strip()

    def set_activity_name(self, name: str):
        """Set the activity name."""
        self.activity_name.setText(name)

    def get_activity_description(self) -> str:
        """Get the activity description."""
        return self.activity_description.toPlainText().strip()

    def set_activity_description(self, description: str):
        """Set the activity description."""
        self.activity_description.setText(description)

    def get_activity_date_iso(self) -> str:
        """Get the selected activity date as ISO string."""
        if self.datetime_manager:
            return self.datetime_manager.get_selected_date_iso()
        return ""

    def set_activity_date(self, date_obj):
        """Set the activity date."""
        if self.datetime_manager and date_obj:
            self.datetime_manager.load_from_date(date_obj)

    def get_num_students(self) -> Optional[int]:
        """Get the number of students."""
        text = self.num_students.text().strip()
        if text:
            try:
                return int(text)
            except ValueError:
                logger.warning(f"Invalid number of students: {text}")
                return None
        return None

    def set_num_students(self, num: Optional[int]):
        """Set the number of students."""
        if num is not None:
            self.num_students.setText(str(num))
        else:
            self.num_students.clear()

    def get_num_groups(self) -> Optional[int]:
        """Get the number of groups."""
        text = self.num_groups.text().strip()
        if text:
            try:
                return int(text)
            except ValueError:
                logger.warning(f"Invalid number of groups: {text}")
                return None
        return None

    def set_num_groups(self, num: Optional[int]):
        """Set the number of groups."""
        if num is not None:
            self.num_groups.setText(str(num))
        else:
            self.num_groups.clear()

    def clear_all_fields(self):
        """Clear all form fields."""
        self.activity_name.clear()
        self.activity_description.clear()
        self.num_students.clear()
        self.num_groups.clear()
        if self.datetime_manager:
            self.datetime_manager.set_defaults()
