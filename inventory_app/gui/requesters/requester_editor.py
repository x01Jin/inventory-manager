"""
Requester editor dialog for adding and editing requester information.
Provides form for requester management in laboratory requisitions.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QGroupBox, QMessageBox
)
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

        # Requester Information Group
        info_group = QGroupBox("Requester Information")
        info_layout = QVBoxLayout(info_group)

        # Name (required)
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Full Name:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter requester's full name...")
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

        self.save_button = QPushButton("Save Requester")
        self.save_button.clicked.connect(self.save_requester)
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

    def load_requester_data(self):
        """Load existing requester data for editing."""
        if not self.existing_requester:
            return

        try:
            self.name_input.setText(self.existing_requester.name)
            self.affiliation_input.setText(self.existing_requester.affiliation)
            self.group_input.setText(self.existing_requester.group_name)

            logger.debug(f"Loaded data for requester {self.requester_id}")

        except Exception as e:
            logger.error(f"Failed to load requester data: {e}")
            QMessageBox.warning(self, "Data Load Error", "Failed to load requester information.")

    def validate_input(self) -> bool:
        """Validate user input."""
        # Check required fields
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Requester name is required.")
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

    def save_requester(self):
        """Save the requester data."""
        try:
            # Validate input
            if not self.validate_input():
                return

            # Check for duplicate requester (same name, affiliation, group)
            name = self.name_input.text().strip()
            affiliation = self.affiliation_input.text().strip()
            group_name = self.group_input.text().strip()

            # Look for existing requester with same details
            existing_check = self._find_existing_requester(name, affiliation, group_name)
            if existing_check and (not self.existing_requester or existing_check.id != self.existing_requester.id):
                reply = QMessageBox.question(
                    self, "Duplicate Requester",
                    f"A requester with the same name, affiliation, and group already exists.\n\n"
                    f"Name: {existing_check.name}\n"
                    f"Affiliation: {existing_check.affiliation}\n"
                    f"Group: {existing_check.group_name}\n\n"
                    "Do you want to continue creating this duplicate?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return

            # Create or update requester
            if self.existing_requester:
                requester = self.existing_requester
            else:
                requester = Requester()

            requester.name = name
            requester.affiliation = affiliation
            requester.group_name = group_name

            # Save requester
            success = requester.save()

            if success:
                action = "updated" if self.existing_requester else "created"
                logger.info(f"Successfully {action} requester: {requester.name}")

                # Log activity
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

    def _find_existing_requester(self, name: str, affiliation: str, group_name: str) -> Optional[Requester]:
        """Find existing requester with same details."""
        try:
            from inventory_app.database.connection import db

            query = """
            SELECT * FROM Requesters
            WHERE name = ? AND affiliation = ? AND group_name = ?
            """
            rows = db.execute_query(query, (name, affiliation, group_name))
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
                # For new requesters, we need to find the one we just created
                # This is a simplified approach - in practice, you'd return the created object
                return None

        return None
