"""
Item Return Dialog - Simplified one-time return process.

Provides a simple dialog for final return processing where users specify
lost quantities for non-consumables and returned quantities for consumables.
Once processed, the requisition is locked and cannot be edited.
"""

from typing import List, Optional
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGroupBox,
    QMessageBox,
    QInputDialog,
    QSpinBox,
    QWidget,
    QComboBox,
    QLineEdit,
)
from PyQt6.QtCore import Qt, pyqtSignal

from .return_processor import ReturnProcessor, ReturnItem
from inventory_app.database.models import Requisition, Requester
from inventory_app.database.connection import db
from inventory_app.utils.logger import logger
from inventory_app.utils.date_utils import (
    parse_datetime_iso,
    parse_date_iso,
    format_date_short,
)
from inventory_app.gui.styles import DarkTheme


class ReturnItemWidget(QWidget):
    """Simplified widget for handling return/loss input for a single item.

    For non-consumables, also tracks defective/broken items with condition type and notes
    per beta test requirement B.2.
    """

    # Signal emitted when return/loss values change
    valueChanged = pyqtSignal()

    # Condition types for defective items
    CONDITION_TYPES = ["BROKEN", "DEFECTIVE", "DAMAGED", "OTHER"]

    def __init__(self, return_item: ReturnItem, item_name: str, parent=None):
        super().__init__(parent)
        self.return_item = return_item
        self.item_name = item_name
        self.setup_ui()

    def setup_ui(self):
        """Setup the simplified UI for this return item."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(15)

        # Item info section
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        # Item name
        self.item_label = QLabel(f"📦 {self.item_name}")
        self.item_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        info_layout.addWidget(self.item_label)

        # Requested quantity
        self.requested_label = QLabel(
            f"Requested: {self.return_item.quantity_requested}"
        )
        self.requested_label.setStyleSheet("font-size: 9pt; color: #666;")
        info_layout.addWidget(self.requested_label)

        layout.addLayout(info_layout, 3)

        # Return controls section - simplified based on item type
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(4)

        if self.return_item.is_consumable:
            # For consumables: return spinbox (how much is being returned unused)
            return_layout = QHBoxLayout()
            return_layout.setSpacing(5)
            return_layout.addWidget(QLabel("✅ Return unused:"))
            self.returned_spin = QSpinBox()
            self.returned_spin.setRange(0, self.return_item.quantity_requested)
            self.returned_spin.setValue(0)  # Default to none returned (all consumed)
            self.returned_spin.setFixedWidth(60)
            self.returned_spin.valueChanged.connect(self._on_return_changed)
            return_layout.addWidget(self.returned_spin)
            return_layout.addStretch()
            controls_layout.addLayout(return_layout)
        else:
            # For non-consumables: lost spinbox + defective items tracking
            lost_layout = QHBoxLayout()
            lost_layout.setSpacing(5)
            lost_layout.addWidget(QLabel("❌ Lost:"))
            self.lost_spin = QSpinBox()
            self.lost_spin.setRange(0, self.return_item.quantity_requested)
            self.lost_spin.setValue(0)  # Default to none lost
            self.lost_spin.setFixedWidth(60)
            self.lost_spin.valueChanged.connect(self._on_lost_changed)
            lost_layout.addWidget(self.lost_spin)
            lost_layout.addStretch()
            controls_layout.addLayout(lost_layout)

            # Defective items section (per beta test B.2)
            defective_layout = QHBoxLayout()
            defective_layout.setSpacing(5)
            defective_layout.addWidget(QLabel("⚠️ Defective:"))
            self.defective_spin = QSpinBox()
            self.defective_spin.setRange(0, self.return_item.quantity_requested)
            self.defective_spin.setValue(0)
            self.defective_spin.setFixedWidth(60)
            self.defective_spin.valueChanged.connect(self._on_defective_changed)
            defective_layout.addWidget(self.defective_spin)

            # Condition type dropdown
            self.condition_combo = QComboBox()
            self.condition_combo.addItems(self.CONDITION_TYPES)
            self.condition_combo.setFixedWidth(100)
            self.condition_combo.setEnabled(False)  # Enable when defective > 0
            self.condition_combo.currentTextChanged.connect(self._on_condition_changed)
            defective_layout.addWidget(self.condition_combo)
            defective_layout.addStretch()
            controls_layout.addLayout(defective_layout)

            # Notes for defective items
            notes_layout = QHBoxLayout()
            notes_layout.setSpacing(5)
            notes_layout.addWidget(QLabel("📝 Notes:"))
            self.notes_input = QLineEdit()
            self.notes_input.setPlaceholderText("Describe defect (optional)")
            self.notes_input.setEnabled(False)  # Enable when defective > 0
            self.notes_input.textChanged.connect(self._on_notes_changed)
            notes_layout.addWidget(self.notes_input)
            controls_layout.addLayout(notes_layout)

        layout.addLayout(controls_layout, 3)

        # Summary section
        summary_layout = QVBoxLayout()
        summary_layout.setSpacing(2)

        self.summary_label = QLabel(self._get_summary_text())
        self.summary_label.setStyleSheet(
            "font-weight: bold; font-size: 10pt; text-align: center;"
        )
        self.summary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        summary_layout.addWidget(self.summary_label)

        layout.addLayout(summary_layout, 2)

        # Add a subtle border
        self.setStyleSheet("""
            ReturnItemWidget {
                border: 1px solid #ddd;
                border-radius: 8px;
                background-color: #fafafa;
                margin: 2px;
            }
        """)

    def _on_return_changed(self, value: int):
        """Handle returned quantity change for consumables."""
        self.return_item.quantity_returned = value
        self._update_display()

    def _on_lost_changed(self, value: int):
        """Handle lost quantity change for non-consumables."""
        self.return_item.quantity_lost = value
        self._update_defective_max()
        self._update_display()

    def _on_defective_changed(self, value: int):
        """Handle defective quantity change for non-consumables."""
        self.return_item.quantity_defective = value
        # Enable/disable condition and notes based on defective quantity
        has_defective = value > 0
        self.condition_combo.setEnabled(has_defective)
        self.notes_input.setEnabled(has_defective)
        self._update_display()

    def _on_condition_changed(self, condition: str):
        """Handle condition type change."""
        # Store condition type in return_item for later use
        # The return_processor will use this when saving defective items
        pass  # Condition is read directly from combo when processing

    def _on_notes_changed(self, notes: str):
        """Handle notes change for defective items."""
        self.return_item.defective_notes = notes

    def _update_defective_max(self):
        """Update defective spinbox max based on returned quantity."""
        if not self.return_item.is_consumable and hasattr(self, "defective_spin"):
            # Defective can only be from items that were returned (not lost)
            max_defective = (
                self.return_item.quantity_requested - self.return_item.quantity_lost
            )
            self.defective_spin.setMaximum(max_defective)
            # Clamp current value if needed
            if self.defective_spin.value() > max_defective:
                self.defective_spin.setValue(max_defective)

    def get_condition_type(self) -> str:
        """Get selected condition type for defective items."""
        if hasattr(self, "condition_combo"):
            return self.condition_combo.currentText()
        return "OTHER"

    def _update_display(self):
        """Update status and summary displays."""
        self.summary_label.setText(self._get_summary_text())

        # Update background color based on completion
        if self.return_item.is_fully_processed():
            self.setStyleSheet(f"""
                ReturnItemWidget {{
                    border: 2px solid {DarkTheme.SUCCESS_COLOR};
                    border-radius: 8px;
                    background-color: #f0fdf4;
                    margin: 2px;
                }}
            """)
        else:
            self.setStyleSheet("""
                ReturnItemWidget {
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    background-color: #fafafa;
                    margin: 2px;
                }
            """)

        # Emit signal to notify parent dialog of changes
        self.valueChanged.emit()

    def _get_summary_text(self) -> str:
        """Get summary text for this item."""
        if self.return_item.is_consumable:
            returned = self.return_item.quantity_returned
            if returned > 0:
                return f"✅ {returned} unused returned"
            else:
                return "❌ All consumed"
        else:
            lost = self.return_item.quantity_lost
            defective = self.return_item.quantity_defective
            returned = self.return_item.quantity_requested - lost

            parts = []
            if returned > 0:
                parts.append(f"✅ {returned} returned")
            if lost > 0:
                parts.append(f"❌ {lost} lost")
            if defective > 0:
                parts.append(f"⚠️ {defective} defective")

            return " | ".join(parts) if parts else "✅ All returned"


class ItemReturnDialog(QDialog):
    """
    Simplified dialog for one-time final return processing.

    Allows users to specify final lost quantities for non-consumables
    and returned quantities for consumables. Once processed, locked.
    """

    def __init__(self, requisition_id: int, parent=None):
        super().__init__(parent)
        self.requisition_id = requisition_id
        self.return_processor = ReturnProcessor()
        self.return_items: List[ReturnItem] = []
        self.item_widgets: List[ReturnItemWidget] = []

        # Get requisition and requester info
        self.requisition = self._get_requisition(requisition_id)
        self.requester = (
            self._get_requester(self.requisition.requester_id)
            if self.requisition
            else None
        )

        if not self.requisition or not self.requester:
            QMessageBox.critical(self, "Error", "Could not load requisition data.")
            self.reject()
            return

        # Check if already processed
        if self.return_processor.is_requisition_processed(requisition_id):
            QMessageBox.information(
                self,
                "Already Processed",
                "This requisition has already been processed and is locked.",
            )
            self.reject()
            return

        self.setup_ui()
        self.load_return_data()
        logger.info(
            f"One-time return dialog initialized for requisition {requisition_id}"
        )

    def setup_ui(self):
        """Setup the simplified dialog UI."""
        self.setWindowTitle(
            f"Final Return Processing - Requisition #{self.requisition_id}"
        )
        self.setModal(True)
        self.setMinimumSize(700, 500)
        self.resize(800, 600)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Header with warning about one-time processing
        header_label = QLabel("🔒 Final Return Processing")
        header_label.setStyleSheet(
            "font-size: 18pt; font-weight: bold; margin-bottom: 10px;"
        )
        layout.addWidget(header_label)

        warning_label = QLabel(
            "⚠️ This is a ONE-TIME process. Once you click 'Process Returns', "
            "the requisition will be locked and cannot be edited."
        )
        warning_label.setStyleSheet(
            f"font-size: 10pt; color: {DarkTheme.ERROR_COLOR}; font-weight: bold; padding: 8px; background-color: #fef2f2; border-radius: 4px;"
        )
        warning_label.setWordWrap(True)
        layout.addWidget(warning_label)

        # Requisition info
        info_group = QGroupBox("Requisition Information")
        info_layout = QVBoxLayout(info_group)

        requester_text = (
            f"👤 Requester: {self.requester.name} ({self.requester.affiliation})"
            if self.requester
            else "Requester: Unknown"
        )
        requester_label = QLabel(requester_text)
        requester_label.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(requester_label)

        activity_text = (
            f"📝 Activity: {self.requisition.lab_activity_name}"
            if self.requisition
            else "Activity: Unknown"
        )
        activity_label = QLabel(activity_text)
        info_layout.addWidget(activity_label)

        if self.requisition and self.requisition.lab_activity_date:
            date_text = f"📅 Activity Date: {format_date_short(self.requisition.lab_activity_date)}"
            date_label = QLabel(date_text)
            info_layout.addWidget(date_label)

        layout.addWidget(info_group)

        # Items section
        items_group = QGroupBox("Items to Process")
        items_layout = QVBoxLayout(items_group)

        # Instructions
        instructions = QLabel(
            "• For CONSUMABLES: Specify how many were returned UNUSED\n"
            "• For NON-CONSUMABLES: Specify how many were LOST/DAMAGED\n"
            "All quantities must be accounted for before processing."
        )
        instructions.setStyleSheet("font-size: 10pt; color: #666; font-style: italic;")
        instructions.setWordWrap(True)
        items_layout.addWidget(instructions)

        # Items container
        self.items_container = QWidget()
        self.items_layout = QVBoxLayout(self.items_container)
        self.items_layout.setSpacing(10)
        self.items_layout.setContentsMargins(10, 10, 10, 10)

        items_layout.addWidget(self.items_container)

        layout.addWidget(items_group)

        # Summary section
        summary_group = QGroupBox("Processing Summary")
        summary_layout = QVBoxLayout(summary_group)

        self.summary_label = QLabel("Ready to process")
        self.summary_label.setStyleSheet(
            "font-weight: bold; padding: 10px; font-size: 11pt;"
        )
        summary_layout.addWidget(self.summary_label)

        layout.addWidget(summary_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.process_button = QPushButton("🔒 Process Returns (Final)")
        self.process_button.clicked.connect(self.process_returns)
        self.process_button.setEnabled(
            True
        )  # Always enabled - user gets warnings and confirmation
        button_layout.addWidget(self.process_button)

        cancel_button = QPushButton("❌ Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

    def load_return_data(self):
        """Load return data and create simplified item widgets."""
        try:
            # Get return items from processor
            self.return_items = self.return_processor.get_requisition_items_for_return(
                self.requisition_id
            )

            # Get item names
            item_names = self._get_item_names()

            # Clear existing widgets
            self._clear_item_widgets()

            # Create widgets for each item
            for return_item in self.return_items:
                item_name = item_names.get(
                    return_item.item_id, f"Item #{return_item.item_id}"
                )
                widget = ReturnItemWidget(return_item, item_name, self)
                # Connect widget value changes to dialog summary updates
                widget.valueChanged.connect(self._update_summary)
                self.items_layout.addWidget(widget)
                self.item_widgets.append(widget)

            # Add stretch at the end
            self.items_layout.addStretch()

            # Update summary
            self._update_summary()

            logger.info(f"Loaded return data for {len(self.return_items)} items")

        except Exception as e:
            logger.error(f"Failed to load return data: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load return data: {str(e)}")

    def _clear_item_widgets(self):
        """Clear all item widgets."""
        for widget in self.item_widgets:
            self.items_layout.removeWidget(widget)
            widget.deleteLater()
        self.item_widgets.clear()

    def _update_summary(self):
        """Update the processing summary."""
        if not self.return_items:
            self.summary_label.setText("No items to process")
            return

        total_items = len(self.return_items)

        # Separate consumables and non-consumables for summary
        consumables = [item for item in self.return_items if item.is_consumable]
        non_consumables = [item for item in self.return_items if not item.is_consumable]

        summary_parts = [f"Items: {total_items} total     "]

        # Add appropriate labels
        if consumables:
            total_returned = sum(item.quantity_returned for item in consumables)
            summary_parts.append(f"     Consumables returned: {total_returned}     ")

        if non_consumables:
            total_lost = sum(item.quantity_lost for item in non_consumables)
            total_defective = sum(item.quantity_defective for item in non_consumables)
            summary_parts.append(f"     Non-consumables lost: {total_lost}     ")
            if total_defective > 0:
                summary_parts.append(f"     Defective: {total_defective}     ")

        self.summary_label.setText(" | ".join(summary_parts))

        # Button stays enabled - validation happens during processing

    def _collect_defective_condition_types(self) -> dict:
        """Collect condition types from widgets for defective items.

        Returns:
            Dict mapping item_id to condition_type string
        """
        condition_types = {}
        for widget in self.item_widgets:
            if (
                not widget.return_item.is_consumable
                and widget.return_item.quantity_defective > 0
            ):
                condition_types[widget.return_item.item_id] = (
                    widget.get_condition_type()
                )
        return condition_types

    def process_returns(self):
        """Process the final returns - one-time operation."""
        try:
            # Confirm one-time processing
            reply = QMessageBox.question(
                self,
                "Confirm Final Processing",
                "⚠️ This will process all returns and LOCK the requisition permanently.\n\n"
                "• Edit and Return buttons will be disabled\n"
                "• Only deletion will be allowed\n\n"
                "Are you sure you want to proceed?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if reply != QMessageBox.StandardButton.Yes:
                return

            # Get editor name
            editor_name, ok = QInputDialog.getText(
                self, "Editor Information", "Enter your name/initials (required):"
            )

            if not ok or not editor_name.strip():
                QMessageBox.warning(self, "Required", "Editor name is required.")
                return

            # Collect condition types from widgets before processing
            condition_types = self._collect_defective_condition_types()

            # Process final returns (includes defective items recording)
            success = self.return_processor.process_returns(
                self.requisition_id,
                self.return_items,
                editor_name.strip(),
                condition_types,
            )

            if success:
                QMessageBox.information(
                    self,
                    "Success",
                    "✅ Returns processed successfully!\n\n"
                    "• Stock movements have been recorded\n"
                    "• Requisition is now LOCKED\n"
                    "• Edit and Return buttons are disabled",
                )
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to process returns.")

        except Exception as e:
            logger.error(f"Failed to process returns: {e}")
            QMessageBox.critical(self, "Error", f"Failed to process returns: {str(e)}")

    def _get_requisition(self, requisition_id: int) -> Optional[Requisition]:
        """Get requisition by ID."""
        try:
            query = "SELECT * FROM Requisitions WHERE id = ?"
            rows = db.execute_query(query, (requisition_id,))
            if not rows:
                return None

            req_dict = dict(rows[0])
            # Convert dates using date_utils
            if req_dict.get("expected_request"):
                req_dict["expected_request"] = parse_datetime_iso(
                    req_dict["expected_request"]
                )
            if req_dict.get("expected_return"):
                req_dict["expected_return"] = parse_datetime_iso(
                    req_dict["expected_return"]
                )
            if req_dict.get("lab_activity_date"):
                req_dict["lab_activity_date"] = parse_date_iso(
                    req_dict["lab_activity_date"]
                )

            return Requisition(**req_dict)
        except Exception as e:
            logger.error(f"Failed to get requisition {requisition_id}: {e}")
            return None

    def _get_requester(self, requester_id: int) -> Optional[Requester]:
        """Get requester by ID."""
        try:
            return Requester.get_by_id(requester_id)
        except Exception as e:
            logger.error(f"Failed to get requester {requester_id}: {e}")
            return None

    def _get_item_names(self) -> dict:
        """Get item names for display."""
        try:
            item_ids = [item.item_id for item in self.return_items]
            if not item_ids:
                return {}

            # Create placeholders for the IN clause
            placeholders = ",".join("?" * len(item_ids))

            query = f"SELECT id, name FROM Items WHERE id IN ({placeholders})"
            rows = db.execute_query(query, tuple(item_ids))

            return {row["id"]: row["name"] for row in rows}
        except Exception as e:
            logger.error(f"Failed to get item names: {e}")
            return {}
