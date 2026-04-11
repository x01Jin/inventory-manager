"""
Edit Requisition Dialog - Edit mode implementation.

Thin wrapper around BaseRequisitionDialog for editing existing requisitions.
Allows free editing of all fields like reverting to creation state.
"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QMessageBox,
)
from PyQt6.QtCore import pyqtSignal, QTimer

from .base_requisition_dialog import BaseRequisitionDialog
from .requester_selector_widget import RequesterSelectorWidget
from .activity_details_widget import ActivityDetailsWidget
from .status_watcher import status_watcher
from inventory_app.utils.logger import logger


class EditRequisitionDialog(BaseRequisitionDialog):
    """
    Dialog for editing existing laboratory requisitions.

    Simplified version that allows free editing of all fields,
    behaving like reverting the requisition to creation state.
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
        self.requisition_id = requisition_summary.requisition.id

        super().__init__(mode="edit", parent=parent)

        # Set exclusion for stock calculations during editing
        self.temp_requisition_id = self.requisition_id

        # Load existing data into form fields
        self.load_existing_data_simple()

        logger.info(
            f"Edit requisition dialog initialized for ID: {self.requisition_id}"
        )

    def _create_requisition_details_panel(self):
        """Create requisition details panel with editable requester selection."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(5)

        # Requester selection widget - in edit mode, mode cannot be changed
        self.requester_widget = RequesterSelectorWidget(parent=self, edit_mode=True)
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
        """Setup edit-specific buttons (placed in right panel action area)."""
        # If the action area wasn't created for some reason, fall back to bottom layout
        target_layout = getattr(self, "action_buttons_layout", None)
        if target_layout is None:
            from PyQt6.QtWidgets import QHBoxLayout

            target_layout = QHBoxLayout()
            target_layout.addStretch()
            layout.addLayout(target_layout)

        # Update button
        self.update_button = QPushButton("✅ Update Requisition")
        self.update_button.clicked.connect(self.update_requisition)
        self.update_button.setEnabled(False)  # Initially disabled
        target_layout.addWidget(self.update_button)

        # Cancel button
        cancel_button = QPushButton("❌ Cancel")
        cancel_button.clicked.connect(self.reject)
        target_layout.addWidget(cancel_button)

    def _on_requester_selected(self, requester):
        """Handle requester selection from widget."""
        self.selected_requester = requester
        self.update_create_button_state()

    def update_create_button_state(self):
        """Update update button enabled state based on form completeness."""
        has_requester = self.selected_requester is not None
        has_activity = self.activity_widget.get_activity_name().strip() != ""
        has_items = len(self.selected_items) > 0

        self.update_button.setEnabled(has_requester and has_activity and has_items)

    def load_existing_data_simple(self):
        """Load existing requisition data into form fields simply."""
        try:
            from inventory_app.database.models import RequisitionItem
            from inventory_app.database.connection import db
            from datetime import datetime

            # Load requester
            if self.requisition_summary.requester:
                self.selected_requester = self.requisition_summary.requester
                self.requester_widget.set_selected_requester(self.selected_requester)

            # Load activity details
            req = self.requisition_summary.requisition
            if hasattr(req, "lab_activity_name") and req.lab_activity_name:
                self.activity_widget.set_activity_name(req.lab_activity_name)

            # Activity description
            if (
                hasattr(req, "lab_activity_description")
                and req.lab_activity_description
            ):
                self.activity_widget.set_activity_description(
                    req.lab_activity_description
                )
            elif hasattr(self.requisition_summary, "activity_description"):
                self.activity_widget.set_activity_description(
                    self.requisition_summary.activity_description or ""
                )

            # Activity date - improved loading with error handling
            if hasattr(req, "lab_activity_date") and req.lab_activity_date:
                try:
                    # Ensure we have a date object
                    activity_date = req.lab_activity_date
                    if isinstance(activity_date, str):
                        from datetime import date

                        activity_date = date.fromisoformat(activity_date)

                    if activity_date:
                        self.activity_widget.set_activity_date(activity_date)
                        logger.info(f"Loaded activity date: {activity_date}")
                except Exception as date_error:
                    logger.warning(f"Failed to load activity date: {date_error}")
                    # Set to current date as fallback
                    from inventory_app.utils.date_utils import get_current_date

                    self.activity_widget.set_activity_date(get_current_date())

            # Number of students/groups
            if hasattr(req, "num_students") and req.num_students is not None:
                self.activity_widget.set_num_students(req.num_students)
            if hasattr(req, "num_groups") and req.num_groups is not None:
                self.activity_widget.set_num_groups(req.num_groups)

            # Load schedule dates with improved error handling
            if hasattr(req, "expected_request") and req.expected_request:
                try:
                    request_dt = req.expected_request
                    if isinstance(request_dt, str):
                        request_dt = datetime.fromisoformat(request_dt)

                    if isinstance(request_dt, datetime):
                        self.schedule_manager.set_request_datetime(request_dt)
                        logger.info(f"Loaded request datetime: {request_dt}")
                except Exception as dt_error:
                    logger.warning(f"Failed to load request datetime: {dt_error}")

            if hasattr(req, "expected_return") and req.expected_return:
                try:
                    return_dt = req.expected_return
                    if isinstance(return_dt, str):
                        return_dt = datetime.fromisoformat(return_dt)

                    if isinstance(return_dt, datetime):
                        self.schedule_manager.set_return_datetime(return_dt)
                        logger.info(f"Loaded return datetime: {return_dt}")
                except Exception as dt_error:
                    logger.warning(f"Failed to load return datetime: {dt_error}")

            # Load items simply
            req_items = RequisitionItem.get_by_requisition(self.requisition_id)
            for req_item in req_items:
                # Get item details
                item_query = """
                SELECT i.id as item_id, i.name as item_name, c.name as category_name,
                       ib.id as batch_id, ib.batch_number, ib.quantity_received as available_stock
                FROM Items i
                JOIN Categories c ON i.category_id = c.id
                LEFT JOIN Item_Batches ib ON ib.item_id = i.id
                WHERE i.id = ? LIMIT 1
                """
                item_result = db.execute_query(item_query, (req_item.item_id,))
                if item_result:
                    item_data = item_result[0]
                    item = self.item_manager._create_standard_item_structure(
                        item_data, req_item.quantity_requested
                    )
                    self.selected_items.append(item)

            # Update displays
            self.update_selected_items_display()
            self.update_create_button_state()

            logger.info(f"Loaded existing data for requisition {self.requisition_id}")

        except Exception as e:
            logger.error(f"Failed to load existing data: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load data: {str(e)}")

    def update_requisition(self):
        """Update the requisition with current form data."""
        try:
            # Gather form data from widgets
            activity_name = self.activity_widget.get_activity_name()
            activity_description = self.activity_widget.get_activity_description()
            activity_date = self.activity_widget.get_activity_date_iso()

            expected_request = self.schedule_manager.get_request_datetime()
            expected_return = self.schedule_manager.get_return_datetime()

            # Basic validation
            if not expected_request or not expected_return:
                QMessageBox.warning(
                    self,
                    "Validation Error",
                    "Please set both request and return times.",
                )
                return

            if not self.selected_requester:
                QMessageBox.warning(
                    self, "Validation Error", "Please select a requester."
                )
                return

            # Get numeric fields from widget
            num_students = self.activity_widget.get_num_students()
            num_groups = self.activity_widget.get_num_groups()

            # Convert to QDateTime for validation
            from inventory_app.utils.date_utils import datetime_to_qdatetime

            expected_request_qt = datetime_to_qdatetime(expected_request)
            expected_return_qt = datetime_to_qdatetime(expected_return)

            if expected_request_qt is None or expected_return_qt is None:
                QMessageBox.warning(
                    self, "Validation Error", "Invalid date/time format."
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
            from datetime import date

            # Server-side validation using ValidationService
            from inventory_app.services import ValidationService

            svc = ValidationService()
            requisition_data = {
                "expected_request": expected_request.isoformat()
                if expected_request
                else "",
                "expected_return": expected_return.isoformat()
                if expected_return
                else "",
                "lab_activity_name": activity_name,
                "lab_activity_date": activity_date or date.today().isoformat(),
            }
            items_payload = [
                {"item_id": item["item_id"], "quantity_requested": item["quantity"]}
                for item in self.selected_items
            ]
            # Ensure requester id is present and an int
            requester_id = None
            if self.selected_requester and self.selected_requester.id is not None:
                requester_id = self.selected_requester.id
            else:
                QMessageBox.warning(
                    self, "Validation Error", "Please select a valid requester."
                )
                return

            if not svc.validate_requisition_creation(
                requester_id,
                requisition_data,
                items_payload,
            ):
                QMessageBox.warning(
                    self,
                    "Validation Error",
                    svc.get_last_error() or "Invalid requisition data",
                )
                return

            # Update requisition
            from datetime import date
            from inventory_app.database.models import Requisition, RequisitionItem
            from inventory_app.database.connection import db
            from inventory_app.utils.date_utils import (
                parse_datetime_iso,
                parse_date_iso,
            )

            # Get current requisition data
            query = "SELECT * FROM Requisitions WHERE id = ?"
            rows = db.execute_query(query, (self.requisition_id,))
            if not rows:
                QMessageBox.critical(self, "Error", "Requisition not found.")
                return

            # Create Requisition object from database data
            req_dict = dict(rows[0])
            # Convert dates
            if req_dict.get("expected_request"):
                req_dict["expected_request"] = parse_datetime_iso(
                    req_dict["expected_request"]
                )
            if req_dict.get("expected_return"):
                req_dict["expected_return"] = parse_datetime_iso(
                    req_dict["expected_return"]
                )
            if req_dict.get("lab_activity_date"):
                req_dict["lab_activity_date"] = parse_date_iso(
                    req_dict["lab_activity_date"]
                )

            req = Requisition(**req_dict)

            # Update main fields
            if self.selected_requester and self.selected_requester.id is not None:
                req.requester_id = self.selected_requester.id
            req.expected_request = expected_request
            req.expected_return = expected_return
            req.lab_activity_name = activity_name
            req.lab_activity_description = activity_description
            req.lab_activity_date = (
                date.fromisoformat(activity_date) if activity_date else date.today()
            )
            req.num_students = num_students
            req.num_groups = num_groups

            # Update requisition and modifications in a single transaction
            from inventory_app.database.connection import db as global_db
            from inventory_app.services.requisition_activity import (
                requisition_activity_manager,
            )

            try:
                with global_db.transaction(immediate=True):
                    # Require editor attribution for audit trail before persisting changes.
                    editor_name = self.get_editor_name()
                    if not editor_name:
                        raise Exception("Editor name is required")

                    if not req.save(editor_name):
                        raise Exception("Failed to save requisition")

                    # Clear existing items and re-create
                    db.execute_update(
                        "DELETE FROM Requisition_Items WHERE requisition_id = ?",
                        (self.requisition_id,),
                    )

                    # Delete existing stock movements to prevent double reservation
                    self.stock_service.delete_movements_for_requisition(
                        self.requisition_id
                    )

                    # Add new items
                    for item in self.selected_items:
                        req_item = RequisitionItem()
                        req_item.requisition_id = self.requisition_id
                        req_item.item_id = item["item_id"]
                        req_item.quantity_requested = item["quantity"]
                        if not req_item.save():
                            raise Exception(f"Failed to save item {item['item_id']}")

                    # Create stock movements for the updated requisition
                    if not self.item_manager.create_stock_movements_for_requisition(
                        self.requisition_id, self.selected_items
                    ):
                        raise Exception("Failed to create stock movements")

                    # Log activity (include in transaction)
                    success = requisition_activity_manager.log_requisition_updated(
                        requisition_id=self.requisition_id,
                        requester_name=self.selected_requester.name,
                        user_name=editor_name,
                    )
                    if not success:
                        raise Exception("Failed to log requisition update activity")
            except Exception as e:
                logger.error(f"Failed to update requisition in transaction: {e}")
                QMessageBox.critical(self, "Error", f"Failed to update: {str(e)}")
                return

            logger.info(f"Requisition {self.requisition_id} updated successfully")
            QMessageBox.information(
                self, "Success", "Requisition updated successfully!"
            )

            # Start the status update workflow with 0.5 second delay
            self._start_status_update_workflow()

        except Exception as e:
            logger.error(f"Failed to update requisition: {e}")
            QMessageBox.critical(self, "Error", f"Failed to update: {str(e)}")

    def _start_status_update_workflow(self):
        """Start the status update workflow with 0.5 second delay."""
        # Create timer for 0.5 second delay before status update
        self.status_timer = QTimer(self)
        self.status_timer.setSingleShot(True)
        self.status_timer.timeout.connect(self._update_status_after_delay)
        self.status_timer.start(500)  # 500ms = 0.5 seconds

    def _update_status_after_delay(self):
        """Update requisition status after the delay."""
        try:
            # Update status using the status watcher
            new_status = status_watcher.update_status_for_requisition(
                self.requisition_id
            )
            logger.info(
                f"Status updated to {new_status} for requisition {self.requisition_id}"
            )

            # Start refresh timer for another 0.5 second delay
            self.refresh_timer = QTimer(self)
            self.refresh_timer.setSingleShot(True)
            self.refresh_timer.timeout.connect(self._refresh_after_status_update)
            self.refresh_timer.start(500)  # 500ms = 0.5 seconds

        except Exception as e:
            logger.error(
                f"Failed to update status for requisition {self.requisition_id}: {e}"
            )
            # Continue with refresh even if status update fails
            self._refresh_after_status_update()

    def _refresh_after_status_update(self):
        """Refresh the UI after status update."""
        try:
            # Refresh available items to show updated stock
            self.load_available_items()

            # Emit signal to notify parent of the update
            self.requisition_updated.emit()

            # Close the dialog
            self.accept()

        except Exception as e:
            logger.error(f"Failed to refresh after status update: {e}")
            # Still close the dialog even if refresh fails
            self.accept()
