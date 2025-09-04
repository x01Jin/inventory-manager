"""
Requisition preview panel - displays detailed information for selected requisition.
Shows comprehensive details in a vertical layout when a requisition is selected.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGroupBox,
    QScrollArea, QFrame
)
from PyQt6.QtCore import Qt

from inventory_app.gui.requisitions.requisitions_model import RequisitionSummary
from inventory_app.gui.styles import DarkTheme
from inventory_app.utils.logger import logger
from inventory_app.gui.requisitions.requisition_management.return_processor import ReturnProcessor


class RequisitionPreview(QWidget):
    """
    Preview panel showing detailed information for a selected requisition.
    Displays comprehensive details in a clean vertical layout.
    """

    def __init__(self, parent=None):
        """Initialize the preview panel."""
        super().__init__(parent)
        self.setMinimumWidth(350)
        self.current_requisition: Optional[RequisitionSummary] = None

        self.setup_ui()
        logger.info("Requisition preview panel initialized")

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Create scroll area for long content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setFrameStyle(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        # Container widget for scroll area
        self.container = QWidget()
        self.container.setStyleSheet("background-color: transparent;")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(15)

        scroll_area.setWidget(self.container)
        layout.addWidget(scroll_area)

        # Initial empty state
        self.show_empty_state()

    def show_empty_state(self):
        """Show empty state when no requisition is selected."""
        self.clear_container()

        empty_label = QLabel("Select a requisition")
        empty_label.setStyleSheet(f"""
            QLabel {{
                color: {DarkTheme.TEXT_MUTED};
                font-size: {DarkTheme.FONT_SIZE_TITLE}pt;
                font-style: italic;
                text-align: center;
                padding: 40px;
            }}
        """)
        empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.container_layout.addWidget(empty_label)
        self.container_layout.addStretch()

    def clear_container(self):
        """Clear all widgets from the container."""
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

    def update_preview(self, requisition_summary: Optional[RequisitionSummary]):
        """Update the preview with requisition details."""
        try:
            self.current_requisition = requisition_summary

            if not requisition_summary:
                self.show_empty_state()
                return

            self.clear_container()
            self.populate_details(requisition_summary)
            self.container_layout.addStretch()

            logger.debug(f"Updated preview for requisition {requisition_summary.requisition.id}")

        except Exception as e:
            logger.error(f"Failed to update preview: {e}")
            self.show_empty_state()

    def populate_details(self, req_summary: RequisitionSummary):
        """Populate the preview with detailed requisition information."""
        req = req_summary.requisition
        requester = req_summary.requester

        # Header
        header = QLabel("📋 Requisition Details")
        header.setStyleSheet(f"font-size: {DarkTheme.FONT_SIZE_TITLE}pt; font-weight: bold; margin-bottom: 10px;")
        self.container_layout.addWidget(header)

        # Status at the very top
        status_frame = self.create_status_section(req.status)
        self.container_layout.addWidget(status_frame)

        # Requester Information
        requester_section = self.create_requester_section(requester)
        self.container_layout.addWidget(requester_section)

        # Timeline (below requester info as requested)
        timeline_section = self.create_timeline_section(req)
        self.container_layout.addWidget(timeline_section)

        # Activity Details
        activity_section = self.create_activity_section(req)
        self.container_layout.addWidget(activity_section)

        # Requested Items
        items_section = self.create_items_section(req_summary.items, req_summary.total_items)
        self.container_layout.addWidget(items_section)

        # Return Details (only show for processed requisitions)
        if req.status == "returned" and req.id is not None:
            return_details_section = self.create_return_details_section(req.id)
            self.container_layout.addWidget(return_details_section)

    def create_status_section(self, status: str) -> QFrame:
        """Create the status section at the top."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.NoFrame)
        frame.setStyleSheet("QFrame { border: none; background-color: transparent; }")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 10, 15, 10)

        color = self._get_status_color(status)
        status_label = QLabel(f"📊 Status: {status.upper()}")
        status_label.setStyleSheet(f"font-size: {DarkTheme.FONT_SIZE_NORMAL}pt; font-weight: bold; color: {color};")
        layout.addWidget(status_label)

        return frame

    def create_requester_section(self, requester) -> QGroupBox:
        """Create the requester information section."""
        group = QGroupBox("👤 Requester Information")
        group.setStyleSheet(self._get_group_style())

        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        name_label = QLabel(f"• Name: {requester.name}")
        name_label.setStyleSheet(f"font-weight: bold; font-size: {DarkTheme.FONT_SIZE_NORMAL}pt;")
        layout.addWidget(name_label)

        affiliation_label = QLabel(f"• Affiliation: {requester.affiliation}")
        layout.addWidget(affiliation_label)

        group_label = QLabel(f"• Group: {requester.group_name}")
        layout.addWidget(group_label)

        return group

    def create_timeline_section(self, req) -> QGroupBox:
        """Create the timeline section with all dates."""
        group = QGroupBox("⏰ Timeline")
        group.setStyleSheet(self._get_group_style())

        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # Expected Request
        if req.expected_request:
            expected_request_str = req.expected_request.strftime("%Y-%m-%d %H:%M")
            expected_request_label = QLabel(f"• Expected Request: {expected_request_str}")
            layout.addWidget(expected_request_label)

        # Requested Date
        if req.datetime_requested:
            requested_str = req.datetime_requested.strftime("%Y-%m-%d %H:%M")
            requested_label = QLabel(f"• Requested Date: {requested_str}")
            requested_label.setStyleSheet(f"font-weight: bold; color: {DarkTheme.SUCCESS_COLOR};")
            layout.addWidget(requested_label)
        else:
            not_requested_label = QLabel("• Requested Date:  Reserved")
            not_requested_label.setStyleSheet(f"font-style: italic; color: {DarkTheme.WARNING_COLOR};")
            layout.addWidget(not_requested_label)

        # Expected Return
        if req.expected_return:
            expected_return_str = req.expected_return.strftime("%Y-%m-%d %H:%M")
            expected_return_label = QLabel(f"• Expected Return: {expected_return_str}")
            layout.addWidget(expected_return_label)

        return group

    def create_activity_section(self, req) -> QGroupBox:
        """Create the activity details section."""
        group = QGroupBox("📝 Activity Details")
        group.setStyleSheet(self._get_group_style())

        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        activity_label = QLabel(f"• Activity: {req.lab_activity_name}")
        activity_label.setStyleSheet(f"font-weight: bold; font-size: {DarkTheme.FONT_SIZE_NORMAL}pt;")
        layout.addWidget(activity_label)

        if req.lab_activity_date:
            date_str = req.lab_activity_date.strftime("%Y-%m-%d")
            date_label = QLabel(f"• Activity Date: {date_str}")
            layout.addWidget(date_label)

        if req.num_students:
            students_label = QLabel(f"• Students: {req.num_students}")
            layout.addWidget(students_label)

        if req.num_groups:
            groups_label = QLabel(f"• Groups: {req.num_groups}")
            layout.addWidget(groups_label)

        return group

    def create_items_section(self, items: list, total_count: int) -> QGroupBox:
        """Create the Requested Items section."""
        group = QGroupBox(f"📦 Requested Items ({total_count})")
        group.setStyleSheet(self._get_group_style())

        layout = QVBoxLayout(group)
        layout.setSpacing(5)

        if not items:
            no_items_label = QLabel("No items requested")
            no_items_label.setStyleSheet(f"font-style: italic; color: {DarkTheme.TEXT_MUTED};")
            layout.addWidget(no_items_label)
        else:
            for item in items:
                item_text = f"• {item['name']} (x{item['quantity_requested']})"
                item_label = QLabel(item_text)
                item_label.setStyleSheet("font-size: 9pt;")
                layout.addWidget(item_label)

        return group

    def _get_status_color(self, status: str) -> str:
        """Get color for status text."""
        colors = {
            "active": "#f59e0b",    # Bright orange/yellow
            "returned": "#10b981", # Bright green
            "overdue": "#ef4444",  # Bright red
            "requested": "#06b6d4" # Bright cyan
        }
        return colors.get(status, "#ffffff")

    def _get_group_style(self) -> str:
        """Get consistent styling for group boxes."""
        return f"""
            QGroupBox {{
                font-weight: bold;
                border: none;
                border-radius: 0px;
                margin-top: 15px;
                padding-top: 10px;
                background-color: transparent;
                border: none;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: {DarkTheme.TEXT_PRIMARY};
                border: none;
                background-color: transparent;
            }}
        """

    def create_return_details_section(self, requisition_id: int) -> QGroupBox:
        """Create the Return Details section for processed requisitions."""
        group = QGroupBox("🔒 Final Return Details")
        group.setStyleSheet(self._get_group_style())

        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        try:
            # Get return summary from processor
            return_processor = ReturnProcessor()
            summary = return_processor.get_requisition_return_summary(requisition_id)

            if not summary or (summary['total_returned'] == 0 and summary['total_lost'] == 0):
                no_returns_label = QLabel("No return details available")
                no_returns_label.setStyleSheet(f"font-style: italic; color: {DarkTheme.TEXT_MUTED};")
                layout.addWidget(no_returns_label)
                return group

            # Display consumables returned
            if summary['returned_consumables']:
                returned_section = QLabel("✅ Consumables Returned:")
                returned_section.setStyleSheet("font-weight: bold; font-size: 10pt; margin-top: 5px;")
                layout.addWidget(returned_section)

                for item in summary['returned_consumables']:
                    item_label = QLabel(f"  • {item['item_name']} (x{item['quantity']})")
                    item_label.setStyleSheet("font-size: 9pt; margin-left: 10px;")
                    layout.addWidget(item_label)

            # Display non-consumables lost
            if summary['lost_non_consumables']:
                lost_section = QLabel("❌ Non-Consumables Lost/Damaged:")
                lost_section.setStyleSheet("font-weight: bold; font-size: 10pt; margin-top: 5px;")
                layout.addWidget(lost_section)

                for item in summary['lost_non_consumables']:
                    item_label = QLabel(f"  • {item['item_name']} (x{item['quantity']})")
                    item_label.setStyleSheet("font-size: 9pt; margin-left: 10px;")
                    layout.addWidget(item_label)

            # Summary totals
            totals_label = QLabel(
                f"📊 Totals: {summary['total_returned']} returned, {summary['total_lost']} lost"
            )
            totals_label.setStyleSheet(f"font-weight: bold; font-size: 10pt; color: {DarkTheme.SUCCESS_COLOR}; margin-top: 8px;")
            layout.addWidget(totals_label)

            # Lock notice
            lock_notice = QLabel("🔒 This requisition has been processed and is locked from further editing.")
            lock_notice.setStyleSheet(f"font-size: 9pt; color: {DarkTheme.WARNING_COLOR}; font-style: italic; margin-top: 5px;")
            layout.addWidget(lock_notice)

        except Exception as e:
            logger.error(f"Failed to create return details section: {e}")
            error_label = QLabel("Error loading return details")
            error_label.setStyleSheet(f"font-style: italic; color: {DarkTheme.ERROR_COLOR};")
            layout.addWidget(error_label)

        return group

    def get_current_requisition_id(self) -> Optional[int]:
        """Get the ID of the currently displayed requisition."""
        if self.current_requisition and self.current_requisition.requisition:
            return self.current_requisition.requisition.id
        return None
