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
from inventory_app.utils.logger import logger


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
        empty_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 14pt;
                font-style: italic;
                text-align: center;
                padding: 40px;
            }
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
        borrower = req_summary.borrower

        # Header
        header = QLabel("📋 Requisition Details")
        header.setStyleSheet("font-size: 14pt; font-weight: bold; margin-bottom: 10px; padding: 0; border: none; background-color: transparent;")
        self.container_layout.addWidget(header)

        # Status at the very top
        status_frame = self.create_status_section(req.status)
        self.container_layout.addWidget(status_frame)

        # Borrower Information
        borrower_section = self.create_borrower_section(borrower)
        self.container_layout.addWidget(borrower_section)

        # Timeline (below borrower info as requested)
        timeline_section = self.create_timeline_section(req)
        self.container_layout.addWidget(timeline_section)

        # Activity Details
        activity_section = self.create_activity_section(req)
        self.container_layout.addWidget(activity_section)

        # Borrowed Items
        items_section = self.create_items_section(req_summary.items, req_summary.total_items)
        self.container_layout.addWidget(items_section)

    def create_status_section(self, status: str) -> QFrame:
        """Create the status section at the top."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.NoFrame)
        frame.setStyleSheet("QFrame { border: none; background-color: transparent; }")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 10, 15, 10)

        status_label = QLabel(f"📊 Status: {status}")
        status_label.setStyleSheet(f"""
            QLabel {{
                font-size: 12pt;
                font-weight: bold;
                color: {self._get_status_color(status)};
                padding: 0;
                margin: 0;
                border: none;
                background-color: transparent;
            }}
        """)
        layout.addWidget(status_label)

        return frame

    def create_borrower_section(self, borrower) -> QGroupBox:
        """Create the borrower information section."""
        group = QGroupBox("👤 Borrower Information")
        group.setStyleSheet(self._get_group_style())

        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        name_label = QLabel(f"• Name: {borrower.name}")
        name_label.setStyleSheet("font-weight: bold; font-size: 10pt; padding: 0; margin: 0; border: none; background-color: transparent;")
        layout.addWidget(name_label)

        affiliation_label = QLabel(f"• Affiliation: {borrower.affiliation}")
        affiliation_label.setStyleSheet("padding: 0; margin: 0; border: none; background-color: transparent;")
        layout.addWidget(affiliation_label)

        group_label = QLabel(f"• Group: {borrower.group_name}")
        group_label.setStyleSheet("padding: 0; margin: 0; border: none; background-color: transparent;")
        layout.addWidget(group_label)

        return group

    def create_timeline_section(self, req) -> QGroupBox:
        """Create the timeline section with all dates."""
        group = QGroupBox("⏰ Timeline")
        group.setStyleSheet(self._get_group_style())

        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # Expected Borrow
        if req.expected_borrow:
            expected_borrow_str = req.expected_borrow.strftime("%Y-%m-%d %H:%M")
            expected_borrow_label = QLabel(f"• Expected Borrow: {expected_borrow_str}")
            expected_borrow_label.setStyleSheet("padding: 0; margin: 0; border: none; background-color: transparent;")
            layout.addWidget(expected_borrow_label)

        # Borrowed Date
        if req.datetime_borrowed:
            borrowed_str = req.datetime_borrowed.strftime("%Y-%m-%d %H:%M")
            borrowed_label = QLabel(f"• Borrowed Date: {borrowed_str}")
            borrowed_label.setStyleSheet("font-weight: bold; color: #28a745; padding: 0; margin: 0; border: none; background-color: transparent;")
            layout.addWidget(borrowed_label)
        else:
            not_borrowed_label = QLabel("• Borrowed Date:  Reserved")
            not_borrowed_label.setStyleSheet("font-style: italic; color: #856404; padding: 0; margin: 0; border: none; background-color: transparent;")
            layout.addWidget(not_borrowed_label)

        # Expected Return
        if req.expected_return:
            expected_return_str = req.expected_return.strftime("%Y-%m-%d %H:%M")
            expected_return_label = QLabel(f"• Expected Return: {expected_return_str}")
            expected_return_label.setStyleSheet("padding: 0; margin: 0; border: none; background-color: transparent;")
            layout.addWidget(expected_return_label)

        return group

    def create_activity_section(self, req) -> QGroupBox:
        """Create the activity details section."""
        group = QGroupBox("📝 Activity Details")
        group.setStyleSheet(self._get_group_style())

        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        activity_label = QLabel(f"• Activity: {req.lab_activity_name}")
        activity_label.setStyleSheet("font-weight: bold; font-size: 10pt; padding: 0; margin: 0; border: none; background-color: transparent;")
        layout.addWidget(activity_label)

        if req.lab_activity_date:
            date_str = req.lab_activity_date.strftime("%Y-%m-%d")
            date_label = QLabel(f"• Activity Date: {date_str}")
            date_label.setStyleSheet("padding: 0; margin: 0; border: none; background-color: transparent;")
            layout.addWidget(date_label)

        if req.num_students:
            students_label = QLabel(f"• Students: {req.num_students}")
            students_label.setStyleSheet("padding: 0; margin: 0; border: none; background-color: transparent;")
            layout.addWidget(students_label)

        if req.num_groups:
            groups_label = QLabel(f"• Groups: {req.num_groups}")
            groups_label.setStyleSheet("padding: 0; margin: 0; border: none; background-color: transparent;")
            layout.addWidget(groups_label)

        return group

    def create_items_section(self, items: list, total_count: int) -> QGroupBox:
        """Create the borrowed items section."""
        group = QGroupBox(f"📦 Borrowed Items ({total_count})")
        group.setStyleSheet(self._get_group_style())

        layout = QVBoxLayout(group)
        layout.setSpacing(5)

        if not items:
            no_items_label = QLabel("No items borrowed")
            no_items_label.setStyleSheet("font-style: italic; color: #666; padding: 0; margin: 0; border: none; background-color: transparent;")
            layout.addWidget(no_items_label)
        else:
            for item in items:
                item_text = f"• {item['name']} (x{item['quantity_borrowed']})"
                item_label = QLabel(item_text)
                item_label.setStyleSheet("font-size: 9pt; padding: 0; margin: 0; border: none; background-color: transparent;")
                layout.addWidget(item_label)

        return group

    def _get_status_color(self, status: str) -> str:
        """Get color for status text."""
        colors = {
            "Active": "#f59e0b",    # Bright orange/yellow
            "Returned": "#10b981", # Bright green
            "Overdue": "#ef4444",  # Bright red
            "requested": "#06b6d4" # Bright cyan
        }
        return colors.get(status, "#ffffff")

    def _get_group_style(self) -> str:
        """Get consistent styling for group boxes."""
        return """
            QGroupBox {
                font-weight: bold;
                border: none;
                border-radius: 0px;
                margin-top: 15px;
                padding-top: 10px;
                background-color: transparent;
                border: none;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #ffffff;
                border: none;
                background-color: transparent;
            }
        """

    def get_current_requisition_id(self) -> Optional[int]:
        """Get the ID of the currently displayed requisition."""
        if self.current_requisition and self.current_requisition.requisition:
            return self.current_requisition.requisition.id
        return None
