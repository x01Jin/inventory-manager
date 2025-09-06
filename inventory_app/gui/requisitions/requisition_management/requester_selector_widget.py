"""
Requester Selector Widget - Reusable component for requester selection.

Extracted from BaseRequisitionDialog to eliminate code duplication
between create and edit requisition dialogs.
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
    """

    # Signal emitted when requester is selected
    requester_selected = pyqtSignal(object)  # Requester object

    def __init__(self, title="👥 Requester Information", parent=None):
        """
        Initialize the requester selector widget.

        Args:
            title: Title for the group box
            parent: Parent widget
        """
        super().__init__(title, parent)
        self.selected_requester = None
        self._setup_ui()

    def _setup_ui(self):
        """Setup the widget UI."""
        layout = QVBoxLayout(self)

        # Requester display
        self.requester_info = QLabel("No requester selected")
        self.requester_info.setStyleSheet("font-weight: bold; padding: 5px;")
        layout.addWidget(self.requester_info)

        # Requester selection button
        select_requester_btn = QPushButton("Select Requester")
        select_requester_btn.clicked.connect(self.select_requester)
        layout.addWidget(select_requester_btn)

    def select_requester(self):
        """Open requester selection dialog."""
        try:
            from inventory_app.gui.requesters.requester_selector import RequesterSelector

            selector = RequesterSelector(parent=self)
            if selector.exec() == RequesterSelector.DialogCode.Accepted:
                selected_requester_id = selector.get_selected_requester_id()
                if selected_requester_id:
                    # Get the requester object from the model
                    from inventory_app.gui.requesters.requester_model import RequesterModel

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
            self.requester_info.setText(
                f"{requester.name} ({requester.affiliation})"
            )
        else:
            self.requester_info.setText("No requester selected")

        # Emit signal
        self.requester_selected.emit(requester)

    def get_selected_requester(self) -> Optional[Requester]:
        """Get the currently selected requester."""
        return self.selected_requester

    def clear_selection(self):
        """Clear the current requester selection."""
        self.set_selected_requester(None)
