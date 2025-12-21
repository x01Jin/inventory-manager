"""
Navigation panel component for the inventory application.
Simple and clean navigation using composition with live clock display.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import pyqtSignal, QTimer
from datetime import datetime

from inventory_app.gui.styles import get_current_theme


class NavigationPanel(QWidget):
    """Navigation panel with theme-aware styling."""

    page_changed = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.setFixedWidth(220)

        # Get current theme
        Theme = get_current_theme()

        self.setStyleSheet(
            f"background-color: {Theme.SECONDARY_DARK}; border-right: 1px solid {Theme.BORDER_COLOR};"
        )

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # App title
        title = QLabel("📊 L.I.M.")
        title.setStyleSheet(
            f"color: {Theme.ACCENT_COLOR}; font-size: {Theme.FONT_SIZE_HEADER}pt; font-weight: bold; padding: 20px; background-color: {Theme.PRIMARY_DARK};"
        )
        layout.addWidget(title)

        # Navigation buttons
        nav_items = [
            ("🏠", "Dashboard", 0),
            ("📦", "Inventory", 1),
            ("📋", "Requisitions", 2),
            ("👥", "Requesters", 3),
            ("📊", "Reports", 4),
            ("⚙️", "Settings", 5),
            ("❓", "Help", 6),
        ]

        self.nav_buttons = []
        for icon, text, page_index in nav_items:
            btn = self.create_nav_button(icon, text, page_index)
            self.nav_buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()

        # User info
        user_info = QLabel("👤 Hello User!")
        user_info.setStyleSheet(
            f"color: {Theme.TEXT_SECONDARY}; padding: 15px; font-size: {Theme.FONT_SIZE_NORMAL}pt; border-top: 1px solid {Theme.BORDER_COLOR};"
        )
        layout.addWidget(user_info)

        # Live clock display
        self.clock_label = QLabel()
        self.clock_label.setStyleSheet(
            f"color: {Theme.TEXT_SECONDARY}; padding: 10px 15px; font-size: {Theme.FONT_SIZE_NORMAL}pt; font-family: 'Courier New'; border-top: 1px solid {Theme.BORDER_COLOR};"
        )
        layout.addWidget(self.clock_label)

        # Setup live clock timer
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)  # Update every second for real-time display

        # Initial clock update
        self.update_clock()

        # Set first button as active
        self.set_active_button(0)

    def create_nav_button(self, icon: str, text: str, page_index: int):
        """Create a navigation button."""
        Theme = get_current_theme()
        btn = QPushButton(f"{icon} {text}")
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                text-align: left;
                padding: 12px 20px;
                font-size: {Theme.FONT_SIZE_LARGE}pt;
                color: {Theme.TEXT_SECONDARY};
            }}
            QPushButton:hover {{
                background-color: {Theme.ACCENT_HOVER};
                color: {Theme.TEXT_PRIMARY};
            }}
            QPushButton:checked {{
                background-color: {Theme.ACCENT_COLOR};
                color: {Theme.TEXT_PRIMARY};
                border-left: 3px solid {Theme.SUCCESS_COLOR};
            }}
        """)

        btn.setCheckable(True)
        btn.clicked.connect(lambda: self.handle_button_click(page_index))
        return btn

    def handle_button_click(self, page_index: int):
        """Handle navigation button clicks."""
        self.set_active_button(page_index)
        self.page_changed.emit(page_index)

    def set_active_button(self, index: int):
        """Set the active navigation button."""
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

    def update_clock(self):
        """Update the clock display with current date and time."""
        now = datetime.now()
        time_str = now.strftime("%Y-%m-%d %H:%M:%S")
        self.clock_label.setText(f"🕐 {time_str}")
