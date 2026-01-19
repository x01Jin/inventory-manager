"""
Item service - handles item-related business logic operations.
Provides centralized item management with composition pattern.
"""

from typing import List, Dict, Optional
from inventory_app.database.connection import db
from inventory_app.database.models import Category, Supplier
from inventory_app.utils.logger import logger
from inventory_app.services.movement_types import MovementType
from inventory_app.services.stock_calculation_service import stock_calculation_service
from inventory_app.gui.reports.columns import inventory_common_joins_sql
import warnings


class ItemService:
    """
    Service for item-related operations.
    Handles item queries, availability checks, and dictionary building.
    """

    def __init__(self):
        """Initialize the item service."""
        logger.info("Item service initialized")

    # Removed redundant build_item_dict method - using batch-centric approach now

    def get_inventory_items_for_selection(
        self,
        search_term: Optional[str] = None,
        exclude_requested: bool = True,
        exclude_requisition_id: Optional[int] = None,
    ) -> List[Dict]:
        """
        Get inventory items formatted for selection in requisitions.
        LEGACY METHOD: Now delegates to batch-centric method for backward compatibility.

        Args:
            search_term: Optional search term to filter items
            exclude_requested: Whether to exclude currently Requested items
            exclude_requisition_id: Requisition ID to exclude from requested check

        Returns:
            List of item dictionaries
        """
        # Deprecated: Use batch-centric selection APIs (`get_inventory_batches_for_selection`) where possible
        with warnings.catch_warnings():
            warnings.simplefilter("once", DeprecationWarning)
            warnings.warn(
                "get_inventory_items_for_selection() is deprecated and will be removed in a future release; use get_inventory_batches_for_selection() instead",
                DeprecationWarning,
                stacklevel=2,
            )
        batch_data = self.get_inventory_batches_for_selection(
            search_term, exclude_requested, exclude_requisition_id
        )
        return self._convert_batch_data_to_item_format(batch_data)

    def get_inventory_batches_for_selection(
        self,
        search_term: Optional[str] = None,
        exclude_requested: bool = True,
        exclude_requisition_id: Optional[int] = None,
    ) -> List[Dict]:
        """
        Get inventory batches formatted for selection in requisitions.
        Shows individual batches with their specific available stock.

        Optimized to calculate available stock in a single query instead of
        making individual queries per batch.

        Args:
            search_term: Optional search term to filter batches
            exclude_requested: Whether to exclude batches with no available stock
            exclude_requisition_id: Requisition ID to exclude from requested check

        Returns:
            List of batch dictionaries with availability info
        """
        try:
            # Build optimized query that calculates available stock inline
            # This avoids N+1 query problem by calculating stock in single query
            query = (
                """
            SELECT
                ib.id as batch_id,
                ib.item_id,
                ib.batch_number,
                ib.date_received,
                ib.quantity_received,
                i.name as item_name,
                i.category_id,
                i.size,
                i.brand,
                i.other_specifications,
                c.name as category_name,
                s.name as supplier_name,
                i.is_consumable,
                -- Calculate total stock: received - consumed - disposed + returned
                (
                    ib.quantity_received
                    - COALESCE(
                        (SELECT SUM(sm.quantity) FROM Stock_Movements sm 
                         WHERE sm.batch_id = ib.id AND sm.movement_type = ?), 0
                    )
                    - COALESCE(
                        (SELECT SUM(sm.quantity) FROM Stock_Movements sm 
                         WHERE sm.batch_id = ib.id AND sm.movement_type = ?), 0
                    )
                    + COALESCE(
                        (SELECT SUM(sm.quantity) FROM Stock_Movements sm 
                         WHERE sm.batch_id = ib.id AND sm.movement_type = ?), 0
                    )
                ) as total_stock,
                -- Calculate requested quantity (RESERVATION for consumables, REQUEST for non-consumables)
                COALESCE(
                    (SELECT SUM(sm.quantity) FROM Stock_Movements sm
                     WHERE sm.batch_id = ib.id
                       AND sm.movement_type IN (?, ?)
                       AND (? = -1 OR sm.source_id != ?)), 0
                ) as requested_qty
            FROM Item_Batches ib
            JOIN Items i ON ib.item_id = i.id
            """
                + inventory_common_joins_sql()
                + """
            WHERE ib.disposal_date IS NULL
            """
            )

            # Base params for movement types and exclusion
            params = [
                MovementType.CONSUMPTION.value,
                MovementType.DISPOSAL.value,
                MovementType.RETURN.value,
                MovementType.RESERVATION.value,
                MovementType.REQUEST.value,
                exclude_requisition_id if exclude_requisition_id else -1,
                exclude_requisition_id if exclude_requisition_id else -1,
            ]

            if search_term:
                query += " AND i.name LIKE ?"
                params.append(f"%{search_term}%")

            query += " ORDER BY i.name, ib.date_received DESC"

            rows = db.execute_query(query, tuple(params))

            result = []
            for row in rows:
                batch_dict = dict(row)

                # Calculate available stock from the query results
                total_stock = batch_dict.get("total_stock", 0) or 0
                requested_qty = batch_dict.get("requested_qty", 0) or 0
                available_stock = max(0, total_stock - requested_qty)

                # Skip batches with no available stock if exclude_requested is True
                if exclude_requested and available_stock <= 0:
                    continue

                # Add availability information
                batch_dict.update(
                    {
                        "available_stock": available_stock,
                        "total_stock": total_stock,
                        "batch_display_name": f"{batch_dict['item_name']} (Batch #{batch_dict['batch_number']})",
                    }
                )

                result.append(batch_dict)

            return result

        except Exception as e:
            logger.error(f"Failed to get inventory batches: {e}")
            return []

    def _convert_batch_data_to_item_format(self, batch_data: List[Dict]) -> List[Dict]:
        """
        Convert batch data to item format for backward compatibility.
        Aggregates batch information into item-level data.

        Args:
            batch_data: List of batch dictionaries

        Returns:
            List of item dictionaries
        """
        try:
            # Group batches by item
            item_groups = {}
            for batch in batch_data:
                item_id = batch["item_id"]
                if item_id not in item_groups:
                    item_groups[item_id] = {
                        "id": item_id,
                        "name": batch["item_name"],
                        "category_name": batch["category_name"],
                        "supplier_name": batch["supplier_name"],
                        "size": batch["size"],
                        "brand": batch["brand"],
                        "other_specifications": batch["other_specifications"],
                        "is_consumable": batch["is_consumable"],
                        "total_stock": 0,
                        "available_stock": 0,
                        "batches": [],
                    }

                # Aggregate stock information
                item_groups[item_id]["total_stock"] += batch["total_stock"]
                item_groups[item_id]["available_stock"] += batch["available_stock"]
                item_groups[item_id]["batches"].append(batch)

            return list(item_groups.values())

        except Exception as e:
            logger.error(f"Failed to convert batch data to item format: {e}")
            return []

    def get_requisition_items_with_details(self, requisition_id: int) -> List[Dict]:
        """
        Get detailed item information for a specific requisition.

        Args:
            requisition_id: ID of the requisition

        Returns:
            List of item details with quantities
        """
        try:
            query = """
            SELECT ri.item_id, ri.quantity_requested, i.name, i.category_id, i.size, i.brand,
                c.name as category_name, s.name as supplier_name
            FROM Requisition_Items ri
            JOIN Items i ON ri.item_id = i.id
            LEFT JOIN Categories c ON i.category_id = c.id
            LEFT JOIN Suppliers s ON i.supplier_id = s.id
            WHERE ri.requisition_id = ?
            """
            rows = db.execute_query(query, (requisition_id,))
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get requisition items for {requisition_id}: {e}")
            return []

    def _get_category_name(self, category_id: int) -> str:
        """Get category name by ID."""
        try:
            category = Category.get_by_id(category_id)
            return category.name if category else "Unknown"
        except Exception:
            return "Unknown"

    def _get_supplier_name(self, supplier_id: Optional[int]) -> str:
        """Get supplier name by ID."""
        try:
            if supplier_id is None:
                return "Unknown"
            supplier = Supplier.get_by_id(supplier_id)
            return supplier.name if supplier else "Unknown"
        except Exception:
            return "Unknown"

    def _get_total_stock(self, item_id: int) -> int:
        """Get total stock for an item accounting for all stock movements."""
        return stock_calculation_service.calculate_total_stock(item_id)

    def _get_available_stock_for_batch(
        self, batch_id: int, exclude_requisition_id: Optional[int] = None
    ) -> int:
        """
        Get available stock for a specific batch using consistent calculations.
        Accounts for all stock movements: CONSUMPTION, DISPOSAL, RETURN.

        Args:
            batch_id: ID of the batch
            exclude_requisition_id: Requisition ID to exclude from requested calculation (for editing)

        Returns:
            Available stock for the batch
        """
        try:
            total_stock = stock_calculation_service.calculate_batch_stock(batch_id)

            requested_query = """
            SELECT COALESCE(SUM(sm.quantity), 0) as requested_qty
            FROM Stock_Movements sm
            JOIN Items i ON sm.item_id = i.id
            WHERE sm.batch_id = ?
            AND (
                (i.is_consumable = 1 AND sm.movement_type = ?) OR
                (i.is_consumable = 0 AND sm.movement_type = ?)
            )
            """

            params = (
                batch_id,
                MovementType.RESERVATION.value,
                MovementType.REQUEST.value,
            )
            if exclude_requisition_id:
                requested_query += " AND sm.source_id != ?"
                params = (
                    batch_id,
                    MovementType.RESERVATION.value,
                    MovementType.REQUEST.value,
                    exclude_requisition_id,
                )

            requested_rows = db.execute_query(requested_query, params)
            requested_qty = requested_rows[0]["requested_qty"] if requested_rows else 0

            return max(0, total_stock - requested_qty)

        except Exception as e:
            logger.error(f"Failed to get available stock for batch {batch_id}: {e}")
            return 0

    def get_available_stock_for_batch_excluding_requisition(
        self, batch_id: int, exclude_requisition_id: int
    ) -> int:
        """
        Get available stock for a batch, excluding a specific requisition's stock movements.
        This is used during editing to show correct available stock.

        Args:
            batch_id: ID of the batch
            exclude_requisition_id: Requisition ID to exclude from calculations

        Returns:
            Available stock excluding the specified requisition
        """
        return self._get_available_stock_for_batch(batch_id, exclude_requisition_id)
