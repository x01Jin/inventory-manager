"""
Dark theme styling for the inventory application GUI.
Provides consistent styling and theming.
"""

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor


class DarkTheme:
    """Dark theme color palette and styling constants."""

    # Colors
    PRIMARY_DARK = "#1e1e2e"
    SECONDARY_DARK = "#2a2a3c"
    ACCENT_COLOR = "#7c3aed"
    ACCENT_HOVER = "#8b5cf6"
    TEXT_PRIMARY = "#ffffff"
    TEXT_SECONDARY = "#a1a1aa"
    TEXT_MUTED = "#71717a"
    BORDER_COLOR = "#3f3f46"
    SUCCESS_COLOR = "#10b981"
    WARNING_COLOR = "#f59e0b"
    ERROR_COLOR = "#ef4444"
    INFO_COLOR = "#06b6d4"

    # Fonts
    FONT_FAMILY = "Segoe UI"
    FONT_SIZE_NORMAL = 10
    FONT_SIZE_LARGE = 12
    FONT_SIZE_TITLE = 16
    FONT_SIZE_HEADER = 20

    @staticmethod
    def apply_dark_theme(app: QApplication):
        """Apply dark theme to the entire application."""
        palette = QPalette()

        # Window colors
        palette.setColor(QPalette.ColorRole.Window, QColor(DarkTheme.PRIMARY_DARK))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(DarkTheme.TEXT_PRIMARY))
        palette.setColor(QPalette.ColorRole.Base, QColor(DarkTheme.SECONDARY_DARK))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(DarkTheme.PRIMARY_DARK))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(DarkTheme.SECONDARY_DARK))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(DarkTheme.TEXT_PRIMARY))

        # Text colors
        palette.setColor(QPalette.ColorRole.Text, QColor(DarkTheme.TEXT_PRIMARY))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(DarkTheme.TEXT_PRIMARY))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(DarkTheme.TEXT_PRIMARY))
        palette.setColor(QPalette.ColorRole.Link, QColor(DarkTheme.ACCENT_COLOR))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(DarkTheme.ACCENT_COLOR))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(DarkTheme.TEXT_PRIMARY))

        # Button colors
        palette.setColor(QPalette.ColorRole.Button, QColor(DarkTheme.SECONDARY_DARK))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(DarkTheme.TEXT_PRIMARY))

        # Other elements
        palette.setColor(QPalette.ColorRole.Light, QColor(DarkTheme.BORDER_COLOR))
        palette.setColor(QPalette.ColorRole.Midlight, QColor(DarkTheme.BORDER_COLOR))
        palette.setColor(QPalette.ColorRole.Dark, QColor(DarkTheme.PRIMARY_DARK))
        palette.setColor(QPalette.ColorRole.Mid, QColor(DarkTheme.SECONDARY_DARK))
        palette.setColor(QPalette.ColorRole.Shadow, QColor(DarkTheme.BORDER_COLOR))

        app.setPalette(palette)

        # Set comprehensive stylesheet
        app.setStyleSheet(DarkTheme.get_stylesheet())

    @staticmethod
    def get_stylesheet():
        """Get the complete stylesheet for dark theme."""
        return f"""
            /* Global styles */
            QWidget {{
                background-color: {DarkTheme.PRIMARY_DARK};
                color: {DarkTheme.TEXT_PRIMARY};
                font-family: {DarkTheme.FONT_FAMILY};
                font-size: {DarkTheme.FONT_SIZE_NORMAL}pt;
            }}

            /* Buttons */
            QPushButton {{
                background-color: {DarkTheme.SECONDARY_DARK};
                border: 1px solid {DarkTheme.BORDER_COLOR};
                border-radius: 6px;
                padding: 8px 16px;
                font-size: {DarkTheme.FONT_SIZE_NORMAL}pt;
                font-weight: 500;
            }}

            QPushButton:hover {{
                background-color: {DarkTheme.ACCENT_HOVER};
                border-color: {DarkTheme.ACCENT_COLOR};
            }}

            QPushButton:pressed {{
                background-color: {DarkTheme.ACCENT_COLOR};
            }}

            QPushButton:disabled {{
                background-color: {DarkTheme.SECONDARY_DARK};
                color: {DarkTheme.TEXT_MUTED};
                border-color: {DarkTheme.BORDER_COLOR};
            }}

            /* Group boxes */
            QGroupBox {{
                font-size: {DarkTheme.FONT_SIZE_LARGE}pt;
                font-weight: bold;
                border: 2px solid {DarkTheme.BORDER_COLOR};
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 10px;
            }}

            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: {DarkTheme.TEXT_PRIMARY};
                font-weight: bold;
            }}

            /* Tables */
            QTableWidget {{
                gridline-color: {DarkTheme.BORDER_COLOR};
                background-color: {DarkTheme.SECONDARY_DARK};
                border: 1px solid {DarkTheme.BORDER_COLOR};
                border-radius: 6px;
                selection-background-color: {DarkTheme.ACCENT_COLOR};
            }}

            QTableWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {DarkTheme.BORDER_COLOR};
            }}

            QTableWidget::item:selected {{
                background-color: {DarkTheme.ACCENT_COLOR};
            }}

            QHeaderView::section {{
                background-color: {DarkTheme.SECONDARY_DARK};
                color: {DarkTheme.TEXT_PRIMARY};
                padding: 8px;
                border: 1px solid {DarkTheme.BORDER_COLOR};
                font-weight: bold;
            }}

            /* Labels */
            QLabel {{
                color: {DarkTheme.TEXT_PRIMARY};
            }}

            /* Frames */
            QFrame {{
                border: 1px solid {DarkTheme.BORDER_COLOR};
                border-radius: 6px;
            }}

            /* Progress bars */
            QProgressBar {{
                border: 1px solid {DarkTheme.BORDER_COLOR};
                border-radius: 4px;
                text-align: center;
                background-color: {DarkTheme.SECONDARY_DARK};
            }}

            QProgressBar::chunk {{
                background-color: {DarkTheme.SUCCESS_COLOR};
                border-radius: 2px;
            }}

            /* Status bar */
            QStatusBar {{
                background-color: {DarkTheme.SECONDARY_DARK};
                border-top: 1px solid {DarkTheme.BORDER_COLOR};
            }}

            QStatusBar QLabel {{
                color: {DarkTheme.TEXT_SECONDARY};
            }}
        """
