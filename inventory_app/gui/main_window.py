"""
Main window for the Laboratory Inventory Application.
Simple and clean composition using navigation and dashboard.
"""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QStackedWidget, QLabel, QVBoxLayout

from inventory_app.gui.styles import DarkTheme
from inventory_app.gui.navigation import NavigationPanel
from inventory_app.gui.dashboard import DashboardPage
from inventory_app.gui.inventory.inventory_page import InventoryPage
from inventory_app.gui.requisitions.requisitions_page import RequisitionsPage
from inventory_app.gui.borrowers.borrowers_page import BorrowersPage
from inventory_app.gui.settings.settings_page import SettingsPage


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
        self.borrowers_page = BorrowersPage()
        self.reports_page = self.create_placeholder("Reports", "📊 Generate usage reports")
        self.settings_page = SettingsPage()

        # Add pages to stack
        self.content_stack.addWidget(self.dashboard_page)    # Index 0
        self.content_stack.addWidget(self.inventory_page)    # Index 1
        self.content_stack.addWidget(self.requisitions_page) # Index 2
        self.content_stack.addWidget(self.borrowers_page)    # Index 3
        self.content_stack.addWidget(self.reports_page)      # Index 4
        self.content_stack.addWidget(self.settings_page)     # Index 5

        # Connect navigation
        self.nav_panel.page_changed.connect(self.on_page_changed)

        print("Laboratory Inventory Application ready")

    def on_page_changed(self, page_index: int):
        """Handle page changes and refresh page data."""
        try:
            # Switch to the requested page
            self.content_stack.setCurrentIndex(page_index)

            # Refresh the page data when switching
            if page_index == 0 and hasattr(self.dashboard_page, 'refresh_data'):  # Dashboard
                self.dashboard_page.refresh_data()
                print("Refreshed dashboard data")
            elif page_index == 1 and hasattr(self.inventory_page, 'refresh_data'):  # Inventory
                self.inventory_page.refresh_data()
                print("Refreshed inventory data")
            elif page_index == 2 and hasattr(self.requisitions_page, 'refresh_data'):  # Requisitions
                self.requisitions_page.refresh_data()
                print("Refreshed requisitions data")
            elif page_index == 3 and hasattr(self.borrowers_page, 'refresh_data'):  # Borrowers
                self.borrowers_page.refresh_data()
                print("Refreshed borrowers data")

        except Exception as e:
            print(f"Failed to change page to {page_index}: {e}")

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
