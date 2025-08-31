"""
Inventory statistics widget.
Displays quick statistics about the inventory.
"""

from typing import Dict, Any
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QGroupBox
from inventory_app.utils.logger import logger


class InventoryStats(QWidget):
    """Widget for displaying inventory statistics."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        logger.info("Inventory stats initialized")

    def setup_ui(self):
        """Setup the statistics UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # Statistics group
        stats_group = QGroupBox("Quick Statistics")
        stats_layout = QHBoxLayout(stats_group)
        stats_layout.setContentsMargins(10, 10, 10, 10)
        stats_layout.setSpacing(20)

        # Total items
        self.total_label = QLabel("📦 Total Items: 0")
        stats_layout.addWidget(self.total_label)

        # Consumable items
        self.consumable_label = QLabel("🔄 Consumable: 0")
        stats_layout.addWidget(self.consumable_label)

        # Non-consumable items
        self.non_consumable_label = QLabel("🔧 Equipment: 0")
        stats_layout.addWidget(self.non_consumable_label)

        # Alerts
        self.alerts_label = QLabel("⚠️ Alerts: 0")
        stats_layout.addWidget(self.alerts_label)

        # Expiration alerts
        self.expiration_label = QLabel("⏰ Expiring: 0")
        stats_layout.addWidget(self.expiration_label)

        # Calibration alerts
        self.calibration_label = QLabel("🔧 Calibration: 0")
        stats_layout.addWidget(self.calibration_label)

        stats_layout.addStretch()
        layout.addWidget(stats_group)

    def update_statistics(self, stats: Dict[str, Any]):
        """Update the statistics display."""
        try:
            self.total_label.setText(f"📦 Total Items: {stats.get('total_items', 0)}")
            self.consumable_label.setText(f"🔄 Consumable: {stats.get('consumable_items', 0)}")
            self.non_consumable_label.setText(f"🔧 Equipment: {stats.get('non_consumable_items', 0)}")
            self.alerts_label.setText(f"⚠️ Alerts: {stats.get('total_alerts', 0)}")
            self.expiration_label.setText(f"⏰ Expiring: {stats.get('expiring_alerts', 0)}")
            self.calibration_label.setText(f"🔧 Calibration: {stats.get('calibration_alerts', 0)}")

            logger.debug(f"Updated statistics: {stats}")

        except Exception as e:
            logger.error(f"Error updating statistics: {e}")

    def clear_statistics(self):
        """Clear all statistics to default values."""
        default_stats = {
            "total_items": 0,
            "consumable_items": 0,
            "non_consumable_items": 0,
            "total_alerts": 0,
            "expiring_alerts": 0,
            "calibration_alerts": 0
        }
        self.update_statistics(default_stats)
        logger.debug("Statistics cleared")
