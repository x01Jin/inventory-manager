"""
Requester Selector Widget - Reusable component for requester selection.

Extracted from BaseRequisitionDialog to eliminate code duplication
between create and edit requisition dialogs.
Supports requester selection from database with type-specific validation.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QGroupBox,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QMessageBox,
)
from PyQt6.QtCore import pyqtSignal

from inventory_app.database.models import Requester
from inventory_app.utils.logger import logger


class RequesterSelectorWidget(QGroupBox):
    """
    Reusable widget for selecting a laboratory requester.

    Provides consistent UI and behavior across different dialogs.
    Requesters are selected from the database with type-specific validation.
    """

    requester_selected = pyqtSignal(object)

    def __init__(
        self, title="Requester Information", parent=None, edit_mode: bool = False
    ):
        """
        Initialize the requester selector widget.

        Args:
            title: Title for the group box
            parent: Parent widget
            edit_mode: If True, disable requester selection changes
        """
        super().__init__(title, parent)
        self.selected_requester = None
        self._edit_mode = edit_mode
        self._setup_ui()

    def _setup_ui(self):
        """Setup the widget UI."""
        from PyQt6.QtWidgets import QSizePolicy
        
        # Set size policy to prevent expanding vertically - use Fixed to take minimum space
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        # Requester display
        self.requester_info = QLabel("No requester selected")
        self.requester_info.setStyleSheet("font-weight: bold; padding: 2px;")
        layout.addWidget(self.requester_info)

        # Requester selection button (disabled in edit mode)
        if not self._edit_mode:
            select_requester_btn = QPushButton("Select Requester")
            select_requester_btn.clicked.connect(self.select_requester)
            layout.addWidget(select_requester_btn)

        # Validation label - only shows when there's an error
        self.validation_label = QLabel("")
        self.validation_label.setStyleSheet("color: #ef4444; font-size: 9pt;")
        self.validation_label.setVisible(False)  # Hide by default
        layout.addWidget(self.validation_label)

    def select_requester(self):
        """Open requester selection dialog."""
        try:
            from inventory_app.gui.requesters.requester_selector import (
                RequesterSelector,
            )

            selector = RequesterSelector(parent=self)
            if selector.exec() == RequesterSelector.DialogCode.Accepted:
                selected_requester_id = selector.get_selected_requester_id()
                if selected_requester_id:
                    from inventory_app.gui.requesters.requester_model import (
                        RequesterModel,
                    )

                    requester_model = RequesterModel()
                    requester_model.load_data()
                    selected_requester = requester_model.get_requester_by_id(
                        selected_requester_id
                    )

                    if selected_requester:
                        self.set_selected_requester(selected_requester)
                        logger.info(f"Requester selected: {selected_requester.name}")

        except Exception as e:
            logger.error(f"Failed to select requester: {e}")
            QMessageBox.critical(self, "Error", f"Failed to select requester: {str(e)}")

    def set_selected_requester(self, requester: Optional[Requester]):
        """
        Set the selected requester.

        Args:
            requester: Requester object to select, or None to clear
        """
        self.selected_requester = requester
        if requester:
            req_type = requester.requester_type.capitalize() if requester.requester_type else ""
            details = ""
            if requester.requester_type == "student":
                details = f" ({requester.grade_level} - {requester.section})"
            elif requester.requester_type == "teacher":
                details = f" ({requester.department})"
            self.requester_info.setText(f"{requester.name} ({req_type}){details}")
        else:
            self.requester_info.setText("No requester selected")

        self.requester_selected.emit(requester)
        self._update_validation()

    def get_selected_requester(self) -> Optional[Requester]:
        """Get the currently selected requester."""
        return self.selected_requester

    def validate(self) -> tuple[bool, str]:
        """
        Validate that a requester is selected.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.selected_requester:
            return False, "A requester must be selected."
        return True, ""

    def clear_selection(self):
        """Clear the current requester selection."""
        self.set_selected_requester(None)

    def load_requester(self, requester_id: int):
        """Load an existing requester by ID."""
        try:
            requester = Requester.get_by_id(requester_id)
            if requester:
                self.set_selected_requester(requester)
        except Exception as e:
            logger.error(f"Failed to load requester {requester_id}: {e}")

    def _update_validation(self):
        """Update validation label."""
        if not self.selected_requester:
            self.validation_label.setText("A requester must be selected.")
            self.validation_label.setVisible(True)
        else:
            self.validation_label.setText("")
            self.validation_label.setVisible(False)
