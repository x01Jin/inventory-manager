"""
Edit Requisition Dialog - Complete workflow for editing existing laboratory requisitions.
Provides comprehensive interface for modifying borrower details, activity details, and item selection.
Uses composition pattern with existing services for robust functionality.
"""

from typing import List, Dict, Optional
from datetime import datetime, date
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QMessageBox, QLineEdit,
    QTextEdit, QSpinBox, QDateEdit, QListWidget,
    QListWidgetItem, QSplitter, QWidget, QDateTimeEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QDateTime

from inventory_app.database.models import Borrower, Requisition, RequisitionItem
from inventory_app.database.connection import db
from inventory_app.services.item_service import ItemService
from inventory_app.services.stock_movement_service import StockMovementService
from inventory_app.gui.borrowers.borrower_selector import BorrowerSelector
from inventory_app.utils.logger import logger
from inventory_app.utils.activity_logger import activity_logger


class EditRequisitionDialog(QDialog):
    """
    Comprehensive dialog for editing existing laboratory requisitions.
    Handles complete workflow from borrower details to item assignment.
    """

    # Signal emitted when requisition is successfully updated
    requisition_updated = pyqtSignal(int)  # Requisition ID

    def __init__(self, requisition_summary, parent=None):
        """Initialize the edit requisition dialog."""
        super().__init__(parent)

        # Store original requisition data
        self.original_requisition = requisition_summary.requisition
        self.original_borrower = requisition_summary.borrower
        self.original_items = requisition_summary.items.copy()

        # Compose with services
        self.item_service = ItemService()
        self.stock_service = StockMovementService()

        # Initialize data
        self.selected_borrower: Optional[Borrower] = self.original_borrower
        self.selected_items: List[Dict] = self.original_items.copy()  # List of {item_id, quantity, batch_id}

        self.setup_ui()
        self.load_existing_data()
        logger.info(f"Edit requisition dialog initialized for requisition {self.original_requisition.id}")

    def setup_ui(self):
        """Setup the comprehensive user interface."""
        self.setWindowTitle("📋 Edit Laboratory Requisition")
        self.setModal(True)
        self.resize(1280, 600)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Header
        header = QLabel("Edit Laboratory Requisition")
        header.setStyleSheet("font-size: 18pt; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header)

        # Info label showing original requisition ID
        info_label = QLabel(f"Requisition ID: {self.original_requisition.id}")
        info_label.setStyleSheet("font-size: 10pt; color: #666; font-style: italic;")
        layout.addWidget(info_label)

        # Main content splitter with three panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Left panel - Requisition details
        left_panel = self._create_requisition_details_panel()
        splitter.addWidget(left_panel)

        # Middle panel - Item selection
        middle_panel = self._create_item_selection_panel()
        splitter.addWidget(middle_panel)

        # Right panel - Selected items
        right_panel = self._create_selected_items_summary()
        splitter.addWidget(right_panel)

        splitter.setSizes([350, 500, 350])

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.update_button = QPushButton("✅ Update Requisition")
        self.update_button.clicked.connect(self.update_requisition)
        self.update_button.setEnabled(False)
        button_layout.addWidget(self.update_button)

        self.cancel_button = QPushButton("❌ Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

    def _create_requisition_details_panel(self) -> QWidget:
        """Create the left panel with requisition details."""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Borrower information (read-only)
        borrower_group = QGroupBox("👥 Borrower Information (Cannot be changed)")
        borrower_layout = QVBoxLayout(borrower_group)

        self.borrower_info = QLabel("Loading...")
        self.borrower_info.setStyleSheet("padding: 10px; font-weight: bold; background-color: #f8f9fa; border-radius: 5px;")
        borrower_layout.addWidget(self.borrower_info)

        layout.addWidget(borrower_group)

        # Activity details
        activity_group = QGroupBox("📝 Activity Details")
        activity_layout = QVBoxLayout(activity_group)

        # Activity name
        activity_layout.addWidget(QLabel("Activity Name:"))
        self.activity_name = QLineEdit()
        self.activity_name.setPlaceholderText("e.g., Chemistry Experiment 1")
        activity_layout.addWidget(self.activity_name)

        # Expected borrow date/time
        borrow_layout = QHBoxLayout()
        borrow_layout.addWidget(QLabel("Expected Borrow:"))
        self.expected_borrow = QDateTimeEdit()
        self.expected_borrow.setCalendarPopup(True)
        self.expected_borrow.setDisplayFormat("MMM dd, yyyy hh:mm AP")
        borrow_layout.addWidget(self.expected_borrow)
        activity_layout.addLayout(borrow_layout)

        # Expected return date/time
        return_layout = QHBoxLayout()
        return_layout.addWidget(QLabel("Expected Return:"))
        self.expected_return = QDateTimeEdit()
        self.expected_return.setCalendarPopup(True)
        self.expected_return.setDisplayFormat("MMM dd, yyyy hh:mm AP")
        return_layout.addWidget(self.expected_return)
        activity_layout.addLayout(return_layout)

        # Activity date
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("Activity Date:"))
        self.activity_date = QDateEdit()
        self.activity_date.setCalendarPopup(True)
        self.activity_date.setDisplayFormat("MMM dd, yyyy")
        date_layout.addWidget(self.activity_date)
        activity_layout.addLayout(date_layout)

        # Students and groups
        numbers_layout = QHBoxLayout()

        numbers_layout.addWidget(QLabel("Students:"))
        self.num_students = QSpinBox()
        self.num_students.setRange(0, 1000)
        self.num_students.setValue(0)
        numbers_layout.addWidget(self.num_students)

        numbers_layout.addWidget(QLabel("Groups:"))
        self.num_groups = QSpinBox()
        self.num_groups.setRange(0, 100)
        self.num_groups.setValue(0)
        numbers_layout.addWidget(self.num_groups)

        activity_layout.addLayout(numbers_layout)

        layout.addWidget(activity_group)

        # Notes
        notes_group = QGroupBox("📋 Notes (Optional)")
        notes_layout = QVBoxLayout(notes_group)
        self.notes = QTextEdit()
        self.notes.setPlaceholderText("Additional notes or special instructions...")
        self.notes.setMaximumHeight(80)
        notes_layout.addWidget(self.notes)

        layout.addWidget(notes_group)

        # Connect form field signals to update button state
        self.activity_name.textChanged.connect(self.update_update_button_state)
        self.expected_borrow.dateTimeChanged.connect(self.update_update_button_state)
        self.expected_return.dateTimeChanged.connect(self.update_update_button_state)
        self.activity_date.dateChanged.connect(self.update_update_button_state)
        self.num_students.valueChanged.connect(self.update_update_button_state)
        self.num_groups.valueChanged.connect(self.update_update_button_state)

        layout.addStretch()
        return panel

    def _create_item_selection_panel(self) -> QWidget:
        """Create the right panel with item selection."""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Search and filter
        search_group = QGroupBox("🔍 Search Items")
        search_layout = QVBoxLayout(search_group)

        self.item_search = QLineEdit()
        self.item_search.setPlaceholderText("Search items by name...")
        self.item_search.textChanged.connect(self.search_items)
        search_layout.addWidget(self.item_search)

        layout.addWidget(search_group)

        # Available items list
        items_group = QGroupBox("📦 Available Items")
        items_layout = QVBoxLayout(items_group)

        self.available_items_list = QListWidget()
        self.available_items_list.itemDoubleClicked.connect(self.add_item_to_selection)
        items_layout.addWidget(self.available_items_list)

        # Add item button
        add_item_btn = QPushButton("➕ Add Selected Item")
        add_item_btn.clicked.connect(self.add_item_to_selection)
        items_layout.addWidget(add_item_btn)

        layout.addWidget(items_group)

        # Load initial items (excluding items already in this requisition)
        self.load_available_items()

        return panel

    def _create_selected_items_summary(self) -> QGroupBox:
        """Create the selected items summary panel."""
        group = QGroupBox("🛒 Selected Items")
        layout = QVBoxLayout(group)

        self.selected_items_list = QListWidget()
        layout.addWidget(self.selected_items_list)

        # Summary info
        self.items_summary = QLabel("No items selected")
        self.items_summary.setStyleSheet("font-weight: bold; padding: 5px;")
        layout.addWidget(self.items_summary)

        # Remove item button
        remove_btn = QPushButton("➖ Remove Selected Item")
        remove_btn.clicked.connect(self.remove_selected_item)
        layout.addWidget(remove_btn)

        return group

    def load_existing_data(self):
        """Load existing requisition data into the form."""
        try:
            req = self.original_requisition

            # Borrower info (read-only)
            self.borrower_info.setText(
                f"Selected: {self.original_borrower.name}\n"
                f"Affiliation: {self.original_borrower.affiliation}\n"
                f"Group: {self.original_borrower.group_name}"
            )

            # Activity details
            self.activity_name.setText(req.lab_activity_name or "")

            # Dates
            if req.expected_borrow:
                self.expected_borrow.setDateTime(QDateTime(req.expected_borrow))
            else:
                self.expected_borrow.setDateTime(QDateTime.currentDateTime())

            if req.expected_return:
                self.expected_return.setDateTime(QDateTime(req.expected_return))
            else:
                # Set default return time to 1 hour from borrow time
                default_return = self.expected_borrow.dateTime().addSecs(3600)
                self.expected_return.setDateTime(default_return)

            if req.lab_activity_date:
                self.activity_date.setDate(QDate(req.lab_activity_date))
            else:
                self.activity_date.setDate(QDate.currentDate())

            # Numbers
            self.num_students.setValue(req.num_students or 0)
            self.num_groups.setValue(req.num_groups or 0)

            # Load selected items
            self.load_selected_items()

            # Update button state
            self.update_update_button_state()

            logger.info(f"Loaded existing data for requisition {req.id}")

        except Exception as e:
            logger.error(f"Failed to load existing requisition data: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load requisition data: {str(e)}")

    def load_selected_items(self):
        """Load the currently selected items from the original requisition."""
        try:
            self.selected_items_list.clear()

            for item in self.original_items:
                display_text = (
                    f"{item['name']} (x{item['quantity_borrowed']}) - "
                    f"[{item.get('category_name', 'Unknown')}]"
                )

                list_item = QListWidgetItem(display_text)
                list_item.setData(Qt.ItemDataRole.UserRole, item)
                self.selected_items_list.addItem(list_item)

            # Update summary
            if self.original_items:
                total_quantity = sum(item['quantity_borrowed'] for item in self.original_items)
                self.items_summary.setText(
                    f"Total Items: {len(self.original_items)} | "
                    f"Total Quantity: {total_quantity}"
                )
            else:
                self.items_summary.setText("No items selected")

        except Exception as e:
            logger.error(f"Failed to load selected items: {e}")

    def load_available_items(self):
        """Load available items for selection (excluding current requisition)."""
        try:
            # Get available items, excluding those already in this requisition
            items = self.item_service.get_inventory_batches_for_selection(
                exclude_requisition_id=self.original_requisition.id
            )
            self.available_items_list.clear()

            for item in items:
                display_text = (
                    f"{item['item_name']} "
                    f"(Batch #{item['batch_number']}) - "
                    f"Available: {item['available_stock']} "
                    f"[{item['category_name']}]"
                )

                list_item = QListWidgetItem(display_text)
                list_item.setData(Qt.ItemDataRole.UserRole, item)
                self.available_items_list.addItem(list_item)

            logger.info(f"Loaded {len(items)} available items for editing")

        except Exception as e:
            logger.error(f"Failed to load available items: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load items: {str(e)}")

    def search_items(self, search_text: str):
        """Filter items based on search text."""
        for i in range(self.available_items_list.count()):
            item = self.available_items_list.item(i)
            if item is not None:
                item_data = item.data(Qt.ItemDataRole.UserRole)
                if item_data:
                    item_name = item_data.get('item_name', '').lower()
                    category = item_data.get('category_name', '').lower()
                    search_lower = search_text.lower()

                    visible = (search_lower in item_name or
                              search_lower in category or
                              not search_text.strip())
                    item.setHidden(not visible)

    def add_item_to_selection(self):
        """Add selected item to requisition."""
        current_item = self.available_items_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "No Selection", "Please select an item first.")
            return

        item_data = current_item.data(Qt.ItemDataRole.UserRole)
        if not item_data:
            return

        # Check if item already selected
        for selected in self.selected_items:
            if (selected['item_id'] == item_data['item_id'] and
                selected.get('batch_id') == item_data.get('batch_id')):
                QMessageBox.information(self, "Already Selected",
                                      "This item batch is already in your selection.")
                return

        # Get quantity from user
        available_stock = item_data['available_stock']
        quantity, ok = self._get_quantity_from_user(
            item_data['item_name'],
            available_stock,
            item_data['batch_number']
        )

        if ok and quantity > 0:
            selected_item = {
                'item_id': item_data['item_id'],
                'batch_id': item_data['batch_id'],
                'name': item_data['item_name'],
                'quantity_borrowed': quantity,
                'category_name': item_data['category_name']
            }

            self.selected_items.append(selected_item)
            self.update_selected_items_display()
            self.update_update_button_state()

            logger.info(f"Added item {item_data['item_name']} (x{quantity}) to selection")

    def _get_quantity_from_user(self, item_name: str, max_quantity: int, batch_number: int) -> tuple[int, bool]:
        """Get quantity from user with validation."""
        from PyQt6.QtWidgets import QInputDialog

        quantity, ok = QInputDialog.getInt(
            self,
            "Select Quantity",
            f"Enter quantity for {item_name} (Batch #{batch_number}):\n"
            f"Available: {max_quantity}",
            value=1,
            min=1,
            max=max_quantity
        )

        return quantity, ok if ok is not None else False

    def remove_selected_item(self):
        """Remove selected item from requisition."""
        current_row = self.selected_items_list.currentRow()
        if current_row >= 0 and current_row < len(self.selected_items):
            removed_item = self.selected_items.pop(current_row)
            self.update_selected_items_display()
            self.update_update_button_state()
            logger.info(f"Removed item {removed_item['name']} from selection")

    def update_selected_items_display(self):
        """Update the display of selected items."""
        self.selected_items_list.clear()

        total_quantity = 0
        for item in self.selected_items:
            display_text = (
                f"{item['name']} (x{item['quantity_borrowed']}) - "
                f"[{item.get('category_name', 'Unknown')}]"
            )

            list_item = QListWidgetItem(display_text)
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            self.selected_items_list.addItem(list_item)

            total_quantity += item['quantity_borrowed']

        # Update summary
        if self.selected_items:
            self.items_summary.setText(
                f"Total Items: {len(self.selected_items)} | "
                f"Total Quantity: {total_quantity}"
            )
        else:
            self.items_summary.setText("No items selected")

    def update_update_button_state(self):
        """Update the update button enabled state."""
        has_activity = self.activity_name.text().strip() != ""
        has_items = len(self.selected_items) > 0

        # Check if anything has changed
        has_changes = self._has_changes()

        self.update_button.setEnabled(has_activity and has_items and has_changes)

    def _has_changes(self) -> bool:
        """Check if there are any changes from the original requisition."""
        try:
            req = self.original_requisition

            # Check activity details
            if self.activity_name.text().strip() != (req.lab_activity_name or ""):
                return True

            if self.expected_borrow.dateTime().toPyDateTime() != req.expected_borrow:
                return True

            if self.expected_return.dateTime().toPyDateTime() != req.expected_return:
                return True

            if self.activity_date.date().toPyDate() != req.lab_activity_date:
                return True

            if self.num_students.value() != (req.num_students or 0):
                return True

            if self.num_groups.value() != (req.num_groups or 0):
                return True

            # Check items changes
            if len(self.selected_items) != len(self.original_items):
                return True

            # Check each item
            for orig_item in self.original_items:
                found = False
                for sel_item in self.selected_items:
                    if (sel_item['item_id'] == orig_item['item_id'] and
                        sel_item['quantity_borrowed'] == orig_item['quantity_borrowed']):
                        found = True
                        break
                if not found:
                    return True

            return False

        except Exception as e:
            logger.error(f"Failed to check for changes: {e}")
            return True  # Assume changes if error

    def update_requisition(self):
        """Update the requisition with all validations."""
        if not self._validate_requisition():
            return

        if not self.selected_borrower or not self.selected_borrower.id:
            QMessageBox.critical(self, "Error", "No borrower selected.")
            return

        try:
            # Convert Qt datetime to Python datetime
            expected_borrow_dt = self.expected_borrow.dateTime().toPyDateTime()
            expected_return_dt = self.expected_return.dateTime().toPyDateTime()

            # Update requisition record
            self.original_requisition.expected_borrow = expected_borrow_dt
            self.original_requisition.expected_return = expected_return_dt
            self.original_requisition.lab_activity_name = self.activity_name.text().strip()
            self.original_requisition.lab_activity_date = self.activity_date.date().toPyDate()
            self.original_requisition.num_students = self.num_students.value()
            self.original_requisition.num_groups = self.num_groups.value()

            # Save requisition
            if not self.original_requisition.save("System"):  # TODO: Get actual editor name
                QMessageBox.critical(self, "Error", "Failed to update requisition.")
                return

            # Handle item changes
            if not self._update_requisition_items():
                QMessageBox.critical(self, "Error", "Failed to update requisition items.")
                return

            # Log activity
            activity_logger.log_activity(
                activity_logger.REQUISITION_EDITED,
                f"Updated requisition: {self.original_requisition.lab_activity_name}",
                self.original_requisition.id,
                "requisition",
                "System"  # TODO: Get actual user
            )

            # Build detailed success message
            message = "Requisition updated successfully!\n\n"
            message += "📋 Requisition Details:\n"
            message += f"Activity: {self.original_requisition.lab_activity_name}\n\n"

            message += "👥 Borrower Information:\n"
            message += f"Name: {self.selected_borrower.name}\n"
            message += f"Affiliation: {self.selected_borrower.affiliation}\n"
            message += f"Group: {self.selected_borrower.group_name}\n\n"

            message += "📦 Items Borrowed:\n"
            for item in self.selected_items:
                message += f"• {item['name']} (x{item['quantity_borrowed']}) [{item.get('category_name', 'Unknown')}]\n"

            QMessageBox.information(self, "Success", message)

            self.requisition_updated.emit(self.original_requisition.id)
            self.accept()

        except Exception as e:
            logger.error(f"Failed to update requisition: {e}")
            QMessageBox.critical(self, "Error", f"Failed to update requisition: {str(e)}")

    def _update_requisition_items(self) -> bool:
        """Update requisition items and handle stock movements."""
        try:
            # Get current items from database
            current_items = self.item_service.get_requisition_items_with_details(self.original_requisition.id)

            # Find items to remove
            items_to_remove = []
            for current_item in current_items:
                found = False
                for selected_item in self.selected_items:
                    if (current_item['item_id'] == selected_item['item_id'] and
                        current_item['quantity_borrowed'] == selected_item['quantity_borrowed']):
                        found = True
                        break
                if not found:
                    items_to_remove.append(current_item)

            # Find items to add
            items_to_add = []
            for selected_item in self.selected_items:
                found = False
                for current_item in current_items:
                    if (current_item['item_id'] == selected_item['item_id'] and
                        current_item['quantity_borrowed'] == selected_item['quantity_borrowed']):
                        found = True
                        break
                if not found:
                    items_to_add.append(selected_item)

            # Remove old items and return stock
            for item in items_to_remove:
                # Delete requisition item
                db_query = "DELETE FROM Requisition_Items WHERE requisition_id = ? AND item_id = ?"
                db.execute_update(db_query, (self.original_requisition.id, item['item_id']))

                # Record return movement
                self.stock_service.record_return(
                    item_id=item['item_id'],
                    quantity=item['quantity_borrowed'],
                    source_id=self.original_requisition.id,
                    note=f"Returned during requisition edit: {self.original_requisition.lab_activity_name}",
                    batch_id=item.get('batch_id')
                )

            # Add new items and consume stock
            for item in items_to_add:
                # Create requisition item
                req_item = RequisitionItem(
                    requisition_id=self.original_requisition.id,
                    item_id=item['item_id'],
                    quantity_borrowed=item['quantity_borrowed']
                )

                if not req_item.save():
                    logger.error(f"Failed to save requisition item for {item['name']}")
                    return False

                # Record consumption movement
                self.stock_service.record_consumption(
                    item_id=item['item_id'],
                    quantity=item['quantity_borrowed'],
                    source_id=self.original_requisition.id,
                    note=f"Borrowed during requisition edit: {self.original_requisition.lab_activity_name}",
                    batch_id=item.get('batch_id')
                )

            return True

        except Exception as e:
            logger.error(f"Failed to update requisition items: {e}")
            return False

    def _validate_requisition(self) -> bool:
        """Validate requisition data before update."""
        if not self.activity_name.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter an activity name.")
            return False

        if not self.selected_items:
            QMessageBox.warning(self, "Validation Error", "Please select at least one item.")
            return False

        # Validate expected dates
        expected_borrow_dt = self.expected_borrow.dateTime().toPyDateTime()
        expected_return_dt = self.expected_return.dateTime().toPyDateTime()

        if expected_return_dt <= expected_borrow_dt:
            QMessageBox.warning(self, "Validation Error",
                              "Expected return date/time must be after expected borrow date/time.")
            return False

        # Validate activity date is not too far in the past
        activity_date = self.activity_date.date().toPyDate()
        if activity_date < date.today():
            reply = QMessageBox.question(
                self, "Past Date Warning",
                "The activity date is in the past. Continue anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return False

        return True

    @staticmethod
    def edit_requisition(requisition_summary, parent=None) -> Optional[int]:
        """
        Static method to edit a requisition.
        Returns the requisition ID if successful, None otherwise.
        """
        # Check if requisition can be edited
        if requisition_summary.status == "returned":
            QMessageBox.warning(parent, "Cannot Edit",
                              "Fully returned requisitions cannot be edited.")
            return None

        dialog = EditRequisitionDialog(requisition_summary, parent)
        dialog.exec()
        return None
