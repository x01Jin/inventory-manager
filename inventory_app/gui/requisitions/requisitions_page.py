"""
Requisitions management page - Under Construction
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt


class RequisitionsPage(QWidget):
    """Placeholder requisitions management page - Under Construction."""

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(20)

        # Under construction message
        construction_label = QLabel("🚧 Requisitions Page Under Construction 🚧")
        construction_label.setStyleSheet("""
            font-size: 24pt;
            font-weight: bold;
            color: #666;
        """)
        construction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        description_label = QLabel(
            "This feature is currently being developed.\n"
            "Please check back later for laboratory requisition management functionality."
        )
        description_label.setStyleSheet("""
            font-size: 14pt;
            color: #888;
            text-align: center;
        """)
        description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description_label.setWordWrap(True)

        layout.addStretch()
        layout.addWidget(construction_label)
        layout.addWidget(description_label)
        layout.addStretch()
