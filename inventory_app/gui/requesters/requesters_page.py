"""
Requesters management page - dedicated page for requester management.
Provides complete CRUD operations for requesters with dedicated interface.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QMessageBox, QLineEdit
)
from PyQt6.QtCore import pyqtSignal

from inventory_app.gui.requesters.requester_model import RequesterModel
from inventory_app.gui.requesters.requester_table import RequesterTable
from inventory_app.gui.requesters.requester_editor import RequesterEditor
from inventory_app.utils.logger import logger


class RequestersPage(QWidget):
    """
    Dedicated requesters management page.
    Provides complete requester management interface.
    """

    # Signals for integration with main application
    requester_selected = pyqtSignal(int)  # Requester ID selected
    data_changed = pyqtSignal()          # Data was modified

    def __init__(self, parent=None):
        """Initialize the requesters page."""
        super().__init__(parent)

        # Initialize components using composition
        self.model = RequesterModel()
        self.table = RequesterTable()

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

        action_layout.addWidget(self.add_button)
        action_layout.addWidget(self.edit_button)
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
        """Refresh all requester data."""
        try:
            logger.info("Refreshing requester data...")

            # Load data from model
            success = self.model.load_data()
            if not success:
                QMessageBox.warning(self, "Data Load Error",
                                  "Failed to load requester data from database.")
                return

            # Update table
            self._update_table()

            # Update status
            stats = self.model.get_statistics()
            self.status_label.setText(
                f"Total: {stats['total_requesters']} requesters"
            )

            logger.info(f"Refreshed requester data: {stats['total_requesters']} requesters displayed")

        except Exception as e:
            logger.error(f"Failed to refresh requester data: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load requester data: {str(e)}")

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
            QMessageBox.warning(self, "No Selection", "Please select a requester to edit.")
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

    def _on_requester_selected(self, requester_id: int):
        """Handle requester selection."""
        has_selection = requester_id is not None
        self.edit_button.setEnabled(has_selection)

        if has_selection:
            self.requester_selected.emit(requester_id)

    def _on_requester_double_clicked(self, requester_id: int):
        """Handle double-click on requester (edit action)."""
        self.edit_selected_requester()

    def _update_table(self):
        """Update table with current filtered data."""
        try:
            filtered_requesters = self.model.get_filtered_rows()
            self.table.populate_table(filtered_requesters)

            # Update search input styling based on filter state
            has_filter = bool(self.search_input.text().strip())
            if has_filter:
                self.search_input.setStyleSheet("background-color: #e8f4fd; border: 1px solid #0078d4;")
            else:
                self.search_input.setStyleSheet("")

        except Exception as e:
            logger.error(f"Failed to update table: {e}")

    def _clear_search(self):
        """Clear the search input."""
        self.search_input.clear()
        self.model.clear_filters()
        self._update_table()
