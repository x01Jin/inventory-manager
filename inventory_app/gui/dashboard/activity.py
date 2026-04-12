"""
Activity management for the dashboard.
Handles recent activity display.
"""

from PyQt6.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QWidget,
    QVBoxLayout,
    QStyledItemDelegate,
)
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
        text_rect = font_metrics.boundingRect(
            0, 0, available_width, 0, Qt.TextFlag.TextWordWrap, text
        )

        # Return size with reduced minimum height
        height = max(text_rect.height() + 6, 20)  # Reduced padding, minimum 20px
        return QSize(available_width, height)

    def paint(self, painter, option, index):
        """Paint the item with word wrapping enabled."""
        # Call parent paint method - word wrap is handled by setWordWrap on the item
        super().paint(painter, option, index)


class ActivityManager:
    """Manager for dashboard activity display."""

    LATEST_ACTIVITY_MIN_HEIGHT = 35

    def __init__(self):
        pass

    def load_activity_data(self):
        """Load activity data from database. Called in background thread."""
        try:
            activities = activity_logger.get_recent_activities(51)
            logger.debug(f"Loaded {len(activities)} activities from database")
            return activities
        except Exception as e:
            logger.error(f"Failed to load activity data: {e}")
            return []

    def populate_activity_widget(self, activity_container, activities):
        """Populate activity widget with loaded data."""
        try:
            if not activities:
                logger.debug("No activities to display")
                self._clear_tables()
                return

            logger.debug(
                f"Populating activity widget with {len(activities)} activities"
            )

            if hasattr(self, "latest_table") and hasattr(self, "history_table"):
                if activities:
                    self._populate_table(self.latest_table, activities[:1])
                    logger.debug(
                        f"Populated latest table with {min(1, len(activities))} activities"
                    )

                if len(activities) > 1:
                    self._populate_table(self.history_table, activities[1:51])
                    logger.debug(
                        f"Populated history table with {min(50, len(activities) - 1)} activities"
                    )
                else:
                    self._clear_table(self.history_table)
            else:
                logger.error(
                    "ActivityManager missing latest_table or history_table attributes"
                )
                self._clear_tables()
        except Exception as e:
            logger.error(f"Failed to populate activity widget: {e}")
            self._clear_tables()

    def update_recent_activity(self, activity_container):
        """Update the recent activity tables with real data."""
        try:
            activities = activity_logger.get_recent_activities(51)

            if not activities:
                self._clear_tables()
                return

            if hasattr(self, "latest_table") and hasattr(self, "history_table"):
                if activities:
                    self._populate_table(self.latest_table, activities[:1])

                if len(activities) > 1:
                    self._populate_table(self.history_table, activities[1:51])
                else:
                    self._clear_table(self.history_table)

        except Exception as e:
            logger.error(f"Failed to update recent activity: {e}")
            self._clear_tables()

    def _populate_table(self, table_group, activities):
        """Populate a table with activity data."""
        table_name = table_group.objectName().replace("_group", "_table")
        table = table_group.findChild(QTableWidget, table_name)
        if not table:
            table = table_group.findChild(QTableWidget)
            if not table:
                logger.error(
                    f"Could not find QTableWidget in group box: {table_group.title()}"
                )
                return

        table.setRowCount(len(activities))

        for row, activity in enumerate(activities):
            desc = activity.get("description", "")
            desc_item = QTableWidgetItem(desc)
            desc_item.setToolTip(desc)
            table.setItem(row, 0, desc_item)

            user = activity.get("user", "System")
            user_item = QTableWidgetItem(user)
            table.setItem(row, 1, user_item)

            if activity.get("time") is not None:
                time_str = f"{date_utils.format_date_short(activity['time'])} at {date_utils.format_time_12h(activity['time'])}"
            else:
                time_str = "Unknown time"
            time_item = QTableWidgetItem(time_str)
            table.setItem(row, 2, time_item)

        if table_group.title() == "Latest Activity":
            table.resizeRowsToContents()
            self._adjust_latest_activity_height(table)
        logger.debug(f"Populated table with {len(activities)} rows")

    def _adjust_latest_activity_height(self, table: QTableWidget):
        """Set Latest Activity table height to fit wrapped row content."""
        row_count = table.rowCount()
        frame_height = table.frameWidth() * 2
        margins = table.contentsMargins()
        margins_height = margins.top() + margins.bottom()

        if row_count > 0:
            content_height = sum(table.rowHeight(row) for row in range(row_count))
            target_height = content_height + frame_height + margins_height + 4
        else:
            target_height = self.LATEST_ACTIVITY_MIN_HEIGHT

        target_height = max(target_height, self.LATEST_ACTIVITY_MIN_HEIGHT)
        table.setMinimumHeight(target_height)
        table.setMaximumHeight(target_height)

    def _clear_tables(self):
        """Clear both tables (defensive - handles deleted or missing widgets)."""
        if hasattr(self, "latest_table"):
            self._clear_table(self.latest_table)
        if hasattr(self, "history_table"):
            self._clear_table(self.history_table)

    def _clear_table(self, table_group):
        """Clear a specific table safely."""
        try:
            if not table_group:
                return
            table = table_group.findChild(QTableWidget)
            if table:
                table.setRowCount(0)
                if table_group.title() == "Latest Activity":
                    self._adjust_latest_activity_height(table)
        except RuntimeError as e:
            # Widget may have been deleted on teardown; ignore and log
            logger.warning(f"Could not clear table (widget deleted): {e}")

    def create_activity_widget(self):
        """Create and configure the activity widget with two tables."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.latest_table = self._create_activity_table("Latest Activity", 1)
        layout.addWidget(self.latest_table)
        logger.debug(f"Created latest_table: {self.latest_table.objectName()}")

        self.history_table = self._create_activity_table("Activity History", 50)
        layout.addWidget(self.history_table)
        logger.debug(f"Created history_table: {self.history_table.objectName()}")

        container.setSizePolicy(
            container.sizePolicy().Policy.Expanding,
            container.sizePolicy().Policy.Expanding,
        )

        logger.debug("Activity widget created with tables")
        return container

    def _create_activity_table(self, title, max_rows):
        """Create a configured activity table."""
        # Create group box for the table
        from PyQt6.QtWidgets import QGroupBox

        group = QGroupBox(title)
        group.setObjectName(
            f"{title.replace(' ', '_')}_group"
        )  # Set object name for easier lookup
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(2, 2, 2, 2)

        # Create table
        table = QTableWidget()
        table.setObjectName(f"{title.replace(' ', '_')}_table")  # Set object name
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Description", "User", "Time"])
        if title == "Latest Activity":
            table.setMinimumHeight(self.LATEST_ACTIVITY_MIN_HEIGHT)

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
        table.setColumnWidth(1, 70)  # User
        table.setColumnWidth(2, 70)  # Time

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
