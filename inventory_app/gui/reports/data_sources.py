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


def get_dynamic_report_data(
    start_date: date,
    end_date: date,
    granularity: str,
    category_filter: str = "",
    supplier_filter: str = "",
    include_consumables: bool = True,
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
                    row.get("ACTUAL_INVENTORY"),
                    row.get("SIZE"),
                    row.get("BRAND"),
                    row.get("OTHER SPECIFICATIONS"),
                )
                if item_key not in pivoted:
                    base = {
                        "ITEMS": item_key[0],
                        "CATEGORIES": item_key[1],
                        "ACTUAL_INVENTORY": item_key[2],
                        "SIZE": item_key[3],
                        "BRAND": item_key[4],
                        "OTHER SPECIFICATIONS": item_key[5],
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
    try:
        query = """
            SELECT
                i.name AS "Item Name",
                c.name AS "Category",
                i.size AS "Size",
                i.brand AS "Brand",
                COALESCE(SUM(ib.quantity_received), 0) - COALESCE(SUM(sm.quantity), 0) AS "Current Stock",
                i.other_specifications AS "Specifications"
            FROM Items i
            JOIN Categories c ON c.id = i.category_id
            LEFT JOIN Item_Batches ib ON ib.item_id = i.id AND ib.disposal_date IS NULL
            LEFT JOIN Stock_Movements sm ON sm.item_id = i.id AND sm.movement_type IN ('%s', '%s')
            """

        params = []
        if category_filter:
            query += " WHERE c.name = ?"
            params.append(category_filter)

        query += " GROUP BY i.id, i.name, c.name, i.size, i.brand, i.other_specifications ORDER BY c.name, i.name"
        query = query % (
            MovementType.CONSUMPTION.value,
            MovementType.DISPOSAL.value,
        )

        return db.execute_query(query, tuple(params)) or []

    except Exception as e:
        logger.error(f"Failed to get stock levels data: {e}")
        return []


def get_trends_data(
    start_date: date,
    end_date: date,
    granularity: str = "monthly",
    group_by: str = "item",
    top_n: Optional[int] = None,
    include_consumables: bool = True,
    category_filter: str = "",
) -> List[Dict]:
    try:
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
            result_rows, key=lambda r: (r.get("TOTAL QUANTITY") or 0), reverse=True
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
    try:
        query = """
            SELECT
                i.name AS "Item Name",
                c.name AS "Category",
                i.size AS "Size",
                i.brand AS "Brand",
                i.expiration_date AS "Expiration Date",
                COALESCE(SUM(ib.quantity_received), 0) AS "Stock Quantity",
                i.other_specifications AS "Specifications"
            FROM Items i
            JOIN Categories c ON c.id = i.category_id
            LEFT JOIN Item_Batches ib ON ib.item_id = i.id AND ib.disposal_date IS NULL
            WHERE i.expiration_date BETWEEN ? AND ?
            """

        params = [start_date.isoformat(), end_date.isoformat()]

        if category_filter:
            query += " AND c.name = ?"
            params.append(category_filter)

        query += " GROUP BY i.id, i.name, c.name, i.size, i.brand, i.expiration_date, i.other_specifications ORDER BY i.expiration_date"

        return db.execute_query(query, tuple(params)) or []

    except Exception as e:
        logger.error(f"Failed to get expiration data: {e}")
        return []


def get_low_stock_data(category_filter: str = "", threshold: int = 10) -> List[Dict]:
    try:
        rows = get_stock_levels_data(category_filter=category_filter)
        if not rows:
            return []

        filtered = [r for r in rows if (r.get("Current Stock") or 0) < threshold]
        filtered = sorted(filtered, key=lambda r: (r.get("Current Stock") or 0))
        return filtered

    except Exception as e:
        logger.error(f"Failed to get low stock data: {e}")
        return []


def get_acquisition_history_data(
    start_date: date, end_date: date, category_filter: str = ""
) -> List[Dict]:
    try:
        query = """
            SELECT
                i.name AS "Item Name",
                c.name AS "Category",
                ib.date_received AS "Acquisition Date",
                ib.quantity_received AS "Quantity Received",
                ib.batch_number AS "Batch Number",
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

        query += " ORDER BY ib.date_received DESC, i.name"

        return db.execute_query(query, tuple(params)) or []

    except Exception as e:
        logger.error(f"Failed to get acquisition history data: {e}")
        return []


def get_calibration_due_data(
    start_date: date, end_date: date, category_filter: str = ""
) -> List[Dict]:
    try:
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
            WHERE i.calibration_date BETWEEN ? AND ?
            """

        params = [start_date.isoformat(), end_date.isoformat()]

        if category_filter:
            query += " AND c.name = ?"
            params.append(category_filter)

        query += " ORDER BY i.calibration_date"

        return db.execute_query(query, tuple(params)) or []

    except Exception as e:
        logger.error(f"Failed to get calibration due data: {e}")
        return []


def get_usage_statistics(start_date: date, end_date: date) -> Dict:
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
