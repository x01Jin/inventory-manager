"""
Main window for the Laboratory Inventory Application.
Simple and clean composition using navigation and dashboard.
"""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QStackedWidget, QLabel, QVBoxLayout

from inventory_app.gui.styles import DarkTheme
from inventory_app.gui.navigation import NavigationPanel
from inventory_app.gui.dashboard import DashboardPage
from inventory_app.gui.inventory_page import InventoryPage
from inventory_app.gui.requisitions_page import RequisitionsPage


class MainWindow(QMainWindow):
    """Main application window with dark mode UI."""

    def __init__(self):
        super().__init__()
        print("Initializing Laboratory Inventory Application...")

        self.setWindowTitle("Laboratory Inventory Monitor")
        self.setMinimumSize(1000, 700)

        # Apply dark theme
        app_instance = QApplication.instance()
        if app_instance and isinstance(app_instance, QApplication):
            DarkTheme.apply_dark_theme(app_instance)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Navigation panel
        self.nav_panel = NavigationPanel()
        main_layout.addWidget(self.nav_panel)

        # Content area
        self.content_stack = QStackedWidget()
        main_layout.addWidget(self.content_stack, 1)

        # Create pages
        self.dashboard_page = DashboardPage()
        self.inventory_page = InventoryPage()
        self.requisitions_page = RequisitionsPage()
        self.reports_page = self.create_placeholder("Reports", "📊 Generate usage reports")
        self.settings_page = self.create_placeholder("Settings", "⚙️ Configure preferences")

        # Add pages to stack
        self.content_stack.addWidget(self.dashboard_page)    # Index 0
        self.content_stack.addWidget(self.inventory_page)    # Index 1
        self.content_stack.addWidget(self.requisitions_page) # Index 2
        self.content_stack.addWidget(self.reports_page)      # Index 3
        self.content_stack.addWidget(self.settings_page)     # Index 4

        # Connect navigation
        self.nav_panel.page_changed.connect(self.content_stack.setCurrentIndex)

        print("Laboratory Inventory Application ready")

    def create_placeholder(self, title: str, description: str):
        """Create placeholder page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)

        header = QLabel(title)
        header.setStyleSheet(f"font-size: {DarkTheme.FONT_SIZE_TITLE}pt; font-weight: bold; color: {DarkTheme.TEXT_PRIMARY};")
        layout.addWidget(header)

        desc = QLabel(description)
        desc.setStyleSheet(f"color: {DarkTheme.TEXT_SECONDARY}; font-size: {DarkTheme.FONT_SIZE_LARGE}pt;")
        layout.addWidget(desc)

        placeholder = QLabel("🚧 Under development")
        placeholder.setStyleSheet(f"color: {DarkTheme.TEXT_MUTED}; font-style: italic; padding: 50px; text-align: center;")
        layout.addWidget(placeholder)

        layout.addStretch()
        return page


def main():
    """Main application entry point."""
    try:
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()

        print("Laboratory Inventory Application started successfully")
        return app.exec()

    except Exception as e:
        print(f"Failed to start application: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
