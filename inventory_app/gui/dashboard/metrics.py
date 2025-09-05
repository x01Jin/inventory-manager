"""
Metrics management for the dashboard.
Handles metric calculations and card creation.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox, QGridLayout
from PyQt6.QtCore import Qt

from inventory_app.gui.styles import DarkTheme
from inventory_app.database.connection import db
from inventory_app.utils.logger import logger

class MetricsManager:
    """Manager for dashboard metrics."""

    def __init__(self):
        pass

    def create_compact_metric_card(self, title: str, value: str):
        """Create a compact metric card widget."""
        card = QGroupBox(title)
        card.setStyleSheet(f"background-color: {DarkTheme.SECONDARY_DARK}; border: 1px solid {DarkTheme.BORDER_COLOR}; border-radius: 5px; padding: 8px; font-size: 9pt;")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)

        value_label = QLabel(value)
        value_label.setStyleSheet(f"""
            font-size: {DarkTheme.FONT_SIZE_HEADER}pt; 
            font-weight: bold;
            border: none;
            background-color: transparent;
        """)

        layout.addWidget(value_label, alignment=Qt.AlignmentFlag.AlignCenter)
    
        return card

    def get_metric_keys(self):
        """Get the list of metric keys and their display names."""
        return [
            ('total_items', '📦 Total Items'),
            ('total_stock', '📊 Total Stock'),
            ('recent_adds', '🆕 Recent Adds'),
            ('low_stock', '⚠️ Low Stock'),
            ('expiring_soon', '⏰ Expiring Soon'),
            ('ongoing_reqs', '📋 Ongoing Reqs'),
            ('requested_reqs', '📝 Requested Reqs'),
            ('active_reqs', '🔄 Active Reqs'),
            ('overdue_reqs', '🚨 Overdue Reqs')
        ]
    
    def get_all_metrics(self):
        """Get all metric data from database."""
        try:
            metrics = {}

            # Total items
            items_query = "SELECT COUNT(*) as count FROM Items"
            items_result = db.execute_query(items_query)
            metrics['total_items'] = items_result[0]['count'] if items_result else 0

            # Total stock
            stock_query = """
            SELECT
                COALESCE(SUM(ib.quantity_received), 0) - COALESCE(disposed.disposed_qty, 0) as total_stock
            FROM Item_Batches ib
            LEFT JOIN (
                SELECT SUM(quantity) as disposed_qty
                FROM Stock_Movements
                WHERE movement_type = 'DISPOSAL'
            ) disposed ON 1=1
            WHERE ib.disposal_date IS NULL
            """
            stock_result = db.execute_query(stock_query)
            metrics['total_stock'] = stock_result[0]['total_stock'] if stock_result and stock_result[0]['total_stock'] else 0

            # Low stock items (stock < 10)
            low_stock_query = """
            SELECT COUNT(*) as count FROM (
                SELECT ib.item_id,
                        SUM(ib.quantity_received) - COALESCE(SUM(sm.quantity), 0) as current_stock
                FROM Item_Batches ib
                LEFT JOIN Stock_Movements sm ON sm.item_id = ib.item_id AND sm.movement_type IN ('CONSUMPTION', 'DISPOSAL')
                WHERE ib.disposal_date IS NULL
                GROUP BY ib.item_id
                HAVING current_stock < 10 AND current_stock > 0
            )
            """
            low_stock_result = db.execute_query(low_stock_query)
            metrics['low_stock'] = low_stock_result[0]['count'] if low_stock_result else 0

            # Expiring soon (next 30 days)
            from datetime import datetime, timedelta
            expiry_date = (datetime.now() + timedelta(days=30)).date().isoformat()
            expiring_query = f"SELECT COUNT(*) as count FROM Items WHERE expiration_date <= '{expiry_date}' AND expiration_date IS NOT NULL"
            expiring_result = db.execute_query(expiring_query)
            metrics['expiring_soon'] = expiring_result[0]['count'] if expiring_result else 0

            # Recent additions (last 7 days)
            recent_date = (datetime.now() - timedelta(days=7)).date().isoformat()
            recent_query = f"SELECT COUNT(*) as count FROM Items WHERE last_modified >= '{recent_date}'"
            recent_result = db.execute_query(recent_query)
            metrics['recent_adds'] = recent_result[0]['count'] if recent_result else 0

            # Ongoing requisitions (requested + active + overdue)
            ongoing_reqs_query = "SELECT COUNT(*) as count FROM Requisitions WHERE status IN ('requested', 'active', 'overdue')"
            ongoing_result = db.execute_query(ongoing_reqs_query)
            metrics['ongoing_reqs'] = ongoing_result[0]['count'] if ongoing_result else 0

            # Requested requisitions
            requested_reqs_query = "SELECT COUNT(*) as count FROM Requisitions WHERE status = 'requested'"
            requested_result = db.execute_query(requested_reqs_query)
            metrics['requested_reqs'] = requested_result[0]['count'] if requested_result else 0

            # Active requisitions
            active_reqs_query = "SELECT COUNT(*) as count FROM Requisitions WHERE status = 'active'"
            active_result = db.execute_query(active_reqs_query)
            metrics['active_reqs'] = active_result[0]['count'] if active_result else 0

            # Overdue requisitions
            overdue_reqs_query = "SELECT COUNT(*) as count FROM Requisitions WHERE status = 'overdue'"
            overdue_result = db.execute_query(overdue_reqs_query)
            metrics['overdue_reqs'] = overdue_result[0]['count'] if overdue_result else 0

            return metrics

        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return {
                'total_items': 0, 'total_stock': 0, 'recent_adds': 0,
                'low_stock': 0, 'expiring_soon': 0, 'ongoing_reqs': 0,
                'requested_reqs': 0, 'active_reqs': 0, 'overdue_reqs': 0
            }

    def create_metrics_widget(self):
        """Create a widget containing all metric cards in a compact grid."""
        
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        metrics = self.get_all_metrics()
        metric_keys = self.get_metric_keys()
        
        # Create 3x3 grid of metric cards
        for i, (key, title) in enumerate(metric_keys):
            row = i // 3
            col = i % 3
            value = str(metrics.get(key, 0))
            card = self.create_compact_metric_card(title, value)
            layout.addWidget(card, row, col)
        
        return widget

    def update_metrics_widget(self, metrics_widget):
        """Update the metrics widget with current data."""
        try:
            metrics = self.get_all_metrics()
            metric_keys = self.get_metric_keys()
            
            layout = metrics_widget.layout()
            if not layout:
                return
            
            # Update each card in the grid
            for i, (key, title) in enumerate(metric_keys):
                value = str(metrics.get(key, 0))
                card = layout.itemAt(i).widget()
                if card:
                    # Update the value label (only child in the card's layout)
                    card_layout = card.layout()
                    if card_layout and card_layout.count() >= 1:
                        value_label = card_layout.itemAt(0).widget()
                        if hasattr(value_label, 'setText'):
                            value_label.setText(value)
                            
        except Exception as e:
            logger.error(f"Failed to update metrics widget: {e}")
