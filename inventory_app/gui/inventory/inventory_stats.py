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

        # Total batches
        self.total_label = QLabel("📦 Total Batches: 0")
        stats_layout.addWidget(self.total_label)

        # Total stock
        self.total_stock_label = QLabel("🔄 Total Stock: 0")
        stats_layout.addWidget(self.total_stock_label)

        # Available stock
        self.available_stock_label = QLabel("✅ Available Stock: 0")
        stats_layout.addWidget(self.available_stock_label)

        # Low stock
        self.low_stock_label = QLabel("⚠️ Low Stock: 0")
        stats_layout.addWidget(self.low_stock_label)

        # Alert statistics
        self.expiring_label = QLabel("⏰ Expiring: 0")
        stats_layout.addWidget(self.expiring_label)

        self.expired_label = QLabel("❌ Expired: 0")
        stats_layout.addWidget(self.expired_label)

        self.calibration_warning_label = QLabel("🔧 Cal. Warning: 0")
        stats_layout.addWidget(self.calibration_warning_label)

        self.calibration_due_label = QLabel("🔧 Cal. Due: 0")
        stats_layout.addWidget(self.calibration_due_label)

        stats_layout.addStretch()
        layout.addWidget(stats_group)

    def update_statistics(self, stats: Dict[str, Any]):
        """Update the statistics display."""
        try:
            self.total_label.setText(f"📦 Total Batches: {stats.get('total_batches', 0)}")
            self.total_stock_label.setText(f"🔄 Total Stock: {stats.get('total_stock', 0)}")
            self.available_stock_label.setText(f"✅ Available Stock: {stats.get('available_stock', 0)}")
            self.low_stock_label.setText(f"⚠️ Low Stock: {stats.get('low_stock', 0)}")

            # Update alert statistics
            self.expiring_label.setText(f"⏰ Expiring: {stats.get('expiring', 0)}")
            self.expired_label.setText(f"❌ Expired: {stats.get('expired', 0)}")
            self.calibration_warning_label.setText(f"🔧 Cal. Warning: {stats.get('calibration_warning', 0)}")
            self.calibration_due_label.setText(f"🔧 Cal. Due: {stats.get('calibration_due', 0)}")

            logger.debug(f"Updated statistics: {stats}")

        except Exception as e:
            logger.error(f"Error updating statistics: {e}")

    def clear_statistics(self):
        """Clear all statistics to default values."""
        default_stats = {
            "total_batches": 0,
            "total_stock": 0,
            "available_stock": 0,
            "low_stock": 0,
            "expiring": 0,
            "expired": 0,
            "calibration_warning": 0,
            "calibration_due": 0
        }
        self.update_statistics(default_stats)
        logger.debug("Statistics cleared")
