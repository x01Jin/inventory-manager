"""
Requester selector dialog for selecting requesters in requisition workflow.
Provides searchable interface for selecting existing requesters.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QTableWidget, QTableWidgetItem,
    QGroupBox, QMessageBox, QHeaderView, QAbstractItemView, QCheckBox
)
from PyQt6.QtCore import Qt

from inventory_app.gui.requesters.requester_model import RequesterModel, RequesterRow
from inventory_app.utils.logger import logger


class RequesterSelector(QDialog):
    """Dialog for selecting requesters for requisitions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = RequesterModel()
        self.selected_requester_id: Optional[int] = None

        self.setWindowTitle("Select Requester for Requisition")
        self.setup_ui()
        self.load_requesters()

    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header
        header = QLabel("👥 Select Requester for Requisition")
        header.setStyleSheet("font-size: 14pt; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header)

        # Search section
        search_group = QGroupBox("Search Requesters")
        search_layout = QHBoxLayout(search_group)

        search_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name, affiliation, or group...")
        self.search_input.textChanged.connect(self.filter_requesters)
        search_layout.addWidget(self.search_input)

        layout.addWidget(search_group)

        # Filter section
        filter_layout = QHBoxLayout()
        self.hide_zero_requisitions = QCheckBox("Hide requesters with no requisitions")
        self.hide_zero_requisitions.stateChanged.connect(self.filter_requesters)
        filter_layout.addWidget(self.hide_zero_requisitions)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Requesters table
        table_group = QGroupBox("Available Requesters")
        table_layout = QVBoxLayout(table_group)

        self.requesters_table = QTableWidget()
        self.requesters_table.setColumnCount(4)
        self.requesters_table.setHorizontalHeaderLabels([
            "Requisitions", "Name", "Affiliation", "Group"
        ])

        # Configure table
        header = self.requesters_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.requesters_table.setAlternatingRowColors(True)
        self.requesters_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.requesters_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.requesters_table.itemSelectionChanged.connect(self.on_row_selected)

        # Set column widths
        self.requesters_table.setColumnWidth(0, 100)  # Requisitions
        self.requesters_table.setColumnWidth(1, 200)  # Name
        self.requesters_table.setColumnWidth(2, 250)  # Affiliation
        self.requesters_table.setColumnWidth(3, 250)  # Group

        table_layout.addWidget(self.requesters_table)
        layout.addWidget(table_group)

        # Selected requester info
        self.selection_info = QLabel("No requester selected")
        self.selection_info.setStyleSheet("font-weight: bold; padding: 10px; background-color: #2a2a3c; border: 1px solid #3f3f46; border-radius: 5px;")
        layout.addWidget(self.selection_info)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.select_button = QPushButton("Select")
        self.select_button.clicked.connect(self.confirm_selection)
        self.select_button.setEnabled(False)
        button_layout.addWidget(self.select_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

        # Set dialog properties
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)
        self.setModal(True)

    def load_requesters(self):
        """Load all requesters."""
        try:
            success = self.model.load_data()
            if success:
                self.filter_requesters()  # This will populate the table
                logger.info("Loaded requesters for selection")
            else:
                QMessageBox.warning(self, "Load Error", "Failed to load requesters from database.")
        except Exception as e:
            logger.error(f"Failed to load requesters: {e}")
            QMessageBox.critical(self, "Error", "Failed to load requesters.")

    def filter_requesters(self):
        """Filter requesters based on search term."""
        try:
            filtered_requesters = self.model.get_filtered_rows()
            self.populate_table(filtered_requesters)
        except Exception as e:
            logger.error(f"Failed to filter requesters: {e}")

    def populate_table(self, requesters: list[RequesterRow]):
        """Populate the requesters table."""
        try:
            self.requesters_table.setRowCount(0)

            # Apply filter for zero requisitions if checkbox is checked
            if self.hide_zero_requisitions.isChecked():
                requesters = [b for b in requesters if b.requisitions_count > 0]

            for requester in requesters:
                row_position = self.requesters_table.rowCount()
                self.requesters_table.insertRow(row_position)

                # Requisitions count
                requisitions_item = QTableWidgetItem(str(requester.requisitions_count))
                self.requesters_table.setItem(row_position, 0, requisitions_item)

                # Name
                name_item = QTableWidgetItem(requester.name)
                name_item.setData(Qt.ItemDataRole.UserRole, requester.id)
                self.requesters_table.setItem(row_position, 1, name_item)

                # Affiliation
                self.requesters_table.setItem(row_position, 2, QTableWidgetItem(requester.affiliation))

                # Group
                self.requesters_table.setItem(row_position, 3, QTableWidgetItem(requester.group_name))

            logger.debug(f"Populated table with {len(requesters)} requesters")

        except Exception as e:
            logger.error(f"Failed to populate table: {e}")

    def on_requester_selected(self, requester_id: int):
        """Handle requester selection."""
        try:
            # Get requester details
            requester = self.model.get_requester_by_id(requester_id)
            if requester:
                self.selected_requester_id = requester_id
                self.selection_info.setText(
                    f"Selected: {requester.name} ({requester.affiliation})"
                )
                self.select_button.setEnabled(True)

                # Highlight selected row
                for row in range(self.requesters_table.rowCount()):
                    item = self.requesters_table.item(row, 1)  # Name is in column 1
                    if item and item.data(Qt.ItemDataRole.UserRole) == requester_id:
                        self.requesters_table.selectRow(row)
                        break

                logger.info(f"Selected requester: {requester.name} (ID: {requester_id})")

        except Exception as e:
            logger.error(f"Failed to select requester {requester_id}: {e}")

    def on_row_selected(self):
        """Handle table row selection."""
        try:
            current_row = self.requesters_table.currentRow()
            if current_row >= 0:
                name_item = self.requesters_table.item(current_row, 1)  # Column 1 = Name
                if name_item is not None:
                    requester_id = name_item.data(Qt.ItemDataRole.UserRole)
                    if requester_id is not None:
                        self.on_requester_selected(requester_id)
        except Exception as e:
            logger.error(f"Failed to handle row selection: {e}")

    def confirm_selection(self):
        """Confirm requester selection and close dialog."""
        if self.selected_requester_id is not None:
            self.accept()
        else:
            QMessageBox.warning(self, "No Selection", "Please select a requester first.")

    def get_selected_requester_id(self) -> Optional[int]:
        """Get the selected requester ID."""
        return self.selected_requester_id

    @staticmethod
    def select_requester(parent=None) -> Optional[int]:
        """
        Static method to show requester selection dialog.
        Returns the selected requester ID or None if cancelled.
        """
        dialog = RequesterSelector(parent)
        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            return dialog.get_selected_requester_id()

        return None
