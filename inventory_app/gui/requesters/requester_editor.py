"""
Requester editor dialog for adding and editing requester information.
Provides tab-based form for requester management in laboratory requisitions.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QTabWidget, QWidget,
    QMessageBox, QFormLayout
)
from PyQt6.QtCore import Qt

from inventory_app.database.models import Requester
from inventory_app.services.requesters_activity import requesters_activity_manager
from inventory_app.utils.logger import logger


class RequesterEditor(QDialog):
    """Dialog for adding and editing requester information."""

    def __init__(self, parent=None, requester_id: Optional[int] = None):
        super().__init__(parent)
        self.requester_id = requester_id
        self.existing_requester = None

        if requester_id:
            self.existing_requester = Requester.get_by_id(requester_id)
            self.setWindowTitle("Edit Requester")
        else:
            self.setWindowTitle("Add New Requester")

        self.setup_ui()
        self.load_requester_data()

    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        self._setup_student_tab()
        self._setup_teacher_tab()
        self._setup_faculty_tab()

        self.editor_layout = QFormLayout()
        self.editor_layout.setSpacing(10)
        self.editor_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.editor_input = QLineEdit()
        self.editor_input.setPlaceholderText("Enter your name or initials...")
        self.editor_layout.addRow("Your Name/Initials:", self.editor_input)

        editor_container = QWidget()
        editor_container.setLayout(self.editor_layout)
        layout.addWidget(editor_container)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_requester)
        self.save_button.setDefault(True)
        button_layout.addWidget(self.save_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

        self.setMinimumWidth(400)
        self.setModal(True)
        self._update_tab_positions()

    def _setup_student_tab(self):
        """Setup the Student tab."""
        tab = QWidget()
        form_layout = QFormLayout(tab)
        form_layout.setSpacing(10)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.student_name = QLineEdit()
        self.student_name.setPlaceholderText("Enter student's full name")

        self.grade_level = QLineEdit()
        self.grade_level.setPlaceholderText("e.g., Grade 7, Grade 10")

        self.section = QLineEdit()
        self.section.setPlaceholderText("e.g., Section A, Einstein")

        form_layout.addRow("Full Name:", self.student_name)
        form_layout.addRow("Grade Level:", self.grade_level)
        form_layout.addRow("Section:", self.section)

        self.tab_widget.addTab(tab, "Student")

    def _setup_teacher_tab(self):
        """Setup the Teacher tab."""
        tab = QWidget()
        form_layout = QFormLayout(tab)
        form_layout.setSpacing(10)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.teacher_name = QLineEdit()
        self.teacher_name.setPlaceholderText("Enter teacher's full name")

        self.department = QLineEdit()
        self.department.setPlaceholderText("e.g., Science, Mathematics")

        form_layout.addRow("Full Name:", self.teacher_name)
        form_layout.addRow("Department:", self.department)

        self.tab_widget.addTab(tab, "Teacher")

    def _setup_faculty_tab(self):
        """Setup the Faculty tab."""
        tab = QWidget()
        form_layout = QFormLayout(tab)
        form_layout.setSpacing(10)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.faculty_name = QLineEdit()
        self.faculty_name.setPlaceholderText("Enter faculty name")

        form_layout.addRow("Full Name:", self.faculty_name)

        self.tab_widget.addTab(tab, "Faculty")

    def _update_tab_positions(self):
        """Ensure tabs are positioned at the top for minimal height."""
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)

    def _get_current_type(self) -> str:
        """Get the current requester type based on selected tab."""
        current_index = self.tab_widget.currentIndex()
        if current_index == 0:
            return "student"
        elif current_index == 1:
            return "teacher"
        else:
            return "faculty"

    def _get_current_name_field(self) -> QLineEdit:
        """Get the name field for the current tab."""
        current_index = self.tab_widget.currentIndex()
        if current_index == 0:
            return self.student_name
        elif current_index == 1:
            return self.teacher_name
        else:
            return self.faculty_name

    def _switch_to_tab(self, requester_type: str):
        """Switch to the appropriate tab based on requester type."""
        if requester_type == "student":
            self.tab_widget.setCurrentIndex(0)
        elif requester_type == "teacher":
            self.tab_widget.setCurrentIndex(1)
        else:
            self.tab_widget.setCurrentIndex(2)

    def load_requester_data(self):
        """Load existing requester data for editing."""
        if not self.existing_requester:
            return

        try:
            req_type = self.existing_requester.requester_type or "teacher"
            self._switch_to_tab(req_type)

            if req_type == "student":
                self.student_name.setText(self.existing_requester.name or "")
                self.grade_level.setText(self.existing_requester.grade_level or "")
                self.section.setText(self.existing_requester.section or "")
            elif req_type == "teacher":
                self.teacher_name.setText(self.existing_requester.name or "")
                self.department.setText(self.existing_requester.department or "")
            else:
                self.faculty_name.setText(self.existing_requester.name or "")

            logger.debug(f"Loaded data for requester {self.requester_id}")

        except Exception as e:
            logger.error(f"Failed to load requester data: {e}")
            QMessageBox.warning(self, "Data Load Error", "Failed to load requester information.")

    def validate_input(self) -> tuple[bool, str]:
        """Validate user input.

        Returns:
            Tuple of (is_valid, error_message)
        """
        req_type = self._get_current_type()
        name_field = self._get_current_name_field()

        if not name_field.text().strip():
            return False, "Name is required."

        if not self.editor_input.text().strip():
            return False, "Editor name is required."

        if req_type == "student":
            if not self.grade_level.text().strip():
                return False, "Grade level is required."
            if not self.section.text().strip():
                return False, "Section is required."
        elif req_type == "teacher":
            if not self.department.text().strip():
                return False, "Department is required."

        return True, ""

    def save_requester(self):
        """Save the requester data."""
        try:
            is_valid, error_msg = self.validate_input()
            if not is_valid:
                QMessageBox.warning(self, "Validation Error", error_msg)
                return

            req_type = self._get_current_type()
            name_field = self._get_current_name_field()
            name = name_field.text().strip()

            existing_check = self._find_existing_requester(name, req_type)
            if existing_check and (not self.existing_requester or existing_check.id != self.existing_requester.id):
                reply = QMessageBox.question(
                    self, "Duplicate Requester",
                    f"A requester with the same name and type already exists.\n\n"
                    f"Name: {existing_check.name}\n"
                    f"Type: {existing_check.requester_type.capitalize()}\n\n"
                    "Do you want to continue creating this duplicate?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return

            if self.existing_requester:
                requester = self.existing_requester
            else:
                requester = Requester()

            requester.name = name
            requester.requester_type = req_type

            if req_type == "student":
                requester.grade_level = self.grade_level.text().strip()
                requester.section = self.section.text().strip()
                requester.department = None
            elif req_type == "teacher":
                requester.grade_level = None
                requester.section = None
                requester.department = self.department.text().strip()
            else:
                requester.grade_level = None
                requester.section = None
                requester.department = None

            success = requester.save()

            if success:
                action = "updated" if self.existing_requester else "created"
                logger.info(f"Successfully {action} requester: {requester.name}")

                editor_name = self.editor_input.text().strip()
                if self.existing_requester:
                    requesters_activity_manager.log_requester_updated(
                        requester_name=name,
                        user_name=editor_name
                    )
                else:
                    requesters_activity_manager.log_requester_added(
                        requester_name=name,
                        user_name=editor_name
                    )

                QMessageBox.information(self, "Success", f"Requester {action} successfully!")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to save requester. Please try again.")

        except Exception as e:
            logger.error(f"Error saving requester: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save requester: {str(e)}")

    def _find_existing_requester(self, name: str, requester_type: str) -> Optional[Requester]:
        """Find existing requester with same name and type."""
        try:
            from inventory_app.database.connection import db

            query = """
            SELECT * FROM Requesters
            WHERE name = ? AND requester_type = ?
            """
            rows = db.execute_query(query, (name, requester_type))
            if rows:
                return Requester(**dict(rows[0]))

        except Exception as e:
            logger.error(f"Error checking for duplicate requester: {e}")

        return None

    @staticmethod
    def get_requester_data(parent=None, requester_id: Optional[int] = None) -> Optional[Requester]:
        """
        Static method to get requester data from dialog.
        Returns the requester object if saved, None if cancelled.
        """
        dialog = RequesterEditor(parent, requester_id)
        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            if requester_id:
                return Requester.get_by_id(requester_id)
            else:
                return None

        return None
