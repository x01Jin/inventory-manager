"""
Requisitions management page - Complete laboratory requesting system.
Provides full CRUD operations for requisitions with requester management.
"""

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGroupBox,
    QMessageBox,
    QInputDialog,
    QSplitter,
    QSizePolicy,
)

from inventory_app.gui.requisitions.requisitions_model import RequisitionsModel
from inventory_app.gui.requisitions.requisitions_table import RequisitionsTable
from inventory_app.gui.requisitions.requisitions_filters import RequisitionsFilters
from inventory_app.gui.requisitions.requisition_preview import RequisitionPreview
from inventory_app.gui.requisitions.requisition_management import (
    NewRequisitionDialog,
    EditRequisitionDialog,
    ItemReturnDialog,
)
from inventory_app.utils.internal_time import check_and_update_requisition_statuses
from inventory_app.utils.logger import logger


class RequisitionsPage(QWidget):
    """
    Main requisitions management page.
    Provides complete laboratory requesting workflow management.
    """

    # Signals for integration with main application
    requisition_selected = pyqtSignal(int)  # Requisition ID selected
    data_changed = pyqtSignal()  # Data was modified

    def __init__(self, parent=None):
        """Initialize the requisitions page."""
        super().__init__(parent)

        # Initialize components using composition
        self.model = RequisitionsModel()
        self.filters = RequisitionsFilters()
        self.table = RequisitionsTable()
        self.preview = RequisitionPreview()

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

        # Create main horizontal splitter for (filters + table) + preview
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Left panel: Filters + Table (vertical layout)
        left_panel = QWidget()
        left_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)

        # Filters section
        self.filters.set_model(self.model)
        left_layout.addWidget(self.filters)

        # Table section
        table_group = QGroupBox("Laboratory Requisitions")
        table_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        table_layout = QVBoxLayout(table_group)
        table_layout.addWidget(self.table)
        left_layout.addWidget(table_group)

        main_splitter.addWidget(left_panel)

        # Right panel: Preview
        preview_group = QGroupBox("Requisition Details")
        preview_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.addWidget(self.preview)
        main_splitter.addWidget(preview_group)

        # Set initial splitter proportions (left_panel:preview = 3:1)
        main_splitter.setSizes([750, 250])

        layout.addWidget(main_splitter)

        # Status bar
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #666; font-size: 10pt;")
        layout.addWidget(self.status_label)

    def _setup_connections(self):
        """Setup signal connections between components."""
        # Table selection to preview panel and button states
        self.table.requisition_selected.connect(self._on_requisition_selected)
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)

        # Filter signals - connect to both model and refresh
        self.filters.search_changed.connect(self._on_filter_changed)
        self.filters.requester_filter_changed.connect(self._on_filter_changed)
        self.filters.status_filter_changed.connect(self._on_filter_changed)
        self.filters.date_range_changed.connect(self._on_filter_changed)
        self.filters.clear_filters_requested.connect(self._on_filters_cleared)

    def refresh_data(self):
        """Refresh all requisition data."""
        try:
            # Load initial data from model
            success = self.model.load_data()
            if not success:
                logger.error("❌ STEP 1 FAILED: Failed to load initial data")
                QMessageBox.warning(
                    self,
                    "Data Load Error",
                    "Failed to load requisition data from database.",
                )
                return

            # Perform manual status check and update database
            updated_count = check_and_update_requisition_statuses()

            if updated_count > 0:
                # Reload data to get updated statuses
                success = self.model.load_data()
                if not success:
                    logger.error(
                        "❌ STEP 3 FAILED: Failed to reload data after status updates"
                    )
                    QMessageBox.warning(
                        self,
                        "Data Reload Error",
                        "Failed to reload requisition data after status updates.",
                    )
                    return

            # Reload requester options (in case new requesters have requisitions)
            self.filters._load_requester_options()

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

        except Exception as e:
            logger.error(f"Failed to refresh requisition data: {e}")
            QMessageBox.critical(
                self, "Error", f"Failed to load requisition data: {str(e)}"
            )

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
            QMessageBox.critical(
                self, "Error", f"Failed to open new requisition dialog: {str(e)}"
            )

    def _on_requisition_created(self, requisition_id: int):
        """Handle successful requisition creation."""
        try:
            logger.info(f"New requisition created with ID: {requisition_id}")

            # Refresh the data to show the new requisition
            self.refresh_data()

            # Emit signal to notify other components
            self.data_changed.emit()

        except Exception as e:
            logger.error(f"Failed to handle requisition creation: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to refresh data after creating requisition: {str(e)}",
            )

    def edit_requisition(self):
        """Open dialog to edit the currently selected requisition."""
        try:
            requisition_id = self.table.get_selected_requisition_id()
            if not requisition_id:
                QMessageBox.warning(
                    self, "No Selection", "Please select a requisition to edit."
                )
                return

            # Get the requisition summary from the model
            requisition_summary = self.model.get_requisition_by_id(requisition_id)
            if not requisition_summary:
                QMessageBox.warning(self, "Error", "Could not find requisition data.")
                return

            # Check if requisition can be edited
            if requisition_summary.status == "returned":
                QMessageBox.warning(
                    self, "Cannot Edit", "Fully returned requisitions cannot be edited."
                )
                return

            # Create and show the edit dialog
            dialog = EditRequisitionDialog(requisition_summary, parent=self)

            # Connect signal to refresh data when requisition is updated
            dialog.requisition_updated.connect(self.refresh_data)
            dialog.requisition_updated.connect(self.data_changed.emit)

            # Show the dialog
            dialog.exec()

        except Exception as e:
            logger.error(f"Failed to open edit requisition dialog: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open edit dialog: {str(e)}")

    def return_items(self):
        """Open dialog to process item returns for the selected requisition."""
        try:
            requisition_id = self.table.get_selected_requisition_id()
            if not requisition_id:
                QMessageBox.warning(
                    self, "No Selection", "Please select a requisition to return items for."
                )
                return

            # Get the requisition summary from the model
            requisition_summary = self.model.get_requisition_by_id(requisition_id)
            if not requisition_summary:
                QMessageBox.warning(self, "Error", "Could not find requisition data.")
                return

            # Check if requisition has already been processed
            if requisition_summary.status == "returned":
                QMessageBox.information(
                    self, "Already Processed",
                    "This requisition has already been processed and is locked.\n"
                    "Edit and Return buttons are disabled. Only deletion is allowed."
                )
                return

            # Create and show the return dialog
            dialog = ItemReturnDialog(requisition_id, parent=self)

            # Show the dialog (returns True if processed successfully)
            if dialog.exec():
                # Refresh data after successful processing
                self.refresh_data()
                self.data_changed.emit()

        except Exception as e:
            logger.error(f"Failed to open return dialog: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open return dialog: {str(e)}")

    def delete_requisition(self):
        """Delete the currently selected requisition."""
        requisition_id = self.table.get_selected_requisition_id()
        if not requisition_id:
            QMessageBox.warning(
                self, "No Selection", "Please select a requisition to delete."
            )
            return

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            "Are you sure you want to delete this requisition?\n\n"
            "This action cannot be undone and will remove all associated requesting records.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            # Ask for editor name (Spec #14)
            editor_name, ok = QInputDialog.getText(
                self, "Editor Information", "Enter your name/initials (required):"
            )
            if not ok or not editor_name.strip():
                QMessageBox.warning(self, "Required", "Editor name is required.")
                return

            # Delete the requisition
            if self.model.delete_requisition(requisition_id, editor_name.strip()):
                logger.info(f"Requisition {requisition_id} deleted by {editor_name}")

                QMessageBox.information(
                    self, "Success", "Requisition deleted successfully!"
                )
                self.refresh_data()
                self.data_changed.emit()
            else:
                QMessageBox.critical(self, "Error", "Failed to delete requisition.")

        except Exception as e:
            logger.error(f"Failed to delete requisition {requisition_id}: {e}")
            QMessageBox.critical(
                self, "Error", f"Failed to delete requisition: {str(e)}"
            )

    def _on_filter_changed(self):
        """Handle any filter change - apply filters and refresh table."""
        try:
            # Apply all current filters from the filter widget
            current_filters = self.filters.get_current_filters()

            # Apply filters to model
            if "search_term" in current_filters:
                self.model.filter_by_search(current_filters["search_term"])
            if "requester_filter" in current_filters:
                self.model.filter_by_requester(current_filters["requester_filter"])
            if "status_filter" in current_filters:
                self.model.filter_by_status(current_filters["status_filter"])
            if "date_from" in current_filters or "date_to" in current_filters:
                self.model.filter_by_date_range(
                    current_filters.get("date_from"), current_filters.get("date_to")
                )

            # Refresh table with filtered data
            rows = self.model.get_filtered_rows()
            self.table.populate_table(rows)

            # Update filter summary
            total_count = len(self.model.all_requisitions)
            filtered_count = len(rows)
            self.filters.update_summary(total_count, filtered_count)

            logger.debug(
                f"Applied filters: {filtered_count} of {total_count} requisitions shown"
            )

        except Exception as e:
            logger.error(f"Failed to apply filters: {e}")

    def _on_requisition_selected(self, requisition_id: int):
        """Handle requisition selection from table - update preview panel and button states."""
        try:
            if requisition_id:
                # Get the requisition summary from the model
                requisition_summary = self.model.get_requisition_by_id(requisition_id)
                if requisition_summary:
                    self.preview.update_preview(requisition_summary)
                    logger.debug(
                        f"Updated preview for selected requisition {requisition_id}"
                    )
                else:
                    logger.warning(
                        f"Could not find requisition {requisition_id} in model"
                    )
                    self.preview.update_preview(None)
            else:
                # No selection - show empty state
                self.preview.update_preview(None)

            # Update button states based on selection
            self._update_action_button_states(requisition_id)

        except Exception as e:
            logger.error(
                f"Failed to update preview for requisition {requisition_id}: {e}"
            )
            self.preview.update_preview(None)
            self._update_action_button_states(None)

    def _update_action_button_states(self, requisition_id: Optional[int]):
        """Update the enabled state of action buttons based on selection and status."""
        try:
            has_selection = requisition_id is not None

            if has_selection:
                # Get requisition status to determine button states
                requisition_summary = self.model.get_requisition_by_id(requisition_id)
                is_processed = (requisition_summary and
                              requisition_summary.status == "returned")

                # Edit and Return buttons disabled for processed requisitions
                self.edit_button.setEnabled(not is_processed)
                self.return_button.setEnabled(not is_processed)
                self.delete_button.setEnabled(True)  # Delete always enabled for selected items

                # Update button tooltips to explain disabled state
                if is_processed:
                    self.edit_button.setToolTip("Cannot edit: Requisition has been processed and locked")
                    self.return_button.setToolTip("Cannot return: Requisition has been processed and locked")
                else:
                    self.edit_button.setToolTip("")
                    self.return_button.setToolTip("")
            else:
                # No selection - disable all buttons
                self.edit_button.setEnabled(False)
                self.return_button.setEnabled(False)
                self.delete_button.setEnabled(False)

            logger.debug(f"Action buttons updated for selection: {has_selection}")

        except Exception as e:
            logger.error(f"Failed to update action button states: {e}")

    def _on_table_selection_changed(self):
        """Handle table selection changes (including deselection)."""
        try:
            # Get current selection
            requisition_id = self.table.get_selected_requisition_id()

            # Update preview based on selection
            if requisition_id:
                requisition_summary = self.model.get_requisition_by_id(requisition_id)
                if requisition_summary:
                    self.preview.update_preview(requisition_summary)
                    logger.debug(
                        f"Updated preview for selected requisition {requisition_id}"
                    )
                else:
                    logger.warning(
                        f"Could not find requisition {requisition_id} in model"
                    )
                    self.preview.update_preview(None)
            else:
                # No selection - show empty state
                self.preview.update_preview(None)

            # Update button states based on selection
            self._update_action_button_states(requisition_id)

        except Exception as e:
            logger.error(f"Failed to handle table selection change: {e}")
            self.preview.update_preview(None)
            self._update_action_button_states(None)

    def _on_filters_cleared(self):
        """Handle filters cleared event."""
        logger.debug("Filters cleared, refreshing data")
        self.refresh_data()
