"""Background worker for dashboard metrics loading.

Consolidates multiple database queries into fewer calls for better performance.
"""

from typing import Dict, Any
from datetime import datetime, timedelta

from inventory_app.database.connection import db
from inventory_app.utils.logger import logger
from inventory_app.services.movement_types import MovementType
from inventory_app.services.item_status_service import item_status_service


def get_consolidated_metrics() -> Dict[str, Any]:
    """
    Get all dashboard metrics in consolidated database queries.
    Consolidates most dashboard metrics into optimized DB queries and
    sources alert-related counts from the shared status service.

    Returns:
        Dictionary with all metric values
    """
    try:
        metrics = {}
        today = datetime.now().date()

        # Query 1: Item counts (total items, recent adds)
        items_query = """
            SELECT
                COUNT(*) as total_items,
                COUNT(CASE WHEN last_modified >= ? THEN 1 END) as recent_adds
            FROM Items
        """
        recent_date = (today - timedelta(days=7)).isoformat()
        items_result = db.execute_query(items_query, (recent_date,))
        if items_result:
            metrics["total_items"] = items_result[0]["total_items"] or 0
            metrics["recent_adds"] = items_result[0]["recent_adds"] or 0

        # Query 2: Stock calculations (total stock, low stock)
        stock_query = """
            SELECT
                COALESCE(SUM(ib.quantity_received), 0) -
                COALESCE(movements.total_consumed, 0) -
                COALESCE(movements.total_disposed, 0) +
                COALESCE(movements.total_returned, 0) as total_stock,
                COUNT(CASE WHEN stock_calc.current_stock < 10 AND stock_calc.current_stock > 0 THEN 1 END) as low_stock
            FROM Item_Batches ib
            LEFT JOIN (
                SELECT
                    ib.item_id,
                    SUM(ib.quantity_received) -
                    COALESCE(SUM(CASE WHEN sm.movement_type = ? THEN sm.quantity ELSE 0 END), 0) -
                    COALESCE(SUM(CASE WHEN sm.movement_type = ? THEN sm.quantity ELSE 0 END), 0) +
                    COALESCE(SUM(CASE WHEN sm.movement_type = ? THEN sm.quantity ELSE 0 END), 0) as current_stock
                FROM Item_Batches ib
                LEFT JOIN Stock_Movements sm ON sm.item_id = ib.item_id
                WHERE ib.disposal_date IS NULL
                GROUP BY ib.item_id
            ) stock_calc ON ib.item_id = stock_calc.item_id
            CROSS JOIN (
                SELECT
                    SUM(CASE WHEN movement_type = ? THEN quantity ELSE 0 END) as total_consumed,
                    SUM(CASE WHEN movement_type = ? THEN quantity ELSE 0 END) as total_disposed,
                    SUM(CASE WHEN movement_type = ? THEN quantity ELSE 0 END) as total_returned
                FROM Stock_Movements
            ) movements
            WHERE ib.disposal_date IS NULL
        """
        stock_params = (
            MovementType.CONSUMPTION.value,
            MovementType.DISPOSAL.value,
            MovementType.RETURN.value,
            MovementType.CONSUMPTION.value,
            MovementType.DISPOSAL.value,
            MovementType.RETURN.value,
        )
        stock_result = db.execute_query(stock_query, stock_params)
        if stock_result:
            metrics["total_stock"] = stock_result[0]["total_stock"] or 0
            metrics["low_stock"] = stock_result[0]["low_stock"] or 0

        # Expiring count is sourced from the shared status service so dashboard
        # metric windows match the alerts panel logic.
        alert_counts = item_status_service.get_alert_counts()
        metrics["expiring_soon"] = alert_counts.get("expiring", 0)

        # Query 4: Requisition counts (all statuses in one query)
        reqs_query = """
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN status = 'requested' THEN 1 END) as requested,
                COUNT(CASE WHEN status = 'active' THEN 1 END) as active,
                COUNT(CASE WHEN status = 'overdue' THEN 1 END) as overdue
            FROM Requisitions
            WHERE status IN ('requested', 'active', 'overdue')
        """
        reqs_result = db.execute_query(reqs_query)
        if reqs_result:
            metrics["ongoing_reqs"] = reqs_result[0]["total"] or 0
            metrics["requested_reqs"] = reqs_result[0]["requested"] or 0
            metrics["active_reqs"] = reqs_result[0]["active"] or 0
            metrics["overdue_reqs"] = reqs_result[0]["overdue"] or 0

        return metrics

    except Exception as e:
        logger.error(f"Failed to get consolidated metrics: {e}")
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
