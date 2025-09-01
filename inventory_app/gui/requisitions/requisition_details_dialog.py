"""
Requisition details dialog - collects mandatory requisition information.
Dialog for entering lab activity details, student count, and group configuration.
"""

from datetime import date
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QSpinBox, QDateEdit, QPushButton,
    QMessageBox, QFormLayout, QGroupBox
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont

from inventory_app.utils.logger import logger


class RequisitionDetailsDialog(QDialog):
    """
    Dialog for collecting mandatory requisition details.
    Collects lab activity information and class configuration.
    """

    def __init__(self, parent=None, initial_data=None):
        """
        Initialize the requisition details dialog.

        Args:
            parent: Parent widget
            initial_data: Dict with initial values for editing existing requisitions
        """
        super().__init__(parent)

        self.initial_data = initial_data or {}
        self.setup_ui()
        self.load_initial_data()

        logger.info("Requisition details dialog initialized")

    def setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("Laboratory Activity Details")
        self.setModal(True)
        self.setMinimumWidth(450)
        self.resize(500, 350)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header = QLabel("Enter Laboratory Activity Information")
        header_font = QFont()
        header_font.setPointSize(12)
        header_font.setBold(True)
        header.setFont(header_font)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Activity details group
        activity_group = QGroupBox("Activity Information")
        activity_layout = QFormLayout(activity_group)
        activity_layout.setContentsMargins(15, 15, 15, 15)
        activity_layout.setSpacing(10)

        # Lab activity name
        self.activity_name_edit = QLineEdit()
        self.activity_name_edit.setPlaceholderText("e.g., Chemical Reactions Lab, Microscope Study")
        activity_layout.addRow("Activity Name:", self.activity_name_edit)

        # Lab activity date
        self.activity_date_edit = QDateEdit()
        self.activity_date_edit.setCalendarPopup(True)
        self.activity_date_edit.setDate(QDate.currentDate())
        activity_layout.addRow("Activity Date:", self.activity_date_edit)

        layout.addWidget(activity_group)

        # Class configuration group
        class_group = QGroupBox("Class Configuration")
        class_layout = QFormLayout(class_group)
        class_layout.setContentsMargins(15, 15, 15, 15)
        class_layout.setSpacing(10)

        # Number of students
        self.students_spin = QSpinBox()
        self.students_spin.setMinimum(1)
        self.students_spin.setMaximum(200)
        self.students_spin.setValue(30)
        self.students_spin.setSuffix(" students")
        class_layout.addRow("Total Students:", self.students_spin)

        # Number of groups
        self.groups_spin = QSpinBox()
        self.groups_spin.setMinimum(1)
        self.groups_spin.setMaximum(50)
        self.groups_spin.setValue(6)
        self.groups_spin.setSuffix(" groups")
        class_layout.addRow("Number of Groups:", self.groups_spin)

        # Help text
        help_text = QLabel(
            "<small><i>This information helps track resource usage patterns and plan future laboratory sessions.</i></small>"
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: #666; margin-top: 10px;")
        class_layout.addRow("", help_text)

        layout.addWidget(class_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setDefault(True)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)

        layout.addLayout(button_layout)

        # Set tab order
        self.activity_name_edit.setFocus()

    def load_initial_data(self):
        """Load initial data for editing existing requisitions."""
        if self.initial_data:
            # Activity name
            if 'lab_activity_name' in self.initial_data:
                self.activity_name_edit.setText(self.initial_data['lab_activity_name'])

            # Activity date
            if 'lab_activity_date' in self.initial_data:
                activity_date = self.initial_data['lab_activity_date']
                if isinstance(activity_date, date):
                    qdate = QDate(activity_date.year, activity_date.month, activity_date.day)
                    self.activity_date_edit.setDate(qdate)

            # Students
            if 'num_students' in self.initial_data and self.initial_data['num_students']:
                self.students_spin.setValue(self.initial_data['num_students'])

            # Groups
            if 'num_groups' in self.initial_data and self.initial_data['num_groups']:
                self.groups_spin.setValue(self.initial_data['num_groups'])

    def get_requisition_data(self):
        """
        Get the collected requisition data.

        Returns:
            Dict with requisition details
        """
        activity_date = self.activity_date_edit.date()
        activity_date_py = date(
            activity_date.year(),
            activity_date.month(),
            activity_date.day()
        )

        return {
            'lab_activity_name': self.activity_name_edit.text().strip(),
            'lab_activity_date': activity_date_py,
            'num_students': self.students_spin.value(),
            'num_groups': self.groups_spin.value()
        }

    def accept(self):
        """Handle OK button click with validation."""
        # Validate required fields
        if not self.activity_name_edit.text().strip():
            QMessageBox.warning(
                self, "Validation Error",
                "Please enter the laboratory activity name."
            )
            self.activity_name_edit.setFocus()
            return

        # Validate date is not in the past (optional - could be a past activity)
        # activity_date = self.activity_date_edit.date()
        # if activity_date < QDate.currentDate():
        #     QMessageBox.warning(
        #         self, "Validation Error",
        #         "Activity date cannot be in the past."
        #     )
        #     return

        # Validate group size logic
        students = self.students_spin.value()
        groups = self.groups_spin.value()

        if groups > students:
            QMessageBox.warning(
                self, "Validation Error",
                f"Number of groups ({groups}) cannot exceed number of students ({students})."
            )
            self.groups_spin.setFocus()
            return

        logger.info(f"Requisition details validated: {students} students, {groups} groups")
        super().accept()

    @staticmethod
    def get_details(parent=None, initial_data=None):
        """
        Static method to show dialog and get results.

        Args:
            parent: Parent widget
            initial_data: Initial data for editing

        Returns:
            Tuple of (accepted, data_dict) or (False, None) if cancelled
        """
        dialog = RequisitionDetailsDialog(parent, initial_data)
        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            return True, dialog.get_requisition_data()
        else:
            return False, None
