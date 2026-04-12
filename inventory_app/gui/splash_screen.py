"""Splash screen for database migration progress."""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QProgressBar, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from inventory_app.gui.styles import DarkTheme


class SplashScreen(QDialog):
    """Splash screen dialog showing migration progress."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Laboratory Inventory Manager")
        self.setFixedSize(400, 150)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("Laboratory Inventory Manager")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {DarkTheme.TEXT_PRIMARY};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self.status_label = QLabel("Applying updates...")
        self.status_label.setFont(QFont("Segoe UI", 10))
        self.status_label.setStyleSheet(f"color: {DarkTheme.TEXT_SECONDARY};")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {DarkTheme.SECONDARY_DARK};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {DarkTheme.ACCENT_COLOR};
                border-radius: 3px;
            }}
        """)
        layout.addWidget(self.progress_bar)

    def update_progress(self, status: str, percent: int) -> None:
        """Update progress bar and status text.

        Args:
            status: Current status message
            percent: Progress percentage (0-100)
        """
        self.status_label.setText(status)
        self.progress_bar.setValue(percent)
