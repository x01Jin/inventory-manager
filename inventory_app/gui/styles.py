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

            /* Global focus outline suppression - eliminates striped square focus rectangles */
            * {{
                outline: none;
            }}

            *:focus {{
                outline: none;
            }}

            QWidget:focus {{
                outline: none;
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

            /* Table item focus suppression */
            QTableWidget::item:focus {{
                outline: none;
                border: none;
            }}

            QTableWidget:focus {{
                outline: none;
            }}

            /* Table Headers */
            QHeaderView {{
                background-color: {DarkTheme.SECONDARY_DARK};
            }}

            QHeaderView::section {{
                background-color: {DarkTheme.SECONDARY_DARK};
                color: {DarkTheme.TEXT_PRIMARY};
                padding: 8px;
                border: 1px solid {DarkTheme.BORDER_COLOR};
                font-weight: bold;
                font-size: {DarkTheme.FONT_SIZE_NORMAL}pt;
            }}

            QHeaderView::section:vertical {{
                background-color: {DarkTheme.SECONDARY_DARK};
                color: {DarkTheme.TEXT_SECONDARY};
                padding: 4px;
                border: 1px solid {DarkTheme.BORDER_COLOR};
                font-size: {DarkTheme.FONT_SIZE_NORMAL}pt;
                max-width: 40px;
            }}

            /* Corner button (select all) */
            QTableWidget QTableCornerButton::section {{
                background-color: {DarkTheme.SECONDARY_DARK};
                border: 1px solid {DarkTheme.BORDER_COLOR};
            }}

            /* Labels - Global styling to prevent borders */
            QLabel {{
                color: {DarkTheme.TEXT_PRIMARY};
                padding: 0px;
                margin: 0px;
                border: none;
                border-width: 0px;
                border-style: none;
                border-radius: 0px;
                background-color: transparent;
                background: transparent;
                outline: none;
                font-size: {DarkTheme.FONT_SIZE_NORMAL}pt;
            }}

            /* Ensure all QLabel variants have no borders */
            QLabel::item {{
                border: none;
                background-color: transparent;
            }}

            QLabel:disabled {{
                border: none;
                background-color: transparent;
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

            /* Tab widgets */
            QTabWidget {{
                background-color: {DarkTheme.PRIMARY_DARK};
                border: 1px solid {DarkTheme.BORDER_COLOR};
                border-radius: 6px;
            }}

            QTabWidget::pane {{
                border: 1px solid {DarkTheme.BORDER_COLOR};
                border-radius: 4px;
                background-color: {DarkTheme.SECONDARY_DARK};
                top: -1px;
            }}

            QTabBar {{
                background-color: {DarkTheme.SECONDARY_DARK};
                border-bottom: 1px solid {DarkTheme.BORDER_COLOR};
            }}

            QTabBar::tab {{
                background-color: {DarkTheme.SECONDARY_DARK};
                color: {DarkTheme.TEXT_SECONDARY};
                border: 1px solid {DarkTheme.BORDER_COLOR};
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 8px 16px;
                margin-right: 2px;
                font-size: {DarkTheme.FONT_SIZE_NORMAL}pt;
                font-weight: 500;
            }}

            QTabBar::tab:selected {{
                background-color: {DarkTheme.ACCENT_COLOR};
                color: {DarkTheme.TEXT_PRIMARY};
                border-color: {DarkTheme.ACCENT_COLOR};
            }}

            QTabBar::tab:hover {{
                background-color: {DarkTheme.ACCENT_HOVER};
                color: {DarkTheme.TEXT_PRIMARY};
                border-color: {DarkTheme.ACCENT_HOVER};
            }}

            QTabBar::tab:!selected {{
                margin-top: 2px;
            }}

            /* Date/Time widgets */
            QDateEdit {{
                background-color: {DarkTheme.SECONDARY_DARK};
                color: {DarkTheme.TEXT_PRIMARY};
                border: 1px solid {DarkTheme.BORDER_COLOR};
                border-radius: 6px;
                padding: 6px 8px;
                font-size: {DarkTheme.FONT_SIZE_NORMAL}pt;
                min-width: 100px;
            }}

            QDateEdit:hover {{
                border-color: {DarkTheme.ACCENT_HOVER};
            }}

            QDateEdit:focus {{
                border-color: {DarkTheme.ACCENT_COLOR};
            }}

            QDateEdit::drop-down {{
                border: none;
                width: 20px;
            }}

            QDateEdit::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid {DarkTheme.TEXT_SECONDARY};
                margin-right: 4px;
            }}

            QDateEdit::down-arrow:hover {{
                border-top-color: {DarkTheme.ACCENT_COLOR};
            }}

            /* DateTime Edit widgets */
            QDateTimeEdit {{
                background-color: {DarkTheme.SECONDARY_DARK};
                color: {DarkTheme.TEXT_PRIMARY};
                border: 1px solid {DarkTheme.BORDER_COLOR};
                border-radius: 6px;
                padding: 6px 8px;
                font-size: {DarkTheme.FONT_SIZE_NORMAL}pt;
                min-width: 140px;
            }}

            QDateTimeEdit:hover {{
                border-color: {DarkTheme.ACCENT_HOVER};
            }}

            QDateTimeEdit:focus {{
                border-color: {DarkTheme.ACCENT_COLOR};
            }}

            QDateTimeEdit::drop-down {{
                border: none;
                width: 20px;
            }}

            QDateTimeEdit::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid {DarkTheme.TEXT_SECONDARY};
                margin-right: 4px;
            }}

            QDateTimeEdit::down-arrow:hover {{
                border-top-color: {DarkTheme.ACCENT_COLOR};
            }}

            /* Calendar widget */
            QCalendarWidget {{
                background-color: {DarkTheme.SECONDARY_DARK};
                color: {DarkTheme.TEXT_PRIMARY};
                border: 1px solid {DarkTheme.BORDER_COLOR};
                border-radius: 6px;
            }}

            QCalendarWidget QWidget {{
                background-color: {DarkTheme.SECONDARY_DARK};
                color: {DarkTheme.TEXT_PRIMARY};
            }}

            QCalendarWidget QAbstractItemView {{
                background-color: {DarkTheme.SECONDARY_DARK};
                selection-background-color: {DarkTheme.ACCENT_COLOR};
                selection-color: {DarkTheme.TEXT_PRIMARY};
                border: none;
            }}

            QCalendarWidget QAbstractItemView:enabled {{
                color: {DarkTheme.TEXT_PRIMARY};
            }}

            QCalendarWidget QAbstractItemView:disabled {{
                color: {DarkTheme.TEXT_MUTED};
            }}

            /* Calendar navigation */
            QCalendarWidget QToolButton {{
                background-color: {DarkTheme.SECONDARY_DARK};
                color: {DarkTheme.TEXT_PRIMARY};
                border: none;
                border-radius: 4px;
                padding: 4px;
                font-size: {DarkTheme.FONT_SIZE_NORMAL}pt;
            }}

            QCalendarWidget QToolButton:hover {{
                background-color: {DarkTheme.ACCENT_HOVER};
                color: {DarkTheme.TEXT_PRIMARY};
            }}

            /* Calendar header */
            QCalendarWidget #qt_calendar_calendarview {{
                background-color: {DarkTheme.SECONDARY_DARK};
                border: none;
            }}

            /* Day names header */
            QCalendarWidget QWidget#qt_calendar_navigationbar {{
                background-color: {DarkTheme.PRIMARY_DARK};
                border-bottom: 1px solid {DarkTheme.BORDER_COLOR};
            }}

            /* Spin boxes */
            QSpinBox {{
                background-color: {DarkTheme.SECONDARY_DARK};
                color: {DarkTheme.TEXT_PRIMARY};
                border: 1px solid {DarkTheme.BORDER_COLOR};
                border-radius: 6px;
                padding: 6px 8px;
                font-size: {DarkTheme.FONT_SIZE_NORMAL}pt;
                min-width: 60px;
            }}

            QSpinBox:hover {{
                border-color: {DarkTheme.ACCENT_HOVER};
            }}

            QSpinBox:focus {{
                border-color: {DarkTheme.ACCENT_COLOR};
            }}

            QSpinBox::up-button, QSpinBox::down-button {{
                background-color: {DarkTheme.SECONDARY_DARK};
                border: none;
                width: 16px;
            }}

            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background-color: {DarkTheme.ACCENT_HOVER};
            }}

            QSpinBox::up-arrow {{
                image: none;
                border-left: 3px solid transparent;
                border-right: 3px solid transparent;
                border-bottom: 3px solid {DarkTheme.TEXT_SECONDARY};
                margin-bottom: 2px;
            }}

            QSpinBox::down-arrow {{
                image: none;
                border-left: 3px solid transparent;
                border-right: 3px solid transparent;
                border-top: 3px solid {DarkTheme.TEXT_SECONDARY};
                margin-top: 2px;
            }}

            QSpinBox::up-arrow:hover {{
                border-bottom-color: {DarkTheme.ACCENT_COLOR};
            }}

            QSpinBox::down-arrow:hover {{
                border-top-color: {DarkTheme.ACCENT_COLOR};
            }}

            /* Text input widgets */
            QLineEdit {{
                background-color: {DarkTheme.SECONDARY_DARK};
                color: {DarkTheme.TEXT_PRIMARY};
                border: 1px solid {DarkTheme.BORDER_COLOR};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: {DarkTheme.FONT_SIZE_NORMAL}pt;
                selection-background-color: {DarkTheme.ACCENT_COLOR};
                selection-color: {DarkTheme.TEXT_PRIMARY};
            }}

            QLineEdit:hover {{
                border-color: {DarkTheme.ACCENT_HOVER};
            }}

            QLineEdit:focus {{
                border-color: {DarkTheme.ACCENT_COLOR};
                background-color: {DarkTheme.PRIMARY_DARK};
            }}

            QLineEdit:read-only {{
                background-color: {DarkTheme.SECONDARY_DARK};
                color: {DarkTheme.TEXT_SECONDARY};
                border-color: {DarkTheme.BORDER_COLOR};
            }}

            /* Combo boxes */
            QComboBox {{
                background-color: {DarkTheme.SECONDARY_DARK};
                color: {DarkTheme.TEXT_PRIMARY};
                border: 1px solid {DarkTheme.BORDER_COLOR};
                border-radius: 6px;
                padding: 6px 8px;
                font-size: {DarkTheme.FONT_SIZE_NORMAL}pt;
                min-width: 100px;
            }}

            QComboBox:hover {{
                border-color: {DarkTheme.ACCENT_HOVER};
            }}

            QComboBox:focus {{
                border-color: {DarkTheme.ACCENT_COLOR};
            }}

            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}

            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid {DarkTheme.TEXT_SECONDARY};
                margin-right: 4px;
            }}

            QComboBox::down-arrow:hover {{
                border-top-color: {DarkTheme.ACCENT_COLOR};
            }}

            QComboBox QAbstractItemView {{
                background-color: {DarkTheme.SECONDARY_DARK};
                color: {DarkTheme.TEXT_PRIMARY};
                border: 1px solid {DarkTheme.BORDER_COLOR};
                border-radius: 4px;
                selection-background-color: {DarkTheme.ACCENT_COLOR};
                selection-color: {DarkTheme.TEXT_PRIMARY};
            }}

            QComboBox QAbstractItemView::item {{
                padding: 8px;
                border-bottom: 1px solid {DarkTheme.BORDER_COLOR};
            }}

            QComboBox QAbstractItemView::item:hover {{
                background-color: {DarkTheme.ACCENT_HOVER};
            }}

            /* Text areas */
            QTextEdit {{
                background-color: {DarkTheme.SECONDARY_DARK};
                color: {DarkTheme.TEXT_PRIMARY};
                border: 1px solid {DarkTheme.BORDER_COLOR};
                border-radius: 6px;
                padding: 8px;
                font-size: {DarkTheme.FONT_SIZE_NORMAL}pt;
                selection-background-color: {DarkTheme.ACCENT_COLOR};
                selection-color: {DarkTheme.TEXT_PRIMARY};
            }}

            QTextEdit:hover {{
                border-color: {DarkTheme.ACCENT_HOVER};
            }}

            QTextEdit:focus {{
                border-color: {DarkTheme.ACCENT_COLOR};
                background-color: {DarkTheme.PRIMARY_DARK};
            }}

            /* Plain text edit */
            QPlainTextEdit {{
                background-color: {DarkTheme.SECONDARY_DARK};
                color: {DarkTheme.TEXT_PRIMARY};
                border: 1px solid {DarkTheme.BORDER_COLOR};
                border-radius: 6px;
                padding: 8px;
                font-size: {DarkTheme.FONT_SIZE_NORMAL}pt;
                selection-background-color: {DarkTheme.ACCENT_COLOR};
                selection-color: {DarkTheme.TEXT_PRIMARY};
            }}

            QPlainTextEdit:hover {{
                border-color: {DarkTheme.ACCENT_HOVER};
            }}

            QPlainTextEdit:focus {{
                border-color: {DarkTheme.ACCENT_COLOR};
                background-color: {DarkTheme.PRIMARY_DARK};
            }}
        """
