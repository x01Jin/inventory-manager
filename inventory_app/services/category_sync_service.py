"""
Development-only category synchronization utilities.

This module keeps the Categories table aligned with the canonical categories
defined in category_config while preserving existing item links by remapping
legacy category rows before cleanup.
"""

from __future__ import annotations

from typing import Dict, Optional

from inventory_app.database.connection import db
from inventory_app.services.category_config import get_all_category_names
from inventory_app.utils.logger import logger


def _normalize_category_name(name: str) -> str:
    """Normalize category labels for alias-insensitive matching."""
    return "".join(ch for ch in name.lower() if ch.isalnum())


def _choose_target_category_id(
    legacy_name: str,
    canonical_ids_by_name: Dict[str, int],
    canonical_ids_by_normalized: Dict[str, int],
) -> Optional[int]:
    """Choose a canonical target category id for a legacy category label."""
    normalized = _normalize_category_name(legacy_name)

    target = canonical_ids_by_normalized.get(normalized)
    if target is not None:
        return target

    if "ta" in normalized and "non" in normalized and "consum" in normalized:
        return canonical_ids_by_name.get("Others")

    if "uncategorized" in normalized or normalized in {"", "na", "none"}:
        return canonical_ids_by_name.get("Uncategorized")

    return canonical_ids_by_name.get("Others")


def sync_development_categories() -> bool:
    """Synchronize Categories table with canonical category configuration.

    Behavior:
    - Insert any missing canonical categories.
    - Remap items from legacy categories to canonical categories.
    - Delete deprecated category rows after remapping.

    Returns:
        True on success, False on failure.
    """
    canonical_names = get_all_category_names()
    canonical_set = set(canonical_names)

    try:
        with db.transaction(immediate=True):
            existing_rows = db.execute_query("SELECT id, name FROM Categories")
            existing_names_lower = {str(r["name"]).lower() for r in existing_rows}

            for name in canonical_names:
                if name.lower() not in existing_names_lower:
                    db.execute_update(
                        "INSERT INTO Categories (name) VALUES (?)", (name,)
                    )
                    logger.info(f"Inserted missing canonical category: {name}")

            refreshed_rows = db.execute_query("SELECT id, name FROM Categories")

            canonical_ids_by_name: Dict[str, int] = {}
            canonical_ids_by_normalized: Dict[str, int] = {}
            for row in refreshed_rows:
                row_name = str(row["name"])
                if row_name in canonical_set:
                    row_id = int(row["id"])
                    canonical_ids_by_name[row_name] = row_id
                    canonical_ids_by_normalized[_normalize_category_name(row_name)] = (
                        row_id
                    )

            remapped_items = 0
            removed_categories = 0

            for row in refreshed_rows:
                category_id = int(row["id"])
                category_name = str(row["name"])

                if category_name in canonical_set:
                    continue

                target_id = _choose_target_category_id(
                    category_name,
                    canonical_ids_by_name,
                    canonical_ids_by_normalized,
                )

                if target_id is None:
                    logger.warning(
                        f"No target category found for legacy category '{category_name}', skipping"
                    )
                    continue

                if target_id != category_id:
                    remapped_items += db.execute_update(
                        "UPDATE Items SET category_id = ? WHERE category_id = ?",
                        (target_id, category_id),
                    )

                db.execute_update("DELETE FROM Categories WHERE id = ?", (category_id,))
                removed_categories += 1
                logger.info(
                    f"Mapped legacy category '{category_name}' to canonical id {target_id} and removed legacy row"
                )

            logger.info(
                "Category sync complete: "
                f"{len(canonical_names)} canonical categories ensured, "
                f"{remapped_items} item mappings updated, "
                f"{removed_categories} legacy categories removed"
            )

        return True
    except Exception:
        logger.exception("Failed to synchronize development categories")
        return False
