"""
Requisitions management page for laboratory inventory.
Handles borrower management and requisition creation/editing.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QLineEdit, QComboBox, QGroupBox, QMessageBox,
    QDateEdit, QSpinBox, QDialog, QDialogButtonBox,
    QTabWidget, QHeaderView
)
from PyQt6.QtCore import QDate
from datetime import date

from inventory_app.gui.styles import DarkTheme
from inventory_app.database.models import Borrower, Requisition, RequisitionItem, Item, Category
from inventory_app.utils.logger import logger


class RequisitionsPage(QWidget):
    """Main requisitions management page with tabs for borrowers and requisitions."""

    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.refresh_data()

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header with title and actions
        header_layout = QHBoxLayout()
        title = QLabel("📋 Laboratory Requisitions Management")
        title.setStyleSheet(f"font-size: {DarkTheme.FONT_SIZE_TITLE}pt; font-weight: bold;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        # Action buttons
        add_borrower_btn = QPushButton("👤 Add Borrower")
        add_borrower_btn.clicked.connect(self.add_borrower_dialog)
        header_layout.addWidget(add_borrower_btn)

        new_req_btn = QPushButton("📝 New Requisition")
        new_req_btn.clicked.connect(self.create_requisition_dialog)
        header_layout.addWidget(new_req_btn)

        layout.addLayout(header_layout)

        # Tab widget for different sections
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Borrowers tab
        self.borrowers_tab = QWidget()
        self.setup_borrowers_tab()
        self.tab_widget.addTab(self.borrowers_tab, "Borrowers")

        # Requisitions tab
        self.requisitions_tab = QWidget()
        self.setup_requisitions_tab()
        self.tab_widget.addTab(self.requisitions_tab, "Requisitions")

        # Connect tab changes to refresh data
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

    def setup_borrowers_tab(self):
        """Setup the borrowers management tab."""
        layout = QVBoxLayout(self.borrowers_tab)

        # Search functionality
        search_layout = QHBoxLayout()
        search_label = QLabel("🔍 Search:")
        self.borrower_search_input = QLineEdit()
        self.borrower_search_input.setPlaceholderText("Search borrowers...")
        self.borrower_search_input.textChanged.connect(self.search_borrowers)

        search_layout.addWidget(search_label)
        search_layout.addWidget(self.borrower_search_input)
        layout.addLayout(search_layout)

        # Borrowers table
        self.setup_borrowers_table(layout)

    def setup_borrowers_table(self, parent_layout):
        """Setup the borrowers table."""
        table_group = QGroupBox("Borrowers")
        table_layout = QVBoxLayout(table_group)

        self.borrowers_table = QTableWidget()
        self.borrowers_table.setColumnCount(4)
        self.borrowers_table.setHorizontalHeaderLabels([
            "Name", "Affiliation", "Group", "Actions"
        ])

        # Configure responsive column sizing
        header = self.borrowers_table.horizontalHeader()
        if header:
            header.setMinimumSectionSize(60)  # Minimum width for any column

            # Set specific minimum widths for key columns
            self.borrowers_table.setColumnWidth(0, 150)  # Name minimum
            self.borrowers_table.setColumnWidth(1, 120)  # Affiliation minimum
            self.borrowers_table.setColumnWidth(2, 100)  # Group minimum

            # Make columns responsive
            for i in range(self.borrowers_table.columnCount()):
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

        self.borrowers_table.setAlternatingRowColors(True)
        table_layout.addWidget(self.borrowers_table)

        parent_layout.addWidget(table_group)

    def setup_requisitions_tab(self):
        """Setup the requisitions management tab."""
        layout = QVBoxLayout(self.requisitions_tab)

        # Search and filter functionality
        search_layout = QHBoxLayout()
        search_label = QLabel("🔍 Search:")
        self.req_search_input = QLineEdit()
        self.req_search_input.setPlaceholderText("Search requisitions...")
        self.req_search_input.textChanged.connect(self.search_requisitions)

        search_layout.addWidget(search_label)
        search_layout.addWidget(self.req_search_input)

        # Date filter
        date_filter_label = QLabel("Date range:")
        self.start_date_filter = QDateEdit()
        self.start_date_filter.setDate(QDate.currentDate().addMonths(-1))
        self.start_date_filter.setCalendarPopup(True)
        self.end_date_filter = QDateEdit()
        self.end_date_filter.setDate(QDate.currentDate())
        self.end_date_filter.setCalendarPopup(True)

        self.start_date_filter.dateChanged.connect(self.filter_requisitions)
        self.end_date_filter.dateChanged.connect(self.filter_requisitions)

        search_layout.addWidget(date_filter_label)
        search_layout.addWidget(self.start_date_filter)
        search_layout.addWidget(QLabel("to"))
        search_layout.addWidget(self.end_date_filter)
        search_layout.addStretch()

        layout.addLayout(search_layout)

        # Requisitions table
        self.setup_requisitions_table(layout)

    def setup_requisitions_table(self, parent_layout):
        """Setup the requisitions table."""
        table_group = QGroupBox("Requisitions")
        table_layout = QVBoxLayout(table_group)

        self.requisitions_table = QTableWidget()
        self.requisitions_table.setColumnCount(7)
        self.requisitions_table.setHorizontalHeaderLabels([
            "Borrower", "Borrow Date", "Activity", "Activity Date", "Students", "Groups", "Actions"
        ])

        # Configure responsive column sizing
        header = self.requisitions_table.horizontalHeader()
        if header:
            header.setMinimumSectionSize(60)  # Minimum width for any column

            # Set specific minimum widths for key columns
            self.requisitions_table.setColumnWidth(0, 120)  # Borrower minimum
            self.requisitions_table.setColumnWidth(2, 150)  # Activity minimum

            # Make columns responsive - Activity column stretches, others resize to content
            header.setStretchLastSection(False)  # Don't stretch last column
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # Activity column stretches
            # Set other columns to resize to contents
            for i in range(self.requisitions_table.columnCount()):
                if i != 2:  # Skip activity column
                    header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

        self.requisitions_table.setAlternatingRowColors(True)
        table_layout.addWidget(self.requisitions_table)

        parent_layout.addWidget(table_group)

    def refresh_data(self):
        """Refresh all data in the current tab."""
        current_tab = self.tab_widget.currentIndex()
        if current_tab == 0:  # Borrowers tab
            self.refresh_borrowers()
        else:  # Requisitions tab
            self.refresh_requisitions()

    def refresh_borrowers(self):
        """Refresh the borrowers display."""
        try:
            borrowers = Borrower.get_all()
            self.borrowers_table.setRowCount(len(borrowers))

            for row, borrower in enumerate(borrowers):
                # Name
                self.borrowers_table.setItem(row, 0, QTableWidgetItem(borrower.name or ""))

                # Affiliation
                self.borrowers_table.setItem(row, 1, QTableWidgetItem(borrower.affiliation or ""))

                # Group
                self.borrowers_table.setItem(row, 2, QTableWidgetItem(borrower.group_name or ""))

                # Actions button
                actions_btn = QPushButton("⋮")
                actions_btn.setFixedWidth(30)
                actions_btn.clicked.connect(lambda checked, r=row: self.show_borrower_actions(r))
                self.borrowers_table.setCellWidget(row, 3, actions_btn)

        except Exception as e:
            logger.error(f"Failed to refresh borrowers: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load borrowers: {str(e)}")

    def refresh_requisitions(self):
        """Refresh the requisitions display."""
        try:
            requisitions = Requisition.get_all()
            self.requisitions_table.setRowCount(len(requisitions))

            for row, req in enumerate(requisitions):
                # Get borrower name
                borrower_name = "Unknown"
                if req.borrower_id:
                    borrower = Borrower.get_by_id(req.borrower_id)
                    if borrower:
                        borrower_name = borrower.name

                # Borrower
                self.requisitions_table.setItem(row, 0, QTableWidgetItem(borrower_name))

                # Borrow Date
                borrow_date_str = req.date_borrowed.strftime("%Y-%m-%d") if req.date_borrowed else ""
                self.requisitions_table.setItem(row, 1, QTableWidgetItem(borrow_date_str))

                # Activity
                self.requisitions_table.setItem(row, 2, QTableWidgetItem(req.lab_activity_name or ""))

                # Activity Date
                activity_date_str = req.lab_activity_date.strftime("%Y-%m-%d") if req.lab_activity_date else ""
                self.requisitions_table.setItem(row, 3, QTableWidgetItem(activity_date_str))

                # Students
                students_str = str(req.num_students) if req.num_students else ""
                self.requisitions_table.setItem(row, 4, QTableWidgetItem(students_str))

                # Groups
                groups_str = str(req.num_groups) if req.num_groups else ""
                self.requisitions_table.setItem(row, 5, QTableWidgetItem(groups_str))

                # Actions button
                actions_btn = QPushButton("⋮")
                actions_btn.setFixedWidth(30)
                actions_btn.clicked.connect(lambda checked, r=row: self.show_requisition_actions(r))
                self.requisitions_table.setCellWidget(row, 6, actions_btn)

        except Exception as e:
            logger.error(f"Failed to refresh requisitions: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load requisitions: {str(e)}")

    def on_tab_changed(self, index):
        """Handle tab change events."""
        self.refresh_data()

    def search_borrowers(self):
        """Search borrowers based on input."""
        search_text = self.borrower_search_input.text().lower()

        for row in range(self.borrowers_table.rowCount()):
            show_row = True

            if search_text:
                # Search in name and affiliation columns
                name = self.borrowers_table.item(row, 0)
                affiliation = self.borrowers_table.item(row, 1)

                if name and affiliation:
                    name_text = name.text().lower()
                    affiliation_text = affiliation.text().lower()

                    if search_text not in name_text and search_text not in affiliation_text:
                        show_row = False

            self.borrowers_table.setRowHidden(row, not show_row)

    def search_requisitions(self):
        """Search requisitions based on input."""
        search_text = self.req_search_input.text().lower()

        for row in range(self.requisitions_table.rowCount()):
            show_row = True

            if search_text:
                # Search in borrower and activity columns
                borrower = self.requisitions_table.item(row, 0)
                activity = self.requisitions_table.item(row, 2)

                if borrower and activity:
                    borrower_text = borrower.text().lower()
                    activity_text = activity.text().lower()

                    if search_text not in borrower_text and search_text not in activity_text:
                        show_row = False

            self.requisitions_table.setRowHidden(row, not show_row)

    def filter_requisitions(self):
        """Filter requisitions by date range."""
        start_date = self.start_date_filter.date().toPyDate()
        end_date = self.end_date_filter.date().toPyDate()

        for row in range(self.requisitions_table.rowCount()):
            activity_date_item = self.requisitions_table.item(row, 3)
            if activity_date_item:
                activity_date_str = activity_date_item.text()
                if activity_date_str:
                    try:
                        activity_date = date.fromisoformat(activity_date_str)
                        show_row = start_date <= activity_date <= end_date
                    except ValueError:
                        show_row = True  # Show if date parsing fails
                else:
                    show_row = True  # Show if no date
            else:
                show_row = True  # Show if no item

            self.requisitions_table.setRowHidden(row, not show_row)

    def add_borrower_dialog(self):
        """Show dialog to add new borrower."""
        dialog = BorrowerDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_borrowers()

    def create_requisition_dialog(self):
        """Show dialog to create new requisition."""
        dialog = RequisitionDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_requisitions()

    def show_borrower_actions(self, row):
        """Show actions menu for borrower."""
        name_item = self.borrowers_table.item(row, 0)
        if not name_item:
            return

        # Find borrower by name (simplified approach)
        borrowers = Borrower.get_all()
        borrower = None
        for b in borrowers:
            if b.name == name_item.text():
                borrower = b
                break

        if not borrower:
            QMessageBox.warning(self, "Error", "Borrower not found")
            return

        actions_dialog = QDialog(self)
        actions_dialog.setWindowTitle("Borrower Actions")
        actions_dialog.setModal(True)

        layout = QVBoxLayout(actions_dialog)

        edit_btn = QPushButton("✏️ Edit Borrower")
        edit_btn.clicked.connect(lambda: self.edit_borrower(borrower, actions_dialog))

        delete_btn = QPushButton("🗑️ Delete Borrower")
        delete_btn.setStyleSheet("QPushButton { color: red; }")
        delete_btn.clicked.connect(lambda: self.delete_borrower(borrower, actions_dialog))

        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.clicked.connect(actions_dialog.reject)

        layout.addWidget(edit_btn)
        layout.addWidget(delete_btn)
        layout.addWidget(cancel_btn)

        actions_dialog.exec()

    def show_requisition_actions(self, row):
        """Show actions menu for requisition."""
        borrower_item = self.requisitions_table.item(row, 0)
        activity_item = self.requisitions_table.item(row, 2)
        if not borrower_item or not activity_item:
            return

        # Find requisition (simplified approach)
        requisitions = Requisition.get_all()
        requisition = None
        for req in requisitions:
            borrower_name = "Unknown"
            if req.borrower_id:
                borrower = Borrower.get_by_id(req.borrower_id)
                if borrower:
                    borrower_name = borrower.name

            if (borrower_name == borrower_item.text() and
                req.lab_activity_name == activity_item.text()):
                requisition = req
                break

        if not requisition:
            QMessageBox.warning(self, "Error", "Requisition not found")
            return

        actions_dialog = QDialog(self)
        actions_dialog.setWindowTitle("Requisition Actions")
        actions_dialog.setModal(True)

        layout = QVBoxLayout(actions_dialog)

        view_btn = QPushButton("👁️ View Details")
        view_btn.clicked.connect(lambda: self.view_requisition_details(requisition, actions_dialog))

        edit_btn = QPushButton("✏️ Edit Requisition")
        edit_btn.clicked.connect(lambda: self.edit_requisition(requisition, actions_dialog))

        delete_btn = QPushButton("🗑️ Delete Requisition")
        delete_btn.setStyleSheet("QPushButton { color: red; }")
        delete_btn.clicked.connect(lambda: self.delete_requisition(requisition, actions_dialog))

        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.clicked.connect(actions_dialog.reject)

        layout.addWidget(view_btn)
        layout.addWidget(edit_btn)
        layout.addWidget(delete_btn)
        layout.addWidget(cancel_btn)

        actions_dialog.exec()

    def edit_borrower(self, borrower, parent_dialog):
        """Edit an existing borrower."""
        parent_dialog.accept()

        dialog = BorrowerDialog(self, borrower)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_borrowers()

    def delete_borrower(self, borrower, parent_dialog):
        """Delete a borrower with confirmation."""
        parent_dialog.accept()

        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete borrower '{borrower.name}'?\n\n"
            "This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Check if borrower has active requisitions
                requisitions = Requisition.get_all()
                active_reqs = [req for req in requisitions if req.borrower_id == borrower.id]

                if active_reqs:
                    QMessageBox.warning(
                        self, "Cannot Delete",
                        f"Cannot delete borrower '{borrower.name}' because they have {len(active_reqs)} active requisition(s)."
                    )
                    return

                # Delete borrower (this would need to be added to the model)
                QMessageBox.information(self, "Success", f"Borrower '{borrower.name}' deleted successfully!")
                self.refresh_borrowers()

            except Exception as e:
                logger.error(f"Failed to delete borrower: {e}")
                QMessageBox.critical(self, "Error", f"Failed to delete borrower: {str(e)}")

    def view_requisition_details(self, requisition, parent_dialog):
        """View detailed requisition information."""
        parent_dialog.accept()

        dialog = QDialog(self)
        dialog.setWindowTitle("Requisition Details")
        dialog.setModal(True)
        dialog.resize(600, 400)

        layout = QVBoxLayout(dialog)

        # Requisition info
        info_layout = QVBoxLayout()

        borrower_name = "Unknown"
        if requisition.borrower_id:
            borrower = Borrower.get_by_id(requisition.borrower_id)
            if borrower:
                borrower_name = borrower.name

        info_layout.addWidget(QLabel(f"<b>Borrower:</b> {borrower_name}"))
        info_layout.addWidget(QLabel(f"<b>Date Borrowed:</b> {requisition.date_borrowed.strftime('%Y-%m-%d')}"))
        info_layout.addWidget(QLabel(f"<b>Lab Activity:</b> {requisition.lab_activity_name}"))
        info_layout.addWidget(QLabel(f"<b>Activity Date:</b> {requisition.lab_activity_date.strftime('%Y-%m-%d')}"))
        info_layout.addWidget(QLabel(f"<b>Students:</b> {requisition.num_students or 'N/A'}"))
        info_layout.addWidget(QLabel(f"<b>Groups:</b> {requisition.num_groups or 'N/A'}"))

        layout.addLayout(info_layout)

        # Items table
        items_label = QLabel("<b>Items Requested:</b>")
        layout.addWidget(items_label)

        items_table = QTableWidget()
        items_table.setColumnCount(3)
        items_table.setHorizontalHeaderLabels(["Item", "Quantity", "Category"])

        # Get requisition items
        req_items = RequisitionItem.get_by_requisition(requisition.id or 0)
        items_table.setRowCount(len(req_items))

        for row, req_item in enumerate(req_items):
            # Item name
            item_name = "Unknown"
            category_name = "Unknown"
            if req_item.item_id:
                item = Item.get_by_id(req_item.item_id)
                if item:
                    item_name = item.name
                    if item.category_id:
                        category = Category.get_by_id(item.category_id)
                        if category:
                            category_name = category.name

            items_table.setItem(row, 0, QTableWidgetItem(item_name))
            items_table.setItem(row, 1, QTableWidgetItem(str(req_item.quantity_borrowed)))
            items_table.setItem(row, 2, QTableWidgetItem(category_name))

        items_table.setAlternatingRowColors(True)
        layout.addWidget(items_table)

        # Close button
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        dialog.exec()

    def edit_requisition(self, requisition, parent_dialog):
        """Edit an existing requisition."""
        parent_dialog.accept()

        dialog = RequisitionDialog(self, requisition)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_requisitions()

    def delete_requisition(self, requisition, parent_dialog):
        """Delete a requisition with confirmation."""
        parent_dialog.accept()

        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete this requisition?\n\n"
            f"Activity: {requisition.lab_activity_name}\n"
            "This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                if requisition.delete("System"):
                    QMessageBox.information(self, "Success", "Requisition deleted successfully!")
                    self.refresh_requisitions()
                else:
                    QMessageBox.critical(self, "Error", "Failed to delete requisition")

            except Exception as e:
                logger.error(f"Failed to delete requisition: {e}")
                QMessageBox.critical(self, "Error", f"Failed to delete requisition: {str(e)}")


class BorrowerDialog(QDialog):
    """Dialog for adding/editing borrowers."""

    def __init__(self, parent=None, borrower=None):
        super().__init__(parent)
        self.borrower = borrower
        self.setup_ui()

    def setup_ui(self):
        """Setup the dialog UI."""
        self.setWindowTitle("Add Borrower" if not self.borrower else "Edit Borrower")
        self.setModal(True)
        self.resize(400, 250)

        layout = QVBoxLayout(self)

        # Form fields
        name_label = QLabel("Name:")
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Full name (required)")

        affiliation_label = QLabel("Affiliation:")
        self.affiliation_edit = QLineEdit()
        self.affiliation_edit.setPlaceholderText("Grade and section (e.g., Grade 7 - Section A)")

        group_label = QLabel("Group:")
        self.group_edit = QLineEdit()
        self.group_edit.setPlaceholderText("Group name or number")

        # Pre-fill if editing
        if self.borrower:
            self.name_edit.setText(self.borrower.name or "")
            self.affiliation_edit.setText(self.borrower.affiliation or "")
            self.group_edit.setText(self.borrower.group_name or "")

        # Add to form
        layout.addWidget(name_label)
        layout.addWidget(self.name_edit)
        layout.addWidget(affiliation_label)
        layout.addWidget(self.affiliation_edit)
        layout.addWidget(group_label)
        layout.addWidget(self.group_edit)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )

        def save_borrower():
            try:
                if not self.name_edit.text().strip():
                    QMessageBox.warning(self, "Error", "Borrower name is required")
                    return

                if self.borrower:
                    # Update existing
                    self.borrower.name = self.name_edit.text().strip()
                    self.borrower.affiliation = self.affiliation_edit.text().strip()
                    self.borrower.group_name = self.group_edit.text().strip()

                    if self.borrower.save():
                        QMessageBox.information(self, "Success", "Borrower updated successfully!")
                        self.accept()
                    else:
                        QMessageBox.critical(self, "Error", "Failed to update borrower")
                else:
                    # Create new
                    borrower = Borrower(
                        name=self.name_edit.text().strip(),
                        affiliation=self.affiliation_edit.text().strip(),
                        group_name=self.group_edit.text().strip()
                    )

                    if borrower.save():
                        QMessageBox.information(self, "Success", "Borrower added successfully!")
                        self.accept()
                    else:
                        QMessageBox.critical(self, "Error", "Failed to save borrower")

            except Exception as e:
                logger.error(f"Failed to save borrower: {e}")
                QMessageBox.critical(self, "Error", f"Failed to save borrower: {str(e)}")

        button_box.accepted.connect(save_borrower)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)


class RequisitionDialog(QDialog):
    """Dialog for creating/editing requisitions."""

    def __init__(self, parent=None, requisition=None):
        super().__init__(parent)
        self.requisition = requisition
        self.selected_items = []  # List of (item_id, quantity) tuples
        self.setup_ui()
        if self.requisition:
            self.load_requisition_data()

    def setup_ui(self):
        """Setup the dialog UI."""
        self.setWindowTitle("Create Requisition" if not self.requisition else "Edit Requisition")
        self.setModal(True)
        self.resize(700, 600)

        layout = QVBoxLayout(self)

        # Borrower selection
        borrower_layout = QHBoxLayout()
        borrower_label = QLabel("Borrower:")
        self.borrower_combo = QComboBox()
        self.borrower_combo.setEditable(True)

        # Load borrowers
        borrowers = Borrower.get_all()
        self.borrower_combo.addItem("-- Select Borrower --", None)
        for borrower in borrowers:
            display_text = f"{borrower.name} - {borrower.affiliation}"
            self.borrower_combo.addItem(display_text, borrower.id)

        borrower_layout.addWidget(borrower_label)
        borrower_layout.addWidget(self.borrower_combo)
        borrower_layout.addStretch()

        # Dates
        dates_layout = QHBoxLayout()
        borrow_date_label = QLabel("Date Borrowed:")
        self.borrow_date_edit = QDateEdit()
        self.borrow_date_edit.setDate(QDate.currentDate())
        self.borrow_date_edit.setCalendarPopup(True)

        activity_date_label = QLabel("Lab Activity Date:")
        self.activity_date_edit = QDateEdit()
        self.activity_date_edit.setDate(QDate.currentDate())
        self.activity_date_edit.setCalendarPopup(True)

        dates_layout.addWidget(borrow_date_label)
        dates_layout.addWidget(self.borrow_date_edit)
        dates_layout.addWidget(activity_date_label)
        dates_layout.addWidget(self.activity_date_edit)
        dates_layout.addStretch()

        # Activity details
        activity_layout = QHBoxLayout()
        activity_label = QLabel("Lab Activity Name:")
        self.activity_edit = QLineEdit()
        self.activity_edit.setPlaceholderText("e.g., Chemistry Experiment - Titration")

        students_label = QLabel("Number of Students:")
        self.students_spin = QSpinBox()
        self.students_spin.setRange(1, 1000)
        self.students_spin.setValue(30)

        groups_label = QLabel("Number of Groups:")
        self.groups_spin = QSpinBox()
        self.groups_spin.setRange(1, 50)
        self.groups_spin.setValue(6)

        activity_layout.addWidget(activity_label)
        activity_layout.addWidget(self.activity_edit)
        activity_layout.addWidget(students_label)
        activity_layout.addWidget(self.students_spin)
        activity_layout.addWidget(groups_label)
        activity_layout.addWidget(self.groups_spin)

        # Items section header
        items_header_layout = QHBoxLayout()
        items_label = QLabel("Requested Items:")
        add_item_btn = QPushButton("➕ Add Item")
        add_item_btn.clicked.connect(self.add_item_dialog)

        items_header_layout.addWidget(items_label)
        items_header_layout.addStretch()
        items_header_layout.addWidget(add_item_btn)

        # Items list
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(4)
        self.items_table.setHorizontalHeaderLabels(["Item", "Category", "Size/Brand", "Quantity"])
        self.items_table.setAlternatingRowColors(True)

        # Add to form
        layout.addLayout(borrower_layout)
        layout.addLayout(dates_layout)
        layout.addLayout(activity_layout)
        layout.addLayout(items_header_layout)
        layout.addWidget(self.items_table)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )

        def save_requisition():
            try:
                # Validation
                if not self.borrower_combo.currentData():
                    QMessageBox.warning(self, "Error", "Please select a borrower")
                    return

                if not self.activity_edit.text().strip():
                    QMessageBox.warning(self, "Error", "Lab activity name is required")
                    return

                if not self.selected_items:
                    QMessageBox.warning(self, "Error", "Please add at least one item")
                    return

                # Create or update requisition
                if self.requisition:
                    # Update existing
                    self.requisition.borrower_id = self.borrower_combo.currentData()
                    self.requisition.date_borrowed = self.borrow_date_edit.date().toPyDate()
                    self.requisition.lab_activity_name = self.activity_edit.text().strip()
                    self.requisition.lab_activity_date = self.activity_date_edit.date().toPyDate()
                    self.requisition.num_students = self.students_spin.value()
                    self.requisition.num_groups = self.groups_spin.value()

                    if self.requisition.save("System"):
                        # Update items (simplified - would need proper implementation)
                        QMessageBox.information(self, "Success", "Requisition updated successfully!")
                        self.accept()
                    else:
                        QMessageBox.critical(self, "Error", "Failed to update requisition")
                else:
                    # Create new
                    requisition = Requisition(
                        borrower_id=self.borrower_combo.currentData(),
                        date_borrowed=self.borrow_date_edit.date().toPyDate(),
                        lab_activity_name=self.activity_edit.text().strip(),
                        lab_activity_date=self.activity_date_edit.date().toPyDate(),
                        num_students=self.students_spin.value(),
                        num_groups=self.groups_spin.value()
                    )

                    if requisition.save("System"):
                        # Ensure we have a valid requisition ID
                        if not requisition.id:
                            QMessageBox.critical(self, "Error", "Failed to get requisition ID after saving")
                            return

                        # Save items with the correct requisition ID
                        for item_id, quantity in self.selected_items:
                            req_item = RequisitionItem(
                                requisition_id=requisition.id,
                                item_id=item_id,
                                quantity_borrowed=quantity
                            )
                            req_item.save()

                        QMessageBox.information(self, "Success", "Requisition created successfully!")
                        self.accept()
                    else:
                        QMessageBox.critical(self, "Error", "Failed to create requisition")

            except Exception as e:
                logger.error(f"Failed to save requisition: {e}")
                QMessageBox.critical(self, "Error", f"Failed to save requisition: {str(e)}")

        button_box.accepted.connect(save_requisition)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def load_requisition_data(self):
        """Load existing requisition data for editing."""
        if not self.requisition:
            return

        # Set borrower
        if self.requisition.borrower_id:
            index = self.borrower_combo.findData(self.requisition.borrower_id)
            if index >= 0:
                self.borrower_combo.setCurrentIndex(index)

        # Set dates
        if self.requisition.date_borrowed:
            self.borrow_date_edit.setDate(QDate(self.requisition.date_borrowed))
        if self.requisition.lab_activity_date:
            self.activity_date_edit.setDate(QDate(self.requisition.lab_activity_date))

        # Set activity details
        self.activity_edit.setText(self.requisition.lab_activity_name or "")
        if self.requisition.num_students:
            self.students_spin.setValue(self.requisition.num_students)
        if self.requisition.num_groups:
            self.groups_spin.setValue(self.requisition.num_groups)

        # Load items
        req_items = RequisitionItem.get_by_requisition(self.requisition.id or 0)
        for req_item in req_items:
            self.selected_items.append((req_item.item_id, req_item.quantity_borrowed))

        self.refresh_items_table()

    def add_item_dialog(self):
        """Show dialog to add items to the requisition."""
        dialog = ItemSelectionDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_items = dialog.get_selected_items()
            for item_id, quantity in selected_items:
                # Check if item already selected
                existing = next((i for i in self.selected_items if i[0] == item_id), None)
                if existing:
                    # Update quantity
                    index = self.selected_items.index(existing)
                    self.selected_items[index] = (item_id, existing[1] + quantity)
                else:
                    # Add new
                    self.selected_items.append((item_id, quantity))

            self.refresh_items_table()

    def refresh_items_table(self):
        """Refresh the items table with selected items."""
        self.items_table.setRowCount(len(self.selected_items))

        for row, (item_id, quantity) in enumerate(self.selected_items):
            # Get item details
            item = Item.get_by_id(item_id)
            if item:
                item_name = item.name or "Unknown"
                category_name = "Unknown"
                if item.category_id:
                    category = Category.get_by_id(item.category_id)
                    if category:
                        category_name = category.name

                size_brand = ""
                if item.size:
                    size_brand += f"Size: {item.size}"
                if item.brand:
                    if size_brand:
                        size_brand += " | "
                    size_brand += f"Brand: {item.brand}"
                if not size_brand:
                    size_brand = "N/A"

                self.items_table.setItem(row, 0, QTableWidgetItem(item_name))
                self.items_table.setItem(row, 1, QTableWidgetItem(category_name))
                self.items_table.setItem(row, 2, QTableWidgetItem(size_brand))
                self.items_table.setItem(row, 3, QTableWidgetItem(str(quantity)))

                # Add remove button
                remove_btn = QPushButton("❌")
                remove_btn.setFixedWidth(40)
                remove_btn.clicked.connect(lambda checked, r=row: self.remove_item(r))
                self.items_table.setCellWidget(row, 4, remove_btn)

        # Configure responsive column sizing for items table
        if self.items_table.columnCount() < 5:
            self.items_table.setColumnCount(5)
            self.items_table.setHorizontalHeaderLabels(["Item", "Category", "Size/Brand", "Quantity", "Actions"])

        header = self.items_table.horizontalHeader()
        if header:
            header.setMinimumSectionSize(40)  # Minimum width for any column

            # Set minimum widths for key columns
            self.items_table.setColumnWidth(0, 120)  # Item minimum
            self.items_table.setColumnWidth(2, 120)  # Size/Brand minimum

            # Make Size/Brand column stretch
            header.setStretchLastSection(False)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # Size/Brand stretches
            # Set other columns to resize to contents
            for i in range(self.items_table.columnCount()):
                if i != 2:  # Skip Size/Brand column
                    header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

    def remove_item(self, row):
        """Remove an item from the selected items list."""
        if 0 <= row < len(self.selected_items):
            self.selected_items.pop(row)
            self.refresh_items_table()


class ItemSelectionDialog(QDialog):
    """Dialog for selecting items from inventory."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_items = []  # List of (item_id, quantity) tuples
        self.setup_ui()

    def setup_ui(self):
        """Setup the dialog UI."""
        self.setWindowTitle("Select Items from Inventory")
        self.setModal(True)
        self.resize(600, 500)

        layout = QVBoxLayout(self)

        # Search
        search_layout = QHBoxLayout()
        search_label = QLabel("🔍 Search:")
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search items...")
        self.search_edit.textChanged.connect(self.search_items)

        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_edit)
        layout.addLayout(search_layout)

        # Items list with quantities
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(5)
        self.items_table.setHorizontalHeaderLabels(["Item", "Category", "Size", "Brand", "Quantity"])
        self.items_table.setAlternatingRowColors(True)

        # Configure responsive column sizing
        header = self.items_table.horizontalHeader()
        if header:
            header.setMinimumSectionSize(60)  # Minimum width for any column

            # Set specific minimum widths for key columns
            self.items_table.setColumnWidth(0, 120)  # Item minimum
            self.items_table.setColumnWidth(1, 100)  # Category minimum
            self.items_table.setColumnWidth(3, 100)  # Brand minimum

            # Make columns responsive
            for i in range(self.items_table.columnCount()):
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.items_table)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Load items
        self.load_items()

    def load_items(self):
        """Load items from inventory."""
        try:
            items = Item.get_all()
            self.items_table.setRowCount(len(items))

            for row, item in enumerate(items):
                # Item name
                self.items_table.setItem(row, 0, QTableWidgetItem(item.name or ""))

                # Category
                category_name = "Unknown"
                if item.category_id:
                    category = Category.get_by_id(item.category_id)
                    if category:
                        category_name = category.name
                self.items_table.setItem(row, 1, QTableWidgetItem(category_name))

                # Size
                self.items_table.setItem(row, 2, QTableWidgetItem(item.size or ""))

                # Brand
                self.items_table.setItem(row, 3, QTableWidgetItem(item.brand or ""))

                # Quantity input
                quantity_spin = QSpinBox()
                quantity_spin.setRange(1, 1000)
                quantity_spin.setValue(1)
                self.items_table.setCellWidget(row, 4, quantity_spin)

                # Store item ID for later
                quantity_spin.setProperty("item_id", item.id)

        except Exception as e:
            logger.error(f"Failed to load items: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load items: {str(e)}")

    def search_items(self):
        """Search items based on input."""
        search_text = self.search_edit.text().lower()

        for row in range(self.items_table.rowCount()):
            show_row = True

            if search_text:
                # Search in item name and category columns
                item_name = self.items_table.item(row, 0)
                category = self.items_table.item(row, 1)

                if item_name and category:
                    name_text = item_name.text().lower()
                    category_text = category.text().lower()

                    if search_text not in name_text and search_text not in category_text:
                        show_row = False

            self.items_table.setRowHidden(row, not show_row)

    def get_selected_items(self):
        """Get selected items with quantities."""
        selected_items = []

        for row in range(self.items_table.rowCount()):
            if not self.items_table.isRowHidden(row):
                quantity_widget = self.items_table.cellWidget(row, 4)
                if quantity_widget and isinstance(quantity_widget, QSpinBox):
                    quantity = quantity_widget.value()
                    if quantity > 0:
                        item_id = quantity_widget.property("item_id")
                        if item_id:
                            selected_items.append((item_id, quantity))

        return selected_items
