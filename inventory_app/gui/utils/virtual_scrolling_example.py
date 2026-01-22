"""
Factory functions for creating VirtualTableModel instances for inventory data.

Provides callbacks for fetching inventory items with pagination support,
including status caching for styled row display.
"""

from typing import List, Dict, Any, Callable, Optional, TYPE_CHECKING
from inventory_app.utils.logger import logger

if TYPE_CHECKING:
    from inventory_app.gui.utils.virtual_table_model import VirtualTableModel


def create_inventory_fetch_callback(
    filters: Optional[Dict[str, Any]] = None,
) -> Callable[[int, int], List[Dict[str, Any]]]:
    """
    Create a fetch callback for inventory data.

    Args:
        filters: Optional filters to apply (search, category, supplier)

    Returns:
        Function(start, limit) -> List of row dictionaries
    """
    from inventory_app.database.connection import get_db_connection

    def fetch(start: int, limit: int) -> List[Dict[str, Any]]:
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()

                base_query = """
                    SELECT i.id, i.name, i.size, i.brand, i.other_specifications,
                           s.name as supplier_name, i.calibration_date, i.expiration_date,
                           i.is_consumable, i.acquisition_date, i.last_modified,
                           COALESCE(SUM(ib.quantity), 0) as total_stock,
                           COALESCE(SUM(CASE WHEN ib.expiration_date > date('now') THEN ib.quantity ELSE 0 END), 0) as available_stock
                    FROM Items i
                    LEFT JOIN Item_Batches ib ON i.id = ib.item_id
                    LEFT JOIN Suppliers s ON i.supplier_id = s.id
                """

                where_clauses = []
                params = []

                if filters:
                    search = filters.get("search", "").strip()
                    if search:
                        where_clauses.append(
                            "(i.name LIKE ? OR i.other_specifications LIKE ?)"
                        )
                        params.extend([f"%{search}%", f"%{search}%"])

                    category = filters.get("category", "").strip()
                    if category:
                        where_clauses.append(
                            "i.category_id IN (SELECT id FROM Categories WHERE name = ?)"
                        )
                        params.append(category)

                    supplier = filters.get("supplier", "").strip()
                    if supplier:
                        where_clauses.append("s.name = ?")
                        params.append(supplier)

                if where_clauses:
                    base_query += " WHERE " + " AND ".join(where_clauses)

                base_query += """
                    GROUP BY i.id
                    ORDER BY i.name
                    LIMIT ? OFFSET ?
                """

                params.extend([limit, start])

                cursor.execute(base_query, params)
                columns = [desc[0] for desc in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]

                logger.debug(f"Fetched {len(results)} rows starting at {start}")
                return results

        except Exception as e:
            logger.error(f"Error fetching inventory data: {e}")
            return []

    return fetch


def create_status_fetch_callback() -> Callable[[List[int]], Dict[int, Any]]:
    """
    Create a callback for fetching item statuses.

    Returns:
        Function(item_ids) -> Dict mapping item_id to status
    """
    from inventory_app.services.item_status_service import item_status_service

    def fetch(item_ids: List[int]) -> Dict[int, Any]:
        if not item_ids:
            return {}
        try:
            return item_status_service.get_statuses_for_items(item_ids)
        except Exception as e:
            logger.error(f"Error fetching statuses: {e}")
            return {}

    return fetch


def get_inventory_count(filters: Optional[Dict[str, Any]] = None) -> int:
    """
    Get total count of inventory items (for setting model row count).

    Args:
        filters: Optional filters to apply

    Returns:
        Total number of matching items
    """
    from inventory_app.database.connection import get_db_connection

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            base_query = "SELECT COUNT(DISTINCT i.id) FROM Items i LEFT JOIN Item_Batches ib ON i.id = ib.item_id LEFT JOIN Suppliers s ON i.supplier_id = s.id"

            where_clauses = []
            params = []

            if filters:
                search = filters.get("search", "").strip()
                if search:
                    where_clauses.append(
                        "(i.name LIKE ? OR i.other_specifications LIKE ?)"
                    )
                    params.extend([f"%{search}%", f"%{search}%"])

                category = filters.get("category", "").strip()
                if category:
                    where_clauses.append(
                        "i.category_id IN (SELECT id FROM Categories WHERE name = ?)"
                    )
                    params.append(category)

                supplier = filters.get("supplier", "").strip()
                if supplier:
                    where_clauses.append("s.name = ?")
                    params.append(supplier)

            if where_clauses:
                base_query += " WHERE " + " AND ".join(where_clauses)

            cursor.execute(base_query, params)
            result = cursor.fetchone()
            return result[0] if result else 0

    except Exception as e:
        logger.error(f"Error counting inventory items: {e}")
        return 0


def create_inventory_virtual_model(
    filters: Optional[Dict[str, Any]] = None, parent: Optional[Any] = None
) -> "VirtualTableModel":
    """
    Factory function to create a configured VirtualTableModel for inventory.

    Args:
        filters: Optional filters to apply
        parent: Parent QObject

    Returns:
        Configured VirtualTableModel instance
    """
    from inventory_app.gui.utils.virtual_table_model import VirtualTableModel

    total_count = get_inventory_count(filters)

    columns = [
        "Stock/Available",
        "Name",
        "Size",
        "Brand",
        "Other Specifications",
        "Supplier",
        "Calibration Date",
        "Expiry/Disposal Date",
        "Item Type",
        "Acquisition Date",
        "Last Modified",
    ]

    model = VirtualTableModel(
        total_rows=total_count,
        fetch_callback=create_inventory_fetch_callback(filters),
        columns=columns,
        parent=parent,
        status_fetch_callback=create_status_fetch_callback(),
    )

    return model
