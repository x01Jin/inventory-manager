"""
Borrower selector dialog for selecting borrowers in requisition workflow.
Provides searchable interface for selecting existing borrowers.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QTableWidget, QTableWidgetItem,
    QGroupBox, QMessageBox, QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt

from inventory_app.gui.borrowers.borrower_model import BorrowerModel, BorrowerRow
from inventory_app.utils.logger import logger


class BorrowerSelector(QDialog):
    """Dialog for selecting borrowers for requisitions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = BorrowerModel()
        self.selected_borrower_id: Optional[int] = None

        self.setWindowTitle("Select Borrower for Requisition")
        self.setup_ui()
        self.load_borrowers()

    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header
        header = QLabel("👥 Select Borrower for Requisition")
        header.setStyleSheet("font-size: 14pt; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header)

        # Search section
        search_group = QGroupBox("Search Borrowers")
        search_layout = QHBoxLayout(search_group)

        search_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name, affiliation, or group...")
        self.search_input.textChanged.connect(self.filter_borrowers)
        search_layout.addWidget(self.search_input)

        layout.addWidget(search_group)

        # Borrowers table
        table_group = QGroupBox("Available Borrowers")
        table_layout = QVBoxLayout(table_group)

        self.borrowers_table = QTableWidget()
        self.borrowers_table.setColumnCount(3)
        self.borrowers_table.setHorizontalHeaderLabels([
            "Name", "Affiliation", "Group"
        ])

        # Configure table
        header = self.borrowers_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.borrowers_table.setAlternatingRowColors(True)
        self.borrowers_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.borrowers_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.borrowers_table.itemSelectionChanged.connect(self.on_row_selected)

        # Set column widths
        self.borrowers_table.setColumnWidth(0, 200)  # Name
        self.borrowers_table.setColumnWidth(1, 150)  # Affiliation
        self.borrowers_table.setColumnWidth(2, 150)  # Group

        table_layout.addWidget(self.borrowers_table)
        layout.addWidget(table_group)

        # Selected borrower info
        self.selection_info = QLabel("No borrower selected")
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

    def load_borrowers(self):
        """Load all borrowers."""
        try:
            success = self.model.load_data()
            if success:
                self.filter_borrowers()  # This will populate the table
                logger.info("Loaded borrowers for selection")
            else:
                QMessageBox.warning(self, "Load Error", "Failed to load borrowers from database.")
        except Exception as e:
            logger.error(f"Failed to load borrowers: {e}")
            QMessageBox.critical(self, "Error", "Failed to load borrowers.")

    def filter_borrowers(self):
        """Filter borrowers based on search term."""
        try:
            filtered_borrowers = self.model.get_filtered_rows()
            self.populate_table(filtered_borrowers)
        except Exception as e:
            logger.error(f"Failed to filter borrowers: {e}")

    def populate_table(self, borrowers: list[BorrowerRow]):
        """Populate the borrowers table."""
        try:
            self.borrowers_table.setRowCount(0)

            for borrower in borrowers:
                row_position = self.borrowers_table.rowCount()
                self.borrowers_table.insertRow(row_position)

                # Name
                name_item = QTableWidgetItem(borrower.name)
                name_item.setData(Qt.ItemDataRole.UserRole, borrower.id)
                self.borrowers_table.setItem(row_position, 0, name_item)

                # Affiliation
                self.borrowers_table.setItem(row_position, 1, QTableWidgetItem(borrower.affiliation))

                # Group
                self.borrowers_table.setItem(row_position, 2, QTableWidgetItem(borrower.group_name))

            logger.debug(f"Populated table with {len(borrowers)} borrowers")

        except Exception as e:
            logger.error(f"Failed to populate table: {e}")

    def on_borrower_selected(self, borrower_id: int):
        """Handle borrower selection."""
        try:
            # Get borrower details
            borrower = self.model.get_borrower_by_id(borrower_id)
            if borrower:
                self.selected_borrower_id = borrower_id
                self.selection_info.setText(
                    f"Selected: {borrower.name} ({borrower.affiliation})"
                )
                self.select_button.setEnabled(True)

                # Highlight selected row
                for row in range(self.borrowers_table.rowCount()):
                    item = self.borrowers_table.item(row, 0)
                    if item and item.data(Qt.ItemDataRole.UserRole) == borrower_id:
                        self.borrowers_table.selectRow(row)
                        break

                logger.info(f"Selected borrower: {borrower.name} (ID: {borrower_id})")

        except Exception as e:
            logger.error(f"Failed to select borrower {borrower_id}: {e}")

    def on_row_selected(self):
        """Handle table row selection."""
        try:
            selected_items = self.borrowers_table.selectedItems()
            if selected_items:
                # Get the borrower ID from the first column of the selected row
                name_item = selected_items[0]
                borrower_id = name_item.data(Qt.ItemDataRole.UserRole)
                if borrower_id is not None:
                    self.on_borrower_selected(borrower_id)
        except Exception as e:
            logger.error(f"Failed to handle row selection: {e}")

    def confirm_selection(self):
        """Confirm borrower selection and close dialog."""
        if self.selected_borrower_id is not None:
            self.accept()
        else:
            QMessageBox.warning(self, "No Selection", "Please select a borrower first.")

    def get_selected_borrower_id(self) -> Optional[int]:
        """Get the selected borrower ID."""
        return self.selected_borrower_id

    @staticmethod
    def select_borrower(parent=None) -> Optional[int]:
        """
        Static method to show borrower selection dialog.
        Returns the selected borrower ID or None if cancelled.
        """
        dialog = BorrowerSelector(parent)
        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            return dialog.get_selected_borrower_id()

        return None
