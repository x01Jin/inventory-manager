"""
Edit Requisition Dialog - Edit mode implementation.

Thin wrapper around BaseRequisitionDialog for editing existing requisitions.
Handles loading existing data and requisition update workflow.
"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGroupBox,
    QLineEdit,
    QTextEdit,
    QMessageBox,
)
from PyQt6.QtCore import pyqtSignal

from .base_requisition_dialog import BaseRequisitionDialog
from inventory_app.utils.logger import logger


class EditRequisitionDialog(BaseRequisitionDialog):
    """
    Dialog for editing existing laboratory requisitions.

    Thin wrapper around BaseRequisitionDialog that implements
    edit-specific functionality like loading existing data.
    """

    # Signal emitted when requisition is successfully updated
    requisition_updated = pyqtSignal()

    def __init__(self, requisition_summary, parent=None):
        """
        Initialize the edit requisition dialog.

        Args:
            requisition_summary: Summary object containing requisition data
            parent: Parent widget
        """
        self.requisition_summary = requisition_summary
        self.original_requisition = requisition_summary.requisition
        self.original_borrower = requisition_summary.borrower

        super().__init__(mode="edit", parent=parent)

        # Load existing data
        self.load_existing_data()

        logger.info(
            f"Edit requisition dialog initialized for ID: {self.original_requisition.id}"
        )

    def _setup_header(self, layout):
        """Setup edit-specific header."""
        header = QLabel("✏️ Edit Laboratory Requisition")
        header.setStyleSheet("font-size: 18pt; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header)

    def _create_requisition_details_panel(self):
        """Create edit-specific requisition details panel with read-only borrower info."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(15)

        # Borrower info (read-only in edit mode)
        borrower_group = QGroupBox("👥 Borrower (Cannot be changed)")
        borrower_layout = QVBoxLayout(borrower_group)

        self.borrower_info = QLabel("Loading...")
        self.borrower_info.setStyleSheet("font-weight: bold; padding: 5px;")
        borrower_layout.addWidget(self.borrower_info)

        layout.addWidget(borrower_group)

        # Activity details
        activity_group = QGroupBox("📝 Activity Details")
        activity_layout = QVBoxLayout(activity_group)

        # Activity name
        activity_name_layout = QHBoxLayout()
        activity_name_layout.addWidget(QLabel("Activity Name:"))
        self.activity_name = QLineEdit()
        self.activity_name.setPlaceholderText("Enter activity name (required)")
        self.activity_name.textChanged.connect(self.update_create_button_state)
        activity_name_layout.addWidget(self.activity_name)
        activity_layout.addLayout(activity_name_layout)

        # Activity description
        activity_layout.addWidget(QLabel("Description:"))
        self.activity_description = QTextEdit()
        self.activity_description.setPlaceholderText("Optional activity description")
        self.activity_description.setMaximumHeight(80)
        activity_layout.addWidget(self.activity_description)

        # Activity date - compact format [Dec][23][2025]
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("Activity Date:"))
        self.activity_date_selector = self.datetime_manager.create_selector(self)
        date_layout.addWidget(self.activity_date_selector)
        activity_layout.addLayout(date_layout)

        # Number of students/groups
        numbers_layout = QHBoxLayout()

        students_layout = QVBoxLayout()
        students_layout.addWidget(QLabel("Number of Students:"))
        self.num_students = QLineEdit()
        self.num_students.setPlaceholderText("Optional")
        students_layout.addWidget(self.num_students)

        groups_layout = QVBoxLayout()
        groups_layout.addWidget(QLabel("Number of Groups:"))
        self.num_groups = QLineEdit()
        self.num_groups.setPlaceholderText("Optional")
        groups_layout.addWidget(self.num_groups)

        numbers_layout.addLayout(students_layout)
        numbers_layout.addLayout(groups_layout)
        activity_layout.addLayout(numbers_layout)

        layout.addWidget(activity_group)

        return panel

    def _setup_buttons(self, layout):
        """Setup edit-specific buttons."""
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # Update button
        self.update_button = QPushButton("✅ Update Requisition")
        self.update_button.clicked.connect(self.update_requisition)
        self.update_button.setEnabled(
            False
        )  # Initially disabled until changes are made
        button_layout.addWidget(self.update_button)

        # Cancel button
        cancel_button = QPushButton("❌ Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

    def update_create_button_state(self):
        """Update update button enabled state based on form completeness and changes."""
        has_activity = self.activity_name.text().strip() != ""
        has_items = len(self.selected_items) > 0
        has_changes = self._has_changes()

        self.update_button.setEnabled(has_activity and has_items and has_changes)

    def load_existing_data(self):
        """Load existing requisition data into the form."""
        try:
            # Set borrower info (read-only)
            if self.original_borrower:
                self.selected_borrower = self.original_borrower
                self.borrower_info.setText(
                    f"{self.original_borrower.name} ({self.original_borrower.affiliation})"
                )

            # Load activity details
            if (
                hasattr(self.original_requisition, "lab_activity_name")
                and self.original_requisition.lab_activity_name
            ):
                self.activity_name.setText(self.original_requisition.lab_activity_name)

            # Activity description (if available in summary)
            if hasattr(self.requisition_summary, "activity_description"):
                self.activity_description.setText(
                    self.requisition_summary.activity_description or ""
                )

            # Activity date
            if (
                hasattr(self.original_requisition, "lab_activity_date")
                and self.original_requisition.lab_activity_date
            ):
                self.datetime_manager.load_from_date(self.original_requisition.lab_activity_date)

            # Number of students/groups
            if (
                hasattr(self.original_requisition, "num_students")
                and self.original_requisition.num_students
            ):
                self.num_students.setText(str(self.original_requisition.num_students))

            if (
                hasattr(self.original_requisition, "num_groups")
                and self.original_requisition.num_groups
            ):
                self.num_groups.setText(str(self.original_requisition.num_groups))

            # Load dates into schedule manager
            if (
                hasattr(self.original_requisition, "expected_borrow")
                and self.original_requisition.expected_borrow
            ):
                self.schedule_manager.set_borrow_datetime(self.original_requisition.expected_borrow)

            if (
                hasattr(self.original_requisition, "expected_return")
                and self.original_requisition.expected_return
            ):
                self.schedule_manager.set_return_datetime(self.original_requisition.expected_return)

            # Load selected items
            self.load_existing_items()

            logger.info(
                f"Loaded existing data for requisition {self.original_requisition.id}"
            )

        except Exception as e:
            logger.error(f"Failed to load existing requisition data: {e}")
            QMessageBox.critical(
                self, "Error", f"Failed to load requisition data: {str(e)}"
            )

    def load_existing_items(self):
        """Load existing requisition items."""
        try:
            from inventory_app.database.models import RequisitionItem

            # Get requisition items
            req_items = RequisitionItem.get_by_requisition(self.original_requisition.id)

            for req_item in req_items:
                # Get item details by querying the database
                from inventory_app.database.connection import db

                # Query item and batch information
                item_query = """
                SELECT i.id as item_id, i.name as item_name, c.name as category_name,
                       ib.id as batch_id, ib.batch_number,
                       ib.quantity_received as available_stock
                FROM Items i
                JOIN Categories c ON i.category_id = c.id
                LEFT JOIN Item_Batches ib ON ib.item_id = i.id
                WHERE i.id = ?
                LIMIT 1
                """

                item_result = db.execute_query(item_query, (req_item.item_id,))

                if item_result:
                    item_data = item_result[0]
                    # Create standardized item structure
                    item = self.item_manager._create_standard_item_structure(
                        item_data, req_item.quantity_borrowed
                    )
                    self.selected_items.append(item)

            # Update display
            self.update_selected_items_display()
            logger.info(f"Loaded {len(self.selected_items)} items for editing")

        except Exception as e:
            logger.error(f"Failed to load existing items: {e}")

    def _has_changes(self) -> bool:
        """Check if there are any changes from the original data."""
        try:
            # Check activity name
            original_name = (
                getattr(self.original_requisition, "lab_activity_name", "") or ""
            )
            current_name = self.activity_name.text().strip()
            if original_name != current_name:
                return True

            # Check activity date
            original_date = getattr(
                self.original_requisition, "lab_activity_date", None
            )
            current_date_str = self.activity_date_selector.get_selected_date_iso()
            if current_date_str:
                from datetime import date

                try:
                    current_date = date.fromisoformat(current_date_str)
                    if original_date != current_date:
                        return True
                except ValueError:
                    pass  # Invalid date format, consider it a change
            elif original_date:
                return True

            # Check dates
            original_borrow = getattr(
                self.original_requisition, "expected_borrow", None
            )
            current_borrow = self.schedule_manager.get_borrow_datetime()
            if original_borrow != current_borrow:
                return True

            original_return = getattr(
                self.original_requisition, "expected_return", None
            )
            current_return = self.schedule_manager.get_return_datetime()
            if original_return != current_return:
                return True

            # Check numeric fields
            original_students = getattr(self.original_requisition, "num_students", None)
            current_students = self.num_students.text().strip()
            current_students_int = int(current_students) if current_students else None
            if original_students != current_students_int:
                return True

            original_groups = getattr(self.original_requisition, "num_groups", None)
            current_groups = self.num_groups.text().strip()
            current_groups_int = int(current_groups) if current_groups else None
            if original_groups != current_groups_int:
                return True

            # Check items (simplified check)
            # In a real implementation, you'd want to compare the full item lists
            # For now, we'll assume items haven't changed if count is the same
            from inventory_app.database.models import RequisitionItem

            original_items = RequisitionItem.get_by_requisition(
                self.original_requisition.id
            )
            if len(original_items) != len(self.selected_items):
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to check for changes: {e}")
            return True  # Assume changes if we can't check

    def update_requisition(self):
        """Update the existing requisition."""
        try:
            # Gather form data
            activity_name = self.activity_name.text().strip()
            activity_description = self.activity_description.toPlainText().strip()
            activity_date = self.activity_date_selector.get_selected_date_iso()

            expected_borrow = self.schedule_manager.get_borrow_datetime()
            expected_return = self.schedule_manager.get_return_datetime()

            # Parse optional numeric fields
            num_students = None
            num_groups = None

            if self.num_students.text().strip():
                try:
                    num_students = int(self.num_students.text().strip())
                except ValueError:
                    QMessageBox.warning(
                        self,
                        "Invalid Input",
                        "Number of students must be a valid number.",
                    )
                    return

            if self.num_groups.text().strip():
                try:
                    num_groups = int(self.num_groups.text().strip())
                except ValueError:
                    QMessageBox.warning(
                        self,
                        "Invalid Input",
                        "Number of groups must be a valid number.",
                    )
                    return

            # Validate borrower
            if not self.selected_borrower:
                QMessageBox.warning(
                    self, "Validation Error", "Borrower information is missing."
                )
                return

            # Validate borrow/return times are set
            if not expected_borrow or not expected_return:
                QMessageBox.warning(
                    self, "Validation Error", "Please set both borrow and return times."
                )
                return

            # Convert to QDateTime for validation
            from inventory_app.utils.date_utils import datetime_to_qdatetime
            expected_borrow_qt = datetime_to_qdatetime(expected_borrow)
            expected_return_qt = datetime_to_qdatetime(expected_return)

            if expected_borrow_qt is None or expected_return_qt is None:
                QMessageBox.warning(
                    self, "Validation Error", "Invalid date/time format selected."
                )
                return

            # Validate data
            if not self.validator.validate_requisition_data(
                self.selected_borrower,
                self.selected_items,
                expected_borrow_qt,
                expected_return_qt,
                activity_name,
            ):
                return

            # Validate activity date format
            from inventory_app.utils.date_utils import is_valid_date_format
            if activity_date and not is_valid_date_format(activity_date):
                QMessageBox.warning(
                    self, "Invalid Date", "Please select a valid activity date."
                )
                return

            # Check if there are actual changes
            if not self._has_changes():
                QMessageBox.information(self, "No Changes", "No changes detected.")
                return

            # Update requisition
            from datetime import date

            self.original_requisition.expected_borrow = expected_borrow
            self.original_requisition.expected_return = expected_return
            self.original_requisition.lab_activity_name = activity_name
            self.original_requisition.lab_activity_date = (
                date.fromisoformat(activity_date) if activity_date else date.today()
            )
            self.original_requisition.num_students = num_students
            self.original_requisition.num_groups = num_groups

            # Save changes
            if not self.original_requisition.save("System"):
                QMessageBox.critical(self, "Error", "Failed to update requisition.")
                return

            # Log rich activity description
            from inventory_app.services.requisition_activity import (
                requisition_activity_manager,
            )

            items_summary = requisition_activity_manager.format_items_summary(
                self.selected_items
            )
            requisition_activity_manager.log_requisition_updated(
                requisition_id=self.original_requisition.id,
                borrower_name=self.original_borrower.name,
                activity_name=activity_name,
                activity_description=activity_description,
                items_summary=items_summary,
            )

            logger.info(
                f"Requisition {self.original_requisition.id} updated successfully"
            )
            QMessageBox.information(
                self, "Success", "Requisition updated successfully!"
            )

            # Refresh available items to show updated stock
            self.load_available_items()

            # Emit signal and close dialog
            self.requisition_updated.emit()
            self.accept()

        except Exception as e:
            logger.error(f"Failed to update requisition: {e}")
            QMessageBox.critical(
                self, "Error", f"Failed to update requisition: {str(e)}"
            )
