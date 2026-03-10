"""
Metrics management for the dashboard.
Handles metric calculations and card creation.
"""

from typing import Dict, Optional

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox, QGridLayout
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPainter

from inventory_app.gui.styles import get_current_theme
from inventory_app.database.connection import db
from inventory_app.utils.logger import logger
from inventory_app.services.movement_types import MovementType
from inventory_app.services.item_status_service import item_status_service


class SkeletonCard(QGroupBox):
    """Skeleton loading card with animated pulse effect."""

    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        self.setStyleSheet("""
            QGroupBox {
                background-color: transparent;
                border: 1px solid #3a3a3a;
                border-radius: 5px;
                padding: 8px;
                font-size: 9pt;
            }
        """)
        self._pulse_value = 0
        self._pulse_direction = 1
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)

        self.value_label = QLabel("...")
        self.value_label.setStyleSheet("""
            font-size: 18pt;
            font-weight: bold;
            border: none;
            background-color: transparent;
            color: #666;
        """)
        self.value_label.setObjectName("skeleton_value")
        layout.addWidget(self.value_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self._animation_timer = QTimer(self)
        self._animation_timer.timeout.connect(self._animate_pulse)
        self._animation_timer.start(50)

    def _animate_pulse(self):
        self._pulse_value += 0.1 * self._pulse_direction
        if self._pulse_value >= 1.0:
            self._pulse_value = 1.0
            self._pulse_direction = -1
        elif self._pulse_value <= 0.0:
            self._pulse_value = 0.0
            self._pulse_direction = 1
        self.update()

    def paintEvent(self, a0):
        super().paintEvent(a0)
        if hasattr(self, "_pulse_value"):
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            color = QColor(60, 60, 60)
            color.setAlphaF(0.3 + self._pulse_value * 0.2)
            painter.fillRect(self.rect(), color)


class MetricsManager:
    """Manager for dashboard metrics."""

    def __init__(self):
        pass

    def create_compact_metric_card(self, title: str, value: str, loading: bool = False):
        """Create a compact metric card widget."""
        Theme = get_current_theme()
        card = QGroupBox(title)
        card.setStyleSheet(
            f"background-color: {Theme.SECONDARY_DARK}; border: 1px solid {Theme.BORDER_COLOR}; border-radius: 5px; padding: 8px; font-size: 9pt;"
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)

        if loading:
            value_label = QLabel("...")
        else:
            value_label = QLabel(value)
        value_label.setStyleSheet(f"""
            font-size: {Theme.FONT_SIZE_HEADER}pt; 
            font-weight: bold;
            border: none;
            background-color: transparent;
        """)
        value_label.setObjectName("value_label")

        layout.addWidget(value_label, alignment=Qt.AlignmentFlag.AlignCenter)

        return card

    def create_skeleton_metric_card(self, title: str):
        """Create a skeleton loading card for metrics."""
        return SkeletonCard(title)

    def get_metric_keys(self):
        """Get the list of metric keys and their display names."""
        return [
            ("total_items", "📦 Total Items"),
            ("total_stock", "📊 Total Stock"),
            ("recent_adds", "🆕 Recent Adds"),
            ("low_stock", "⚠️ Low Stock"),
            ("expiring_soon", "⏰ Expiring Soon"),
            ("ongoing_reqs", "📋 Ongoing Reqs"),
            ("requested_reqs", "📝 Requested Reqs"),
            ("active_reqs", "🔄 Active Reqs"),
            ("overdue_reqs", "🚨 Overdue Reqs"),
        ]

    def get_all_metrics(self):
        """Get all metric data from database."""
        try:
            metrics = {}

            # Total items
            items_query = "SELECT COUNT(*) as count FROM Items"
            items_result = db.execute_query(items_query)
            metrics["total_items"] = items_result[0]["count"] if items_result else 0

            # Total stock
            stock_query = """
            SELECT
                COALESCE(SUM(ib.quantity_received), 0) -
                COALESCE(movements.total_consumed, 0) -
                COALESCE(movements.total_disposed, 0) +
                COALESCE(movements.total_returned, 0) as total_stock
            FROM Item_Batches ib
            LEFT JOIN (
                SELECT
                    SUM(CASE WHEN movement_type = ? THEN quantity ELSE 0 END) as total_consumed,
                    SUM(CASE WHEN movement_type = ? THEN quantity ELSE 0 END) as total_disposed,
                    SUM(CASE WHEN movement_type = ? THEN quantity ELSE 0 END) as total_returned
                FROM Stock_Movements
            ) movements ON 1=1
            WHERE ib.disposal_date IS NULL
            """
            stock_params = (
                MovementType.CONSUMPTION.value,
                MovementType.DISPOSAL.value,
                MovementType.RETURN.value,
            )
            stock_result = db.execute_query(stock_query, stock_params)
            metrics["total_stock"] = (
                stock_result[0]["total_stock"]
                if stock_result and stock_result[0]["total_stock"]
                else 0
            )

            # Low stock items (stock < 10)
            low_stock_query = """
            SELECT COUNT(*) as count FROM (
                SELECT ib.item_id,
                        SUM(ib.quantity_received) -
                        COALESCE(SUM(CASE WHEN sm.movement_type = ? THEN sm.quantity ELSE 0 END), 0) -
                        COALESCE(SUM(CASE WHEN sm.movement_type = ? THEN sm.quantity ELSE 0 END), 0) +
                        COALESCE(SUM(CASE WHEN sm.movement_type = ? THEN sm.quantity ELSE 0 END), 0) as current_stock
                FROM Item_Batches ib
                LEFT JOIN Stock_Movements sm ON sm.item_id = ib.item_id
                WHERE ib.disposal_date IS NULL
                GROUP BY ib.item_id
                HAVING current_stock < 10 AND current_stock > 0
            )
            """
            low_stock_params = (
                MovementType.CONSUMPTION.value,
                MovementType.DISPOSAL.value,
                MovementType.RETURN.value,
            )
            low_stock_result = db.execute_query(low_stock_query, low_stock_params)
            metrics["low_stock"] = (
                low_stock_result[0]["count"] if low_stock_result else 0
            )

            # Keep metric windows consistent with alert status logic.
            alert_counts = item_status_service.get_alert_counts()
            metrics["expiring_soon"] = alert_counts.get("expiring", 0)

            from datetime import datetime, timedelta

            # Recent additions (last 7 days)
            recent_date = (datetime.now() - timedelta(days=7)).date().isoformat()
            recent_query = (
                "SELECT COUNT(*) as count FROM Items WHERE last_modified >= ?"
            )
            recent_result = db.execute_query(recent_query, (recent_date,))
            metrics["recent_adds"] = recent_result[0]["count"] if recent_result else 0

            # Ongoing requisitions (requested + active + overdue)
            ongoing_reqs_query = "SELECT COUNT(*) as count FROM Requisitions WHERE status IN ('requested', 'active', 'overdue')"
            ongoing_result = db.execute_query(ongoing_reqs_query)
            metrics["ongoing_reqs"] = (
                ongoing_result[0]["count"] if ongoing_result else 0
            )

            # Requested requisitions
            requested_reqs_query = (
                "SELECT COUNT(*) as count FROM Requisitions WHERE status = 'requested'"
            )
            requested_result = db.execute_query(requested_reqs_query)
            metrics["requested_reqs"] = (
                requested_result[0]["count"] if requested_result else 0
            )

            # Active requisitions
            active_reqs_query = (
                "SELECT COUNT(*) as count FROM Requisitions WHERE status = 'active'"
            )
            active_result = db.execute_query(active_reqs_query)
            metrics["active_reqs"] = active_result[0]["count"] if active_result else 0

            # Overdue requisitions
            overdue_reqs_query = (
                "SELECT COUNT(*) as count FROM Requisitions WHERE status = 'overdue'"
            )
            overdue_result = db.execute_query(overdue_reqs_query)
            metrics["overdue_reqs"] = (
                overdue_result[0]["count"] if overdue_result else 0
            )

            return metrics

        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return {
                "total_items": 0,
                "total_stock": 0,
                "recent_adds": 0,
                "low_stock": 0,
                "expiring_soon": 0,
                "ongoing_reqs": 0,
                "requested_reqs": 0,
                "active_reqs": 0,
                "overdue_reqs": 0,
            }

    def create_metrics_widget(self, loading: bool = False):
        """Create a widget containing all metric cards in a compact grid."""

        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        metric_keys = self.get_metric_keys()

        for i, (key, title) in enumerate(metric_keys):
            row = i // 3
            col = i % 3
            value = "..." if loading else "0"
            card = self.create_compact_metric_card(title, value, loading)
            layout.addWidget(card, row, col)

        return widget

    def update_metrics_widget(
        self, metrics_widget, metrics: Optional[Dict[str, int]] = None
    ):
        """Update the metrics widget with current data."""
        try:
            if metrics is None:
                metrics = self.get_all_metrics()
            metric_keys = self.get_metric_keys()

            layout = metrics_widget.layout()
            if not layout:
                return

            for i, (key, title) in enumerate(metric_keys):
                value = str(metrics.get(key, 0))
                card = layout.itemAt(i).widget()
                if card:
                    card_layout = card.layout()
                    if card_layout and card_layout.count() >= 1:
                        value_label = card_layout.itemAt(0).widget()
                        if hasattr(value_label, "setText"):
                            value_label.setText(value)

        except Exception as e:
            logger.error(f"Failed to update metrics widget: {e}")
