"""
Requisitions management page - Complete laboratory borrowing system.
Provides full CRUD operations for requisitions with borrower management.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QMessageBox, QInputDialog
)
from PyQt6.QtCore import pyqtSignal

from inventory_app.gui.requisitions.requisitions_model import RequisitionsModel
from inventory_app.gui.requisitions.requisitions_table import RequisitionsTable
from inventory_app.gui.requisitions.requisitions_filters import RequisitionsFilters
from inventory_app.gui.requisitions.new_requisition import NewRequisitionDialog
from inventory_app.utils.logger import logger


class RequisitionsPage(QWidget):
    """
    Main requisitions management page.
    Provides complete laboratory borrowing workflow management.
    """

    # Signals for integration with main application
    requisition_selected = pyqtSignal(int)  # Requisition ID selected
    data_changed = pyqtSignal()             # Data was modified

    def __init__(self, parent=None):
        """Initialize the requisitions page."""
        super().__init__(parent)

        # Initialize components using composition
        self.model = RequisitionsModel()
        self.filters = RequisitionsFilters()
        self.table = RequisitionsTable()

        # Setup connections between components
        self._setup_connections()

        # Setup UI
        self.setup_ui()

        # Load initial data
        self.refresh_data()

        logger.info("Requisitions page initialized with all components")

    def setup_ui(self):
        """Setup the main user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header with title and refresh button
        header_layout = QHBoxLayout()
        title = QLabel("📋 Laboratory Requisitions")
        title.setStyleSheet("font-size: 16pt; font-weight: bold;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        self.refresh_button = QPushButton("🔄 Refresh")
        self.refresh_button.clicked.connect(self.refresh_data)
        header_layout.addWidget(self.refresh_button)

        layout.addLayout(header_layout)

        # Action buttons row
        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)

        self.add_button = QPushButton("➕ New Requisition")
        self.add_button.clicked.connect(self.new_requisition)

        self.edit_button = QPushButton("✏️ Edit Requisition")
        self.edit_button.clicked.connect(self.edit_requisition)
        self.edit_button.setEnabled(False)

        self.return_button = QPushButton("↩️ Return Items")
        self.return_button.clicked.connect(self.return_items)
        self.return_button.setEnabled(False)

        self.delete_button = QPushButton("🗑️ Delete Requisition")
        self.delete_button.clicked.connect(self.delete_requisition)
        self.delete_button.setEnabled(False)

        action_layout.addWidget(self.add_button)
        action_layout.addWidget(self.edit_button)
        action_layout.addWidget(self.return_button)
        action_layout.addWidget(self.delete_button)
        action_layout.addStretch()

        layout.addLayout(action_layout)

        # Filters section
        self.filters.set_model(self.model)
        layout.addWidget(self.filters)

        # Main content area with requisitions table
        table_group = QGroupBox("Laboratory Requisitions")
        table_layout = QVBoxLayout(table_group)
        table_layout.addWidget(self.table)
        layout.addWidget(table_group)

        # Status bar
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #666; font-size: 10pt;")
        layout.addWidget(self.status_label)

    def _setup_connections(self):
        """Setup signal connections between components."""
        # Filter signals - connect to both model and refresh
        self.filters.search_changed.connect(self._on_filter_changed)
        self.filters.borrower_filter_changed.connect(self._on_filter_changed)
        self.filters.activity_filter_changed.connect(self._on_filter_changed)
        self.filters.status_filter_changed.connect(self._on_filter_changed)
        self.filters.date_range_changed.connect(self._on_filter_changed)
        self.filters.clear_filters_requested.connect(self._on_filters_cleared)

    def refresh_data(self):
        """Refresh all requisition data."""
        try:
            logger.info("Refreshing requisition data...")

            # Load data from model
            success = self.model.load_data()
            if not success:
                QMessageBox.warning(self, "Data Load Error",
                                  "Failed to load requisition data from database.")
                return

            # Reload borrower options (in case new borrowers have requisitions)
            self.filters._load_borrower_options()

            # Get filtered rows for display
            rows = self.model.get_filtered_rows()

            # Update table
            self.table.populate_table(rows)

            # Update filter summary
            total_count = len(self.model.all_requisitions)
            filtered_count = len(rows)
            self.filters.update_summary(total_count, filtered_count)

            # Update status
            stats = self.model.get_statistics()
            self.status_label.setText(
                f"Total: {stats['total_requisitions']} | "
                f"Active: {stats['active_requisitions']} | "
                f"Returned: {stats['returned_requisitions']} | "
                f"Overdue: {stats['overdue_requisitions']}"
            )

            logger.info(f"Refreshed requisition data: {len(rows)} requisitions displayed")

        except Exception as e:
            logger.error(f"Failed to refresh requisition data: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load requisition data: {str(e)}")

    def new_requisition(self):
        """Open dialog to create a new requisition."""
        try:
            # Create the new requisition dialog
            dialog = NewRequisitionDialog(parent=self)

            # Connect signal to refresh data when requisition is created
            dialog.requisition_created.connect(self._on_requisition_created)

            # Show the dialog
            dialog.exec()

        except Exception as e:
            logger.error(f"Failed to open new requisition dialog: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open new requisition dialog: {str(e)}")

    def _on_requisition_created(self, requisition_id: int):
        """Handle successful requisition creation."""
        try:
            logger.info(f"New requisition created with ID: {requisition_id}")

            # Refresh the data to show the new requisition
            self.refresh_data()

            # Emit data changed signal for other parts of the application
            self.data_changed.emit()

            # Show success message
            QMessageBox.information(
                self, "Success",
                f"New requisition created successfully!\nRequisition ID: {requisition_id}"
            )

        except Exception as e:
            logger.error(f"Failed to handle requisition creation: {e}")
            QMessageBox.critical(self, "Error", f"Failed to refresh data after creating requisition: {str(e)}")

    def edit_requisition(self):
        """Open dialog to edit the currently selected requisition."""
        pass

    def return_items(self):
        """Open dialog to process item returns for the selected requisition."""
        pass

    def delete_requisition(self):
        """Delete the currently selected requisition."""
        requisition_id = self.table.get_selected_requisition_id()
        if not requisition_id:
            QMessageBox.warning(self, "No Selection", "Please select a requisition to delete.")
            return

        # Confirm deletion
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            "Are you sure you want to delete this requisition?\n\n"
            "This action cannot be undone and will remove all associated borrowing records.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            # Ask for editor name (Spec #14)
            editor_name, ok = QInputDialog.getText(self, "Editor Information",
                                                  "Enter your name/initials (required):")
            if not ok or not editor_name.strip():
                QMessageBox.warning(self, "Required", "Editor name is required.")
                return

            # Delete the requisition
            if self.model.delete_requisition(requisition_id, editor_name.strip()):
                logger.info(f"Requisition {requisition_id} deleted by {editor_name}")
                QMessageBox.information(self, "Success", "Requisition deleted successfully!")
                self.refresh_data()
                self.data_changed.emit()
            else:
                QMessageBox.critical(self, "Error", "Failed to delete requisition.")

        except Exception as e:
            logger.error(f"Failed to delete requisition {requisition_id}: {e}")
            QMessageBox.critical(self, "Error", f"Failed to delete requisition: {str(e)}")

    def _on_filter_changed(self):
        """Handle any filter change - apply filters and refresh table."""
        try:
            # Apply all current filters from the filter widget
            current_filters = self.filters.get_current_filters()

            # Apply filters to model
            if 'search_term' in current_filters:
                self.model.filter_by_search(current_filters['search_term'])
            if 'borrower_filter' in current_filters:
                self.model.filter_by_borrower(current_filters['borrower_filter'])
            if 'activity_filter' in current_filters:
                self.model.filter_by_activity(current_filters['activity_filter'])
            if 'status_filter' in current_filters:
                self.model.filter_by_status(current_filters['status_filter'])
            if 'date_from' in current_filters or 'date_to' in current_filters:
                self.model.filter_by_date_range(
                    current_filters.get('date_from'),
                    current_filters.get('date_to')
                )

            # Refresh table with filtered data
            rows = self.model.get_filtered_rows()
            self.table.populate_table(rows)

            # Update filter summary
            total_count = len(self.model.all_requisitions)
            filtered_count = len(rows)
            self.filters.update_summary(total_count, filtered_count)

            logger.debug(f"Applied filters: {filtered_count} of {total_count} requisitions shown")

        except Exception as e:
            logger.error(f"Failed to apply filters: {e}")

    def _on_filters_cleared(self):
        """Handle filters cleared event."""
        logger.debug("Filters cleared, refreshing data")
        self.refresh_data()
