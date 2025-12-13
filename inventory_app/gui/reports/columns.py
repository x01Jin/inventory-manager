"""
Shared SQL select column fragments used across reports to avoid duplication.
Provides both report-focused (item/cat/size) and inventory-focused column lists.
"""

from typing import List


# Columns for dynamic pivot reports (consistent aliasing expected by header utils)
REPORT_BASE_COLUMNS: List[str] = [
    "i.name AS ITEMS",
    "c.name AS CATEGORIES",
    "(SELECT COALESCE(SUM(quantity_received), 0) FROM Item_Batches b WHERE b.item_id = i.id) AS ACTUAL_INVENTORY",
    "i.size AS SIZE",
    "i.brand AS BRAND",
    'i.other_specifications AS "OTHER SPECIFICATIONS"',
]


# Inventory queries expose user-friendly Title Case column labels
INVENTORY_BASE_COLUMNS: List[str] = [
    'i.name AS "Item Name"',
    'c.name AS "Category"',
    'i.size AS "Size"',
    'i.brand AS "Brand"',
    'COALESCE(SUM(ib.quantity_received), 0) - COALESCE(SUM(sm.quantity), 0) AS "Current Stock"',
    'i.other_specifications AS "Specifications"',
]

# Identifying columns used in inventory queries that do not compute stock
INVENTORY_IDENT_COLUMNS: List[str] = [
    'i.name AS "Item Name"',
    'c.name AS "Category"',
    'i.size AS "Size"',
    'i.brand AS "Brand"',
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
