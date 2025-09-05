"""
Activity management for the dashboard.
Handles recent activity display.
"""

from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QWidget, QVBoxLayout, QStyledItemDelegate
from PyQt6.QtCore import Qt, QSize

from inventory_app.gui.styles import DarkTheme
from inventory_app.utils.activity_logger import activity_logger
from inventory_app.utils.logger import logger
from inventory_app.utils import date_utils


class WordWrapDelegate(QStyledItemDelegate):
    """Custom delegate for proper word wrapping and size hint calculation."""

    def __init__(self, parent=None):
        super().__init__(parent)

    def sizeHint(self, option, index):
        """Calculate size hint that respects word wrapping."""
        if not index.isValid():
            return QSize()

        # Get the text
        text = index.data(Qt.ItemDataRole.DisplayRole)
        if not text:
            return QSize(0, 20)  # Reduced minimum height

        # Get font metrics
        font_metrics = option.fontMetrics

        # Calculate available width (table column width minus padding)
        available_width = option.rect.width() - 16  # Subtract padding
        if available_width <= 0:
            available_width = 200  # Fallback width

        # Calculate text dimensions with word wrapping
        text_rect = font_metrics.boundingRect(0, 0, available_width, 0,
                                           Qt.TextFlag.TextWordWrap, text)

        # Return size with reduced minimum height
        height = max(text_rect.height() + 6, 20)  # Reduced padding, minimum 20px
        return QSize(available_width, height)

    def paint(self, painter, option, index):
        """Paint the item with word wrapping enabled."""
        # Call parent paint method - word wrap is handled by setWordWrap on the item
        super().paint(painter, option, index)


class ActivityManager:
    """Manager for dashboard activity display."""

    def __init__(self):
        pass

    def update_recent_activity(self, activity_container):
        """Update the recent activity tables with real data."""
        try:
            activities = activity_logger.get_recent_activities(51)  # Get 51 activities (1 latest + 50 history)

            if not activities:
                self._clear_tables()
                return

            # Update latest activity table (first activity)
            if activities:
                self._populate_table(self.latest_table, activities[:1])

            # Update history table (next 50 activities)
            if len(activities) > 1:
                self._populate_table(self.history_table, activities[1:51])
            else:
                self._clear_table(self.history_table)

        except Exception as e:
            logger.error(f"Failed to update recent activity: {e}")
            self._clear_tables()

    def _populate_table(self, table_group, activities):
        """Populate a table with activity data."""
        # Get the table widget from the group box
        table = table_group.findChild(QTableWidget)
        if not table:
            return

        table.setRowCount(len(activities))

        for row, activity in enumerate(activities):
            # Description
            desc = activity.get('description', '')
            desc_item = QTableWidgetItem(desc)
            desc_item.setToolTip(desc)  # Show full text on hover
            table.setItem(row, 0, desc_item)

            # User
            user = activity.get('user', 'System')
            user_item = QTableWidgetItem(user)
            table.setItem(row, 1, user_item)

            # Time
            if activity.get('time') is not None:
                time_str = f"{date_utils.format_date_short(activity['time'])} at {date_utils.format_time_12h(activity['time'])}"
            else:
                time_str = "Unknown time"
            time_item = QTableWidgetItem(time_str)
            table.setItem(row, 2, time_item)

        # Resize rows to content for word wrapping
        table.resizeRowsToContents()

    def _clear_tables(self):
        """Clear both tables."""
        self._clear_table(self.latest_table)
        self._clear_table(self.history_table)

    def _clear_table(self, table_group):
        """Clear a specific table."""
        table = table_group.findChild(QTableWidget)
        if table:
            table.setRowCount(0)

    def create_activity_widget(self):
        """Create and configure the activity widget with two tables."""
        # Create main container widget
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Create latest activity table
        self.latest_table = self._create_activity_table("Latest Activity", 1)
        layout.addWidget(self.latest_table)

        # Create history table
        self.history_table = self._create_activity_table("Activity History", 50)
        layout.addWidget(self.history_table)

        # Set size policy for expansion
        container.setSizePolicy(container.sizePolicy().Policy.Expanding, container.sizePolicy().Policy.Expanding)

        return container

    def _create_activity_table(self, title, max_rows):
        """Create a configured activity table."""
        # Create group box for the table
        from PyQt6.QtWidgets import QGroupBox
        group = QGroupBox(title)
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(2, 2, 2, 2)

        # Create table
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Description", "User", "Time"])
        if title == "Latest Activity":
            table.setMaximumHeight(35)

        # Configure table properties
        table.setAlternatingRowColors(True)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSortingEnabled(False)  # Disable sorting for activity logs

        # Configure headers
        header = table.horizontalHeader()
        if header:
            header.setStretchLastSection(True)
            header.setSectionsMovable(False)
            header.setVisible(False)

        # Set column widths - reduced for compactness
        table.setColumnWidth(0, 300)  # Description
        table.setColumnWidth(1, 70)   # User
        table.setColumnWidth(2, 70)   # Time

        # Configure vertical header
        v_header = table.verticalHeader()
        if v_header:
            v_header.setVisible(False)
            v_header.setDefaultSectionSize(25)

        # Enable word wrap for description column
        delegate = WordWrapDelegate(table)
        table.setItemDelegateForColumn(0, delegate)

        # Hide scrollbars
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Apply styling with reduced sizes and !important overrides
        table.setStyleSheet(f"""
            QTableWidget {{
            border: 1px solid {DarkTheme.BORDER_COLOR} !important;
            border-radius: 3px !important;
            font-size: 8pt !important;
            }}

            QTableWidget::item {{
            padding: 1px !important;
            border-bottom: 1px solid {DarkTheme.BORDER_COLOR} !important;
            font-size: 8pt !important;
            }}

            QHeaderView::section {{
            padding: 2px !important;
            border: 1px solid {DarkTheme.BORDER_COLOR} !important;
            font-weight: bold !important;
            font-size: 8pt !important;
            }}

            QGroupBox {{
            font-size: 10pt !important;
            border: 1px solid {DarkTheme.BORDER_COLOR} !important;
            border-radius: 3px !important;
            margin-top: 0.5ex !important;
            padding-top: 4px !important;
            }}

            QGroupBox::title {{
            font-size: 9pt !important;
            padding: 0 2px 0 2px !important;
            }}
        """)

        group_layout.addWidget(table)
        return group
