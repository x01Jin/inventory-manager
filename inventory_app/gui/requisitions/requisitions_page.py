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
from inventory_app.gui.borrowers.borrower_selector import BorrowerSelector
from inventory_app.gui.requisitions.item_selector import ItemSelector
from inventory_app.gui.requisitions.item_return import ItemReturnDialog
from inventory_app.gui.requisitions.requisition_details_dialog import RequisitionDetailsDialog
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
        self.add_button.clicked.connect(self.add_requisition)

        self.edit_button = QPushButton("✏️ Edit Requisition")
        self.edit_button.clicked.connect(self.edit_selected_requisition)
        self.edit_button.setEnabled(False)

        self.return_button = QPushButton("↩️ Return Items")
        self.return_button.clicked.connect(self.return_selected_items)
        self.return_button.setEnabled(False)

        self.delete_button = QPushButton("🗑️ Delete Requisition")
        self.delete_button.clicked.connect(self.delete_selected_requisition)
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
        # Table signals
        self.table.requisition_selected.connect(self._on_requisition_selected)
        self.table.requisition_double_clicked.connect(self._on_requisition_double_clicked)

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

    def add_requisition(self):
        """Add a new requisition."""
        try:
            # Step 1: Check if borrowers exist
            borrowers = self.model.controller.get_borrowers()
            if not borrowers:
                QMessageBox.information(self, "No Borrowers Available",
                                      "There are no registered borrowers in the system.\n\n"
                                      "Please go to the Borrowers page to add borrowers first, "
                                      "then return here to create requisitions.")
                logger.info("Cannot create requisition: no borrowers available")
                return

            # Step 2: Select borrower
            borrower_id = BorrowerSelector.select_borrower(self)
            if borrower_id is None:
                logger.debug("Borrower selection cancelled")
                return

            logger.info(f"Borrower {borrower_id} selected successfully")

            # Step 3: Select items for the requisition
            item_dialog = ItemSelector(self)
            item_result = item_dialog.exec()

            if item_result != ItemSelector.DialogCode.Accepted:
                logger.debug("Item selection cancelled")
                return

            selected_items = item_dialog.get_selected_items()
            if not selected_items:
                QMessageBox.warning(self, "No Items", "Please select at least one item for the requisition.")
                return

            logger.info(f"Selected {len(selected_items)} items for requisition")

            # Step 4: Gather additional requisition details using dialog
            accepted, activity_data = RequisitionDetailsDialog.get_details(self)
            if not accepted or activity_data is None:
                logger.debug("Activity details cancelled")
                return

            from datetime import date
            requisition_data = {
                'borrower_id': borrower_id,
                'date_borrowed': date.today(),
                'lab_activity_name': activity_data['lab_activity_name'],
                'lab_activity_date': activity_data['lab_activity_date'],
                'num_students': activity_data['num_students'],
                'num_groups': activity_data['num_groups']
            }

            # Step 5: Get editor name (Spec #14)
            editor_name, ok = QInputDialog.getText(self, "Editor Information",
                                                  "Enter your name/initials (required):")
            if not ok or not editor_name.strip():
                QMessageBox.warning(self, "Required", "Editor name is required.")
                return

            # Step 6: Create the complete requisition
            success = self.model.controller.create_requisition_with_existing_borrower(
                requisition_data, selected_items, editor_name.strip()
            )

            if success:
                logger.info("Complete requisition created successfully")
                QMessageBox.information(self, "Success",
                                      "Requisition created successfully!\n\n"
                                      "Borrower and items have been recorded in the system.")
                self.refresh_data()
                self.data_changed.emit()
            else:
                QMessageBox.critical(self, "Error", "Failed to create requisition.")

        except Exception as e:
            logger.error(f"Failed to add requisition: {e}")
            QMessageBox.critical(self, "Error", f"Failed to add requisition: {str(e)}")

    def edit_selected_requisition(self):
        """Edit the items in the currently selected requisition."""
        requisition_id = self.table.get_selected_requisition_id()
        if not requisition_id:
            QMessageBox.warning(self, "No Selection", "Please select a requisition to edit.")
            return

        try:
            # Get the requisition summary to access current items
            requisition_summary = self.model.get_requisition_by_id(requisition_id)
            if not requisition_summary:
                QMessageBox.warning(self, "Error", "Could not find requisition details.")
                return

            # Format current items for ItemSelector (pre-selected items)
            current_items = []
            for item in requisition_summary.items:
                current_items.append({
                    'item_id': item['item_id'],
                    'name': item['name'],  # This will be the display name with LAB code
                    'quantity_borrowed': item['quantity_borrowed']
                })

            logger.info(f"Pre-selecting {len(current_items)} items for editing")

            # Open item selector with current items pre-selected
            item_dialog = ItemSelector(self, current_items, requisition_id)
            item_result = item_dialog.exec()

            if item_result != ItemSelector.DialogCode.Accepted:
                logger.debug("Item editing cancelled")
                return

            selected_items = item_dialog.get_selected_items()
            if not selected_items:
                QMessageBox.warning(self, "No Items", "Please select at least one item for the requisition.")
                return

            logger.info(f"Selected {len(selected_items)} items for requisition update")

            # Get editor name (Spec #14)
            editor_name, ok = QInputDialog.getText(self, "Editor Information",
                                                  "Enter your name/initials (required):")
            if not ok or not editor_name.strip():
                QMessageBox.warning(self, "Required", "Editor name is required.")
                return

            # Use existing borrower_id (borrower changes should be handled via BorrowerEditor)
            borrower_id = requisition_summary.borrower.id
            if not borrower_id:
                QMessageBox.critical(self, "Error", "Invalid borrower information.")
                return

            # Step 5: Allow editing of activity details
            current_activity_data = {
                'lab_activity_name': requisition_summary.requisition.lab_activity_name or "",
                'lab_activity_date': requisition_summary.requisition.lab_activity_date,
                'num_students': requisition_summary.requisition.num_students,
                'num_groups': requisition_summary.requisition.num_groups
            }

            accepted, activity_data = RequisitionDetailsDialog.get_details(self, current_activity_data)
            if not accepted or activity_data is None:
                logger.debug("Activity details editing cancelled")
                return

            # Prepare requisition data with updated activity information
            requisition_data = {
                'borrower_id': borrower_id,
                'date_borrowed': requisition_summary.requisition.date_borrowed,
                'lab_activity_name': activity_data['lab_activity_name'],
                'lab_activity_date': activity_data['lab_activity_date'],
                'num_students': activity_data['num_students'],
                'num_groups': activity_data['num_groups']
            }

            # Update the requisition with new items
            success = self.model.update_requisition(
                requisition_id, borrower_id, requisition_data, selected_items, editor_name.strip()
            )

            if success:
                logger.info(f"Requisition {requisition_id} updated successfully")
                QMessageBox.information(self, "Success",
                                      "Requisition updated successfully!\n\n"
                                      "Activity details and items have been updated.")
                self.refresh_data()
                self.data_changed.emit()
            else:
                QMessageBox.critical(self, "Error", "Failed to update requisition.")

        except Exception as e:
            logger.error(f"Failed to edit requisition {requisition_id}: {e}")
            QMessageBox.critical(self, "Error", f"Failed to edit requisition: {str(e)}")

    def return_selected_items(self):
        """Process return of items for selected requisition."""
        requisition_id = self.table.get_selected_requisition_id()
        if not requisition_id:
            QMessageBox.warning(self, "No Selection", "Please select a requisition to return items.")
            return

        try:
            logger.info(f"Opening return dialog for requisition {requisition_id}")

            # Open the return dialog
            return_dialog = ItemReturnDialog(self, requisition_id)
            return_dialog.return_completed.connect(self._on_return_completed)

            # Show dialog
            result = return_dialog.exec()

            if result == return_dialog.DialogCode.Accepted:
                logger.info(f"Return dialog completed successfully for requisition {requisition_id}")
                # Dialog already handled success message and signal emission
            else:
                logger.debug(f"Return dialog cancelled for requisition {requisition_id}")

        except Exception as e:
            logger.error(f"Failed to return items for requisition {requisition_id}: {e}")
            QMessageBox.critical(self, "Error", f"Failed to return items: {str(e)}")

    def delete_selected_requisition(self):
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

    def _on_requisition_selected(self, requisition_id: int):
        """Handle requisition selection."""
        has_selection = requisition_id is not None
        self.edit_button.setEnabled(has_selection)
        self.return_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)

        if has_selection:
            self.requisition_selected.emit(requisition_id)

    def _on_requisition_double_clicked(self, requisition_id: int):
        """Handle double-click on requisition (edit action)."""
        self.edit_selected_requisition()

    def _on_return_completed(self):
        """Handle successful return completion."""
        logger.info("Return completed, refreshing data")
        self.refresh_data()
        self.data_changed.emit()

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
