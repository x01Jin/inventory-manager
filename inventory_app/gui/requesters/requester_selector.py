"""
Requester selector dialog for selecting requesters in requisition workflow.
Provides searchable interface for selecting existing requesters with tabbed tables.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QGroupBox,
    QMessageBox,
    QTabWidget,
    QWidget,
)

from inventory_app.gui.requesters.requester_model import RequesterModel
from inventory_app.gui.requesters.requester_table import RequesterTable
from inventory_app.utils.logger import logger


class RequesterSelector(QDialog):
    """Dialog for selecting requesters for requisitions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = RequesterModel()
        self.selected_requester_id: Optional[int] = None

        self.students_table = RequesterTable(requester_type="student")
        self.teachers_table = RequesterTable(requester_type="teacher")
        self.faculty_table = RequesterTable(requester_type="faculty")

        self._current_tab = "student"

        self.setWindowTitle("Select Requester for Requisition")
        self._setup_connections()
        self.setup_ui()
        self.load_requesters()

    def _setup_connections(self):
        """Setup signal connections between tables and selection handling."""
        self.students_table.requester_selected.connect(self._on_requester_selected)
        self.teachers_table.requester_selected.connect(self._on_requester_selected)
        self.faculty_table.requester_selected.connect(self._on_requester_selected)

        self.students_table.requester_double_clicked.connect(self.confirm_selection)
        self.teachers_table.requester_double_clicked.connect(self.confirm_selection)
        self.faculty_table.requester_double_clicked.connect(self.confirm_selection)

    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        header = QLabel("Select Requester for Requisition")
        header.setStyleSheet("font-size: 14pt; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header)

        search_group = QGroupBox("Search Requesters")
        search_layout = QHBoxLayout(search_group)

        search_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Search by name, grade, section, or department..."
        )
        self.search_input.textChanged.connect(self.filter_requesters)
        search_layout.addWidget(self.search_input)

        layout.addWidget(search_group)

        table_group = QGroupBox("Available Requesters")
        table_layout = QVBoxLayout(table_group)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabWidget::pane { border: 1px solid #444; }")

        students_tab = QWidget()
        students_layout = QVBoxLayout(students_tab)
        students_layout.addWidget(self.students_table)
        self.tabs.addTab(students_tab, "Students")

        teachers_tab = QWidget()
        teachers_layout = QVBoxLayout(teachers_tab)
        teachers_layout.addWidget(self.teachers_table)
        self.tabs.addTab(teachers_tab, "Teachers")

        faculty_tab = QWidget()
        faculty_layout = QVBoxLayout(faculty_tab)
        faculty_layout.addWidget(self.faculty_table)
        self.tabs.addTab(faculty_tab, "Faculty/Individual")

        self.tabs.currentChanged.connect(self._on_tab_changed)
        table_layout.addWidget(self.tabs)
        layout.addWidget(table_group)

        self.selection_info = QLabel("No requester selected")
        self.selection_info.setStyleSheet(
            "font-weight: bold; padding: 10px; background-color: #2a2a3c; border: 1px solid #3f3f46; border-radius: 5px;"
        )
        layout.addWidget(self.selection_info)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.select_button = QPushButton("Select")
        self.select_button.clicked.connect(self.confirm_selection)
        self.select_button.setEnabled(False)
        button_layout.addWidget(self.select_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

        self.setMinimumWidth(700)
        self.setMinimumHeight(500)
        self.setModal(True)

    def _on_tab_changed(self, index: int) -> None:
        """Handle tab change to update current table."""
        tab_types = ["student", "teacher", "faculty"]
        if 0 <= index < len(tab_types):
            self._current_tab = tab_types[index]

    def load_requesters(self):
        """Load all requesters."""
        try:
            success = self.model.load_data()
            if success:
                self.filter_requesters()
                logger.info("Loaded requesters for selection")
            else:
                QMessageBox.warning(
                    self, "Load Error", "Failed to load requesters from database."
                )
        except Exception as e:
            logger.error(f"Failed to load requesters: {e}")
            QMessageBox.critical(self, "Error", "Failed to load requesters.")

    def filter_requesters(self):
        """Filter requesters based on search term."""
        try:
            self.model.filter_by_search(self.search_input.text())
            filtered_requesters = self.model.get_filtered_rows()

            students = [r for r in filtered_requesters if r.requester_type == "student"]
            teachers = [r for r in filtered_requesters if r.requester_type == "teacher"]
            faculty = [r for r in filtered_requesters if r.requester_type == "faculty"]

            self.students_table.populate_table(students)
            self.teachers_table.populate_table(teachers)
            self.faculty_table.populate_table(faculty)

            logger.debug(f"Filtered requesters: {len(students)} students, {len(teachers)} teachers, {len(faculty)} faculty")

        except Exception as e:
            logger.error(f"Failed to filter requesters: {e}")

    def _on_requester_selected(self, requester_id: int):
        """Handle requester selection from any table."""
        try:
            if requester_id is None:
                return

            requester = self.model.get_requester_by_id(requester_id)
            if requester:
                self.selected_requester_id = requester_id
                self.selection_info.setText(f"Selected: {requester.name}")
                self.select_button.setEnabled(True)

                logger.info(f"Selected requester: {requester.name} (ID: {requester_id})")

        except Exception as e:
            logger.error(f"Failed to select requester {requester_id}: {e}")

    def confirm_selection(self):
        """Confirm requester selection and close dialog."""
        if self.selected_requester_id is not None:
            self.accept()
        else:
            QMessageBox.warning(
                self, "No Selection", "Please select a requester first."
            )

    def get_selected_requester_id(self) -> Optional[int]:
        """Get the selected requester ID."""
        return self.selected_requester_id

    @staticmethod
    def select_requester(parent=None) -> Optional[int]:
        """
        Static method to show requester selection dialog.
        Returns the selected requester ID or None if cancelled.
        """
        dialog = RequesterSelector(parent)
        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            return dialog.get_selected_requester_id()

        return None
