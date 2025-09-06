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
    QMessageBox,
)
from PyQt6.QtCore import pyqtSignal

from .base_requisition_dialog import BaseRequisitionDialog
from .requester_selector_widget import RequesterSelectorWidget
from .activity_details_widget import ActivityDetailsWidget
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

        # Requester selection widget
        self.requester_widget = RequesterSelectorWidget(parent=self)
        self.requester_widget.requester_selected.connect(self._on_requester_selected)
        layout.addWidget(self.requester_widget)

        # Activity details widget
        self.activity_widget = ActivityDetailsWidget(parent=self)
        self.activity_widget.set_datetime_manager(self.datetime_manager)
        self.activity_widget.activity_name_changed.connect(self.update_create_button_state)
        self.activity_widget.field_changed.connect(self.update_create_button_state)
        layout.addWidget(self.activity_widget)

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

    def _on_requester_selected(self, requester):
        """Handle requester selection from widget."""
        self.selected_requester = requester
        self.update_create_button_state()

    def update_create_button_state(self):
        """Update create button enabled state based on form completeness."""
        has_requester = self.selected_requester is not None
        has_activity = self.activity_widget.get_activity_name().strip() != ""
        has_items = len(self.selected_items) > 0

        self.create_button.setEnabled(has_requester and has_activity and has_items)

    def create_requisition(self):
        """Create the new requisition."""
        try:
            # Gather form data from widgets
            activity_name = self.activity_widget.get_activity_name()
            activity_description = self.activity_widget.get_activity_description()
            activity_date = self.activity_widget.get_activity_date_iso()

            expected_request = self.schedule_manager.get_request_datetime()
            expected_return = self.schedule_manager.get_return_datetime()

            # Validate request/return times are set
            if not expected_request or not expected_return:
                QMessageBox.warning(
                    self, "Validation Error", "Please set both request and return times."
                )
                return

            # Get optional numeric fields from widget
            num_students = self.activity_widget.get_num_students()
            num_groups = self.activity_widget.get_num_groups()

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
