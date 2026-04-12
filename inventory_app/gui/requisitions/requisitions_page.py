"""
Requisitions management page - Complete laboratory requesting system.
Provides full CRUD operations for requisitions with requester management.

Uses background threading via QThreadPool for data loading to prevent
UI freezes on slower hardware. Supports parallel data loading for improved
performance.
"""

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QShowEvent
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
    QProgressBar,
    QFileDialog,
)

from inventory_app.gui.requisitions.requisitions_model import RequisitionsModel
from inventory_app.gui.requisitions.requisitions_table import RequisitionsTable
from inventory_app.gui.requisitions.requisitions_filters import RequisitionsFilters
from inventory_app.gui.requisitions.requisition_preview import RequisitionPreview
from inventory_app.gui.styles import get_current_theme
from inventory_app.gui.requisitions.requisition_management import (
    NewRequisitionDialog,
    EditRequisitionDialog,
    ItemReturnDialog,
)
from inventory_app.gui.utils.worker import Worker, run_in_background
from inventory_app.gui.utils.parallel_loader import (
    ParallelDataLoader,
    LoadTask,
    LoadProgress,
    parallel_load_manager,
    LoadPriority,
)
from inventory_app.utils.logger import logger


class RequisitionsPage(QWidget):
    """
    Main requisitions management page.
    Provides complete laboratory requesting workflow management with async loading.
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

        # Track current worker for cancellation
        self._current_worker: Optional[Worker] = None
        self._parallel_loader: Optional[ParallelDataLoader] = None
        self._is_loading = False

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
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Header with title and refresh button
        header_layout = QHBoxLayout()
        Theme = get_current_theme()
        title = QLabel("📋 Laboratory Requisitions")
        title.setStyleSheet(f"font-size: {Theme.FONT_SIZE_TITLE}pt; font-weight: bold;")
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

        self.print_button = QPushButton("🖨️ Print")
        self.print_button.clicked.connect(self.print_requisition)
        self.print_button.setEnabled(False)

        action_layout.addWidget(self.add_button)
        action_layout.addWidget(self.edit_button)
        action_layout.addWidget(self.return_button)
        action_layout.addWidget(self.delete_button)
        action_layout.addWidget(self.print_button)
        action_layout.addStretch()

        layout.addLayout(action_layout)

        # Progress bar for loading indicator
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Loading requisitions... %p%")
        self.progress_bar.setMaximumHeight(12)
        self.progress_bar.setVisible(False)

        # Create main horizontal splitter for (filters + table) + preview
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        # Left panel: Filters + Table (vertical layout)
        left_panel = QWidget()
        left_panel.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)

        # Filters section
        self.filters.set_model(self.model)
        left_layout.addWidget(self.filters)
        left_layout.setSpacing(10)

        # Table section
        table_group = QGroupBox("Laboratory Requisitions")
        table_group.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        table_layout = QVBoxLayout(table_group)
        table_layout.addWidget(self.table)
        left_layout.addWidget(table_group)

        main_splitter.addWidget(left_panel)

        # Right panel: Preview
        preview_group = QGroupBox("Requisition Details")
        preview_group.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.addWidget(self.preview)
        main_splitter.addWidget(preview_group)

        # Set initial splitter proportions (left_panel:preview = 3:1)
        main_splitter.setSizes([750, 250])

        layout.addWidget(main_splitter)

        # Status bar
        Theme = get_current_theme()
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet(
            f"color: {Theme.TEXT_SECONDARY}; font-size: {Theme.FONT_SIZE_NORMAL}pt;"
        )
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)

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
        """Refresh all requisition data asynchronously using parallel loading."""
        if self._is_loading:
            logger.debug("Load already in progress, skipping")
            return

        # Cancel any existing workers
        if self._current_worker:
            self._current_worker.cancel()
        if self._parallel_loader:
            self._parallel_loader.cancel()

        self._is_loading = True
        self._set_loading_state(True)

        logger.info("Starting parallel requisition data refresh...")

        # Create load tasks for parallel execution
        def load_requisition_data():
            """Load requisition data from database."""
            updated_count = self._update_all_requisition_statuses()
            success = self.model.load_data()
            if not success:
                raise Exception("Failed to load requisition data from database")
            return {
                "success": success,
                "all_requisitions": self.model.all_requisitions,
                "updated_count": updated_count,
            }

        def load_requester_options():
            """Load requester filter options."""
            return self.model.controller.get_requesters_with_requisitions()

        # Use parallel loader for concurrent loading
        self._parallel_loader = parallel_load_manager.load_page_data(
            tasks=[
                LoadTask(
                    "requisitions",
                    load_requisition_data,
                    weight=0.8,
                    priority=LoadPriority.NORMAL,
                ),
                LoadTask(
                    "requesters",
                    load_requester_options,
                    weight=0.2,
                    priority=LoadPriority.NORMAL,
                ),
            ],
            on_progress=self._on_parallel_progress,
            on_complete=self._on_parallel_complete,
            on_error=self._on_parallel_error,
        )

    def _on_parallel_progress(self, progress: LoadProgress):
        """Handle progress update from parallel loader."""
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(int(progress.total_progress))
        self.progress_bar.setFormat(
            f"Loading requisitions... {int(progress.total_progress)}%"
        )

    def _on_parallel_complete(self, results: dict):
        """Handle completion of parallel loading."""
        try:
            req_result = results.get("requisitions", {})
            if not req_result.get("success"):
                logger.error("Data load returned failure")
                QMessageBox.warning(
                    self,
                    "Data Load Error",
                    "Failed to load requisition data from database.",
                )
                self._is_loading = False
                self._parallel_loader = None
                self._set_loading_state(False)
                return

            updated_count = int(req_result.get("updated_count") or 0)
            if updated_count > 0:
                logger.info(
                    f"Updated {updated_count} requisition statuses during refresh"
                )

            requester_options = results.get("requesters", [])
            if isinstance(requester_options, list):
                self.filters.set_requester_options(requester_options)

            # Get filtered rows for display
            rows = self.model.get_filtered_rows()

            # Update table with batched loading
            self._populate_table_batched(rows)

            # Update filter summary
            total_count = len(self.model.all_requisitions)
            filtered_count = len(rows)
            self.filters.update_summary(total_count, filtered_count)

            # Update status
            stats = self.model.get_statistics()
            self.status_label.setText(
                f"Total: {stats['total_requisitions']} | "
                f"Requested: {stats['requested_requisitions']} | "
                f"Active: {stats['active_requisitions']} | "
                f"Overdue: {stats['overdue_requisitions']} | "
                f"Returned: {stats['returned_requisitions']}"
            )

            # Hide progress and re-enable buttons
            self._is_loading = False
            self._parallel_loader = None
            self._set_loading_state(False)

            logger.info(
                f"Refreshed requisition data: {total_count} requisitions loaded"
            )

        except Exception as e:
            logger.error(f"Error processing parallel load results: {e}")
            self._on_load_error((type(e), e, str(e)))

    def _on_parallel_error(self, name: str, error: Exception, traceback_str: str):
        """Handle error from parallel loader."""
        logger.error(f"Parallel load task '{name}' failed: {error}")
        self._on_load_error((type(error), error, traceback_str))

    def _populate_table_batched(self, rows: list):
        """Populate table in batches to prevent UI freeze."""

        total_rows = len(rows)
        if total_rows == 0:
            self.table.setRowCount(0)
            return

        # Disable sorting during population
        self.table.begin_batch_population()

        # Process in batches
        batch_size = 25
        self._pending_rows = rows
        self._batch_index = 0
        self._batch_size = batch_size

        # Update progress bar for batched loading
        self.progress_bar.setRange(0, total_rows)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(f"Loading requisitions... %v/{total_rows}")

        # Start batch processing
        self._process_requisition_batch()

    def _process_requisition_batch(self):
        """Process one batch of requisition rows."""
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QTimer

        # Safety check - ensure we have data to process
        if not hasattr(self, "_pending_rows") or self._pending_rows is None:
            return

        total_rows = len(self._pending_rows)
        start = self._batch_index
        end = min(start + self._batch_size, total_rows)

        if start >= total_rows:
            # Done processing
            self._finish_requisition_table_population()
            return

        # Add only next batch rows to table
        self.table.append_rows(self._pending_rows[start:end])

        # Update progress
        self.progress_bar.setValue(end)

        # Process events to keep UI responsive
        QApplication.processEvents()

        # Schedule next batch if more data and _pending_rows still valid
        self._batch_index = end
        if self._pending_rows is not None and end < total_rows:
            QTimer.singleShot(0, self._process_requisition_batch)
        else:
            self._finish_requisition_table_population()

    def _finish_requisition_table_population(self):
        """Finish table population and restore state."""
        # Restore sorting
        self.table.finalize_batch_population()

        # Clean up
        self._pending_rows = None
        self._batch_index = 0

    def _on_load_error(self, error_tuple: tuple):
        """Handle load error (runs on main thread)."""
        self._is_loading = False
        self._parallel_loader = None
        self._set_loading_state(False)
        exctype, value, tb = error_tuple
        logger.error(f"Failed to refresh data: {value}\n{tb}")
        QMessageBox.critical(
            self, "Error", f"Failed to load requisition data: {str(value)}"
        )

    def _on_load_finished(self):
        """Handle load finished (runs on main thread)."""
        self._is_loading = False
        self._current_worker = None
        self._parallel_loader = None
        self._set_loading_state(False)

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

    def showEvent(self, a0: Optional[QShowEvent]) -> None:
        """Ensure child table layouts are refreshed when the page becomes visible."""
        super().showEvent(a0)
        try:
            # Force table to recompute sizes and repaint to avoid visual glitches
            self.table.resize_columns_to_contents()
            _vp = self.table.viewport()
            if _vp is not None:
                _vp.update()
            self.table.repaint()
        except Exception:
            # Don't let repaint issues break the page
            pass

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
                    self,
                    "No Selection",
                    "Please select a requisition to return items for.",
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
                    self,
                    "Already Processed",
                    "This requisition has already been processed and is locked.\n"
                    "Edit and Return buttons are disabled. Only deletion is allowed.",
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
            QMessageBox.critical(
                self, "Error", f"Failed to open return dialog: {str(e)}"
            )

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

            # Get requester name for activity logging
            requester_name = self._get_requester_name_for_deletion(requisition_id)

            # Delete the requisition
            if self.model.delete_requisition(requisition_id, editor_name.strip()):
                logger.info(f"Requisition {requisition_id} deleted by {editor_name}")

                # Log the deletion activity
                from inventory_app.services.requisition_activity import (
                    requisition_activity_manager,
                )

                requisition_activity_manager.log_requisition_deleted(
                    requisition_id=requisition_id,
                    requester_name=requester_name,
                    user_name=editor_name.strip(),
                )

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

    def print_requisition(self):
        """
        Print or export the currently selected requisition.

        Per beta test requirement B.2: In REQUISITIONS, have an option to print.
        Exports requisition details to a printable PDF or HTML file.
        """
        requisition_id = self.table.get_selected_requisition_id()
        if not requisition_id:
            QMessageBox.warning(
                self, "No Selection", "Please select a requisition to print."
            )
            return

        try:
            requisition_summary = self.model.get_requisition_by_id(requisition_id)
            if not requisition_summary:
                QMessageBox.warning(self, "Error", "Could not load requisition data.")
                return

            # Ask user where to save the file
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Requisition Report",
                f"requisition_{requisition_id}.html",
                "HTML Files (*.html);;All Files (*.*)",
            )

            if not file_path:
                return  # User cancelled

            self._set_loading_state(True, f"Exporting requisition {requisition_id}...")
            run_in_background(
                self._build_and_save_requisition_html,
                requisition_summary,
                file_path,
                on_result=self._on_requisition_export_complete,
                on_error=self._on_requisition_export_error,
                on_finished=lambda: self._set_loading_state(False),
            )

        except Exception as e:
            logger.error(f"Failed to print requisition {requisition_id}: {e}")
            QMessageBox.critical(
                self, "Error", f"Failed to export requisition: {str(e)}"
            )

    @staticmethod
    def _build_and_save_requisition_html(
        req_summary, file_path: str
    ) -> tuple[int | None, str]:
        html_content = RequisitionsPage._generate_requisition_html(req_summary)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        requisition_id = getattr(getattr(req_summary, "requisition", None), "id", None)
        return requisition_id, file_path

    def _on_requisition_export_complete(self, result: tuple[int | None, str]) -> None:
        requisition_id, file_path = result
        QMessageBox.information(
            self,
            "Success",
            f"Requisition report saved successfully!\n\n"
            f"File: {file_path}\n\n"
            "You can open this file in a browser and use Print (Ctrl+P) to print it.",
        )
        logger.info(f"Requisition {requisition_id} exported to {file_path}")

    def _on_requisition_export_error(self, error: tuple) -> None:
        message = "Failed to export requisition"
        if len(error) >= 2:
            message = str(error[1])
        QMessageBox.critical(self, "Error", f"Failed to export requisition: {message}")

    def _set_loading_state(self, is_loading: bool, text: str = "Loading...") -> None:
        self.refresh_button.setEnabled(not is_loading)
        self.add_button.setEnabled(not is_loading)
        self.progress_bar.setVisible(is_loading)
        if is_loading:
            self.progress_bar.setRange(0, 0)
            self.progress_bar.setFormat(text)
            self.edit_button.setEnabled(False)
            self.return_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            self.print_button.setEnabled(False)
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("Loading requisitions... %p%")
            self._update_action_button_states(self.table.get_selected_requisition_id())

    @staticmethod
    def _generate_requisition_html(req_summary) -> str:
        """
        Generate a printable HTML report for a requisition.

        Args:
            req_summary: RequisitionSummary object

        Returns:
            HTML string for the requisition report
        """
        from datetime import date
        from inventory_app.utils.date_utils import format_date_short, format_time_12h
        from inventory_app.gui.requisitions.requisition_management.return_processor import (
            ReturnProcessor,
        )

        req = req_summary.requisition
        requester = req_summary.requester

        # Check if individual request
        is_individual = getattr(req_summary, "is_individual", 0) == 1

        # Format dates
        expected_request_str = ""
        if req.expected_request:
            expected_request_str = f"{format_date_short(req.expected_request)} - {format_time_12h(req.expected_request.time())}"

        expected_return_str = ""
        if req.expected_return:
            expected_return_str = f"{format_date_short(req.expected_return)} - {format_time_12h(req.expected_return.time())}"

        activity_date_str = ""
        if req.lab_activity_date:
            activity_date_str = format_date_short(req.lab_activity_date)

        # Build items table rows
        items_rows = ""
        for i, item in enumerate(req_summary.items, 1):
            items_rows += f"""
            <tr>
                <td>{i}</td>
                <td>{item["name"]}</td>
                <td style="text-align: center;">{item["quantity_requested"]}</td>
            </tr>
            """

        # Build return details section if processed
        return_details_html = ""
        if req.status == "returned" and req.id is not None:
            try:
                return_processor = ReturnProcessor()
                summary = return_processor.get_requisition_return_summary(req.id)

                if summary and (
                    summary["total_returned"] > 0
                    or summary["total_lost"] > 0
                    or summary["total_consumed"] > 0
                ):
                    return_details_html = """
                    <div class="section">
                        <h2>🔒 Final Return Details</h2>
                    """

                    if summary["returned_consumables"]:
                        return_details_html += "<h3>✅ Consumables Returned:</h3><ul>"
                        for item in summary["returned_consumables"]:
                            return_details_html += (
                                f"<li>{item['item_name']} (x{item['quantity']})</li>"
                            )
                        return_details_html += "</ul>"

                    if summary["consumed_items"]:
                        return_details_html += "<h3>🔥 Consumables Consumed:</h3><ul>"
                        for item in summary["consumed_items"]:
                            return_details_html += (
                                f"<li>{item['item_name']} (x{item['quantity']})</li>"
                            )
                        return_details_html += "</ul>"

                    if summary["returned_non_consumables"]:
                        return_details_html += (
                            "<h3>↩️ Non-Consumables Returned:</h3><ul>"
                        )
                        for item in summary["returned_non_consumables"]:
                            return_details_html += (
                                f"<li>{item['item_name']} (x{item['quantity']})</li>"
                            )
                        return_details_html += "</ul>"

                    if summary["lost_non_consumables"]:
                        return_details_html += (
                            "<h3>❌ Non-Consumables Lost/Damaged:</h3><ul>"
                        )
                        for item in summary["lost_non_consumables"]:
                            return_details_html += (
                                f"<li>{item['item_name']} (x{item['quantity']})</li>"
                            )
                        return_details_html += "</ul>"

                    defective_items = return_processor.get_requisition_defective_items(
                        req.id
                    )
                    if defective_items:
                        return_details_html += "<h3>⚠️ Defective Items:</h3><ul>"
                        for item in defective_items:
                            notes = item.get("notes") or ""
                            reporter = item.get("reported_by") or ""
                            return_details_html += (
                                f"<li>{item['item_name']} (x{item['quantity']})"
                            )
                            if notes:
                                return_details_html += f" — Issue: {notes}"
                            if reporter:
                                return_details_html += (
                                    f" <em>(reported by {reporter})</em>"
                                )
                            return_details_html += "</li>"
                        return_details_html += "</ul>"

                    return_details_html += f"""
                        <p class="totals"><strong>Totals:</strong> {summary["total_returned"]} returned, 
                        {summary["total_consumed"]} consumed, {summary["total_lost"]} lost, {summary["total_defective"]} defective</p>
                    </div>
                    """
            except Exception:
                pass  # Skip return details on error

        # Status color mapping
        status_colors = {
            "active": "#22c55e",
            "requested": "#f59e0b",
            "overdue": "#ef4444",
            "returned": "#64748b",
        }
        status_color = status_colors.get(req.status, "#374151")

        if is_individual:
            requester_info_html = f"""
            <span class="info-label">Name:</span>
            <span>{getattr(req_summary, "individual_name", "N/A") or "N/A"}</span>
            """
            if getattr(req_summary, "individual_contact", None):
                requester_info_html += f"""
                <span class="info-label">Contact:</span>
                <span>{req_summary.individual_contact}</span>
                """
            if getattr(req_summary, "individual_purpose", None):
                requester_info_html += f"""
                <span class="info-label">Purpose:</span>
                <span>{req_summary.individual_purpose}</span>
                """
            requester_info_html += """
            <span class="info-label">Type:</span>
            <span>Individual Request</span>
            """
            activity_section_html = ""
        else:
            requester = req_summary.requester
            req_type = getattr(requester, "requester_type", None) or "faculty"
            requester_info_html = f"""
            <span class="info-label">Name:</span>
            <span>{requester.name}</span>
            <span class="info-label">Type:</span>
            <span>{req_type.title()}</span>
            """
            if req_type == "student":
                if requester.grade_level and requester.section:
                    requester_info_html += f"""
                    <span class="info-label">Grade/Section:</span>
                    <span>{requester.grade_level} - {requester.section}</span>
                    """
            elif req_type == "teacher":
                if requester.department:
                    requester_info_html += f"""
                    <span class="info-label">Department:</span>
                    <span>{requester.department}</span>
                    """
            elif req_type == "faculty":
                pass
            activity_section_html = f"""
    <div class="section">
        <h2>Activity Details</h2>
        <div class="info-grid">
            <span class="info-label">Activity:</span>
            <span>{req.lab_activity_name}</span>
            <span class="info-label">Activity Date:</span>
            <span>{activity_date_str}</span>
            <span class="info-label">Students:</span>
            <span>{req.num_students or "N/A"}</span>
            <span class="info-label">Groups:</span>
            <span>{req.num_groups or "N/A"}</span>
        </div>
    </div>
    """

        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Requisition #{req.id} - Laboratory Inventory</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
        }}
        .header {{
            text-align: center;
            border-bottom: 2px solid #333;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            margin: 0;
            color: #333;
        }}
        .header .subtitle {{
            color: #666;
            font-size: 14px;
        }}
        .status {{
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            color: white;
            font-weight: bold;
            background-color: {status_color};
        }}
        .section {{
            margin-bottom: 25px;
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 8px;
        }}
        .section h2 {{
            margin-top: 0;
            color: #333;
            border-bottom: 1px solid #ddd;
            padding-bottom: 10px;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: 150px 1fr;
            gap: 8px;
        }}
        .info-label {{
            font-weight: bold;
            color: #555;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 10px;
            text-align: left;
        }}
        th {{
            background-color: #333;
            color: white;
        }}
        tr:nth-child(even) {{
            background-color: #f2f2f2;
        }}
        .totals {{
            font-weight: bold;
            margin-top: 15px;
            padding: 10px;
            background-color: #e8f5e9;
            border-radius: 4px;
        }}
        .print-footer {{
            text-align: center;
            margin-top: 30px;
            padding-top: 15px;
            border-top: 1px solid #ddd;
            color: #666;
            font-size: 12px;
        }}
        @media print {{
            body {{
                padding: 10px;
            }}
            .section {{
                break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📋 Laboratory Requisition</h1>
        <p class="subtitle">Requisition #{req.id}</p>
        <span class="status">{req.status.upper()}</span>
    </div>
    
    <div class="section">
        <h2>Requester Information</h2>
        <div class="info-grid">
            {requester_info_html}
        </div>
    </div>
    
    <div class="section">
        <h2>Timeline</h2>
        <div class="info-grid">
            <span class="info-label">Expected Request:</span>
            <span>{expected_request_str}</span>
            <span class="info-label">Expected Return:</span>
            <span>{expected_return_str}</span>
        </div>
    </div>
    
    {activity_section_html}
    
    <div class="section">
        <h2>Requested Items ({req_summary.total_items})</h2>
        <table>
            <thead>
                <tr>
                    <th style="width: 50px;">#</th>
                    <th>Item Name</th>
                    <th style="width: 100px;">Quantity</th>
                </tr>
            </thead>
            <tbody>
                {items_rows}
            </tbody>
        </table>
    </div>
    </div>
    
    <div class="section">
        <h2>⏰ Timeline</h2>
        <div class="info-grid">
            <span class="info-label">Expected Request:</span>
            <span>{expected_request_str}</span>
            <span class="info-label">Expected Return:</span>
            <span>{expected_return_str}</span>
        </div>
    </div>
    
    <div class="section">
        <h2>📝 Activity Details</h2>
        <div class="info-grid">
            <span class="info-label">Activity:</span>
            <span>{req.lab_activity_name}</span>
            <span class="info-label">Activity Date:</span>
            <span>{activity_date_str}</span>
            <span class="info-label">Students:</span>
            <span>{req.num_students or "N/A"}</span>
            <span class="info-label">Groups:</span>
            <span>{req.num_groups or "N/A"}</span>
        </div>
    </div>
    
    <div class="section">
        <h2>📦 Requested Items ({req_summary.total_items})</h2>
        <table>
            <thead>
                <tr>
                    <th style="width: 50px;">#</th>
                    <th>Item Name</th>
                    <th style="width: 100px;">Quantity</th>
                </tr>
            </thead>
            <tbody>
                {items_rows}
            </tbody>
        </table>
    </div>
    
    {return_details_html}
    
    <div class="print-footer">
        <p>Generated by Laboratory Inventory Management System</p>
        <p>Printed on: {format_date_short(date.today())}</p>
    </div>
</body>
</html>
        """
        return html

    def _on_filter_changed(self):
        """Handle any filter change - apply filters and refresh table with batched loading."""
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

            # Refresh table with filtered data using batched loading
            rows = self.model.get_filtered_rows()

            # Use batched population for large datasets to prevent UI freeze
            if len(rows) > 50:
                self._populate_table_batched(rows)
            else:
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
                is_processed = (
                    requisition_summary and requisition_summary.status == "returned"
                )

                # Edit and Return buttons disabled for processed requisitions
                self.edit_button.setEnabled(not is_processed)
                self.return_button.setEnabled(not is_processed)
                self.delete_button.setEnabled(
                    True
                )  # Delete always enabled for selected items
                self.print_button.setEnabled(True)  # Print always enabled for selected

                # Update button tooltips to explain disabled state
                if is_processed:
                    self.edit_button.setToolTip(
                        "Cannot edit: Requisition has been processed and locked"
                    )
                    self.return_button.setToolTip(
                        "Cannot return: Requisition has been processed and locked"
                    )
                else:
                    self.edit_button.setToolTip("")
                    self.return_button.setToolTip("")
            else:
                # No selection - disable all buttons
                self.edit_button.setEnabled(False)
                self.return_button.setEnabled(False)
                self.delete_button.setEnabled(False)
                self.print_button.setEnabled(False)

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
        logger.debug("Filters cleared, clearing model and refreshing data")
        self.model.clear_filters()
        self.refresh_data()

    def _update_all_requisition_statuses(self) -> int:
        """
        Update statuses for all requisitions that might need updates.

        This method is called during refresh to ensure all requisitions
        have current status information based on their dates.

        Returns:
            int: Number of requisitions that had their status updated
        """
        try:
            from inventory_app.database.connection import db

            rows = db.execute_query(
                """
                SELECT
                    id,
                    status,
                    CASE
                        WHEN status = 'returned' THEN 'returned'
                        WHEN expected_request IS NOT NULL
                             AND datetime(expected_request) > datetime('now') THEN 'requested'
                        WHEN expected_request IS NOT NULL
                             AND expected_return IS NOT NULL
                             AND datetime(expected_request) <= datetime('now')
                             AND datetime(expected_return) > datetime('now') THEN 'active'
                        WHEN expected_return IS NOT NULL
                             AND datetime(expected_return) <= datetime('now') THEN 'overdue'
                        ELSE 'requested'
                    END AS computed_status
                FROM Requisitions
                WHERE status IN ('requested', 'active', 'overdue')
                """,
                use_cache=False,
            )

            updates = [
                (row["computed_status"], row["id"])
                for row in rows
                if row.get("computed_status")
                and row["computed_status"] != row["status"]
            ]

            if not updates:
                return 0

            with db.transaction(immediate=True):
                db.execute_many(
                    "UPDATE Requisitions SET status = ? WHERE id = ?",
                    updates,
                )

            return len(updates)

        except Exception as e:
            logger.error(f"Failed to update all requisition statuses: {e}")
            return 0

    def _get_requester_name_for_deletion(self, requisition_id: int) -> str:
        """
        Get requester name for deletion activity logging.

        Args:
            requisition_id: ID of the requisition

        Returns:
            str: Requester name or "Unknown" if not found
        """
        try:
            from inventory_app.database.connection import db

            query = """
            SELECT r.name
            FROM Requesters r
            JOIN Requisitions req ON r.id = req.requester_id
            WHERE req.id = ?
            """
            rows = db.execute_query(query, (requisition_id,))
            return rows[0]["name"] if rows else "Unknown"
        except Exception as e:
            logger.error(
                f"Failed to get requester name for deletion of requisition {requisition_id}: {e}"
            )
            return "Unknown"
