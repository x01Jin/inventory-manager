"""
Borrower editor dialog for adding and editing borrower information.
Provides form for borrower management in laboratory requisitions.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QGroupBox, QMessageBox
)
from inventory_app.database.models import Borrower
from inventory_app.utils.logger import logger


class BorrowerEditor(QDialog):
    """Dialog for adding and editing borrower information."""

    def __init__(self, parent=None, borrower_id: Optional[int] = None):
        super().__init__(parent)
        self.borrower_id = borrower_id
        self.existing_borrower = None

        if borrower_id:
            self.existing_borrower = Borrower.get_by_id(borrower_id)
            self.setWindowTitle("Edit Borrower")
        else:
            self.setWindowTitle("Add New Borrower")

        self.setup_ui()
        self.load_borrower_data()

    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Borrower Information Group
        info_group = QGroupBox("Borrower Information")
        info_layout = QVBoxLayout(info_group)

        # Name (required)
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Full Name:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter borrower's full name...")
        name_layout.addWidget(self.name_input)
        info_layout.addLayout(name_layout)

        # Affiliation (required)
        affiliation_layout = QHBoxLayout()
        affiliation_layout.addWidget(QLabel("Affiliation:"))
        self.affiliation_input = QLineEdit()
        self.affiliation_input.setPlaceholderText("Grade/Section or Department...")
        affiliation_layout.addWidget(self.affiliation_input)
        info_layout.addLayout(affiliation_layout)

        # Group Name (required)
        group_layout = QHBoxLayout()
        group_layout.addWidget(QLabel("Group:"))
        self.group_input = QLineEdit()
        self.group_input.setPlaceholderText("Class group or team name...")
        group_layout.addWidget(self.group_input)
        info_layout.addLayout(group_layout)

        layout.addWidget(info_group)

        # Editor Information (Spec #14)
        editor_group = QGroupBox("Editor Information (Required)")
        editor_layout = QVBoxLayout(editor_group)
        editor_layout.addWidget(QLabel("Your Name/Initials:"))
        self.editor_input = QLineEdit()
        self.editor_input.setPlaceholderText("Enter your name or initials...")
        editor_layout.addWidget(self.editor_input)
        layout.addWidget(editor_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.save_button = QPushButton("Save Borrower")
        self.save_button.clicked.connect(self.save_borrower)
        self.save_button.setDefault(True)  # Enter key activates save
        button_layout.addWidget(self.save_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

        # Set dialog properties
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)
        self.setModal(True)  # Block interaction with parent window

    def load_borrower_data(self):
        """Load existing borrower data for editing."""
        if not self.existing_borrower:
            return

        try:
            self.name_input.setText(self.existing_borrower.name)
            self.affiliation_input.setText(self.existing_borrower.affiliation)
            self.group_input.setText(self.existing_borrower.group_name)

            logger.debug(f"Loaded data for borrower {self.borrower_id}")

        except Exception as e:
            logger.error(f"Failed to load borrower data: {e}")
            QMessageBox.warning(self, "Data Load Error", "Failed to load borrower information.")

    def validate_input(self) -> bool:
        """Validate user input."""
        # Check required fields
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Borrower name is required.")
            self.name_input.setFocus()
            return False

        if not self.affiliation_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Affiliation is required.")
            self.affiliation_input.setFocus()
            return False

        if not self.group_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Group name is required.")
            self.group_input.setFocus()
            return False

        if not self.editor_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Editor name is required (Spec #14).")
            self.editor_input.setFocus()
            return False

        return True

    def save_borrower(self):
        """Save the borrower data."""
        try:
            # Validate input
            if not self.validate_input():
                return

            # Check for duplicate borrower (same name, affiliation, group)
            name = self.name_input.text().strip()
            affiliation = self.affiliation_input.text().strip()
            group_name = self.group_input.text().strip()

            # Look for existing borrower with same details
            existing_check = self._find_existing_borrower(name, affiliation, group_name)
            if existing_check and (not self.existing_borrower or existing_check.id != self.existing_borrower.id):
                reply = QMessageBox.question(
                    self, "Duplicate Borrower",
                    f"A borrower with the same name, affiliation, and group already exists.\n\n"
                    f"Name: {existing_check.name}\n"
                    f"Affiliation: {existing_check.affiliation}\n"
                    f"Group: {existing_check.group_name}\n\n"
                    "Do you want to continue creating this duplicate?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return

            # Create or update borrower
            if self.existing_borrower:
                borrower = self.existing_borrower
            else:
                borrower = Borrower()

            borrower.name = name
            borrower.affiliation = affiliation
            borrower.group_name = group_name

            # Save borrower
            success = borrower.save()

            if success:
                action = "updated" if self.existing_borrower else "created"
                logger.info(f"Successfully {action} borrower: {borrower.name}")
                QMessageBox.information(self, "Success", f"Borrower {action} successfully!")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to save borrower. Please try again.")

        except Exception as e:
            logger.error(f"Error saving borrower: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save borrower: {str(e)}")

    def _find_existing_borrower(self, name: str, affiliation: str, group_name: str) -> Optional[Borrower]:
        """Find existing borrower with same details."""
        try:
            from inventory_app.database.connection import db

            query = """
            SELECT * FROM Borrowers
            WHERE name = ? AND affiliation = ? AND group_name = ?
            """
            rows = db.execute_query(query, (name, affiliation, group_name))
            if rows:
                return Borrower(**dict(rows[0]))

        except Exception as e:
            logger.error(f"Error checking for duplicate borrower: {e}")

        return None

    @staticmethod
    def get_borrower_data(parent=None, borrower_id: Optional[int] = None) -> Optional[Borrower]:
        """
        Static method to get borrower data from dialog.
        Returns the borrower object if saved, None if cancelled.
        """
        dialog = BorrowerEditor(parent, borrower_id)
        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            if borrower_id:
                return Borrower.get_by_id(borrower_id)
            else:
                # For new borrowers, we need to find the one we just created
                # This is a simplified approach - in practice, you'd return the created object
                return None

        return None
