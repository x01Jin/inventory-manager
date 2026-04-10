"""Services for merging duplicate supplier and brand reference entries."""

from __future__ import annotations

from typing import List, Tuple

from inventory_app.database.connection import db
from inventory_app.database.models import Brand, Supplier
from inventory_app.utils.activity_logger import activity_logger
from inventory_app.utils.logger import logger


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
                user_name=(editor_name or "System").strip() or "System",
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

    updated_total = 0
    try:
        with db.transaction(immediate=True):
            for source_name in source_names:
                updated = db.execute_update(
                    "UPDATE Items SET brand = ? WHERE LOWER(COALESCE(brand, '')) = LOWER(?)",
                    (target.name, source_name),
                )
                updated_total += int(updated)

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
                user_name=(editor_name or "System").strip() or "System",
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
