"""
Controller for inventory management.
Handles database operations and data loading for inventory items.
"""

from typing import List, Optional, Dict, Any
from datetime import date
from inventory_app.database.connection import db
from inventory_app.services.category_config import get_all_category_names
from inventory_app.services.item_status_service import item_status_service
from inventory_app.services.stock_calculation_service import stock_calculation_service
from inventory_app.services.stock_movement_service import StockMovementService
from inventory_app.utils.logger import logger
from inventory_app.utils.activity_logger import activity_logger
from inventory_app.services.movement_types import MovementType
from inventory_app.gui.reports.columns import inventory_common_joins_sql


class InventoryController:
    """Controller for inventory operations."""

    def __init__(self):
        self.stock_service = StockMovementService()

    def _get_defective_pending_subquery(self) -> str:
        """Return SQL subquery for unresolved defective quantity by item."""
        return """
            SELECT
                pending.item_id,
                COALESCE(SUM(pending.pending_qty), 0) AS defective_count
            FROM (
                SELECT
                    di.id,
                    di.item_id,
                    MAX(0,
                        di.quantity - COALESCE(SUM(
                            CASE
                                WHEN dia.action_type IN ('DISPOSED', 'NOT_DEFECTIVE')
                                THEN dia.quantity
                                ELSE 0
                            END
                        ), 0)
                    ) AS pending_qty
                FROM Defective_Items di
                LEFT JOIN Defective_Item_Actions dia ON dia.defective_item_id = di.id
                GROUP BY di.id, di.item_id, di.quantity
            ) pending
            GROUP BY pending.item_id
        """

    def _get_defective_current_subquery(self) -> str:
        """Return SQL subquery for current-stock defective deduction by item.

        Current stock excludes unresolved defectives.
        Disposed and not-defective confirmations are treated as resolved.
        """
        return """
            SELECT
                current_defectives.item_id,
                COALESCE(SUM(current_defectives.current_defective_qty), 0) AS defective_count
            FROM (
                SELECT
                    di.id,
                    di.item_id,
                    MAX(0,
                        di.quantity - COALESCE(SUM(
                            CASE
                                WHEN dia.action_type IN ('DISPOSED', 'NOT_DEFECTIVE')
                                THEN dia.quantity
                                ELSE 0
                            END
                        ), 0)
                    ) AS current_defective_qty
                FROM Defective_Items di
                LEFT JOIN Defective_Item_Actions dia ON dia.defective_item_id = di.id
                GROUP BY di.id, di.item_id, di.quantity
            ) current_defectives
            GROUP BY current_defectives.item_id
        """

    def _get_stock_calculations(self, item_id: Optional[int] = None) -> str:
        """
        Get consistent stock calculation SQL that accounts for all stock movements.
        Returns SQL subquery for stock calculations.

        Args:
            item_id: Optional item ID filter for single item calculations

        Returns:
            SQL subquery string for stock calculations
        """
        return stock_calculation_service.get_stock_calculation_subquery(item_id)

    def _get_requested_calculations(self) -> str:
        """
        Get consistent requested quantity calculation SQL.
        Two-phase logic: Active requisitions reduce available stock via REQUEST/RESERVATION movements.
        Finalized requisitions don't reduce available stock (movements have been replaced).
        Returns SQL subquery for requested calculations.
        """
        return stock_calculation_service.get_requisition_calculation_subquery()

    def load_inventory_data(self) -> List[Dict[str, Any]]:
        """Load inventory items with related data from database."""
        try:
            query = (
                """
            SELECT
                i.id,
                i.name,
                c.name as category_name,
                i.item_type,
                i.size,
                i.brand,
                s.name as supplier_name,
                i.other_specifications,
                i.po_number,
                i.expiration_date,
                i.calibration_date,
                i.is_consumable,
                COALESCE(ib.first_batch_date, i.acquisition_date) as acquisition_date,
                ib.last_batch_date,
                ib.batch_count,
                ib.batch_summary,
                i.last_modified,
                CASE WHEN sds.item_id IS NOT NULL THEN 1 ELSE 0 END as has_sds,
                COALESCE(defective.defective_count, 0) as defective_count,
                CASE WHEN COALESCE(defective.defective_count, 0) > 0 THEN 1 ELSE 0 END as has_defective,
                MAX(0, COALESCE(stock.total_stock, 0)) as total_stock,
                MAX(0, COALESCE(stock.total_stock, 0) - COALESCE(defective.defective_count, 0) - COALESCE(requested.requested_qty, 0)) as available_stock,
                CASE
                    WHEN EXISTS (
                        SELECT 1 FROM Requisition_Items ri
                        JOIN Requisitions r ON ri.requisition_id = r.id
                        WHERE ri.item_id = i.id
                        AND NOT EXISTS (
                            SELECT 1 FROM Stock_Movements sm
                            WHERE sm.item_id = ri.item_id
                            AND sm.movement_type = ?
                            AND sm.source_id = r.id
                        )
                    ) THEN 1
                    ELSE 0
                END as is_requested
            FROM Items i
            """
                + inventory_common_joins_sql()
                + """
            LEFT JOIN Item_SDS sds ON sds.item_id = i.id
            LEFT JOIN (
                """
                + self._get_defective_current_subquery()
                + """
            ) defective ON defective.item_id = i.id
            LEFT JOIN (
                SELECT
                    item_id,
                    MIN(date_received) as first_batch_date,
                    MAX(date_received) as last_batch_date,
                    COUNT(*) as batch_count,
                    GROUP_CONCAT(
                        'B' || batch_number || ': ' || date_received || ' (' || quantity_received || ' units)',
                        '; '
                    ) as batch_summary
                FROM Item_Batches
                GROUP BY item_id
            ) ib ON i.id = ib.item_id
            LEFT JOIN (
                """
                + self._get_stock_calculations()
                + """
            ) stock ON i.id = stock.item_id
            LEFT JOIN (
                """
                + self._get_requested_calculations()
                + """
            ) requested ON i.id = requested.item_id
            ORDER BY c.name, i.name
            """
            )

            # Prepare ordered params for placeholders inside query text.
            params = (
                # is_requested clause (RETURN)
                MovementType.RETURN.value,
                # _get_stock_calculations() placeholders: CONSUMPTION, DISPOSAL, RETURN
                MovementType.CONSUMPTION.value,
                MovementType.DISPOSAL.value,
                MovementType.RETURN.value,
                # _get_requested_calculations() placeholders: RESERVATION, REQUEST
                MovementType.RESERVATION.value,
                MovementType.REQUEST.value,
            )
            rows = db.execute_query(query, params)
            logger.info(f"Loaded {len(rows)} inventory items from database")
            return rows

        except Exception as e:
            logger.error(f"Error loading inventory data: {e}")
            raise

    def search_items(self, search_term: str) -> List[Dict[str, Any]]:
        """Search items by name, category, or supplier."""
        try:
            if not search_term:
                return []

            query = (
                """
            SELECT
                i.id, i.name, c.name as category_name, i.item_type, i.size, i.brand,
                s.name as supplier_name, i.other_specifications, i.po_number,
                i.expiration_date, i.calibration_date, i.is_consumable,
                COALESCE(ib.first_batch_date, i.acquisition_date) as acquisition_date,
                ib.last_batch_date,
                ib.batch_count,
                ib.batch_summary,
                i.last_modified,
                CASE WHEN sds.item_id IS NOT NULL THEN 1 ELSE 0 END as has_sds,
                COALESCE(defective.defective_count, 0) as defective_count,
                CASE WHEN COALESCE(defective.defective_count, 0) > 0 THEN 1 ELSE 0 END as has_defective,
                MAX(0, COALESCE(stock.total_stock, 0)) as total_stock,
                MAX(0, COALESCE(stock.total_stock, 0) - COALESCE(defective.defective_count, 0) - COALESCE(requested.requested_qty, 0)) as available_stock,
                CASE
                    WHEN EXISTS (
                        SELECT 1 FROM Requisition_Items ri
                        JOIN Requisitions r ON ri.requisition_id = r.id
                        WHERE ri.item_id = i.id
                        AND NOT EXISTS (
                            SELECT 1 FROM Stock_Movements sm
                            WHERE sm.item_id = ri.item_id
                            AND sm.movement_type = ?
                            AND sm.source_id = r.id
                        )
                    ) THEN 1
                    ELSE 0
                END as is_requested
            FROM Items i
            LEFT JOIN Categories c ON i.category_id = c.id
            LEFT JOIN Suppliers s ON i.supplier_id = s.id
            LEFT JOIN Item_SDS sds ON sds.item_id = i.id
            LEFT JOIN (
                SELECT
                    item_id,
                    MIN(date_received) as first_batch_date,
                    MAX(date_received) as last_batch_date,
                    COUNT(*) as batch_count,
                    GROUP_CONCAT(
                        'B' || batch_number || ': ' || date_received || ' (' || quantity_received || ' units)',
                        '; '
                    ) as batch_summary
                FROM Item_Batches
                GROUP BY item_id
            ) ib ON i.id = ib.item_id
            LEFT JOIN (
                """
                + self._get_defective_current_subquery()
                + """
            ) defective ON defective.item_id = i.id
            LEFT JOIN (
                """
                + self._get_stock_calculations()
                + """
            ) stock ON i.id = stock.item_id
            LEFT JOIN (
                """
                + self._get_requested_calculations()
                + """
            ) requested ON i.id = requested.item_id
            WHERE i.name LIKE ? OR c.name LIKE ? OR s.name LIKE ?
            ORDER BY c.name, i.name
            """
            )

            search_pattern = f"%{search_term}%"
            # Params order mirrors placeholder order in the query:
            params = (
                MovementType.RETURN.value,
                MovementType.CONSUMPTION.value,
                MovementType.DISPOSAL.value,
                MovementType.RETURN.value,
                MovementType.RESERVATION.value,
                MovementType.REQUEST.value,
                search_pattern,
                search_pattern,
                search_pattern,
            )
            rows = db.execute_query(query, params)

            logger.debug(f"Search for '{search_term}' returned {len(rows)} items")
            return rows

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    def get_item_usage(
        self,
        item_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Get usage statistics for a specific item (Spec #12)."""
        try:
            query = """
            SELECT
                COUNT(ri.id) as total_requisitions,
                SUM(ri.quantity_requested) as total_quantity_used,
                MIN(r.lab_activity_date) as first_used,
                MAX(r.lab_activity_date) as last_used
            FROM Requisition_Items ri
            JOIN Requisitions r ON ri.requisition_id = r.id
            WHERE ri.item_id = ?
            """

            params = [str(item_id)]

            if start_date and end_date:
                query += " AND r.lab_activity_date BETWEEN ? AND ?"
                params.extend([start_date.isoformat(), end_date.isoformat()])

            params = tuple(params)

            rows = db.execute_query(query, params)

            if rows:
                row = rows[0]
                return {
                    "total_requisitions": row["total_requisitions"] or 0,
                    "total_quantity_used": row["total_quantity_used"] or 0,
                    "first_used": row["first_used"],
                    "last_used": row["last_used"],
                }
            return {
                "total_requisitions": 0,
                "total_quantity_used": 0,
                "first_used": None,
                "last_used": None,
            }

        except Exception as e:
            logger.error(f"Failed to get item usage for {item_id}: {e}")
            return {
                "total_requisitions": 0,
                "total_quantity_used": 0,
                "first_used": None,
                "last_used": None,
            }

    def get_batch_statistics(self) -> Dict[str, int]:
        """Get overall batch statistics for the inventory."""
        try:
            total_batches_query = """
            SELECT COALESCE(COUNT(DISTINCT ib.id), 0) AS total_batches
            FROM Item_Batches ib
            WHERE ib.disposal_date IS NULL
            """
            batch_rows = db.execute_query(total_batches_query)
            total_batches = batch_rows[0]["total_batches"] if batch_rows else 0

            stock_subquery = stock_calculation_service.get_stock_calculation_subquery()
            stock_query = f"""
            SELECT COALESCE(SUM(stock.total_stock), 0) AS total_stock
            FROM (
                {stock_subquery}
            ) stock
            """
            stock_rows = db.execute_query(
                stock_query,
                stock_calculation_service.get_stock_calculation_params(),
            )
            if not stock_rows:
                return {"total_batches": 0, "total_stock": 0, "available_stock": 0}

            total_stock = stock_rows[0]["total_stock"] or 0

            # Calculate available stock using new two-phase logic
            available_query = """
            SELECT COALESCE(SUM(ri.quantity_requested), 0) as total_requested
            FROM Requisition_Items ri
            JOIN Requisitions r ON ri.requisition_id = r.id
            JOIN Items i ON ri.item_id = i.id
            WHERE r.status != 'returned'  -- Only active requisitions reduce available stock
            AND EXISTS (
                SELECT 1 FROM Stock_Movements sm
                WHERE sm.item_id = ri.item_id
                AND sm.source_id = r.id
                AND (
                    (i.is_consumable = 1 AND sm.movement_type = ?) OR
                    (i.is_consumable = 0 AND sm.movement_type = ?)
                )
            )
            """
            available_params = (
                MovementType.RESERVATION.value,
                MovementType.REQUEST.value,
            )
            requested_rows = db.execute_query(available_query, available_params)
            total_requested = (
                requested_rows[0]["total_requested"] if requested_rows else 0
            )

            return {
                "total_batches": total_batches,
                "total_stock": total_stock,
                "available_stock": max(0, total_stock - total_requested),
            }

        except Exception as e:
            logger.error(f"Failed to get batch statistics: {e}")
            return {"total_batches": 0, "total_stock": 0, "available_stock": 0}

    def get_item_usage_history(
        self,
        item_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """Get detailed usage history for an item, including defective return events."""
        try:
            usage_query = """
                SELECT
                    'Usage' AS event_type,
                    r.lab_activity_date AS event_date,
                    i.name AS item_name,
                    req.name AS requester_name,
                    req.grade_level AS grade_level,
                    req.section AS section,
                    r.lab_activity_name AS lab_activity,
                    ri.quantity_requested AS quantity,
                    r.expected_request AS request_date,
                    r.expected_return AS return_date,
                    r.lab_activity_description AS notes
                FROM Requisition_Items ri
                JOIN Requisitions r ON r.id = ri.requisition_id
                JOIN Items i ON i.id = ri.item_id
                JOIN Requesters req ON req.id = r.requester_id
                WHERE ri.item_id = ?
            """

            usage_params: List[Any] = [item_id]
            if start_date:
                usage_query += " AND DATE(r.lab_activity_date) >= ?"
                usage_params.append(start_date.isoformat())
            if end_date:
                usage_query += " AND DATE(r.lab_activity_date) <= ?"
                usage_params.append(end_date.isoformat())

            defective_query = """
                SELECT
                    'Defective' AS event_type,
                    DATE(di.reported_date) AS event_date,
                    di.id AS defective_item_id,
                    COALESCE(SUM(CASE WHEN dia.action_type = 'DISPOSED' THEN dia.quantity ELSE 0 END), 0) AS disposed_qty,
                    COALESCE(SUM(CASE WHEN dia.action_type = 'NOT_DEFECTIVE' THEN dia.quantity ELSE 0 END), 0) AS not_defective_qty,
                    MAX(0,
                        di.quantity - COALESCE(SUM(
                            CASE
                                WHEN dia.action_type IN ('DISPOSED', 'NOT_DEFECTIVE')
                                THEN dia.quantity
                                ELSE 0
                            END
                        ), 0)
                    ) AS pending_defective_qty,
                    i.name AS item_name,
                    req.name AS requester_name,
                    req.grade_level AS grade_level,
                    req.section AS section,
                    r.lab_activity_name AS lab_activity,
                    di.quantity AS quantity,
                    r.expected_request AS request_date,
                    r.expected_return AS return_date,
                    di.notes AS notes
                FROM Defective_Items di
                LEFT JOIN Defective_Item_Actions dia ON dia.defective_item_id = di.id
                JOIN Requisitions r ON r.id = di.requisition_id
                JOIN Items i ON i.id = di.item_id
                JOIN Requesters req ON req.id = r.requester_id
                WHERE di.item_id = ?
            """

            defective_params: List[Any] = [item_id]
            if start_date:
                defective_query += " AND DATE(di.reported_date) >= ?"
                defective_params.append(start_date.isoformat())
            if end_date:
                defective_query += " AND DATE(di.reported_date) <= ?"
                defective_params.append(end_date.isoformat())

            defective_query += """
                GROUP BY
                    di.id,
                    i.name,
                    req.name,
                    req.grade_level,
                    req.section,
                    r.lab_activity_name,
                    di.quantity,
                    r.expected_request,
                    r.expected_return,
                    di.notes,
                    di.reported_date
            """

            usage_rows = db.execute_query(usage_query, tuple(usage_params)) or []
            defective_rows = (
                db.execute_query(defective_query, tuple(defective_params)) or []
            )

            movement_rows: List[Dict[str, Any]] = []
            item_type_rows = db.execute_query(
                "SELECT is_consumable FROM Items WHERE id = ?", (item_id,)
            )
            is_non_consumable = bool(
                item_type_rows and not item_type_rows[0].get("is_consumable")
            )
            if is_non_consumable:
                movement_query = """
                    SELECT
                        CASE
                            WHEN sm.movement_type = 'REQUEST' THEN 'Borrowed'
                            WHEN sm.movement_type = 'RETURN' THEN 'Returned'
                            WHEN sm.movement_type = 'DISPOSAL' THEN 'Lost'
                            ELSE sm.movement_type
                        END AS event_type,
                        DATE(sm.movement_date) AS event_date,
                        i.name AS item_name,
                        req.name AS requester_name,
                        req.grade_level AS grade_level,
                        req.section AS section,
                        r.lab_activity_name AS lab_activity,
                        sm.quantity AS quantity,
                        r.expected_request AS request_date,
                        r.expected_return AS return_date,
                        sm.note AS notes
                    FROM Stock_Movements sm
                    JOIN Items i ON i.id = sm.item_id
                    LEFT JOIN Requisitions r ON r.id = sm.source_id
                    LEFT JOIN Requesters req ON req.id = r.requester_id
                    WHERE sm.item_id = ?
                    AND sm.movement_type IN (?, ?, ?)
                    AND NOT (
                        sm.movement_type = ?
                        AND COALESCE(sm.note, '') LIKE 'Defective confirmation disposal%'
                    )
                """
                movement_params: List[Any] = [
                    item_id,
                    MovementType.REQUEST.value,
                    MovementType.RETURN.value,
                    MovementType.DISPOSAL.value,
                    MovementType.DISPOSAL.value,
                ]
                if start_date:
                    movement_query += " AND DATE(sm.movement_date) >= ?"
                    movement_params.append(start_date.isoformat())
                if end_date:
                    movement_query += " AND DATE(sm.movement_date) <= ?"
                    movement_params.append(end_date.isoformat())

                movement_rows = (
                    db.execute_query(movement_query, tuple(movement_params)) or []
                )

            defective_action_query = """
                SELECT
                    CASE
                        WHEN dia.action_type = 'DISPOSED' THEN 'Disposed'
                        WHEN dia.action_type = 'NOT_DEFECTIVE' THEN 'Not Defective'
                        ELSE dia.action_type
                    END AS event_type,
                    DATE(dia.action_date) AS event_date,
                    di.id AS defective_item_id,
                    NULL AS pending_defective_qty,
                    i.name AS item_name,
                    req.name AS requester_name,
                    req.grade_level AS grade_level,
                    req.section AS section,
                    r.lab_activity_name AS lab_activity,
                    dia.quantity AS quantity,
                    r.expected_request AS request_date,
                    r.expected_return AS return_date,
                    COALESCE(dia.notes, '') AS notes
                FROM Defective_Item_Actions dia
                JOIN Defective_Items di ON di.id = dia.defective_item_id
                JOIN Items i ON i.id = di.item_id
                LEFT JOIN Requisitions r ON r.id = di.requisition_id
                LEFT JOIN Requesters req ON req.id = r.requester_id
                WHERE di.item_id = ?
            """
            defective_action_params: List[Any] = [item_id]
            if start_date:
                defective_action_query += " AND DATE(dia.action_date) >= ?"
                defective_action_params.append(start_date.isoformat())
            if end_date:
                defective_action_query += " AND DATE(dia.action_date) <= ?"
                defective_action_params.append(end_date.isoformat())

            defective_action_rows = (
                db.execute_query(defective_action_query, tuple(defective_action_params))
                or []
            )

            rows = usage_rows + defective_rows + movement_rows + defective_action_rows
            rows.sort(
                key=lambda row: (
                    row.get("event_date") or "",
                    row.get("event_type") or "",
                ),
                reverse=True,
            )
            return rows

        except Exception as e:
            logger.error(f"Failed to get item usage history for {item_id}: {e}")
            return []

    def get_item_defective_details(self, item_id: int) -> List[Dict[str, Any]]:
        """Get defective detail rows for a specific item ordered by newest first."""
        try:
            query = """
                SELECT
                    di.quantity,
                    di.notes,
                    COALESCE(di.editor_name, di.reported_by, 'System') AS reported_by,
                    di.reported_date,
                    r.lab_activity_name AS lab_activity,
                    req.name AS requester_name
                FROM Defective_Items di
                LEFT JOIN Requisitions r ON r.id = di.requisition_id
                LEFT JOIN Requesters req ON req.id = r.requester_id
                WHERE di.item_id = ?
                ORDER BY di.reported_date DESC, di.id DESC
            """
            return db.execute_query(query, (item_id,)) or []
        except Exception as e:
            logger.error(f"Failed to get defective details for item {item_id}: {e}")
            return []

    def apply_defective_action(
        self,
        defective_item_id: int,
        action_type: str,
        quantity: int,
        acted_by: str,
        notes: str = "",
    ) -> bool:
        """Apply a defective confirmation decision for a reported defective entry."""
        try:
            if action_type not in {"DISPOSED", "NOT_DEFECTIVE"}:
                return False
            if quantity <= 0 or not acted_by.strip():
                return False

            row_query = """
                SELECT
                    di.id,
                    di.item_id,
                    di.requisition_id,
                    di.quantity,
                    COALESCE(i.name, 'item') AS item_name,
                    COALESCE(req.name, 'requester') AS requester_name,
                    MAX(0,
                        di.quantity - COALESCE(SUM(
                            CASE
                                WHEN dia.action_type IN ('DISPOSED', 'NOT_DEFECTIVE')
                                THEN dia.quantity
                                ELSE 0
                            END
                        ), 0)
                    ) AS pending_qty
                FROM Defective_Items di
                LEFT JOIN Defective_Item_Actions dia ON dia.defective_item_id = di.id
                LEFT JOIN Items i ON i.id = di.item_id
                LEFT JOIN Requisitions r ON r.id = di.requisition_id
                LEFT JOIN Requesters req ON req.id = r.requester_id
                WHERE di.id = ?
                GROUP BY di.id, di.item_id, di.requisition_id, di.quantity, i.name, req.name
            """
            rows = db.execute_query(row_query, (defective_item_id,))
            if not rows:
                return False

            defective_row = rows[0]
            pending_qty = int(defective_row.get("pending_qty") or 0)
            if quantity > pending_qty:
                return False

            item_id = int(defective_row["item_id"])
            requisition_id = int(defective_row["requisition_id"])
            item_name = str(defective_row.get("item_name") or "item").strip() or "item"
            requester_name = (
                str(defective_row.get("requester_name") or "requester").strip()
                or "requester"
            )
            with db.transaction(immediate=True):
                db.execute_update(
                    """
                    INSERT INTO Defective_Item_Actions (
                        defective_item_id, item_id, action_type, quantity, notes, acted_by
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        defective_item_id,
                        item_id,
                        action_type,
                        quantity,
                        (notes or "").strip(),
                        acted_by.strip(),
                    ),
                )

                if action_type == "DISPOSED":
                    movement_note = (
                        f"Defective confirmation disposal by {acted_by.strip()}: "
                        f"{(notes or 'No details').strip()}"
                    )
                    self.stock_service.record_disposal(
                        item_id=item_id,
                        quantity=quantity,
                        source_id=requisition_id,
                        note=movement_note,
                        batch_id=None,
                    )

                action_label = (
                    "confirmed as disposed"
                    if action_type == "DISPOSED"
                    else "confirmed as not defective"
                )
                details = (notes or "No details").strip()
                activity_logger.log_activity(
                    activity_type=(
                        activity_logger.DEFECTIVE_DISPOSED
                        if action_type == "DISPOSED"
                        else activity_logger.DEFECTIVE_NOT_DEFECTIVE
                    ),
                    description=(
                        f"{action_label} {quantity} unit(s) of {item_name} "
                        f"for {requester_name} - {details}"
                    ),
                    entity_id=item_id,
                    entity_type="item",
                    user_name=acted_by.strip(),
                )

            return True
        except Exception as e:
            logger.error(f"Failed to apply defective action: {e}")
            return False

    def get_categories(self) -> List[str]:
        """Get list of unique categories."""
        try:
            return get_all_category_names()
        except Exception as e:
            logger.error(f"Failed to get categories: {e}")
            return []

    def get_suppliers(self) -> List[str]:
        """Get list of unique suppliers."""
        try:
            rows = db.execute_query("SELECT DISTINCT name FROM Suppliers ORDER BY name")
            return [row["name"] for row in rows]
        except Exception as e:
            logger.error(f"Failed to get suppliers: {e}")
            return []

    def get_inventory_statistics(self) -> Dict[str, Any]:
        """Get complete inventory statistics including alerts."""
        try:
            # Get basic batch statistics
            batch_stats = self.get_batch_statistics()

            # Get alert counts from status service
            alert_counts = item_status_service.get_alert_counts()

            # Get low stock count using centralized stock policy logic.
            low_stock_subquery = stock_calculation_service.get_low_stock_subquery()
            low_stock_query = f"SELECT COUNT(*) as count FROM ({low_stock_subquery})"
            low_stock_result = db.execute_query(
                low_stock_query,
                stock_calculation_service.get_low_stock_params(threshold=10),
            )
            low_stock_count = low_stock_result[0]["count"] if low_stock_result else 0

            # Combine all statistics
            stats = {
                "total_batches": batch_stats["total_batches"],
                "total_stock": batch_stats["total_stock"],
                "available_stock": batch_stats["available_stock"],
                "low_stock": low_stock_count,
                "expiring": alert_counts.get("expiring", 0),
                "expired": alert_counts.get("expired", 0),
                "calibration_warning": alert_counts.get("calibration_warning", 0),
                "calibration_due": alert_counts.get("calibration_due", 0),
            }

            logger.debug(f"Generated complete inventory statistics: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Failed to get inventory statistics: {e}")
            return {
                "total_batches": 0,
                "total_stock": 0,
                "available_stock": 0,
                "low_stock": 0,
                "expiring": 0,
                "expired": 0,
                "calibration_warning": 0,
                "calibration_due": 0,
            }
