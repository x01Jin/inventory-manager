"""
New Requisition Dialog - Create mode implementation.

Thin wrapper around BaseRequisitionDialog for creating new requisitions.
Handles requester selection and requisition creation workflow.
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


class NewRequisitionDialog(BaseRequisitionDialog):
    """
    Dialog for creating new laboratory requisitions.

    Thin wrapper around BaseRequisitionDialog that implements
    create-specific functionality like requester selection.
    """

    # Signal emitted when requisition is successfully created
    requisition_created = pyqtSignal(int)  # Requisition ID

    def __init__(self, parent=None):
        """
        Initialize the new requisition dialog.

        Args:
            parent: Parent widget
        """
        super().__init__(mode="create", parent=parent)
        logger.info("New requisition dialog initialized")

    def _setup_header(self, layout):
        """Setup create-specific header."""
        header = QLabel("➕ Create New Laboratory Requisition")
        header.setStyleSheet("font-size: 18pt; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header)

    def _create_requisition_details_panel(self):
        """Create requisition details panel with requester selection for create mode."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(15)

        # Requester selection (create mode only)
        requester_group = QGroupBox("👥 Requester Information")
        requester_layout = QVBoxLayout(requester_group)

        # Requester display
        self.requester_info = QLabel("No requester selected")
        self.requester_info.setStyleSheet("font-weight: bold; padding: 5px;")
        requester_layout.addWidget(self.requester_info)

        # Requester selection button
        select_requester_btn = QPushButton("Select Requester")
        select_requester_btn.clicked.connect(self.select_requester)
        requester_layout.addWidget(select_requester_btn)

        layout.addWidget(requester_group)

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
        self.datetime_manager.set_defaults()
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
        """Setup create-specific buttons."""
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # Create button
        self.create_button = QPushButton("✅ Create Requisition")
        self.create_button.clicked.connect(self.create_requisition)
        self.create_button.setEnabled(False)  # Initially disabled
        button_layout.addWidget(self.create_button)

        # Cancel button
        cancel_button = QPushButton("❌ Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

    def update_create_button_state(self):
        """Update create button enabled state based on form completeness."""
        has_requester = self.selected_requester is not None
        has_activity = self.activity_name.text().strip() != ""
        has_items = len(self.selected_items) > 0

        self.create_button.setEnabled(has_requester and has_activity and has_items)

    def select_requester(self):
        """Open requester selection dialog."""
        try:
            from inventory_app.gui.requesters.requester_selector import RequesterSelector

            selector = RequesterSelector(parent=self)
            if selector.exec() == RequesterSelector.DialogCode.Accepted:
                selected_requester_id = selector.get_selected_requester_id()
                if selected_requester_id:
                    # Get the requester object from the model
                    from inventory_app.gui.requesters.requester_model import RequesterModel

                    requester_model = RequesterModel()
                    requester_model.load_data()
                    selected_requester = requester_model.get_requester_by_id(
                        selected_requester_id
                    )

                    if selected_requester:
                        self.selected_requester = selected_requester
                        self.requester_info.setText(
                            f"{selected_requester.name} ({selected_requester.affiliation})"
                        )
                        self.update_create_button_state()
                        logger.info(f"Requester selected: {selected_requester.name}")

        except Exception as e:
            logger.error(f"Failed to select requester: {e}")
            QMessageBox.critical(self, "Error", f"Failed to select requester: {str(e)}")

    def create_requisition(self):
        """Create the new requisition."""
        try:
            # Gather form data
            activity_name = self.activity_name.text().strip()
            activity_description = self.activity_description.toPlainText().strip()
            activity_date = self.datetime_manager.get_selected_date_iso()

            expected_request = self.schedule_manager.get_request_datetime()
            expected_return = self.schedule_manager.get_return_datetime()

            # Validate request/return times are set
            if not expected_request or not expected_return:
                QMessageBox.warning(
                    self, "Validation Error", "Please set both request and return times."
                )
                return

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

            # Validate requester
            if not self.selected_requester or not self.selected_requester.id:
                QMessageBox.warning(
                    self, "Validation Error", "Please select a requester."
                )
                return

            # Convert to QDateTime for validation (handle None case)
            from inventory_app.utils.date_utils import datetime_to_qdatetime
            expected_request_qt = datetime_to_qdatetime(expected_request)
            expected_return_qt = datetime_to_qdatetime(expected_return)

            if expected_request_qt is None or expected_return_qt is None:
                QMessageBox.warning(
                    self, "Validation Error", "Invalid date/time format selected."
                )
                return

            # Validate data
            if not self.validator.validate_requisition_data(
                self.selected_requester,
                self.selected_items,
                expected_request_qt,
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

            # Create requisition using models directly
            from inventory_app.database.models import Requisition, RequisitionItem
            from datetime import date

            # Create main requisition
            requisition = Requisition()
            requisition.requester_id = self.selected_requester.id
            requisition.expected_request = expected_request
            requisition.expected_return = expected_return
            requisition.status = "requested"
            requisition.lab_activity_name = activity_name
            requisition.lab_activity_description = activity_description
            requisition.lab_activity_date = (
                date.fromisoformat(activity_date) if activity_date else date.today()
            )
            requisition.num_students = num_students
            requisition.num_groups = num_groups

            # Save requisition
            if not requisition.save("System"):
                QMessageBox.critical(self, "Error", "Failed to create requisition.")
                return

            if not requisition.id:
                QMessageBox.critical(self, "Error", "Failed to get requisition ID.")
                return

            requisition_id = requisition.id

            # Create requisition items
            for item in self.selected_items:
                # Create requisition item
                req_item = RequisitionItem()
                req_item.requisition_id = requisition_id
                req_item.item_id = item["item_id"]
                req_item.quantity_requested = item["quantity"]

                if not req_item.save():
                    logger.error(
                        f"Failed to save requisition item for item {item['item_id']}"
                    )
                    QMessageBox.critical(
                        self, "Error", "Failed to save requisition items."
                    )
                    return

            # Create stock movements for the requisition
            movement_success = self.item_manager.create_stock_movements_for_requisition(
                requisition_id, self.selected_items
            )

            if not movement_success:
                QMessageBox.warning(
                    self, "Stock Movement Warning",
                    "Requisition created but stock movement recording failed.\n"
                    "Please verify stock levels manually."
                )

            # Get editor name from user
            editor_name = self.get_editor_name()
            if not editor_name:
                QMessageBox.warning(self, "Required", "Editor name is required.")
                return

            # Log activity
            from inventory_app.services.requisition_activity import (
                requisition_activity_manager,
            )

            requisition_activity_manager.log_requisition_created(
                requisition_id=requisition_id,
                requester_name=self.selected_requester.name,
                user_name=editor_name,
            )

            logger.info(f"New requisition created with ID: {requisition_id}")
            QMessageBox.information(
                self,
                "Success",
                "Requisition created successfully!",
            )

            # Refresh available items to show updated stock
            self.load_available_items()

            # Emit signal and close dialog
            self.requisition_created.emit(requisition_id)
            self.accept()

        except Exception as e:
            logger.error(f"Failed to create requisition: {e}")
            QMessageBox.critical(
                self, "Error", f"Failed to create requisition: {str(e)}"
            )
