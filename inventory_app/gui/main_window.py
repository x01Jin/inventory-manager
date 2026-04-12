"""
Main window for the Laboratory Inventory Application.
Simple and clean composition using navigation and dashboard.
"""

import sys
import time
from typing import Any
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QStackedWidget,
    QLabel,
    QVBoxLayout,
)
from PyQt6.QtCore import QTimer

from inventory_app.gui.styles import DarkTheme, ThemeManager
from inventory_app.gui.navigation import NavigationPanel
from inventory_app.gui.dashboard.dashboard_page import DashboardPage
from inventory_app.utils.logger import logger


class MainWindow(QMainWindow):
    """Main application window with theme support."""

    PAGE_REFRESH_INTERVAL = 30.0
    REFRESH_DEBOUNCE_DELAY = 500

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Laboratory Inventory Manager (L.I.M.)")
        self.setMinimumSize(1280, 720)

        self._page_refresh_times = {}
        self._refresh_debounce_timer = QTimer()
        self._refresh_debounce_timer.setSingleShot(True)
        self._refresh_debounce_timer.timeout.connect(self._execute_debounced_refresh)
        self._pending_page_index = None

        # Apply theme based on saved preference
        app_instance = QApplication.instance()
        if app_instance and isinstance(app_instance, QApplication):
            theme_manager = ThemeManager.instance()
            theme_manager.apply_theme(app_instance)

        # Center the window
        self.center_window()

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

        # Keep dashboard eager, create other pages only when first opened.
        self.dashboard_page = DashboardPage()
        self.inventory_page = None
        self.requisitions_page = None
        self.requesters_page = None
        self.reports_page = None
        self.settings_page = None
        self.help_page = None

        # Add pages to stack
        self.content_stack.addWidget(self.dashboard_page)  # Index 0
        self.content_stack.addWidget(
            self.create_placeholder("Inventory", "Loading inventory page...")
        )  # Index 1
        self.content_stack.addWidget(
            self.create_placeholder("Requisitions", "Loading requisitions page...")
        )  # Index 2
        self.content_stack.addWidget(
            self.create_placeholder("Requesters", "Loading requesters page...")
        )  # Index 3
        self.content_stack.addWidget(
            self.create_placeholder("Reports", "Loading reports page...")
        )  # Index 4
        self.content_stack.addWidget(
            self.create_placeholder("Settings", "Loading settings page...")
        )  # Index 5
        self.content_stack.addWidget(
            self.create_placeholder("Help", "Loading help page...")
        )  # Index 6

        self._page_instances: dict[int, Any] = {
            0: self.dashboard_page,
        }

        # Connect navigation
        self.nav_panel.page_changed.connect(self.on_page_changed)

    def _create_page_for_index(self, page_index: int):
        """Create page object for stack index on first use."""
        if page_index == 1:
            from inventory_app.gui.inventory.inventory_page import InventoryPage

            self.inventory_page = InventoryPage()
            return self.inventory_page
        if page_index == 2:
            from inventory_app.gui.requisitions.requisitions_page import (
                RequisitionsPage,
            )

            self.requisitions_page = RequisitionsPage()
            return self.requisitions_page
        if page_index == 3:
            from inventory_app.gui.requesters.requesters_page import RequestersPage

            self.requesters_page = RequestersPage()
            return self.requesters_page
        if page_index == 4:
            from inventory_app.gui.reports.reports_page import ReportsPage

            self.reports_page = ReportsPage()
            return self.reports_page
        if page_index == 5:
            from inventory_app.gui.settings.settings_page import SettingsPage

            self.settings_page = SettingsPage()
            return self.settings_page
        if page_index == 6:
            from inventory_app.gui.help.help_page import HelpPage

            self.help_page = HelpPage()
            return self.help_page
        return self.dashboard_page

    def _ensure_page_loaded(self, page_index: int) -> None:
        """Replace placeholder with real page on first navigation."""
        if page_index in self._page_instances:
            return

        page = self._create_page_for_index(page_index)
        placeholder = self.content_stack.widget(page_index)
        self.content_stack.removeWidget(placeholder)
        if placeholder is not None:
            placeholder.deleteLater()
        self.content_stack.insertWidget(page_index, page)
        self._page_instances[page_index] = page
        logger.info(f"Lazily initialized page at index {page_index}")

    def _get_page_instance(self, page_index: int):
        """Get or create page instance for requested index."""
        self._ensure_page_loaded(page_index)
        return self._page_instances.get(page_index)

    def center_window(self):
        """Center the window on the screen."""
        from PyQt6.QtGui import QGuiApplication

        screen = QGuiApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            window_geometry = self.frameGeometry()
            center_point = screen_geometry.center()
            window_geometry.moveCenter(center_point)
            self.move(window_geometry.topLeft())

    def _is_page_data_stale(self, page_index: int) -> bool:
        """Check if page data is stale and needs refresh."""
        current_time = time.monotonic()
        last_refresh = self._page_refresh_times.get(page_index)

        if last_refresh is None:
            return True

        return (current_time - last_refresh) > self.PAGE_REFRESH_INTERVAL

    def _mark_page_refreshed(self, page_index: int) -> None:
        """Mark a page as refreshed."""
        self._page_refresh_times[page_index] = time.monotonic()

    def _execute_debounced_refresh(self) -> None:
        """Execute the debounced refresh for the pending page."""
        if self._pending_page_index is not None:
            self._refresh_page_data(self._pending_page_index)
            self._pending_page_index = None

    def _refresh_page_data(self, page_index: int) -> None:
        """Refresh page data if needed."""
        page = self._get_page_instance(page_index)
        if page is None:
            return

        if page_index == 0 and hasattr(page, "refresh_data"):
            page.refresh_data()
            self._mark_page_refreshed(page_index)
            logger.info("Refreshed dashboard data")
        elif page_index == 1 and hasattr(page, "refresh_data"):
            page.refresh_data()
            self._mark_page_refreshed(page_index)
            logger.info("Refreshed inventory data")
        elif page_index == 2 and hasattr(page, "refresh_data"):
            page.refresh_data()
            self._mark_page_refreshed(page_index)
            logger.info("Refreshed requisitions data")
        elif page_index == 3 and hasattr(page, "refresh_data"):
            page.refresh_data()
            self._mark_page_refreshed(page_index)
            logger.info("Refreshed requesters data")
        elif page_index == 4 and hasattr(page, "refresh_data"):
            try:
                page.refresh_data()
                self._mark_page_refreshed(page_index)
                logger.info("Refreshed reports data")
            except Exception:
                logger.exception("Failed to refresh reports data")
        elif page_index == 5 and hasattr(page, "refresh_data"):
            try:
                page.refresh_data()
                self._mark_page_refreshed(page_index)
                logger.info("Refreshed settings reference data")
            except Exception:
                logger.exception("Failed to refresh settings reference data")
        elif page_index == 6 and hasattr(page, "load_current_tab"):
            try:
                load_current_tab = getattr(page, "load_current_tab", None)
                if callable(load_current_tab):
                    load_current_tab()
                self._mark_page_refreshed(page_index)
                logger.info("Refreshed help tab content")
            except Exception:
                logger.exception("Failed to refresh help tab content")

    def on_page_changed(self, page_index: int):
        """Handle page changes and refresh page data with caching and throttling."""
        try:
            self._ensure_page_loaded(page_index)
            self.content_stack.setCurrentIndex(page_index)

            if self._refresh_debounce_timer.isActive():
                self._refresh_debounce_timer.stop()

            if self._is_page_data_stale(page_index):
                self._pending_page_index = page_index
                self._refresh_debounce_timer.start(self.REFRESH_DEBOUNCE_DELAY)

        except Exception as e:
            logger.error(f"Failed to change page to {page_index}: {e}")

    def create_placeholder(self, title: str, description: str):
        """Create placeholder page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)

        header = QLabel(title)
        header.setStyleSheet(
            f"font-size: {DarkTheme.FONT_SIZE_TITLE}pt; font-weight: bold; color: {DarkTheme.TEXT_PRIMARY};"
        )
        layout.addWidget(header)

        desc = QLabel(description)
        desc.setStyleSheet(
            f"color: {DarkTheme.TEXT_SECONDARY}; font-size: {DarkTheme.FONT_SIZE_LARGE}pt;"
        )
        layout.addWidget(desc)

        placeholder = QLabel("🚧 Under development")
        placeholder.setStyleSheet(
            f"color: {DarkTheme.TEXT_MUTED}; font-style: italic; padding: 50px; text-align: center;"
        )
        layout.addWidget(placeholder)

        layout.addStretch()
        return page


def main():
    """Main application entry point."""
    try:
        app = QApplication(sys.argv)
        window = MainWindow()
        window.showMaximized()

        logger.info("Laboratory Inventory Application started successfully")
        return app.exec()

    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
