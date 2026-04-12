from typing import List, Dict, Optional
from datetime import date
from collections import OrderedDict

from inventory_app.database.connection import db
from inventory_app.gui.reports.query_builder import (
    ReportQueryBuilder,
    ReportStatisticsBuilder,
)
from inventory_app.utils.logger import logger
from inventory_app.gui.reports.report_utils import date_formatter
from inventory_app.services.movement_types import MovementType
from inventory_app.services.category_config import DEFAULT_CATEGORIES


def _get_calibration_category_names() -> List[str]:
    """Return category names that should participate in calibration reporting."""
    return [c.name for c in DEFAULT_CATEGORIES if c.has_calibration]


def get_dynamic_report_data(
    start_date: date,
    end_date: date,
    granularity: str,
    category_filter: str = "",
    supplier_filter: str = "",
    include_consumables: bool = True,
    show_individual_only: bool = False,
) -> List[Dict]:
    try:
        query_builder = ReportQueryBuilder()

        query, params = query_builder.build_dynamic_report_query(
            start_date,
            end_date,
            granularity,
            category_filter=category_filter,
            supplier_filter=supplier_filter,
            include_consumables=include_consumables,
            show_individual_only=show_individual_only,
        )

        rows = query_builder.execute_report_query(query, params)
        if not rows:
            return []

        if query_builder.normalized_fallback or (
            rows and "PERIOD" in rows[0] and "PERIOD_QUANTITY" in rows[0]
        ):
            period_keys = date_formatter.get_period_keys(
                start_date, end_date, granularity
            )
            pivoted = OrderedDict()
            for row in rows:
                item_key = (
                    row.get("ITEMS"),
                    row.get("CATEGORIES"),
                    row.get("ACTUAL INVENTORY", row.get("ACTUAL_INVENTORY")),
                    row.get("SIZE"),
                    row.get("BRAND"),
                    row.get("OTHER SPECIFICATIONS"),
                    row.get("SUPPLIER"),
                )
                if item_key not in pivoted:
                    base = {
                        "ITEMS": item_key[0],
                        "CATEGORIES": item_key[1],
                        "ACTUAL INVENTORY": item_key[2],
                        "SIZE": item_key[3],
                        "BRAND": item_key[4],
                        "OTHER SPECIFICATIONS": item_key[5],
                        "SUPPLIER": item_key[6],
                    }
                    for k in period_keys:
                        base[k] = 0
                    pivoted[item_key] = base

                pkey = row.get("PERIOD")
                qty = row.get("PERIOD_QUANTITY") or 0
                if pkey in pivoted[item_key]:
                    pivoted[item_key][pkey] += qty
                else:
                    pivoted[item_key][pkey] = qty

            result_rows = []
            for base in pivoted.values():
                total = 0
                for k in period_keys:
                    total += base.get(k, 0) or 0
                base["TOTAL QUANTITY"] = total
                result_rows.append(base)
            return result_rows

        return rows

    except Exception as e:
        logger.error(f"Failed to get dynamic report data: {e}")
        return []


def get_stock_levels_data(category_filter: str = "") -> List[Dict]:
    """Get stock levels data with differentiated logic for consumables vs non-consumables.
    Excludes items with 0 current stock (depleted/disposed items).

    Per beta test requirements:
    - Consumables: deduct consumed quantity from original stock
    - Non-consumables: borrow/return does not affect stock baseline; only disposal/loss deducts stock

    The 'Current Stock' column shows:
    - For consumables: Original - Consumed - Disposed + Returned
    - For non-consumables: Original - Disposed
    """
    try:
        # Compute both original (received) and current stock (consumption/disposal/returns)
        # Use CASE expression to differentiate consumable vs non-consumable stock calculation
        query = """
            SELECT
                i.name AS "Item Name",
                c.name AS "Category",
                i.size AS "Size",
                i.brand AS "Brand",
                COALESCE(s.name, 'N/A') AS "Supplier",
                COALESCE(stock.original_stock, 0) AS "Original Stock",
                CASE
                    WHEN i.is_consumable = 1 THEN
                        -- Consumables: deduct consumed/disposed, add returned
                        COALESCE(stock.original_stock, 0) -
                        COALESCE(movements.consumed_qty, 0) -
                        COALESCE(movements.disposed_qty, 0) +
                        COALESCE(movements.returned_qty, 0)
                    ELSE
                        -- Non-consumables: requests/returns are availability only; disposal/loss is permanent
                        COALESCE(stock.original_stock, 0) -
                        COALESCE(movements.disposed_qty, 0)
                END AS "Current Stock",
                i.other_specifications AS "Specifications",
                i.is_consumable AS "Is Consumable"
            FROM Items i
            JOIN Categories c ON c.id = i.category_id
            LEFT JOIN Suppliers s ON s.id = i.supplier_id
            LEFT JOIN (
                SELECT
                    ib.item_id,
                    COALESCE(SUM(ib.quantity_received), 0) AS original_stock
                FROM Item_Batches ib
                WHERE ib.disposal_date IS NULL
                GROUP BY ib.item_id
            ) stock ON stock.item_id = i.id
            LEFT JOIN (
                SELECT
                    sm.item_id,
                    COALESCE(SUM(CASE WHEN sm.movement_type = ? THEN sm.quantity ELSE 0 END), 0) AS consumed_qty,
                    COALESCE(SUM(CASE WHEN sm.movement_type = ? THEN sm.quantity ELSE 0 END), 0) AS disposed_qty,
                    COALESCE(SUM(CASE WHEN sm.movement_type = ? THEN sm.quantity ELSE 0 END), 0) AS returned_qty
                FROM Stock_Movements sm
                GROUP BY sm.item_id
            ) movements ON movements.item_id = i.id
            """

        params = [
            MovementType.CONSUMPTION.value,
            MovementType.DISPOSAL.value,
            MovementType.RETURN.value,
        ]
        if category_filter:
            query += " WHERE c.name = ?"
            params.append(category_filter)

        query += " GROUP BY i.id, i.name, c.name, i.size, i.brand, s.name, i.other_specifications, i.is_consumable, stock.original_stock, movements.consumed_qty, movements.disposed_qty, movements.returned_qty"

        # Filter out items with 0 current stock (depleted/disposed items)
        query += ' HAVING "Current Stock" > 0'

        query += " ORDER BY c.name, i.name"

        return db.execute_query(query, tuple(params)) or []

    except Exception as e:
        logger.error(f"Failed to get stock levels data: {e}")
        return []


def get_trends_data(
    start_date: date,
    end_date: date,
    granularity: Optional[str] = None,
    group_by: str = "item",
    top_n: Optional[int] = None,
    include_consumables: bool = True,
    category_filter: str = "",
) -> List[Dict]:
    try:
        # Use smart granularity when None or 'auto' is provided
        if granularity is None or granularity == "auto":
            granularity = date_formatter.get_smart_granularity(start_date, end_date)
        rows = get_dynamic_report_data(
            start_date,
            end_date,
            granularity,
            category_filter=category_filter,
            supplier_filter="",
            include_consumables=include_consumables,
        )

        if not rows:
            return []

        period_keys = [
            k
            for k in rows[0].keys()
            if k
            not in {
                "ITEMS",
                "CATEGORIES",
                "ACTUAL_INVENTORY",
                "SIZE",
                "BRAND",
                "OTHER SPECIFICATIONS",
                "SUPPLIER",
                "TOTAL QUANTITY",
            }
        ]

        if group_by == "category":
            grouped = OrderedDict()
            for r in rows:
                key = r.get("CATEGORIES")
                if key is None:
                    key = "<Uncategorized>"
                if key not in grouped:
                    base = {"CATEGORIES": key}
                    for k in period_keys:
                        base[k] = 0
                    base["TOTAL QUANTITY"] = 0
                    grouped[key] = base
                for k in period_keys:
                    grouped[key][k] += r.get(k, 0) or 0
                grouped[key]["TOTAL QUANTITY"] += r.get("TOTAL QUANTITY", 0) or 0

            result_rows = list(grouped.values())
        else:
            result_rows = rows

        result_rows = sorted(
            result_rows, key=lambda r: r.get("TOTAL QUANTITY") or 0, reverse=True
        )

        if top_n and isinstance(top_n, int):
            result_rows = result_rows[:top_n]

        return result_rows

    except Exception as e:
        logger.error(f"Failed to get trends data: {e}")
        return []


def get_expiration_data(
    start_date: date, end_date: date, category_filter: str = ""
) -> List[Dict]:
    """Get expiration data, excluding items with 0 current stock.

    Items with 0 stock are assumed to be depleted/disposed and should not appear in alerts.
    """
    try:
        query = """
            SELECT
                i.name AS "Item Name",
                c.name AS "Category",
                i.size AS "Size",
                i.brand AS "Brand",
                i.expiration_date AS "Expiration Date",
                COALESCE(stock.total_stock, 0) AS "Stock Quantity",
                i.other_specifications AS "Specifications"
            FROM Items i
            JOIN Categories c ON c.id = i.category_id
            LEFT JOIN (
                SELECT
                    ib.item_id,
                    SUM(ib.quantity_received) -
                    COALESCE(movements.consumed_qty, 0) -
                    COALESCE(movements.disposed_qty, 0) +
                    COALESCE(movements.returned_qty, 0) as total_stock
                FROM Item_Batches ib
                LEFT JOIN (
                    SELECT
                        sm.item_id,
                        SUM(CASE WHEN sm.movement_type = ? THEN sm.quantity ELSE 0 END) as consumed_qty,
                        SUM(CASE WHEN sm.movement_type = ? THEN sm.quantity ELSE 0 END) as disposed_qty,
                        SUM(CASE WHEN sm.movement_type = ? THEN sm.quantity ELSE 0 END) as returned_qty
                    FROM Stock_Movements sm
                    GROUP BY sm.item_id
                ) movements ON ib.item_id = movements.item_id
                WHERE ib.disposal_date IS NULL
                GROUP BY ib.item_id
            ) stock ON i.id = stock.item_id
            WHERE i.expiration_date BETWEEN ? AND ?
            AND COALESCE(stock.total_stock, 0) > 0
            """

        params = [
            MovementType.CONSUMPTION.value,
            MovementType.DISPOSAL.value,
            MovementType.RETURN.value,
            start_date.isoformat(),
            end_date.isoformat(),
        ]

        if category_filter:
            query += " AND c.name = ?"
            params.append(category_filter)

        query += " GROUP BY i.id, i.name, c.name, i.size, i.brand, i.expiration_date, i.other_specifications, stock.total_stock ORDER BY i.expiration_date"

        return db.execute_query(query, tuple(params)) or []

    except Exception as e:
        logger.error(f"Failed to get expiration data: {e}")
        return []


def get_low_stock_data(
    category_filter: str = "", threshold: Optional[int] = None
) -> List[Dict]:
    try:
        rows = get_stock_levels_data(category_filter=category_filter)
        if not rows:
            return []

        # If a numeric threshold is explicitly provided, treat it as absolute
        if threshold is not None:
            try:
                abs_thresh = int(threshold)
            except Exception:
                abs_thresh = None
        else:
            abs_thresh = None

        filtered = []
        for r in rows:
            current = r.get("Current Stock") or 0
            original = r.get("Original Stock") or 0
            is_consumable = r.get("Is Consumable")

            if abs_thresh is not None:
                # Absolute threshold override
                if current < abs_thresh:
                    filtered.append(r)
                continue

            # Default behaviour: percentage-based thresholds
            # Skip items with no original stock (cannot evaluate percentage)
            if original <= 0:
                continue

            if is_consumable == 1:
                pct_thresh = 0.20
            else:
                pct_thresh = 0.10

            if current <= int(original * pct_thresh):
                filtered.append(r)

        filtered = sorted(filtered, key=lambda r: r.get("Current Stock") or 0)
        return filtered

    except Exception as e:
        logger.error(f"Failed to get low stock data: {e}")
        return []


def get_acquisition_history_data(
    start_date: date, end_date: date, category_filter: str = ""
) -> List[Dict]:
    """Get acquisition history data with batch notation (B1, B2, B3, etc.).

    Per beta test requirement #3: Include B1, B2, B3 notation in reports to indicate
    when items were received multiple times (multiple batches).

    Args:
        start_date: Start date for the report period
        end_date: End date for the report period
        category_filter: Optional filter by category

    Returns:
        List of acquisition records with batch labels
    """
    try:
        query = """
            SELECT
                i.name AS "Item Name",
                c.name AS "Category",
                ib.date_received AS "Acquisition Date",
                ib.quantity_received AS "Quantity Received",
                'B' || ib.batch_number AS "Batch",
                s.name AS "Supplier",
                i.other_specifications AS "Specifications"
            FROM Item_Batches ib
            JOIN Items i ON i.id = ib.item_id
            JOIN Categories c ON c.id = i.category_id
            LEFT JOIN Suppliers s ON s.id = i.supplier_id
            WHERE ib.date_received BETWEEN ? AND ?
            """

        params = [start_date.isoformat(), end_date.isoformat()]

        if category_filter:
            query += " AND c.name = ?"
            params.append(category_filter)

        query += " ORDER BY i.name, ib.batch_number"

        return db.execute_query(query, tuple(params)) or []

    except Exception as e:
        logger.error(f"Failed to get acquisition history data: {e}")
        return []


def get_calibration_due_data(
    start_date: date, end_date: date, category_filter: str = ""
) -> List[Dict]:
    """Get calibration due data, excluding items with 0 current stock.

    Items with 0 stock are assumed to be depleted/disposed and should not appear in alerts.
    """
    try:
        calibration_categories = _get_calibration_category_names()
        if not calibration_categories:
            return []

        category_placeholders = ",".join("?" for _ in calibration_categories)
        query = """
            SELECT
                i.name AS "Item Name",
                c.name AS "Category",
                i.size AS "Size",
                i.brand AS "Brand",
                i.calibration_date AS "Calibration Date",
                i.other_specifications AS "Specifications"
            FROM Items i
            JOIN Categories c ON c.id = i.category_id
            LEFT JOIN (
                SELECT
                    ib.item_id,
                    SUM(ib.quantity_received) -
                    COALESCE(movements.consumed_qty, 0) -
                    COALESCE(movements.disposed_qty, 0) +
                    COALESCE(movements.returned_qty, 0) as total_stock
                FROM Item_Batches ib
                LEFT JOIN (
                    SELECT
                        sm.item_id,
                        SUM(CASE WHEN sm.movement_type = ? THEN sm.quantity ELSE 0 END) as consumed_qty,
                        SUM(CASE WHEN sm.movement_type = ? THEN sm.quantity ELSE 0 END) as disposed_qty,
                        SUM(CASE WHEN sm.movement_type = ? THEN sm.quantity ELSE 0 END) as returned_qty
                    FROM Stock_Movements sm
                    GROUP BY sm.item_id
                ) movements ON ib.item_id = movements.item_id
                GROUP BY ib.item_id
            ) stock ON i.id = stock.item_id
            WHERE i.calibration_date BETWEEN ? AND ?
            AND COALESCE(stock.total_stock, 0) > 0
            AND c.name IN ({})
            """
        query = query.format(category_placeholders)

        params = [
            MovementType.CONSUMPTION.value,
            MovementType.DISPOSAL.value,
            MovementType.RETURN.value,
            start_date.isoformat(),
            end_date.isoformat(),
            *calibration_categories,
        ]

        if category_filter:
            query += " AND c.name = ?"
            params.append(category_filter)

        query += " ORDER BY i.calibration_date"

        return db.execute_query(query, tuple(params)) or []

    except Exception as e:
        logger.error(f"Failed to get calibration due data: {e}")
        return []


def get_update_history_data(
    start_date: date, end_date: date, item_filter: str = ""
) -> List[Dict]:
    """Get update/edit history data for items.

    Per beta test requirement #7: Generate a report showing history of updates/edits
    to the inventory list with editor name, date/time, and reason for editing.

    Args:
        start_date: Start date for the report period
        end_date: End date for the report period
        item_filter: Optional filter by item name

    Returns:
        List of update history records
    """
    try:
        query = """
            SELECT
                i.name AS "Item Name",
                c.name AS "Category",
                uh.editor_name AS "Editor",
                uh.edit_timestamp AS "Edit Date/Time",
                uh.reason AS "Reason for Edit",
                uh.field_name AS "Field",
                uh.old_value AS "Old Value",
                uh.new_value AS "New Value"
            FROM Update_History uh
            JOIN Items i ON i.id = uh.item_id
            JOIN Categories c ON c.id = i.category_id
            WHERE DATE(uh.edit_timestamp) BETWEEN ? AND ?
            """

        params = [start_date.isoformat(), end_date.isoformat()]

        if item_filter:
            query += " AND i.name LIKE ?"
            params.append(f"%{item_filter}%")

        query += " ORDER BY uh.edit_timestamp DESC"

        return db.execute_query(query, tuple(params)) or []

    except Exception as e:
        logger.error(f"Failed to get update history data: {e}")
        return []


def get_disposal_history_data(
    start_date: date, end_date: date, category_filter: str = ""
) -> List[Dict]:
    """Get disposal history data for items.

    Per beta test requirement #16: Create a history profile for disposed items
    including reason for disposal.

    Args:
        start_date: Start date for the report period
        end_date: End date for the report period
        category_filter: Optional filter by category

    Returns:
        List of disposal history records
    """
    try:
        query = """
            SELECT
                COALESCE(i.name, '[Item Deleted]') AS "Item Name",
                COALESCE(c.name, '[Category Unknown]') AS "Category",
                COALESCE(i.size, '-') AS "Size",
                COALESCE(i.brand, '-') AS "Brand",
                dh.reason AS "Disposal Reason",
                dh.disposal_timestamp AS "Disposal Date",
                dh.editor_name AS "Disposed By"
            FROM Disposal_History dh
            LEFT JOIN Items i ON i.id = dh.item_id
            LEFT JOIN Categories c ON c.id = i.category_id
            WHERE DATE(dh.disposal_timestamp) BETWEEN ? AND ?
            """

        params = [start_date.isoformat(), end_date.isoformat()]

        if category_filter:
            query += (
                " AND (c.name = ? OR (c.name IS NULL AND ? = '[Category Unknown]'))"
            )
            params.append(category_filter)
            params.append(category_filter)

        query += " ORDER BY dh.disposal_timestamp DESC"

        return db.execute_query(query, tuple(params)) or []

    except Exception as e:
        logger.error(f"Failed to get disposal history data: {e}")
        return []


def get_usage_by_grade_level_data(
    start_date: date,
    end_date: date,
    category_filter: str = "",
    grade_filter: str = "",
    section_filter: str = "",
    show_individual_only: bool = False,
) -> List[Dict]:
    """Get usage data broken down by grade level and section.

    Per beta test requirement #19: Show usage by different grade levels and sections
    within the specified date range.

    Args:
        start_date: Start date for the report period
        end_date: End date for the report period
        category_filter: Optional filter by category
        grade_filter: Optional filter by grade level
        section_filter: Optional filter by section
        show_individual_only: Whether to show only individual requests

    Returns:
        List of usage records by grade level
    """
    try:
        grade_sum_columns = [
            "SUM(CASE WHEN req.grade_level LIKE '%7%' THEN ri.quantity_requested ELSE 0 END) AS \"GRADE 7\"",
            "SUM(CASE WHEN req.grade_level LIKE '%8%' THEN ri.quantity_requested ELSE 0 END) AS \"GRADE 8\"",
            "SUM(CASE WHEN req.grade_level LIKE '%9%' THEN ri.quantity_requested ELSE 0 END) AS \"GRADE 9\"",
            "SUM(CASE WHEN req.grade_level LIKE '%10%' THEN ri.quantity_requested ELSE 0 END) AS \"GRADE 10\"",
        ]

        query = """
            SELECT
                i.name AS "ITEMS",
                c.name AS "CATEGORIES",
                CASE
                    WHEN i.is_consumable = 1 THEN
                        COALESCE(stock.original_stock, 0) -
                        COALESCE(movements.consumed_qty, 0) -
                        COALESCE(movements.disposed_qty, 0) +
                        COALESCE(movements.returned_qty, 0)
                    ELSE
                        COALESCE(stock.original_stock, 0) -
                        COALESCE(movements.disposed_qty, 0)
                END AS "ACTUAL INVENTORY",
                COALESCE(i.size, '') AS "SIZE",
                COALESCE(i.brand, '') AS "BRAND",
                COALESCE(i.other_specifications, '') AS "OTHER SPECIFICATIONS",
                """
        query += ",\n                ".join(grade_sum_columns)
        query += """,
                SUM(ri.quantity_requested) AS "TOTAL QUANTITY"
            FROM Requisition_Items ri
            JOIN Requisitions r ON r.id = ri.requisition_id
            JOIN Items i ON i.id = ri.item_id
            JOIN Categories c ON c.id = i.category_id
            JOIN Requesters req ON req.id = r.requester_id
            LEFT JOIN (
                SELECT
                    ib.item_id,
                    COALESCE(SUM(ib.quantity_received), 0) AS original_stock
                FROM Item_Batches ib
                WHERE ib.disposal_date IS NULL
                GROUP BY ib.item_id
            ) stock ON stock.item_id = i.id
            LEFT JOIN (
                SELECT
                    sm.item_id,
                    COALESCE(SUM(CASE WHEN sm.movement_type = 'CONSUMPTION' THEN sm.quantity ELSE 0 END), 0) AS consumed_qty,
                    COALESCE(SUM(CASE WHEN sm.movement_type = 'DISPOSAL' THEN sm.quantity ELSE 0 END), 0) AS disposed_qty,
                    COALESCE(SUM(CASE WHEN sm.movement_type = 'RETURN' THEN sm.quantity ELSE 0 END), 0) AS returned_qty
                FROM Stock_Movements sm
                GROUP BY sm.item_id
            ) movements ON movements.item_id = i.id
            WHERE r.lab_activity_date BETWEEN ? AND ?
            """

        params = [start_date.isoformat(), end_date.isoformat()]

        if category_filter:
            query += " AND c.name = ?"
            params.append(category_filter)

        if grade_filter and grade_filter != "All Grades":
            query += " AND req.grade_level = ?"
            params.append(grade_filter)

        if section_filter and section_filter != "All Sections":
            query += " AND req.section = ?"
            params.append(section_filter)

        if show_individual_only:
            query += " AND r.is_individual = 1"

        query += """
            GROUP BY i.id, i.name, c.name, i.size, i.brand, i.other_specifications,
                     i.is_consumable, stock.original_stock,
                     movements.consumed_qty, movements.disposed_qty, movements.returned_qty
            ORDER BY c.name, i.name
        """

        return db.execute_query(query, tuple(params)) or []

    except Exception as e:
        logger.error(f"Failed to get usage by grade level data: {e}")
        return []


def get_usage_statistics(start_date: date, end_date: date) -> Dict:
    """Get usage statistics based on lab activity date.

    NOTE: Statistics are now based on lab_activity_date (when materials are used)
    per beta test requirements, NOT expected_request (borrow date).
    """
    try:
        stats_builder = ReportStatisticsBuilder()

        total_query, total_params = stats_builder.build_usage_statistics_query(
            start_date, end_date
        )
        total_rows = db.execute_query(total_query, total_params)
        total_used = (
            total_rows[0]["total_used"]
            if total_rows and total_rows[0]["total_used"]
            else 0
        )

        category_query, category_params = stats_builder.build_category_statistics_query(
            start_date, end_date
        )
        category_rows = db.execute_query(category_query, category_params) or []

        top_items_query, top_items_params = stats_builder.build_top_items_query(
            start_date, end_date
        )
        top_items_rows = db.execute_query(top_items_query, top_items_params) or []

        return {
            "total_items_used": total_used,
            "categories": category_rows,
            "top_items": top_items_rows,
            "date_range": f"{start_date} to {end_date}",
        }

    except Exception as e:
        logger.error(f"Failed to get usage statistics: {e}")
        return {
            "total_items_used": 0,
            "categories": [],
            "top_items": [],
            "date_range": f"{start_date} to {end_date}",
        }


def get_item_usage_details(item_name: str) -> List[Dict]:
    """Get detailed usage history for a specific item.

    Per beta test requirement #12: When searching, retrieve all usage information
    for individual items including all encoded information (requester, date, quantity, etc.).

    Args:
        item_name: Name of the item to search for (partial match supported)

    Returns:
        List of usage records for the item with all encoded information
    """
    try:
        query = """
            SELECT
                i.name AS "Item Name",
                c.name AS "Category",
                i.size AS "Size",
                i.brand AS "Brand",
                req.name AS "Requested By",
                req.grade_level AS "Grade Level",
                req.section AS "Section",
                ri.quantity_requested AS "Quantity Used",
                r.lab_activity_name AS "Lab Activity",
                r.lab_activity_date AS "Activity Date",
                r.expected_request AS "Request Date",
                r.expected_return AS "Return Date",
                r.lab_activity_description AS "Notes"
            FROM Requisition_Items ri
            JOIN Requisitions r ON r.id = ri.requisition_id
            JOIN Items i ON i.id = ri.item_id
            JOIN Categories c ON c.id = i.category_id
            JOIN Requesters req ON req.id = r.requester_id
            WHERE i.name LIKE ?
            ORDER BY r.lab_activity_date DESC
        """

        params = [f"%{item_name}%"]

        return db.execute_query(query, tuple(params)) or []

    except Exception as e:
        logger.error(f"Failed to get item usage details: {e}")
        return []


def get_item_batch_summary(item_name: str = "") -> List[Dict]:
    """Get batch summary for items showing all receive dates (B1, B2, B3, etc.).

    Per beta test requirement #3: Show batch information with B1, B2, B3 notation
    for items received multiple times.

    Args:
        item_name: Optional filter by item name (partial match)

    Returns:
        List of item batch records with batch labels
    """
    try:
        query = """
            SELECT
                i.name AS "Item Name",
                c.name AS "Category",
                GROUP_CONCAT(
                    'B' || ib.batch_number || ': ' || ib.date_received || ' (' || ib.quantity_received || ' units)',
                    '; '
                ) AS "Batch History",
                COUNT(ib.id) AS "Total Batches",
                COALESCE(SUM(ib.quantity_received), 0) AS "Total Received",
                s.name AS "Supplier"
            FROM Items i
            JOIN Categories c ON c.id = i.category_id
            LEFT JOIN Item_Batches ib ON ib.item_id = i.id
            LEFT JOIN Suppliers s ON s.id = i.supplier_id
        """

        params = []
        if item_name:
            query += " WHERE i.name LIKE ?"
            params.append(f"%{item_name}%")

        query += " GROUP BY i.id, i.name, c.name, s.name ORDER BY i.name"

        return db.execute_query(query, tuple(params)) or []

    except Exception as e:
        logger.error(f"Failed to get item batch summary: {e}")
        return []


def get_defective_items_data(
    start_date: date, end_date: date, category_filter: str = ""
) -> List[Dict]:
    """Get defective/broken items report data.

    Per beta test requirement: Add info for defective/broken items returned.

    Args:
        start_date: Start date for the report period
        end_date: End date for the report period
        category_filter: Optional filter by category

    Returns:
        List of defective item records
    """
    try:
        query = """
            SELECT
                i.name AS "Item Name",
                c.name AS "Category",
                i.size AS "Size",
                i.brand AS "Brand",
                di.quantity AS "Defective Quantity",
                di.notes AS "Notes",
                COALESCE(di.editor_name, di.reported_by) AS "Reported By",
                di.reported_date AS "Report Date",
                r.lab_activity_name AS "Lab Activity",
                req.name AS "Requester"
            FROM Defective_Items di
            JOIN Items i ON i.id = di.item_id
            JOIN Categories c ON c.id = i.category_id
            JOIN Requisitions r ON r.id = di.requisition_id
            JOIN Requesters req ON req.id = r.requester_id
            WHERE DATE(di.reported_date) BETWEEN ? AND ?
        """

        params = [start_date.isoformat(), end_date.isoformat()]

        if category_filter:
            query += " AND c.name = ?"
            params.append(category_filter)

        query += " ORDER BY di.reported_date DESC, i.name"

        return db.execute_query(query, tuple(params)) or []

    except Exception as e:
        logger.error(f"Failed to get defective items data: {e}")
        return []


def get_audit_log_data(
    start_date: date,
    end_date: date,
    editor_filter: str = "",
    action_filter: str = "",
    entity_filter: str = "",
) -> List[Dict]:
    """Return a unified audit log dataset for Task 9 reporting."""
    try:
        query = """
            SELECT * FROM (
                SELECT
                    'ITEM_UPDATE' AS "Action",
                    'item' AS "Entity Type",
                    CAST(uh.item_id AS TEXT) AS "Entity ID",
                    i.name AS "Entity Name",
                    uh.editor_name AS "Editor",
                    uh.edit_timestamp AS "Timestamp",
                    uh.field_name AS "Field",
                    uh.old_value AS "Old Value",
                    uh.new_value AS "New Value",
                    uh.reason AS "Reason"
                FROM Update_History uh
                LEFT JOIN Items i ON i.id = uh.item_id

                UNION ALL

                SELECT
                    'REQUISITION_UPDATE' AS "Action",
                    'requisition' AS "Entity Type",
                    CAST(rh.requisition_id AS TEXT) AS "Entity ID",
                    r.lab_activity_name AS "Entity Name",
                    rh.editor_name AS "Editor",
                    rh.edit_timestamp AS "Timestamp",
                    rh.field_name AS "Field",
                    rh.old_value AS "Old Value",
                    rh.new_value AS "New Value",
                    rh.reason AS "Reason"
                FROM Requisition_History rh
                LEFT JOIN Requisitions r ON r.id = rh.requisition_id

                UNION ALL

                SELECT
                    'ITEM_DISPOSAL' AS "Action",
                    'item' AS "Entity Type",
                    CAST(dh.item_id AS TEXT) AS "Entity ID",
                    COALESCE(i.name, '[Item Deleted]') AS "Entity Name",
                    dh.editor_name AS "Editor",
                    dh.disposal_timestamp AS "Timestamp",
                    NULL AS "Field",
                    NULL AS "Old Value",
                    NULL AS "New Value",
                    dh.reason AS "Reason"
                FROM Disposal_History dh
                LEFT JOIN Items i ON i.id = dh.item_id

                UNION ALL

                SELECT
                    'DEFECTIVE_RECORDED' AS "Action",
                    'requisition' AS "Entity Type",
                    CAST(di.requisition_id AS TEXT) AS "Entity ID",
                    i.name AS "Entity Name",
                    COALESCE(di.editor_name, di.reported_by) AS "Editor",
                    di.reported_date AS "Timestamp",
                    'quantity_defective' AS "Field",
                    NULL AS "Old Value",
                    CAST(di.quantity AS TEXT) AS "New Value",
                    COALESCE(di.notes, '') AS "Reason"
                FROM Defective_Items di
                LEFT JOIN Items i ON i.id = di.item_id

                UNION ALL

                SELECT
                    al.activity_type AS "Action",
                    COALESCE(al.entity_type, '') AS "Entity Type",
                    CASE WHEN al.entity_id IS NULL THEN '' ELSE CAST(al.entity_id AS TEXT) END AS "Entity ID",
                    '' AS "Entity Name",
                    COALESCE(al.user_name, 'System') AS "Editor",
                    al.timestamp AS "Timestamp",
                    NULL AS "Field",
                    NULL AS "Old Value",
                    NULL AS "New Value",
                    al.description AS "Reason"
                FROM Activity_Log al
            ) unified
            WHERE DATE(unified."Timestamp") BETWEEN ? AND ?
        """

        params: List[str] = [start_date.isoformat(), end_date.isoformat()]

        if editor_filter:
            query += ' AND unified."Editor" LIKE ?'
            params.append(f"%{editor_filter}%")

        if action_filter:
            query += ' AND unified."Action" = ?'
            params.append(action_filter)

        if entity_filter:
            query += ' AND unified."Entity Type" = ?'
            params.append(entity_filter)

        query += ' ORDER BY unified."Timestamp" DESC'

        return db.execute_query(query, tuple(params)) or []
    except Exception as e:
        logger.error(f"Failed to get audit log data: {e}")
        return []
