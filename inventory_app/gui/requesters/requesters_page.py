"""
Requesters management page - dedicated page for requester management.
Provides complete CRUD operations for requesters with dedicated interface.

Uses background threading via QThreadPool for data loading to prevent
UI freezes on slower hardware.
"""

from typing import Optional

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGroupBox,
    QMessageBox,
    QLineEdit,
    QInputDialog,
    QProgressBar,
)
from PyQt6.QtCore import pyqtSignal, Qt

from inventory_app.gui.requesters.requester_model import RequesterModel
from inventory_app.gui.requesters.requester_table import RequesterTable
from inventory_app.gui.requesters.requester_editor import RequesterEditor
from inventory_app.gui.styles import DarkTheme
from inventory_app.gui.utils.worker import run_in_background, Worker
from inventory_app.utils.logger import logger


class RequestersPage(QWidget):
    """
    Dedicated requesters management page.
    Provides complete requester management interface with async loading.
    """

    # Signals for integration with main application
    requester_selected = pyqtSignal(int)  # Requester ID selected
    data_changed = pyqtSignal()  # Data was modified

    def __init__(self, parent=None):
        """Initialize the requesters page."""
        super().__init__(parent)

        # Initialize components using composition
        self.model = RequesterModel()
        self.table = RequesterTable()

        # Track current worker for cancellation
        self._current_worker: Optional[Worker] = None
        self._is_loading = False

        # Setup connections between components
        self._setup_connections()

        # Setup UI
        self.setup_ui()

        # Load initial data
        self.refresh_data()

        logger.info("Requesters page initialized with all components")

    def setup_ui(self):
        """Setup the main user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header with title and refresh button
        header_layout = QHBoxLayout()
        title = QLabel("👥 Laboratory Requesters")
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

        self.add_button = QPushButton("➕ Add Requester")
        self.add_button.clicked.connect(self.add_requester)

        self.edit_button = QPushButton("✏️ Edit Requester")
        self.edit_button.clicked.connect(self.edit_selected_requester)
        self.edit_button.setEnabled(False)

        self.delete_button = QPushButton("🗑️ Delete Requester")
        self.delete_button.clicked.connect(self.delete_selected_requester)
        self.delete_button.setEnabled(False)

        action_layout.addWidget(self.add_button)
        action_layout.addWidget(self.edit_button)
        action_layout.addWidget(self.delete_button)
        action_layout.addStretch()

        layout.addLayout(action_layout)

        # Search/Filter section
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search by name, affiliation, or group:"))

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search term...")
        self.search_input.textChanged.connect(self.model.filter_by_search)
        self.search_input.textChanged.connect(self._update_table)
        search_layout.addWidget(self.search_input)

        self.clear_search_button = QPushButton("Clear")
        self.clear_search_button.clicked.connect(self._clear_search)
        search_layout.addWidget(self.clear_search_button)

        layout.addLayout(search_layout)

        # Progress bar for loading indicator
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Loading requesters... %p%")
        self.progress_bar.setMaximumHeight(20)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Main content area with requesters table
        table_group = QGroupBox("Registered Requesters")
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
        self.table.requester_selected.connect(self._on_requester_selected)
        self.table.requester_double_clicked.connect(self._on_requester_double_clicked)

    def refresh_data(self):
        """Refresh all requester data asynchronously."""
        if self._is_loading:
            logger.debug("Load already in progress, skipping")
            return

        # Cancel any existing worker
        if self._current_worker:
            self._current_worker.cancel()

        self._is_loading = True
        self._set_loading_state(True)

        logger.info("Starting async requester data refresh...")

        # Run data loading in background thread
        self._current_worker = run_in_background(
            self._load_data_background,
            on_result=self._on_data_loaded,
            on_error=self._on_load_error,
            on_finished=self._on_load_finished,
        )

    def _load_data_background(self) -> dict:
        """
        Load requester data in background thread.

        Returns dict with all needed data for UI update.
        This method runs off the main thread.
        """
        # Load data from model
        success = self.model.load_data()
        if not success:
            raise Exception("Failed to load requester data from database")

        stats = self.model.get_statistics()

        return {
            "success": True,
            "stats": stats,
        }

    def _on_data_loaded(self, result: dict):
        """Handle data loaded from background thread (runs on main thread)."""
        try:
            if not result.get("success"):
                logger.error("Data load returned failure")
                QMessageBox.warning(
                    self,
                    "Data Load Error",
                    "Failed to load requester data from database.",
                )
                return

            # Update table with batched loading
            self._update_table_batched()

            # Update status
            stats = result["stats"]
            self.status_label.setText(f"Total: {stats['total_requesters']} requesters")

            logger.info(
                f"Refreshed requester data: {stats['total_requesters']} requesters displayed"
            )

        except Exception as e:
            logger.error(f"Error processing loaded data: {e}")
            QMessageBox.critical(
                self, "Error", f"Failed to process requester data: {str(e)}"
            )

    def _update_table_batched(self):
        """Update table with batched loading to prevent UI freeze."""

        filtered_requesters = self.model.get_filtered_rows()
        total_rows = len(filtered_requesters)

        if total_rows == 0:
            self.table.populate_table([])
            return

        # For small datasets, just load directly
        if total_rows <= 50:
            self.table.populate_table(filtered_requesters)
            return

        # Disable sorting during population
        prev_sorting = self.table.isSortingEnabled()
        self.table.setSortingEnabled(False)

        # Store for batch processing
        self._pending_requesters = filtered_requesters
        self._requester_batch_index = 0
        self._requester_batch_size = 25
        self._requester_prev_sorting = prev_sorting

        # Update progress bar for batched loading
        self.progress_bar.setRange(0, total_rows)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(f"Loading requesters... %v/{total_rows}")
        self.progress_bar.setVisible(True)

        # Start batch processing
        self._process_requester_batch()

    def _process_requester_batch(self):
        """Process one batch of requester rows."""
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QTimer

        # Safety check - ensure we have data to process
        if not hasattr(self, "_pending_requesters") or self._pending_requesters is None:
            return

        total_rows = len(self._pending_requesters)
        start = self._requester_batch_index
        end = min(start + self._requester_batch_size, total_rows)

        if start >= total_rows:
            # Done processing
            self._finish_requester_table_population()
            return

        # Populate table with rows up to current batch
        self.table.populate_table(self._pending_requesters[:end])

        # Update progress
        self.progress_bar.setValue(end)

        # Process events to keep UI responsive
        QApplication.processEvents()

        # Schedule next batch if more data and _pending_requesters still valid
        self._requester_batch_index = end
        if self._pending_requesters is not None and end < total_rows:
            QTimer.singleShot(0, self._process_requester_batch)
        else:
            self._finish_requester_table_population()

    def _finish_requester_table_population(self):
        """Finish table population and restore state."""
        # Restore sorting
        self.table.setSortingEnabled(getattr(self, "_requester_prev_sorting", True))
        if self.table.isSortingEnabled():
            hdr = self.table.horizontalHeader()
            if hdr is not None:
                hdr.setSortIndicator(4, Qt.SortOrder.AscendingOrder)
                hdr.setSortIndicatorShown(False)
                self.table.sortItems(4, Qt.SortOrder.AscendingOrder)

        # Hide progress bar
        self.progress_bar.setVisible(False)

        # Clean up
        self._pending_requesters = None
        self._requester_batch_index = 0

    def _on_load_error(self, error_tuple: tuple):
        """Handle load error (runs on main thread)."""
        exctype, value, tb = error_tuple
        logger.error(f"Failed to refresh data: {value}\n{tb}")
        QMessageBox.critical(
            self, "Error", f"Failed to load requester data: {str(value)}"
        )

    def _on_load_finished(self):
        """Handle load finished (runs on main thread)."""
        self._is_loading = False
        self._current_worker = None
        self._set_loading_state(False)

    def _set_loading_state(self, is_loading: bool):
        """Update UI loading state."""
        self.progress_bar.setVisible(is_loading)
        if is_loading:
            self.progress_bar.setRange(0, 0)  # Indeterminate
        else:
            self.progress_bar.setRange(0, 100)

        # Disable buttons during load
        self.refresh_button.setEnabled(not is_loading)
        self.add_button.setEnabled(not is_loading)

    def add_requester(self):
        """Add a new requester."""
        try:
            dialog = RequesterEditor(self)
            if dialog.exec() == RequesterEditor.DialogCode.Accepted:
                logger.info("New requester added")
                self.refresh_data()
                self.data_changed.emit()
        except Exception as e:
            logger.error(f"Failed to add requester: {e}")
            QMessageBox.critical(self, "Error", f"Failed to add requester: {str(e)}")

    def edit_selected_requester(self):
        """Edit the currently selected requester."""
        requester_id = self.table.get_selected_requester_id()
        if not requester_id:
            QMessageBox.warning(
                self, "No Selection", "Please select a requester to edit."
            )
            return

        try:
            dialog = RequesterEditor(self, requester_id)
            if dialog.exec() == RequesterEditor.DialogCode.Accepted:
                logger.info(f"Requester {requester_id} edited")
                self.refresh_data()
                self.data_changed.emit()
        except Exception as e:
            logger.error(f"Failed to edit requester {requester_id}: {e}")
            QMessageBox.critical(self, "Error", f"Failed to edit requester: {str(e)}")

    def delete_selected_requester(self):
        """Delete the currently selected requester."""
        requester_id = self.table.get_selected_requester_id()
        if not requester_id:
            QMessageBox.warning(
                self, "No Selection", "Please select a requester to delete."
            )
            return

        # Check if requester has requisitions (shouldn't happen due to UI state, but double-check)
        if self.model.requester_has_requisitions(requester_id):
            QMessageBox.warning(
                self,
                "Cannot Delete",
                "Cannot delete requester: requester has recorded requisitions.",
            )
            return

        # Get requester details for confirmation
        requester = self.model.get_requester_by_id(requester_id)
        if not requester:
            QMessageBox.warning(self, "Error", "Requester not found.")
            return

        # Show confirmation dialog
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete requester '{requester.name}'?\n\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Ask for editor name
            editor_name, ok = QInputDialog.getText(
                self, "Editor Information", "Your Name/Initials:", text=""
            )

            if not ok or not editor_name.strip():
                QMessageBox.warning(
                    self, "Required Information", "Editor name is required."
                )
                return

            try:
                success = self.model.delete_requester(requester_id, editor_name.strip())
                if success:
                    QMessageBox.information(
                        self, "Success", "Requester deleted successfully!"
                    )
                    self.refresh_data()
                    self.data_changed.emit()
                else:
                    QMessageBox.critical(self, "Error", "Failed to delete requester.")
            except Exception as e:
                logger.error(f"Failed to delete requester {requester_id}: {e}")
                QMessageBox.critical(
                    self, "Error", f"Failed to delete requester: {str(e)}"
                )

    def _on_requester_selected(self, requester_id: int):
        """Handle requester selection."""
        has_selection = requester_id is not None
        self.edit_button.setEnabled(has_selection)

        if has_selection:
            # Check if requester has requisitions to determine delete button state
            has_requisitions = self.model.requester_has_requisitions(requester_id)

            if has_requisitions:
                self.delete_button.setEnabled(False)
                self.delete_button.setToolTip(
                    "Cannot delete: requester has recorded requisitions"
                )
            else:
                self.delete_button.setEnabled(True)
                self.delete_button.setToolTip("Delete this requester")

            self.requester_selected.emit(requester_id)
        else:
            # No selection - disable both buttons
            self.delete_button.setEnabled(False)
            self.delete_button.setToolTip("")

    def _on_requester_double_clicked(self, requester_id: int):
        """Handle double-click on requester (edit action)."""
        self.edit_selected_requester()

    def _update_table(self):
        """Update table with current filtered data using batched loading."""
        try:
            filtered_requesters = self.model.get_filtered_rows()

            # Use batched population for large datasets to prevent UI freeze
            if len(filtered_requesters) > 50:
                self._update_table_batched()
            else:
                self.table.populate_table(filtered_requesters)

            # Update search input styling based on filter state
            has_filter = bool(self.search_input.text().strip())
            if has_filter:
                self.search_input.setStyleSheet(
                    f"background-color: {DarkTheme.PRIMARY_DARK}; border: 1px solid {DarkTheme.ACCENT_COLOR};"
                )
            else:
                self.search_input.setStyleSheet("")

        except Exception as e:
            logger.error(f"Failed to update table: {e}")

    def _clear_search(self):
        """Clear the search input."""
        self.search_input.clear()
        self.model.clear_filters()
        self._update_table()
