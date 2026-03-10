"""
New Requisition Dialog - Create mode implementation.

Thin wrapper around BaseRequisitionDialog for creating new requisitions.
Handles requester selection and requisition creation workflow.
"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QMessageBox,
)
from PyQt6.QtCore import pyqtSignal

from .base_requisition_dialog import BaseRequisitionDialog
from .requester_selector_widget import RequesterSelectorWidget
from .activity_details_widget import ActivityDetailsWidget
from inventory_app.utils.logger import logger
from inventory_app.services import ValidationService


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

    def _create_requisition_details_panel(self):
        """Create requisition details panel with requester selection for create mode."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(5)

        # Requester selection widget
        self.requester_widget = RequesterSelectorWidget(parent=self)
        self.requester_widget.requester_selected.connect(self._on_requester_selected)
        layout.addWidget(self.requester_widget, 0)  # No stretch

        # Activity details widget
        self.activity_widget = ActivityDetailsWidget(parent=self)
        self.activity_widget.set_datetime_manager(self.datetime_manager)
        self.activity_widget.activity_name_changed.connect(
            self.update_create_button_state
        )
        self.activity_widget.field_changed.connect(self.update_create_button_state)
        layout.addWidget(self.activity_widget, 1)  # Allow stretch

        return panel

    def _setup_buttons(self, layout):
        """Setup create-specific buttons (placed in right panel action area)."""
        # If the action area wasn't created for some reason, fall back to bottom layout
        target_layout = getattr(self, "action_buttons_layout", None)
        if target_layout is None:
            from PyQt6.QtWidgets import QHBoxLayout

            target_layout = QHBoxLayout()
            target_layout.addStretch()
            layout.addLayout(target_layout)

        # Create button
        self.create_button = QPushButton("✅ Create Requisition")
        self.create_button.clicked.connect(self.create_requisition)
        self.create_button.setEnabled(False)  # Initially disabled
        target_layout.addWidget(self.create_button)

        # Cancel button
        cancel_button = QPushButton("❌ Cancel")
        cancel_button.clicked.connect(self.reject)
        target_layout.addWidget(cancel_button)

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
                    self,
                    "Validation Error",
                    "Please set both request and return times.",
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

            from datetime import date

            # Server-side validation using ValidationService to enforce bounds and types
            svc = ValidationService()
            requisition_data = {
                "expected_request": expected_request.isoformat(),
                "expected_return": expected_return.isoformat(),
                "lab_activity_name": activity_name,
                "lab_activity_date": activity_date or date.today().isoformat(),
            }
            items_payload = [
                {"item_id": item["item_id"], "quantity_requested": item["quantity"]}
                for item in self.selected_items
            ]
            if not svc.validate_requisition_creation(
                self.selected_requester.id, requisition_data, items_payload
            ):
                QMessageBox.warning(
                    self,
                    "Validation Error",
                    svc.get_last_error() or "Invalid requisition data",
                )
                return

            # Create requisition using models directly
            from inventory_app.database.models import Requisition, RequisitionItem
            from datetime import date

            # Create main requisition and related records inside a transaction
            # so that any failure in saving items or creating movements will
            # cause the entire operation to rollback.
            from inventory_app.database.connection import db as global_db

            # Use an IMMEDIATE transaction to reserve stock atomically and
            # prevent concurrent reservations from oversubscribing stock.
            with global_db.transaction(immediate=True):
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

                # Save requisition; raise on failure to ensure transaction rollback
                if not requisition.save("System"):
                    raise Exception("Failed to create requisition")

                if not requisition.id:
                    raise Exception("Failed to get requisition ID")

                requisition_id = requisition.id

                # Create requisition items
                for item in self.selected_items:
                    # Create requisition item
                    req_item = RequisitionItem()
                    req_item.requisition_id = requisition_id
                    req_item.item_id = item["item_id"]
                    req_item.quantity_requested = item["quantity"]

                    if not req_item.save():
                        raise Exception(
                            f"Failed to save requisition item for item {item['item_id']}"
                        )

                # Create stock movements for the requisition. If movement creation
                # fails, treat it as an error so the transaction will rollback.
                movement_success = (
                    self.item_manager.create_stock_movements_for_requisition(
                        requisition_id, self.selected_items
                    )
                )

                if not movement_success:
                    raise Exception("Failed to create stock movements for requisition")

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
