"""
Borrowers management page - dedicated page for borrower management.
Provides complete CRUD operations for borrowers with dedicated interface.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QMessageBox, QLineEdit
)
from PyQt6.QtCore import pyqtSignal

from inventory_app.gui.borrowers.borrower_model import BorrowerModel
from inventory_app.gui.borrowers.borrower_table import BorrowerTable
from inventory_app.gui.borrowers.borrower_editor import BorrowerEditor
from inventory_app.utils.logger import logger


class BorrowersPage(QWidget):
    """
    Dedicated borrowers management page.
    Provides complete borrower management interface.
    """

    # Signals for integration with main application
    borrower_selected = pyqtSignal(int)  # Borrower ID selected
    data_changed = pyqtSignal()          # Data was modified

    def __init__(self, parent=None):
        """Initialize the borrowers page."""
        super().__init__(parent)

        # Initialize components using composition
        self.model = BorrowerModel()
        self.table = BorrowerTable()

        # Setup connections between components
        self._setup_connections()

        # Setup UI
        self.setup_ui()

        # Load initial data
        self.refresh_data()

        logger.info("Borrowers page initialized with all components")

    def setup_ui(self):
        """Setup the main user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header with title and refresh button
        header_layout = QHBoxLayout()
        title = QLabel("👥 Laboratory Borrowers")
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

        self.add_button = QPushButton("➕ Add Borrower")
        self.add_button.clicked.connect(self.add_borrower)

        self.edit_button = QPushButton("✏️ Edit Borrower")
        self.edit_button.clicked.connect(self.edit_selected_borrower)
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

        # Main content area with borrowers table
        table_group = QGroupBox("Registered Borrowers")
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
        self.table.borrower_selected.connect(self._on_borrower_selected)
        self.table.borrower_double_clicked.connect(self._on_borrower_double_clicked)

    def refresh_data(self):
        """Refresh all borrower data."""
        try:
            logger.info("Refreshing borrower data...")

            # Load data from model
            success = self.model.load_data()
            if not success:
                QMessageBox.warning(self, "Data Load Error",
                                  "Failed to load borrower data from database.")
                return

            # Update table
            self._update_table()

            # Update status
            stats = self.model.get_statistics()
            self.status_label.setText(
                f"Total: {stats['total_borrowers']} borrowers"
            )

            logger.info(f"Refreshed borrower data: {stats['total_borrowers']} borrowers displayed")

        except Exception as e:
            logger.error(f"Failed to refresh borrower data: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load borrower data: {str(e)}")

    def add_borrower(self):
        """Add a new borrower."""
        try:
            dialog = BorrowerEditor(self)
            if dialog.exec() == BorrowerEditor.DialogCode.Accepted:
                logger.info("New borrower added")
                self.refresh_data()
                self.data_changed.emit()
        except Exception as e:
            logger.error(f"Failed to add borrower: {e}")
            QMessageBox.critical(self, "Error", f"Failed to add borrower: {str(e)}")

    def edit_selected_borrower(self):
        """Edit the currently selected borrower."""
        borrower_id = self.table.get_selected_borrower_id()
        if not borrower_id:
            QMessageBox.warning(self, "No Selection", "Please select a borrower to edit.")
            return

        try:
            dialog = BorrowerEditor(self, borrower_id)
            if dialog.exec() == BorrowerEditor.DialogCode.Accepted:
                logger.info(f"Borrower {borrower_id} edited")
                self.refresh_data()
                self.data_changed.emit()
        except Exception as e:
            logger.error(f"Failed to edit borrower {borrower_id}: {e}")
            QMessageBox.critical(self, "Error", f"Failed to edit borrower: {str(e)}")

    def _on_borrower_selected(self, borrower_id: int):
        """Handle borrower selection."""
        has_selection = borrower_id is not None
        self.edit_button.setEnabled(has_selection)

        if has_selection:
            self.borrower_selected.emit(borrower_id)

    def _on_borrower_double_clicked(self, borrower_id: int):
        """Handle double-click on borrower (edit action)."""
        self.edit_selected_borrower()

    def _update_table(self):
        """Update table with current filtered data."""
        try:
            filtered_borrowers = self.model.get_filtered_rows()
            self.table.populate_table(filtered_borrowers)

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
