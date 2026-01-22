"""
Theme styling for the inventory application GUI.
Provides consistent styling and theming with support for dark and light modes.
"""

import json
import os
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor


def get_preferences_path() -> str:
    """Get the path to the preferences file in the user's config directory."""
    if sys.platform == "win32":
        # Windows: %APPDATA%/LIM/preferences.json
        base_dir = os.environ.get("APPDATA", os.path.expanduser("~"))
        config_dir = os.path.join(base_dir, "LIM")
    elif sys.platform == "darwin":
        # macOS: ~/Library/Application Support/LIM/preferences.json
        config_dir = os.path.join(
            os.path.expanduser("~"), "Library", "Application Support", "LIM"
        )
    else:
        # Linux/Unix: ~/.config/LIM/preferences.json
        config_dir = os.path.join(
            os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")), "LIM"
        )

    # Create directory if it doesn't exist
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, "preferences.json")


# Theme preference storage path
PREFERENCES_FILE = get_preferences_path()


class ThemeManager:
    """Manages theme switching and persistence."""

    _instance = None
    _current_theme = "dark"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._current_theme = self.load_preference()

    @classmethod
    def instance(cls):
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def current_theme(self):
        return self._current_theme

    @current_theme.setter
    def current_theme(self, value):
        if value in ("dark", "light") and value != self._current_theme:
            self._current_theme = value
            self.save_preference(value)

    def load_preference(self) -> str:
        """Load theme preference from file."""
        try:
            if os.path.exists(PREFERENCES_FILE):
                with open(PREFERENCES_FILE, "r") as f:
                    data = json.load(f)
                    return data.get("theme", "dark")
        except Exception:
            pass
        return "dark"

    def save_preference(self, theme: str):
        """Save theme preference to file."""
        try:
            data = {}
            if os.path.exists(PREFERENCES_FILE):
                with open(PREFERENCES_FILE, "r") as f:
                    data = json.load(f)
            data["theme"] = theme
            with open(PREFERENCES_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def get_current_theme_class(self):
        """Get the current theme class."""
        return LightTheme if self._current_theme == "light" else DarkTheme

    def apply_theme(self, app: QApplication):
        """Apply the current theme to the application."""
        theme_class = self.get_current_theme_class()
        theme_class.apply_theme(app)


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
    RETURNED_COLOR = "#3B82F6"

    # Fonts
    FONT_FAMILY = "Segoe UI"
    FONT_SIZE_NORMAL = 10
    FONT_SIZE_LARGE = 12
    FONT_SIZE_TITLE = 16
    FONT_SIZE_HEADER = 20

    @staticmethod
    def apply_theme(app: QApplication):
        """Apply dark theme to the entire application."""
        DarkTheme.apply_dark_theme(app)

    @staticmethod
    def apply_dark_theme(app: QApplication):
        """Apply dark theme to the entire application."""
        palette = QPalette()

        # Window colors
        palette.setColor(QPalette.ColorRole.Window, QColor(DarkTheme.PRIMARY_DARK))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(DarkTheme.TEXT_PRIMARY))
        palette.setColor(QPalette.ColorRole.Base, QColor(DarkTheme.SECONDARY_DARK))
        palette.setColor(
            QPalette.ColorRole.AlternateBase, QColor(DarkTheme.PRIMARY_DARK)
        )
        palette.setColor(
            QPalette.ColorRole.ToolTipBase, QColor(DarkTheme.SECONDARY_DARK)
        )
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(DarkTheme.TEXT_PRIMARY))

        # Text colors
        palette.setColor(QPalette.ColorRole.Text, QColor(DarkTheme.TEXT_PRIMARY))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(DarkTheme.TEXT_PRIMARY))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(DarkTheme.TEXT_PRIMARY))
        palette.setColor(QPalette.ColorRole.Link, QColor(DarkTheme.ACCENT_COLOR))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(DarkTheme.ACCENT_COLOR))
        palette.setColor(
            QPalette.ColorRole.HighlightedText, QColor(DarkTheme.TEXT_PRIMARY)
        )

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
                padding: 6px 12px;
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
                padding: 4px 8px;
                border_bottom: 1px solid {DarkTheme.BORDER_COLOR};
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
                padding: 2px 4px;
                border: 1px solid {DarkTheme.BORDER_COLOR};
                font-weight: bold;
                font-size: {DarkTheme.FONT_SIZE_NORMAL}pt;
            }}

            QHeaderView::down-arrow, QHeaderView::up-arrow {{
                image: none;
                width: 0px;
                height: 0px;
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
                border: none !important;
                background-color: transparent !important;
            }}

            /* Additional QLabel border removal with higher specificity */
            QWidget QLabel {{
                border: none !important;
                background-color: transparent !important;
            }}

            * QLabel {{
                border: none !important;
                background-color: transparent !important;
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
                padding: 4px 8px;
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
                padding: 4px 8px;
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
                padding: 3px 3px;
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
                padding: 4px 8px;
                font-size: {DarkTheme.FONT_SIZE_NORMAL}pt;
            }}

            QComboBox:hover {{
                border-color: {DarkTheme.ACCENT_HOVER};
            }}

            QComboBox:focus {{
                border-color: {DarkTheme.ACCENT_COLOR};
            }}

            QComboBox::drop-down {{
                border: none;
                width: 0px;
            }}

            QComboBox::down-arrow {{
                image: none;
                width: 0px;
                height: 0px;
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
                padding: 4px 8px;
                color: {DarkTheme.TEXT_PRIMARY};
                border-bottom: 1px solid {DarkTheme.BORDER_COLOR};
            }}

            QComboBox QAbstractItemView::item:hover {{
                background-color: {DarkTheme.ACCENT_HOVER};
                color: {DarkTheme.TEXT_PRIMARY};
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

            /* Tooltips */
            QToolTip {{
                background-color: {DarkTheme.SECONDARY_DARK};
                color: {DarkTheme.TEXT_PRIMARY};
                border: 1px solid {DarkTheme.BORDER_COLOR};
                border-radius: 6px;
                padding: 8px;
                font-size: {DarkTheme.FONT_SIZE_NORMAL}pt;
                font-family: {DarkTheme.FONT_FAMILY};
            }}

            /* List widgets */
            QListWidget {{
                background-color: {DarkTheme.SECONDARY_DARK};
                color: {DarkTheme.TEXT_PRIMARY};
                border: 1px solid {DarkTheme.BORDER_COLOR};
                border-radius: 6px;
            }}

            QListWidget::item {{
                padding: 4px 8px;
                color: {DarkTheme.TEXT_PRIMARY};
                border_bottom: 1px solid {DarkTheme.BORDER_COLOR};
            }}

            QListWidget::item:selected {{
                background-color: {DarkTheme.ACCENT_COLOR};
                color: {DarkTheme.TEXT_PRIMARY};
            }}

            QListWidget::item:hover {{
                background-color: {DarkTheme.ACCENT_HOVER};
                color: {DarkTheme.TEXT_PRIMARY};
            }}
        """


class LightTheme:
    """Light theme color palette and styling constants with green accent."""

    # Colors - Light mode with green accent
    PRIMARY_DARK = "#ffffff"  # White background
    SECONDARY_DARK = "#f4f4f5"  # Light gray for secondary areas
    ACCENT_COLOR = "#16a34a"  # Green accent (similar to SUCCESS_COLOR but brighter)
    ACCENT_HOVER = "#22c55e"  # Lighter green for hover
    TEXT_PRIMARY = "#18181b"  # Near black for primary text
    TEXT_SECONDARY = "#52525b"  # Dark gray for secondary text
    TEXT_MUTED = "#a1a1aa"  # Muted gray
    BORDER_COLOR = "#d4d4d8"  # Light border
    SUCCESS_COLOR = "#10b981"  # Keep success green
    WARNING_COLOR = "#f59e0b"  # Keep warning orange
    ERROR_COLOR = "#ef4444"  # Keep error red
    INFO_COLOR = "#06b6d4"  # Keep info cyan
    RETURNED_COLOR = "#3B82F6"  # Keep returned blue

    # Fonts (same as dark theme)
    FONT_FAMILY = "Segoe UI"
    FONT_SIZE_NORMAL = 10
    FONT_SIZE_LARGE = 12
    FONT_SIZE_TITLE = 16
    FONT_SIZE_HEADER = 20

    @staticmethod
    def apply_theme(app: QApplication):
        """Apply light theme to the entire application."""
        LightTheme.apply_light_theme(app)

    @staticmethod
    def apply_light_theme(app: QApplication):
        """Apply light theme to the entire application."""
        palette = QPalette()

        # Window colors
        palette.setColor(QPalette.ColorRole.Window, QColor(LightTheme.PRIMARY_DARK))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(LightTheme.TEXT_PRIMARY))
        palette.setColor(QPalette.ColorRole.Base, QColor(LightTheme.SECONDARY_DARK))
        palette.setColor(
            QPalette.ColorRole.AlternateBase, QColor(LightTheme.PRIMARY_DARK)
        )
        palette.setColor(
            QPalette.ColorRole.ToolTipBase, QColor(LightTheme.SECONDARY_DARK)
        )
        palette.setColor(
            QPalette.ColorRole.ToolTipText, QColor(LightTheme.TEXT_PRIMARY)
        )

        # Text colors
        palette.setColor(QPalette.ColorRole.Text, QColor(LightTheme.TEXT_PRIMARY))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(LightTheme.TEXT_PRIMARY))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(LightTheme.TEXT_PRIMARY))
        palette.setColor(QPalette.ColorRole.Link, QColor(LightTheme.ACCENT_COLOR))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(LightTheme.ACCENT_COLOR))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))

        # Button colors
        palette.setColor(QPalette.ColorRole.Button, QColor(LightTheme.SECONDARY_DARK))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(LightTheme.TEXT_PRIMARY))

        # Other elements
        palette.setColor(QPalette.ColorRole.Light, QColor(LightTheme.BORDER_COLOR))
        palette.setColor(QPalette.ColorRole.Midlight, QColor(LightTheme.BORDER_COLOR))
        palette.setColor(QPalette.ColorRole.Dark, QColor(LightTheme.PRIMARY_DARK))
        palette.setColor(QPalette.ColorRole.Mid, QColor(LightTheme.SECONDARY_DARK))
        palette.setColor(QPalette.ColorRole.Shadow, QColor(LightTheme.BORDER_COLOR))

        app.setPalette(palette)

        # Set comprehensive stylesheet
        app.setStyleSheet(LightTheme.get_stylesheet())

    @staticmethod
    def get_stylesheet():
        """Get the complete stylesheet for light theme."""
        return f"""
            /* Global styles */
            QWidget {{
                background-color: {LightTheme.PRIMARY_DARK};
                color: {LightTheme.TEXT_PRIMARY};
                font-family: {LightTheme.FONT_FAMILY};
                font-size: {LightTheme.FONT_SIZE_NORMAL}pt;
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
                background-color: {LightTheme.SECONDARY_DARK};
                border: 1px solid {LightTheme.BORDER_COLOR};
                border-radius: 6px;
                padding: 6px 12px;
                font-size: {LightTheme.FONT_SIZE_NORMAL}pt;
                font-weight: 500;
            }}

            QPushButton:hover {{
                background-color: {LightTheme.ACCENT_HOVER};
                border-color: {LightTheme.ACCENT_COLOR};
                color: #ffffff;
            }}

            QPushButton:pressed {{
                background-color: {LightTheme.ACCENT_COLOR};
                color: #ffffff;
            }}

            QPushButton:disabled {{
                background-color: {LightTheme.SECONDARY_DARK};
                color: {LightTheme.TEXT_MUTED};
                border-color: {LightTheme.BORDER_COLOR};
            }}

            /* Group boxes */
            QGroupBox {{
                font-size: {LightTheme.FONT_SIZE_LARGE}pt;
                font-weight: bold;
                border: 2px solid {LightTheme.BORDER_COLOR};
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 10px;
            }}

            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: {LightTheme.TEXT_PRIMARY};
                font-weight: bold;
            }}

            /* Tables */
            QTableWidget {{
                gridline-color: {LightTheme.BORDER_COLOR};
                background-color: {LightTheme.SECONDARY_DARK};
                border: 1px solid {LightTheme.BORDER_COLOR};
                border-radius: 6px;
                selection-background-color: {LightTheme.ACCENT_COLOR};
                selection-color: #ffffff;
            }}

            QTableWidget::item {{
                padding: 4px 8px;
                border_bottom: 1px solid {LightTheme.BORDER_COLOR};
            }}

            QTableWidget::item:selected {{
                background-color: {LightTheme.ACCENT_COLOR};
                color: #ffffff;
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
                background-color: {LightTheme.SECONDARY_DARK};
            }}

            QHeaderView::section {{
                background-color: {LightTheme.SECONDARY_DARK};
                color: {LightTheme.TEXT_PRIMARY};
                padding: 2px 4px;
                border: 1px solid {LightTheme.BORDER_COLOR};
                font-weight: bold;
                font-size: {LightTheme.FONT_SIZE_NORMAL}pt;
            }}

            QHeaderView::down-arrow, QHeaderView::up-arrow {{
                image: none;
                width: 0px;
                height: 0px;
            }}

            QHeaderView::section:vertical {{
                background-color: {LightTheme.SECONDARY_DARK};
                color: {LightTheme.TEXT_SECONDARY};
                padding: 4px;
                border: 1px solid {LightTheme.BORDER_COLOR};
                font-size: {LightTheme.FONT_SIZE_NORMAL}pt;
                max-width: 40px;
            }}

            /* Corner button (select all) */
            QTableWidget QTableCornerButton::section {{
                background-color: {LightTheme.SECONDARY_DARK};
                border: 1px solid {LightTheme.BORDER_COLOR};
            }}

            /* Labels - Global styling to prevent borders */
            QLabel {{
                color: {LightTheme.TEXT_PRIMARY};
                padding: 0px;
                margin: 0px;
                border: none;
                border-width: 0px;
                border-style: none;
                border-radius: 0px;
                background-color: transparent;
                background: transparent;
                outline: none;
                font-size: {LightTheme.FONT_SIZE_NORMAL}pt;
            }}

            /* Ensure all QLabel variants have no borders */
            QLabel::item {{
                border: none;
                background-color: transparent;
            }}

            QLabel:disabled {{
                border: none !important;
                background-color: transparent !important;
            }}

            /* Additional QLabel border removal with higher specificity */
            QWidget QLabel {{
                border: none !important;
                background-color: transparent !important;
            }}

            * QLabel {{
                border: none !important;
                background-color: transparent !important;
            }}

            /* Frames */
            QFrame {{
                border: 1px solid {LightTheme.BORDER_COLOR};
                border-radius: 6px;
            }}

            /* Progress bars */
            QProgressBar {{
                border: 1px solid {LightTheme.BORDER_COLOR};
                border-radius: 4px;
                text-align: center;
                background-color: {LightTheme.SECONDARY_DARK};
            }}

            QProgressBar::chunk {{
                background-color: {LightTheme.SUCCESS_COLOR};
                border-radius: 2px;
            }}

            /* Status bar */
            QStatusBar {{
                background-color: {LightTheme.SECONDARY_DARK};
                border-top: 1px solid {LightTheme.BORDER_COLOR};
            }}

            QStatusBar QLabel {{
                color: {LightTheme.TEXT_SECONDARY};
            }}

            /* Tab widgets */
            QTabWidget {{
                background-color: {LightTheme.PRIMARY_DARK};
                border: 1px solid {LightTheme.BORDER_COLOR};
                border-radius: 6px;
            }}

            QTabWidget::pane {{
                border: 1px solid {LightTheme.BORDER_COLOR};
                border-radius: 4px;
                background-color: {LightTheme.SECONDARY_DARK};
                top: -1px;
            }}

            QTabBar {{
                background-color: {LightTheme.SECONDARY_DARK};
                border-bottom: 1px solid {LightTheme.BORDER_COLOR};
            }}

            QTabBar::tab {{
                background-color: {LightTheme.SECONDARY_DARK};
                color: {LightTheme.TEXT_SECONDARY};
                border: 1px solid {LightTheme.BORDER_COLOR};
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 8px 16px;
                margin-right: 2px;
                font-size: {LightTheme.FONT_SIZE_NORMAL}pt;
                font-weight: 500;
            }}

            QTabBar::tab:selected {{
                background-color: {LightTheme.ACCENT_COLOR};
                color: #ffffff;
                border-color: {LightTheme.ACCENT_COLOR};
            }}

            QTabBar::tab:hover {{
                background-color: {LightTheme.ACCENT_HOVER};
                color: #ffffff;
                border-color: {LightTheme.ACCENT_HOVER};
            }}

            QTabBar::tab:!selected {{
                margin-top: 2px;
            }}

            /* Date/Time widgets */
            QDateEdit {{
                background-color: {LightTheme.SECONDARY_DARK};
                color: {LightTheme.TEXT_PRIMARY};
                border: 1px solid {LightTheme.BORDER_COLOR};
                border-radius: 6px;
                padding: 4px 8px;
                font-size: {LightTheme.FONT_SIZE_NORMAL}pt;
                min-width: 100px;
            }}

            QDateEdit:hover {{
                border-color: {LightTheme.ACCENT_HOVER};
            }}

            QDateEdit:focus {{
                border-color: {LightTheme.ACCENT_COLOR};
            }}

            QDateEdit::drop-down {{
                border: none;
                width: 20px;
            }}

            QDateEdit::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid {LightTheme.TEXT_SECONDARY};
                margin-right: 4px;
            }}

            QDateEdit::down-arrow:hover {{
                border-top-color: {LightTheme.ACCENT_COLOR};
            }}

            /* DateTime Edit widgets */
            QDateTimeEdit {{
                background-color: {LightTheme.SECONDARY_DARK};
                color: {LightTheme.TEXT_PRIMARY};
                border: 1px solid {LightTheme.BORDER_COLOR};
                border-radius: 6px;
                padding: 4px 8px;
                font-size: {LightTheme.FONT_SIZE_NORMAL}pt;
                min-width: 140px;
            }}

            QDateTimeEdit:hover {{
                border-color: {LightTheme.ACCENT_HOVER};
            }}

            QDateTimeEdit:focus {{
                border-color: {LightTheme.ACCENT_COLOR};
            }}

            QDateTimeEdit::drop-down {{
                border: none;
                width: 20px;
            }}

            QDateTimeEdit::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid {LightTheme.TEXT_SECONDARY};
                margin-right: 4px;
            }}

            QDateTimeEdit::down-arrow:hover {{
                border-top-color: {LightTheme.ACCENT_COLOR};
            }}

            /* Calendar widget */
            QCalendarWidget {{
                background-color: {LightTheme.SECONDARY_DARK};
                color: {LightTheme.TEXT_PRIMARY};
                border: 1px solid {LightTheme.BORDER_COLOR};
                border-radius: 6px;
            }}

            QCalendarWidget QWidget {{
                background-color: {LightTheme.SECONDARY_DARK};
                color: {LightTheme.TEXT_PRIMARY};
            }}

            QCalendarWidget QAbstractItemView {{
                background-color: {LightTheme.SECONDARY_DARK};
                selection-background-color: {LightTheme.ACCENT_COLOR};
                selection-color: #ffffff;
                border: none;
            }}

            QCalendarWidget QAbstractItemView:enabled {{
                color: {LightTheme.TEXT_PRIMARY};
            }}

            QCalendarWidget QAbstractItemView:disabled {{
                color: {LightTheme.TEXT_MUTED};
            }}

            /* Calendar navigation */
            QCalendarWidget QToolButton {{
                background-color: {LightTheme.SECONDARY_DARK};
                color: {LightTheme.TEXT_PRIMARY};
                border: none;
                border-radius: 4px;
                padding: 4px;
                font-size: {LightTheme.FONT_SIZE_NORMAL}pt;
            }}

            QCalendarWidget QToolButton:hover {{
                background-color: {LightTheme.ACCENT_HOVER};
                color: #ffffff;
            }}

            /* Calendar header */
            QCalendarWidget #qt_calendar_calendarview {{
                background-color: {LightTheme.SECONDARY_DARK};
                border: none;
            }}

            /* Day names header */
            QCalendarWidget QWidget#qt_calendar_navigationbar {{
                background-color: {LightTheme.PRIMARY_DARK};
                border-bottom: 1px solid {LightTheme.BORDER_COLOR};
            }}

            /* Spin boxes */
            QSpinBox {{
                background-color: {LightTheme.SECONDARY_DARK};
                color: {LightTheme.TEXT_PRIMARY};
                border: 1px solid {LightTheme.BORDER_COLOR};
                border-radius: 6px;
                padding: 6px 8px;
                font-size: {LightTheme.FONT_SIZE_NORMAL}pt;
                min-width: 60px;
            }}

            QSpinBox:hover {{
                border-color: {LightTheme.ACCENT_HOVER};
            }}

            QSpinBox:focus {{
                border-color: {LightTheme.ACCENT_COLOR};
            }}

            QSpinBox::up-button, QSpinBox::down-button {{
                background-color: {LightTheme.SECONDARY_DARK};
                border: none;
                width: 16px;
            }}

            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background-color: {LightTheme.ACCENT_HOVER};
            }}

            QSpinBox::up-arrow {{
                image: none;
                border-left: 3px solid transparent;
                border-right: 3px solid transparent;
                border-bottom: 3px solid {LightTheme.TEXT_SECONDARY};
                margin-bottom: 2px;
            }}

            QSpinBox::down-arrow {{
                image: none;
                border-left: 3px solid transparent;
                border-right: 3px solid transparent;
                border-top: 3px solid {LightTheme.TEXT_SECONDARY};
                margin-top: 2px;
            }}

            QSpinBox::up-arrow:hover {{
                border-bottom-color: {LightTheme.ACCENT_COLOR};
            }}

            QSpinBox::down-arrow:hover {{
                border-top-color: {LightTheme.ACCENT_COLOR};
            }}

            /* Text input widgets */
            QLineEdit {{
                background-color: {LightTheme.SECONDARY_DARK};
                color: {LightTheme.TEXT_PRIMARY};
                border: 1px solid {LightTheme.BORDER_COLOR};
                border-radius: 6px;
                padding: 3px 3px;
                font-size: {LightTheme.FONT_SIZE_NORMAL}pt;
                selection-background-color: {LightTheme.ACCENT_COLOR};
                selection-color: #ffffff;
            }}

            QLineEdit:hover {{
                border-color: {LightTheme.ACCENT_HOVER};
            }}

            QLineEdit:focus {{
                border-color: {LightTheme.ACCENT_COLOR};
                background-color: {LightTheme.PRIMARY_DARK};
            }}

            QLineEdit:read-only {{
                background-color: {LightTheme.SECONDARY_DARK};
                color: {LightTheme.TEXT_SECONDARY};
                border-color: {LightTheme.BORDER_COLOR};
            }}

            /* Combo boxes */
            QComboBox {{
                background-color: {LightTheme.SECONDARY_DARK};
                color: {LightTheme.TEXT_PRIMARY};
                border: 1px solid {LightTheme.BORDER_COLOR};
                border-radius: 6px;
                padding: 4px 8px;
                font-size: {LightTheme.FONT_SIZE_NORMAL}pt;
            }}

            QComboBox:hover {{
                border-color: {LightTheme.ACCENT_HOVER};
            }}

            QComboBox:focus {{
                border-color: {LightTheme.ACCENT_COLOR};
            }}

            QComboBox::drop-down {{
                border: none;
                width: 0px;
            }}

            QComboBox::down-arrow {{
                image: none;
                width: 0px;
                height: 0px;
            }}

            QComboBox QAbstractItemView {{
                background-color: {LightTheme.SECONDARY_DARK};
                color: {LightTheme.TEXT_PRIMARY};
                border: 1px solid {LightTheme.BORDER_COLOR};
                border-radius: 4px;
                selection-background-color: {LightTheme.ACCENT_COLOR};
                selection-color: #ffffff;
            }}

            QComboBox QAbstractItemView::item {{
                padding: 4px 8px;
                color: {LightTheme.TEXT_PRIMARY};
                border-bottom: 1px solid {LightTheme.BORDER_COLOR};
            }}

            QComboBox QAbstractItemView::item:hover {{
                background-color: {LightTheme.ACCENT_HOVER};
                color: #ffffff;
            }}

            /* Text areas */
            QTextEdit {{
                background-color: {LightTheme.SECONDARY_DARK};
                color: {LightTheme.TEXT_PRIMARY};
                border: 1px solid {LightTheme.BORDER_COLOR};
                border-radius: 6px;
                padding: 8px;
                font-size: {LightTheme.FONT_SIZE_NORMAL}pt;
                selection-background-color: {LightTheme.ACCENT_COLOR};
                selection-color: #ffffff;
            }}

            QTextEdit:hover {{
                border-color: {LightTheme.ACCENT_HOVER};
            }}

            QTextEdit:focus {{
                border-color: {LightTheme.ACCENT_COLOR};
                background-color: {LightTheme.PRIMARY_DARK};
            }}

            /* Plain text edit */
            QPlainTextEdit {{
                background-color: {LightTheme.SECONDARY_DARK};
                color: {LightTheme.TEXT_PRIMARY};
                border: 1px solid {LightTheme.BORDER_COLOR};
                border-radius: 6px;
                padding: 8px;
                font-size: {LightTheme.FONT_SIZE_NORMAL}pt;
                selection-background-color: {LightTheme.ACCENT_COLOR};
                selection-color: #ffffff;
            }}

            QPlainTextEdit:hover {{
                border-color: {LightTheme.ACCENT_HOVER};
            }}

            QPlainTextEdit:focus {{
                border-color: {LightTheme.ACCENT_COLOR};
                background-color: {LightTheme.PRIMARY_DARK};
            }}

            /* Tooltips */
            QToolTip {{
                background-color: {LightTheme.SECONDARY_DARK};
                color: {LightTheme.TEXT_PRIMARY};
                border: 1px solid {LightTheme.BORDER_COLOR};
                border-radius: 6px;
                padding: 8px;
                font-size: {LightTheme.FONT_SIZE_NORMAL}pt;
                font-family: {LightTheme.FONT_FAMILY};
            }}

            /* List widgets */
            QListWidget {{
                background-color: {LightTheme.SECONDARY_DARK};
                color: {LightTheme.TEXT_PRIMARY};
                border: 1px solid {LightTheme.BORDER_COLOR};
                border-radius: 6px;
            }}

            QListWidget::item {{
                padding: 4px 8px;
                color: {LightTheme.TEXT_PRIMARY};
                border-bottom: 1px solid {LightTheme.BORDER_COLOR};
            }}

            QListWidget::item:selected {{
                background-color: {LightTheme.ACCENT_COLOR};
                color: #ffffff;
            }}

            QListWidget::item:hover {{
                background-color: {LightTheme.ACCENT_HOVER};
                color: #ffffff;
            }}

            /* Radio buttons */
            QRadioButton {{
                color: {LightTheme.TEXT_PRIMARY};
                spacing: 8px;
            }}

            QRadioButton::indicator {{
                width: 16px;
                height: 16px;
                border: 2px solid {LightTheme.BORDER_COLOR};
                border-radius: 9px;
                background-color: {LightTheme.SECONDARY_DARK};
            }}

            QRadioButton::indicator:checked {{
                background-color: {LightTheme.ACCENT_COLOR};
                border-color: {LightTheme.ACCENT_COLOR};
            }}

            QRadioButton::indicator:hover {{
                border-color: {LightTheme.ACCENT_HOVER};
            }}

            /* Scroll bars */
            QScrollBar:vertical {{
                background-color: {LightTheme.SECONDARY_DARK};
                width: 12px;
                margin: 0;
                border-radius: 6px;
            }}

            QScrollBar::handle:vertical {{
                background-color: {LightTheme.BORDER_COLOR};
                min-height: 30px;
                border-radius: 6px;
            }}

            QScrollBar::handle:vertical:hover {{
                background-color: {LightTheme.ACCENT_HOVER};
            }}

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}

            QScrollBar:horizontal {{
                background-color: {LightTheme.SECONDARY_DARK};
                height: 12px;
                margin: 0;
                border-radius: 6px;
            }}

            QScrollBar::handle:horizontal {{
                background-color: {LightTheme.BORDER_COLOR};
                min-width: 30px;
                border-radius: 6px;
            }}

            QScrollBar::handle:horizontal:hover {{
                background-color: {LightTheme.ACCENT_HOVER};
            }}

            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
        """


def get_current_theme():
    """Get the current theme class based on saved preference."""
    return ThemeManager.instance().get_current_theme_class()
