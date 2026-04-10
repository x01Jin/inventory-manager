"""Services for merging duplicate supplier/brand/size reference entries."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Tuple

from inventory_app.database.connection import db
from inventory_app.database.models import Brand, Size, Supplier
from inventory_app.utils.activity_logger import activity_logger
from inventory_app.utils.logger import logger
from inventory_app.utils.reference_normalization import (
    build_reference_compare_key,
    build_size_compare_key,
    normalize_metric_size_value,
    normalize_whitespace,
)


def _dedupe_int_ids(values: List[int]) -> List[int]:
    """Return positive integer IDs in insertion order without duplicates."""
    seen: set[int] = set()
    output: List[int] = []
    for value in values:
        if not isinstance(value, int) or value <= 0 or value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output


def _in_clause_placeholders(length: int) -> str:
    return ",".join("?" for _ in range(length))


def _normalize_editor_name(editor_name: str) -> str:
    cleaned = normalize_whitespace(editor_name)
    return cleaned or "System"


def merge_suppliers(
    target_supplier_id: int, source_supplier_ids: List[int], editor_name: str
) -> Tuple[bool, str, int]:
    """Merge source suppliers into a target supplier.

    Returns:
        Tuple (success, message, items_updated_count)
    """
    normalized_sources = _dedupe_int_ids(source_supplier_ids)
    if target_supplier_id in normalized_sources:
        normalized_sources = [
            sid for sid in normalized_sources if sid != target_supplier_id
        ]

    if target_supplier_id <= 0:
        return False, "Please select a valid target supplier.", 0

    if not normalized_sources:
        return False, "Select at least one source supplier to merge.", 0

    target = Supplier.get_by_id(target_supplier_id)
    if target is None:
        return False, "Target supplier was not found.", 0

    placeholders = _in_clause_placeholders(len(normalized_sources))
    source_rows = db.execute_query(
        f"SELECT id, name FROM Suppliers WHERE id IN ({placeholders}) ORDER BY name",
        tuple(normalized_sources),
    )
    if not source_rows:
        return False, "No valid source suppliers were found.", 0

    source_ids = [row["id"] for row in source_rows]
    source_names = [row["name"] for row in source_rows]

    try:
        with db.transaction(immediate=True):
            update_query = f"UPDATE Items SET supplier_id = ? WHERE supplier_id IN ({_in_clause_placeholders(len(source_ids))})"
            updated_items = db.execute_update(
                update_query,
                tuple([target_supplier_id] + source_ids),
            )

            delete_query = f"DELETE FROM Suppliers WHERE id IN ({_in_clause_placeholders(len(source_ids))})"
            db.execute_update(delete_query, tuple(source_ids))

            activity_logger.log_activity(
                "REFERENCE_MERGED",
                (
                    f"Merged suppliers into '{target.name}': "
                    f"{', '.join(source_names)} (updated {updated_items} item(s))"
                ),
                entity_id=target_supplier_id,
                entity_type="supplier",
                user_name=_normalize_editor_name(editor_name),
            )

        return (
            True,
            (
                f"Merged {len(source_ids)} supplier entr"
                f"{'y' if len(source_ids) == 1 else 'ies'} into '{target.name}'. "
                f"Updated {updated_items} item(s)."
            ),
            int(updated_items),
        )
    except Exception as exc:
        logger.error(f"Failed to merge suppliers into {target_supplier_id}: {exc}")
        return False, f"Failed to merge suppliers: {exc}", 0


def merge_brands(
    target_brand_id: int, source_brand_ids: List[int], editor_name: str
) -> Tuple[bool, str, int]:
    """Merge source brands into a target brand.

    Brand references are denormalized in Items.brand, so this operation updates
    case-insensitive text matches for each source brand value.

    Returns:
        Tuple (success, message, items_updated_count)
    """
    normalized_sources = _dedupe_int_ids(source_brand_ids)
    if target_brand_id in normalized_sources:
        normalized_sources = [
            bid for bid in normalized_sources if bid != target_brand_id
        ]

    if target_brand_id <= 0:
        return False, "Please select a valid target brand.", 0

    if not normalized_sources:
        return False, "Select at least one source brand to merge.", 0

    target = Brand.get_by_id(target_brand_id)
    if target is None:
        return False, "Target brand was not found.", 0

    placeholders = _in_clause_placeholders(len(normalized_sources))
    source_rows = db.execute_query(
        f"SELECT id, name FROM Brands WHERE id IN ({placeholders}) ORDER BY name",
        tuple(normalized_sources),
    )
    if not source_rows:
        return False, "No valid source brands were found.", 0

    source_ids = [row["id"] for row in source_rows]
    source_names = [row["name"] for row in source_rows]

    source_keys = {
        build_reference_compare_key(name)
        for name in source_names
        if build_reference_compare_key(name)
    }
    updated_total = 0
    try:
        with db.transaction(immediate=True):
            item_rows = db.execute_query(
                "SELECT id, brand FROM Items WHERE COALESCE(TRIM(brand), '') != ''",
                use_cache=False,
            )
            for item in item_rows:
                if build_reference_compare_key(item.get("brand")) in source_keys:
                    db.execute_update(
                        "UPDATE Items SET brand = ? WHERE id = ?",
                        (target.name, item["id"]),
                    )
                    updated_total += 1

            delete_query = f"DELETE FROM Brands WHERE id IN ({_in_clause_placeholders(len(source_ids))})"
            db.execute_update(delete_query, tuple(source_ids))

            activity_logger.log_activity(
                "REFERENCE_MERGED",
                (
                    f"Merged brands into '{target.name}': "
                    f"{', '.join(source_names)} (updated {updated_total} item(s))"
                ),
                entity_id=target_brand_id,
                entity_type="brand",
                user_name=_normalize_editor_name(editor_name),
            )

        return (
            True,
            (
                f"Merged {len(source_ids)} brand entr"
                f"{'y' if len(source_ids) == 1 else 'ies'} into '{target.name}'. "
                f"Updated {updated_total} item(s)."
            ),
            updated_total,
        )
    except Exception as exc:
        logger.error(f"Failed to merge brands into {target_brand_id}: {exc}")
        return False, f"Failed to merge brands: {exc}", 0


def merge_sizes(
    target_size_id: int, source_size_ids: List[int], editor_name: str
) -> Tuple[bool, str, int]:
    """Merge source sizes into a target size.

    Size references are denormalized in Items.size, so this operation updates
    matching item text values (normalized for spacing/casing/unit aliases), then
    removes merged source size entries.

    Returns:
        Tuple (success, message, items_updated_count)
    """
    normalized_sources = _dedupe_int_ids(source_size_ids)
    if target_size_id in normalized_sources:
        normalized_sources = [
            sid for sid in normalized_sources if sid != target_size_id
        ]

    if target_size_id <= 0:
        return False, "Please select a valid target size.", 0

    if not normalized_sources:
        return False, "Select at least one source size to merge.", 0

    target = Size.get_by_id(target_size_id)
    if target is None:
        return False, "Target size was not found.", 0

    placeholders = _in_clause_placeholders(len(normalized_sources))
    source_rows = db.execute_query(
        f"SELECT id, name FROM Sizes WHERE id IN ({placeholders}) ORDER BY name",
        tuple(normalized_sources),
    )
    if not source_rows:
        return False, "No valid source sizes were found.", 0

    source_ids = [row["id"] for row in source_rows]
    source_names = [row["name"] for row in source_rows]
    source_keys = {
        build_size_compare_key(name)
        for name in source_names
        if build_size_compare_key(name)
    }

    updated_total = 0
    try:
        with db.transaction(immediate=True):
            item_rows = db.execute_query(
                "SELECT id, size FROM Items WHERE COALESCE(TRIM(size), '') != ''",
                use_cache=False,
            )
            for item in item_rows:
                if build_size_compare_key(item.get("size")) in source_keys:
                    db.execute_update(
                        "UPDATE Items SET size = ? WHERE id = ?",
                        (target.name, item["id"]),
                    )
                    updated_total += 1

            delete_query = f"DELETE FROM Sizes WHERE id IN ({_in_clause_placeholders(len(source_ids))})"
            db.execute_update(delete_query, tuple(source_ids))

            activity_logger.log_activity(
                "REFERENCE_MERGED",
                (
                    f"Merged sizes into '{target.name}': "
                    f"{', '.join(source_names)} (updated {updated_total} item(s))"
                ),
                entity_id=target_size_id,
                entity_type="size",
                user_name=_normalize_editor_name(editor_name),
            )

        return (
            True,
            (
                f"Merged {len(source_ids)} size entr"
                f"{'y' if len(source_ids) == 1 else 'ies'} into '{target.name}'. "
                f"Updated {updated_total} item(s)."
            ),
            updated_total,
        )
    except Exception as exc:
        logger.error(f"Failed to merge sizes into {target_size_id}: {exc}")
        return False, f"Failed to merge sizes: {exc}", 0


def _canonicalize_item_size_values() -> int:
    """Normalize existing Items.size values to canonical metric-cased forms."""
    updated = 0
    with db.transaction(immediate=True):
        rows = db.execute_query(
            """
            SELECT id, size
            FROM Items
            WHERE COALESCE(TRIM(size), '') != ''
              AND UPPER(TRIM(size)) != 'N/A'
            """,
            use_cache=False,
        )

        for row in rows:
            raw_size = row.get("size")
            canonical_size = normalize_metric_size_value(raw_size)
            if not canonical_size:
                continue

            if normalize_whitespace(raw_size) != canonical_size:
                db.execute_update(
                    "UPDATE Items SET size = ? WHERE id = ?",
                    (canonical_size, row["id"]),
                )
                updated += 1

    return updated


def _collect_duplicate_groups(
    rows: List[Dict[str, Any]], key_builder: Callable[[str], str]
) -> List[List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        name = normalize_whitespace(str(row.get("name") or ""))
        if not name:
            continue
        key = key_builder(name)
        if not key:
            continue
        grouped.setdefault(key, []).append(row)

    return [
        sorted(group, key=lambda item: int(item["id"]))
        for group in grouped.values()
        if len(group) > 1
    ]


def _merge_duplicate_size_groups(editor_name: str) -> Tuple[int, int]:
    groups_merged = 0
    items_updated = 0

    rows = db.execute_query("SELECT id, name FROM Sizes ORDER BY id", use_cache=False)
    groups = _collect_duplicate_groups(rows, build_size_compare_key)

    for group in groups:
        canonical_name = normalize_metric_size_value(group[0]["name"])
        if not canonical_name:
            continue

        target = next((row for row in group if row["name"] == canonical_name), group[0])
        target_id = int(target["id"])
        source_ids = [int(row["id"]) for row in group if int(row["id"]) != target_id]

        success, _, updated_count = merge_sizes(target_id, source_ids, editor_name)
        if not success:
            continue

        groups_merged += 1
        items_updated += updated_count

        refreshed = Size.get_by_id(target_id)
        if refreshed and refreshed.name != canonical_name:
            refreshed.name = canonical_name
            refreshed.save()

    return groups_merged, items_updated


def _merge_duplicate_brand_groups(editor_name: str) -> Tuple[int, int]:
    groups_merged = 0
    items_updated = 0

    rows = db.execute_query("SELECT id, name FROM Brands ORDER BY id", use_cache=False)
    groups = _collect_duplicate_groups(rows, build_reference_compare_key)

    for group in groups:
        target_id = int(group[0]["id"])
        source_ids = [int(row["id"]) for row in group[1:]]
        success, _, updated_count = merge_brands(target_id, source_ids, editor_name)
        if not success:
            continue
        groups_merged += 1
        items_updated += updated_count

    return groups_merged, items_updated


def _merge_duplicate_supplier_groups(editor_name: str) -> Tuple[int, int]:
    groups_merged = 0
    items_updated = 0

    rows = db.execute_query(
        "SELECT id, name FROM Suppliers ORDER BY id",
        use_cache=False,
    )
    groups = _collect_duplicate_groups(rows, build_reference_compare_key)

    for group in groups:
        target_id = int(group[0]["id"])
        source_ids = [int(row["id"]) for row in group[1:]]
        success, _, updated_count = merge_suppliers(target_id, source_ids, editor_name)
        if not success:
            continue
        groups_merged += 1
        items_updated += updated_count

    return groups_merged, items_updated


def _sync_sizes_from_items() -> int:
    """Create missing `Sizes` entries based on distinct `Items.size` values."""
    rows = db.execute_query("SELECT name FROM Sizes", use_cache=False)
    existing_keys = {
        build_size_compare_key(row.get("name"))
        for row in rows
        if build_size_compare_key(row.get("name"))
    }

    item_rows = db.execute_query(
        """
        SELECT DISTINCT size
        FROM Items
        WHERE COALESCE(TRIM(size), '') != ''
          AND UPPER(TRIM(size)) != 'N/A'
        """,
        use_cache=False,
    )

    created = 0
    for row in item_rows:
        canonical_size = normalize_metric_size_value(row.get("size"))
        size_key = build_size_compare_key(canonical_size)
        if not canonical_size or not size_key or size_key in existing_keys:
            continue

        success, _ = Size(name=canonical_size).save()
        if not success:
            continue

        existing_keys.add(size_key)
        created += 1

    return created


def _sync_brands_from_items() -> int:
    """Create missing `Brands` entries based on distinct `Items.brand` values."""
    rows = db.execute_query("SELECT name FROM Brands", use_cache=False)
    existing_keys = {
        build_reference_compare_key(row.get("name"))
        for row in rows
        if build_reference_compare_key(row.get("name"))
    }

    item_rows = db.execute_query(
        """
        SELECT DISTINCT brand
        FROM Items
        WHERE COALESCE(TRIM(brand), '') != ''
          AND UPPER(TRIM(brand)) != 'N/A'
        """,
        use_cache=False,
    )

    created = 0
    for row in item_rows:
        normalized_brand = normalize_whitespace(str(row.get("brand") or ""))
        brand_key = build_reference_compare_key(normalized_brand)
        if not normalized_brand or not brand_key or brand_key in existing_keys:
            continue

        success, _ = Brand(name=normalized_brand).save()
        if not success:
            continue

        existing_keys.add(brand_key)
        created += 1

    return created


def sync_reference_values_from_items(
    editor_name: str = "System",
) -> Tuple[bool, str, Dict[str, int]]:
    """Synchronize reference tables from denormalized item text values.

    This keeps Settings reference tabs aligned with values that already exist in
    the inventory table (for example imported legacy records with size/brand
    values not yet present in `Sizes`/`Brands`).

    Returns:
        Tuple (success, message, summary)
    """
    summary = {
        "item_sizes_normalized": 0,
        "sizes_added": 0,
        "brands_added": 0,
    }

    try:
        editor = _normalize_editor_name(editor_name)
        logger.debug(f"Running reference sync from items (requested by: {editor})")

        summary["item_sizes_normalized"] = _canonicalize_item_size_values()
        summary["sizes_added"] = _sync_sizes_from_items()
        summary["brands_added"] = _sync_brands_from_items()

        message = (
            "Reference sync complete: "
            f"item sizes normalized={summary['item_sizes_normalized']}, "
            f"sizes added={summary['sizes_added']}, "
            f"brands added={summary['brands_added']}"
        )
        logger.debug(message)
        return True, message, summary
    except Exception as exc:
        logger.error(f"Failed to sync reference values from items: {exc}")
        return False, f"Reference sync failed: {exc}", summary


def normalize_reference_values_for_startup(
    editor_name: str = "System",
) -> Tuple[bool, str, Dict[str, int]]:
    """Normalize and merge reference data at startup.

    Returns:
        Tuple (success, message, summary)
    """
    summary = {
        "item_sizes_normalized": 0,
        "size_groups_merged": 0,
        "size_item_updates": 0,
        "brand_groups_merged": 0,
        "brand_item_updates": 0,
        "supplier_groups_merged": 0,
        "supplier_item_updates": 0,
    }

    try:
        editor = _normalize_editor_name(editor_name)
        summary["item_sizes_normalized"] = _canonicalize_item_size_values()

        size_groups, size_updates = _merge_duplicate_size_groups(editor)
        summary["size_groups_merged"] = size_groups
        summary["size_item_updates"] = size_updates

        # A second pass ensures item rows rewritten during merges also end in
        # canonical metric-cased format (for example, 10 mL instead of 10mL).
        summary["item_sizes_normalized"] += _canonicalize_item_size_values()

        brand_groups, brand_updates = _merge_duplicate_brand_groups(editor)
        summary["brand_groups_merged"] = brand_groups
        summary["brand_item_updates"] = brand_updates

        supplier_groups, supplier_updates = _merge_duplicate_supplier_groups(editor)
        summary["supplier_groups_merged"] = supplier_groups
        summary["supplier_item_updates"] = supplier_updates

        message = (
            "Reference normalization complete: "
            f"sizes normalized={summary['item_sizes_normalized']}, "
            f"size merges={summary['size_groups_merged']}, "
            f"brand merges={summary['brand_groups_merged']}, "
            f"supplier merges={summary['supplier_groups_merged']}"
        )
        return True, message, summary
    except Exception as exc:
        logger.error(f"Failed startup reference normalization: {exc}")
        return False, f"Startup reference normalization failed: {exc}", summary
