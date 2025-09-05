"""
Edit Requisition Dialog - Edit mode implementation.

Thin wrapper around BaseRequisitionDialog for editing existing requisitions.
Allows free editing of all fields like reverting to creation state.
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

        logger.info(f"Edit requisition dialog initialized for ID: {self.requisition_id}")

    def _setup_header(self, layout):
        """Setup edit-specific header."""
        header = QLabel("✏️ Edit Laboratory Requisition")
        header.setStyleSheet("font-size: 18pt; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header)

    def _create_requisition_details_panel(self):
        """Create requisition details panel with editable requester selection."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(15)

        # Requester selection (editable in edit mode)
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
        self.update_button.setEnabled(False)  # Initially disabled
        button_layout.addWidget(self.update_button)

        # Cancel button
        cancel_button = QPushButton("❌ Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

    def update_create_button_state(self):
        """Update update button enabled state based on form completeness."""
        has_requester = self.selected_requester is not None
        has_activity = self.activity_name.text().strip() != ""
        has_items = len(self.selected_items) > 0

        self.update_button.setEnabled(has_requester and has_activity and has_items)

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

    def load_existing_data_simple(self):
        """Load existing requisition data into form fields simply."""
        try:
            from inventory_app.database.models import RequisitionItem
            from inventory_app.database.connection import db

            # Load requester
            if self.requisition_summary.requester:
                self.selected_requester = self.requisition_summary.requester
                if self.selected_requester:
                    self.requester_info.setText(
                        f"{self.selected_requester.name} ({self.selected_requester.affiliation})"
                    )

            # Load activity details
            req = self.requisition_summary.requisition
            if hasattr(req, "lab_activity_name") and req.lab_activity_name:
                self.activity_name.setText(req.lab_activity_name)

            # Activity description
            if hasattr(req, "lab_activity_description") and req.lab_activity_description:
                self.activity_description.setText(req.lab_activity_description)
            elif hasattr(self.requisition_summary, "activity_description"):
                self.activity_description.setText(
                    self.requisition_summary.activity_description or ""
                )

            # Activity date
            if hasattr(req, "lab_activity_date") and req.lab_activity_date:
                self.datetime_manager.load_from_date(req.lab_activity_date)

            # Number of students/groups
            if hasattr(req, "num_students") and req.num_students:
                self.num_students.setText(str(req.num_students))
            if hasattr(req, "num_groups") and req.num_groups:
                self.num_groups.setText(str(req.num_groups))

            # Load schedule dates
            if hasattr(req, "expected_request") and req.expected_request:
                self.schedule_manager.set_request_datetime(req.expected_request)
            if hasattr(req, "expected_return") and req.expected_return:
                self.schedule_manager.set_return_datetime(req.expected_return)

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
            # Gather form data
            activity_name = self.activity_name.text().strip()
            activity_description = self.activity_description.toPlainText().strip()
            activity_date = self.datetime_manager.get_selected_date_iso()

            expected_request = self.schedule_manager.get_request_datetime()
            expected_return = self.schedule_manager.get_return_datetime()

            # Basic validation
            if not expected_request or not expected_return:
                QMessageBox.warning(self, "Validation Error", "Please set both request and return times.")
                return

            if not self.selected_requester:
                QMessageBox.warning(self, "Validation Error", "Please select a requester.")
                return

            # Parse numeric fields
            num_students = num_groups = None
            if self.num_students.text().strip():
                try:
                    num_students = int(self.num_students.text().strip())
                except ValueError:
                    QMessageBox.warning(self, "Invalid Input", "Number of students must be a number.")
                    return
            if self.num_groups.text().strip():
                try:
                    num_groups = int(self.num_groups.text().strip())
                except ValueError:
                    QMessageBox.warning(self, "Invalid Input", "Number of groups must be a number.")
                    return

            # Convert to QDateTime for validation
            from inventory_app.utils.date_utils import datetime_to_qdatetime
            expected_request_qt = datetime_to_qdatetime(expected_request)
            expected_return_qt = datetime_to_qdatetime(expected_return)

            if expected_request_qt is None or expected_return_qt is None:
                QMessageBox.warning(self, "Validation Error", "Invalid date/time format.")
                return

            # Validate data
            if not self.validator.validate_requisition_data(
                self.selected_requester, self.selected_items,
                expected_request_qt, expected_return_qt, activity_name
            ):
                return

            # Update requisition
            from datetime import date
            from inventory_app.database.models import Requisition, RequisitionItem
            from inventory_app.database.connection import db
            from inventory_app.utils.date_utils import parse_datetime_iso, parse_date_iso

            # Get current requisition data
            query = "SELECT * FROM Requisitions WHERE id = ?"
            rows = db.execute_query(query, (self.requisition_id,))
            if not rows:
                QMessageBox.critical(self, "Error", "Requisition not found.")
                return

            # Create Requisition object from database data
            req_dict = dict(rows[0])
            # Convert dates
            if req_dict.get('datetime_requested'):
                req_dict['datetime_requested'] = parse_datetime_iso(req_dict['datetime_requested'])
            if req_dict.get('expected_request'):
                req_dict['expected_request'] = parse_datetime_iso(req_dict['expected_request'])
            if req_dict.get('expected_return'):
                req_dict['expected_return'] = parse_datetime_iso(req_dict['expected_return'])
            if req_dict.get('lab_activity_date'):
                req_dict['lab_activity_date'] = parse_date_iso(req_dict['lab_activity_date'])

            req = Requisition(**req_dict)

            # Update main fields
            if self.selected_requester and self.selected_requester.id is not None:
                req.requester_id = self.selected_requester.id
            req.expected_request = expected_request
            req.expected_return = expected_return
            req.lab_activity_name = activity_name
            req.lab_activity_description = activity_description
            req.lab_activity_date = date.fromisoformat(activity_date) if activity_date else date.today()
            req.num_students = num_students
            req.num_groups = num_groups

            if not req.save("System"):
                QMessageBox.critical(self, "Error", "Failed to update requisition.")
                return

            # Clear existing items and re-create
            db.execute_update("DELETE FROM Requisition_Items WHERE requisition_id = ?", (self.requisition_id,))

            # Delete existing stock movements to prevent double reservation
            self.stock_service.delete_movements_for_requisition(self.requisition_id)

            # Add new items
            for item in self.selected_items:
                req_item = RequisitionItem()
                req_item.requisition_id = self.requisition_id
                req_item.item_id = item["item_id"]
                req_item.quantity_requested = item["quantity"]
                if not req_item.save():
                    logger.error(f"Failed to save item {item['item_id']}")
                    QMessageBox.critical(self, "Error", "Failed to save items.")
                    return

            # Create stock movements for the updated requisition
            movement_success = self.item_manager.create_stock_movements_for_requisition(
                self.requisition_id, self.selected_items
            )

            if not movement_success:
                QMessageBox.warning(
                    self, "Stock Movement Warning",
                    "Requisition updated but stock movement recording failed.\n"
                    "Please verify stock levels manually."
                )

            # Log activity
            from inventory_app.services.requisition_activity import requisition_activity_manager
            requisition_activity_manager.log_requisition_updated(
                requisition_id=self.requisition_id,
                requester_name=self.selected_requester.name,
            )

            logger.info(f"Requisition {self.requisition_id} updated successfully")
            QMessageBox.information(self, "Success", "Requisition updated successfully!")

            # Refresh and close
            self.load_available_items()
            self.requisition_updated.emit()
            self.accept()

        except Exception as e:
            logger.error(f"Failed to update requisition: {e}")
            QMessageBox.critical(self, "Error", f"Failed to update: {str(e)}")
