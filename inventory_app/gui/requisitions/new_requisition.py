"""
New Requisition Dialog - Complete workflow for creating laboratory requisitions.
Provides comprehensive interface for borrower selection, activity details, and item selection.
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
from inventory_app.services.item_service import ItemService
from inventory_app.services.stock_movement_service import StockMovementService
from inventory_app.gui.borrowers.borrower_selector import BorrowerSelector
from inventory_app.utils.logger import logger
from inventory_app.utils.activity_logger import activity_logger


class NewRequisitionDialog(QDialog):
    """
    Comprehensive dialog for creating new laboratory requisitions.
    Handles complete workflow from borrower selection to item assignment.
    """

    # Signal emitted when requisition is successfully created
    requisition_created = pyqtSignal(int)  # Requisition ID

    def __init__(self, parent=None):
        """Initialize the new requisition dialog."""
        super().__init__(parent)

        # Compose with services
        self.item_service = ItemService()
        self.stock_service = StockMovementService()

        # Initialize data
        self.selected_borrower: Optional[Borrower] = None
        self.selected_items: List[Dict] = []  # List of {item_id, quantity, batch_id}

        self.setup_ui()
        logger.info("New requisition dialog initialized")

    def setup_ui(self):
        """Setup the comprehensive user interface."""
        self.setWindowTitle("📋 Create New Requisition")
        self.setModal(True)
        self.resize(1280, 600)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Header
        header = QLabel("Create New Laboratory Requisition")
        header.setStyleSheet("font-size: 18pt; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header)

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

        self.create_button = QPushButton("✅ Create Requisition")
        self.create_button.clicked.connect(self.create_requisition)
        self.create_button.setEnabled(False)
        button_layout.addWidget(self.create_button)

        self.cancel_button = QPushButton("❌ Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

    def _create_requisition_details_panel(self) -> QWidget:
        """Create the left panel with requisition details."""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Borrower selection
        borrower_group = QGroupBox("👥 Borrower Information")
        borrower_layout = QVBoxLayout(borrower_group)

        self.borrower_info = QLabel("No borrower selected")
        self.borrower_info.setStyleSheet("padding: 10px; font-weight: bold; ")
        borrower_layout.addWidget(self.borrower_info)

        select_borrower_btn = QPushButton("Select Borrower")
        select_borrower_btn.clicked.connect(self.select_borrower)
        borrower_layout.addWidget(select_borrower_btn)

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
        self.expected_borrow.setDateTime(QDateTime.currentDateTime())
        self.expected_borrow.setCalendarPopup(True)
        self.expected_borrow.setDisplayFormat("MMM dd, yyyy hh:mm AP")
        borrow_layout.addWidget(self.expected_borrow)
        activity_layout.addLayout(borrow_layout)

        # Expected return date/time
        return_layout = QHBoxLayout()
        return_layout.addWidget(QLabel("Expected Return:"))
        self.expected_return = QDateTimeEdit()
        # Set default return time to 1 hour from borrow time
        default_return = QDateTime.currentDateTime()
        default_return = default_return.addSecs(3600)  # Add 1 hour
        self.expected_return.setDateTime(default_return)
        self.expected_return.setCalendarPopup(True)
        self.expected_return.setDisplayFormat("MMM dd, yyyy hh:mm AP")
        return_layout.addWidget(self.expected_return)
        activity_layout.addLayout(return_layout)

        # Activity date
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("Activity Date:"))
        self.activity_date = QDateEdit()
        self.activity_date.setDate(QDate.currentDate())
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
        self.activity_name.textChanged.connect(self.update_create_button_state)
        self.expected_borrow.dateTimeChanged.connect(self.update_create_button_state)
        self.expected_return.dateTimeChanged.connect(self.update_create_button_state)
        self.activity_date.dateChanged.connect(self.update_create_button_state)
        self.num_students.valueChanged.connect(self.update_create_button_state)
        self.num_groups.valueChanged.connect(self.update_create_button_state)

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

        # Load initial items
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

    def select_borrower(self):
        """Open borrower selection dialog."""
        borrower_id = BorrowerSelector.select_borrower(self)
        if borrower_id:
            try:
                borrower = Borrower.get_by_id(borrower_id)
                if borrower:
                    self.selected_borrower = borrower
                    self.borrower_info.setText(
                        f"Selected: {borrower.name}\n"
                        f"Affiliation: {borrower.affiliation}\n"
                        f"Group: {borrower.group_name}"
                    )
                    self.update_create_button_state()
                    logger.info(f"Selected borrower: {borrower.name} (ID: {borrower_id})")
                else:
                    QMessageBox.warning(self, "Error", "Failed to load borrower details.")
            except Exception as e:
                logger.error(f"Failed to select borrower {borrower_id}: {e}")
                QMessageBox.critical(self, "Error", f"Failed to select borrower: {str(e)}")

    def load_available_items(self):
        """Load available items for selection."""
        try:
            items = self.item_service.get_inventory_batches_for_selection()
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

            logger.info(f"Loaded {len(items)} available items")

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
                selected['batch_id'] == item_data['batch_id']):
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
                'item_name': item_data['item_name'],
                'batch_number': item_data['batch_number'],
                'quantity': quantity,
                'category_name': item_data['category_name']
            }

            self.selected_items.append(selected_item)
            self.update_selected_items_display()
            self.update_create_button_state()

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
            self.update_create_button_state()
            logger.info(f"Removed item {removed_item['item_name']} from selection")

    def update_selected_items_display(self):
        """Update the display of selected items."""
        self.selected_items_list.clear()

        total_quantity = 0
        for item in self.selected_items:
            display_text = (
                f"{item['item_name']} (Batch #{item['batch_number']}) - "
                f"Qty: {item['quantity']} [{item['category_name']}]"
            )

            list_item = QListWidgetItem(display_text)
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            self.selected_items_list.addItem(list_item)

            total_quantity += item['quantity']

        # Update summary
        if self.selected_items:
            self.items_summary.setText(
                f"Total Items: {len(self.selected_items)} | "
                f"Total Quantity: {total_quantity}"
            )
        else:
            self.items_summary.setText("No items selected")

    def update_create_button_state(self):
        """Update the create button enabled state."""
        has_borrower = self.selected_borrower is not None
        has_items = len(self.selected_items) > 0
        has_activity = self.activity_name.text().strip() != ""

        self.create_button.setEnabled(has_borrower and has_items and has_activity)

    def create_requisition(self):
        """Create the requisition with all validations."""
        if not self._validate_requisition():
            return

        if not self.selected_borrower or not self.selected_borrower.id:
            QMessageBox.critical(self, "Error", "No borrower selected.")
            return

        try:
            # Convert Qt datetime to Python datetime
            expected_borrow_dt = self.expected_borrow.dateTime().toPyDateTime()
            expected_return_dt = self.expected_return.dateTime().toPyDateTime()
            current_time = datetime.now()

            # Determine initial status and datetime_borrowed
            if expected_borrow_dt > current_time:
                # This is a reservation
                initial_status = "requested"
                datetime_borrowed = None  # NULL for reservations not yet picked up
            else:
                # This is immediate borrowing
                initial_status = "active"
                datetime_borrowed = current_time

            # Create requisition record
            requisition = Requisition(
                borrower_id=self.selected_borrower.id,
                datetime_borrowed=datetime_borrowed,
                expected_borrow=expected_borrow_dt,
                expected_return=expected_return_dt,
                status=initial_status,
                lab_activity_name=self.activity_name.text().strip(),
                lab_activity_date=self.activity_date.date().toPyDate(),
                num_students=self.num_students.value(),
                num_groups=self.num_groups.value()
            )

            # Save requisition
            if not requisition.save("System"):  # TODO: Get actual editor name
                QMessageBox.critical(self, "Error", "Failed to save requisition.")
                return

            if not requisition.id:
                QMessageBox.critical(self, "Error", "Failed to get requisition ID after saving.")
                return

            # Create requisition items and stock movements
            for item in self.selected_items:
                # Create requisition item
                req_item = RequisitionItem(
                    requisition_id=requisition.id,
                    item_id=item['item_id'],
                    quantity_borrowed=item['quantity']
                )

                if not req_item.save():
                    logger.error(f"Failed to save requisition item for {item['item_name']}")
                    QMessageBox.critical(self, "Error",
                                       f"Failed to add item {item['item_name']} to requisition.")
                    return

                # Record stock movement
                self.stock_service.record_consumption(
                    item_id=item['item_id'],
                    quantity=item['quantity'],
                    source_id=requisition.id,
                    note=f"Borrowed for {requisition.lab_activity_name}",
                    batch_id=item['batch_id']
                )

            # Log activity
            activity_logger.log_activity(
                activity_logger.REQUISITION_CREATED,
                f"Created requisition for {self.selected_borrower.name}: {requisition.lab_activity_name}",
                requisition.id,
                "requisition",
                "System"  # TODO: Get actual user
            )

            # Build detailed success message
            message = "Requisition created successfully!\n\n"
            message += "📋 Requisition Details:\n"
            message += f"Activity: {requisition.lab_activity_name}\n"
            message += f"Status: {requisition.status.title()}\n\n"

            message += "👥 Borrower Information:\n"
            message += f"Name: {self.selected_borrower.name}\n"
            message += f"Affiliation: {self.selected_borrower.affiliation}\n"
            message += f"Group: {self.selected_borrower.group_name}\n\n"

            message += "📦 Items Borrowed:\n"
            for item in self.selected_items:
                message += f"• {item['item_name']} (Batch #{item['batch_number']}) - Qty: {item['quantity']} [{item['category_name']}]\n"

            QMessageBox.information(self, "Success", message)

            self.requisition_created.emit(requisition.id)
            self.accept()

        except Exception as e:
            logger.error(f"Failed to create requisition: {e}")
            QMessageBox.critical(self, "Error", f"Failed to create requisition: {str(e)}")

    def _validate_requisition(self) -> bool:
        """Validate requisition data before creation."""
        if not self.selected_borrower:
            QMessageBox.warning(self, "Validation Error", "Please select a borrower.")
            return False

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
    def create_new_requisition(parent=None) -> Optional[int]:
        """
        Static method to create a new requisition.
        Returns the requisition ID if successful, None otherwise.
        """
        # For now, this method cannot return the requisition ID due to signal timing
        # The dialog will emit the requisition_created signal when successful
        dialog = NewRequisitionDialog(parent)
        dialog.exec()
        return None
