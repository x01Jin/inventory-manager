"""
Shared SQL select column fragments used across reports to avoid duplication.
Provides both report-focused (item/cat/size) and inventory-focused column lists.
"""

from typing import List


# Columns for dynamic pivot reports (consistent aliasing expected by header utils)
REPORT_BASE_COLUMNS: List[str] = [
    "i.name AS ITEMS",
    "c.name AS CATEGORIES",
    "CASE WHEN i.is_consumable = 1 "
    "THEN COALESCE(stock.total_stock, 0) "
    "- COALESCE(movements.consumed_qty, 0) "
    "- COALESCE(movements.disposed_qty, 0) "
    "+ COALESCE(movements.returned_qty, 0) "
    "ELSE COALESCE(stock.total_stock, 0) "
    '- COALESCE(movements.disposed_qty, 0) END AS "ACTUAL INVENTORY"',
    "i.size AS SIZE",
    "i.brand AS BRAND",
    'i.other_specifications AS "OTHER SPECIFICATIONS"',
    "COALESCE(s.name, 'N/A') AS SUPPLIER",
    "COALESCE(i.po_number, 'N/A') AS \"PO NUMBER\"",
]


# Inventory queries expose user-friendly Title Case column labels
INVENTORY_BASE_COLUMNS: List[str] = [
    'i.name AS "Item Name"',
    'c.name AS "Category"',
    'i.size AS "Size"',
    'i.brand AS "Brand"',
    'COALESCE(s.name, "N/A") AS "Supplier"',
    'COALESCE(i.po_number, "N/A") AS "PO Number"',
    "CASE WHEN i.is_consumable = 1 "
    "THEN COALESCE(SUM(ib.quantity_received), 0) "
    '- COALESCE(SUM(CASE WHEN sm.movement_type = "CONSUMPTION" THEN sm.quantity ELSE 0 END), 0) '
    '- COALESCE(SUM(CASE WHEN sm.movement_type = "DISPOSAL" THEN sm.quantity ELSE 0 END), 0) '
    '+ COALESCE(SUM(CASE WHEN sm.movement_type = "RETURN" THEN sm.quantity ELSE 0 END), 0) '
    "ELSE COALESCE(SUM(ib.quantity_received), 0) "
    '- COALESCE(SUM(CASE WHEN sm.movement_type = "DISPOSAL" THEN sm.quantity ELSE 0 END), 0) END AS "Current Stock"',
    'i.other_specifications AS "Specifications"',
]

# Identifying columns used in inventory queries that do not compute stock
INVENTORY_IDENT_COLUMNS: List[str] = [
    'i.name AS "Item Name"',
    'c.name AS "Category"',
    'i.size AS "Size"',
    'i.brand AS "Brand"',
    'COALESCE(s.name, "N/A") AS "Supplier"',
    'COALESCE(i.po_number, "N/A") AS "PO Number"',
    'i.other_specifications AS "Specifications"',
]


def report_base_columns_sql() -> str:
    """Return comma-joined SQL fragment for report base columns."""
    return ",\n                ".join(REPORT_BASE_COLUMNS)


def inventory_base_columns_sql() -> str:
    """Return comma-joined SQL fragment for inventory base columns."""
    return ",\n                ".join(INVENTORY_BASE_COLUMNS)


def inventory_ident_columns_sql() -> str:
    """Return comma-joined SQL fragment for the inventory identifying columns (no computed stock)."""
    return ",\n                ".join(INVENTORY_IDENT_COLUMNS)


def inventory_common_joins_sql() -> str:
    """Return SQL fragment with common JOINs used in inventory queries (categories/suppliers).
    This avoids duplicating join logic across modules.
    """
    return (
        "LEFT JOIN Categories c ON c.id = i.category_id\n"
        "LEFT JOIN Suppliers s ON s.id = i.supplier_id"
    )
