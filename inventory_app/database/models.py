"""
Data models for the inventory application.
Provides classes for database entities with CRUD operations.
Uses composition pattern with DatabaseConnection.
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, date, timezone
from dataclasses import dataclass, field
from enum import Enum

from inventory_app.database.connection import db
from inventory_app.utils.logger import logger
from inventory_app.utils.activity_logger import activity_logger
from inventory_app.utils.reference_normalization import (
    build_reference_compare_key,
    normalize_metric_size_value,
    normalize_whitespace,
)


def _to_iso(value: Optional[date | datetime]) -> Optional[str]:
    """Return ISO string for date/datetime or None if value is None."""
    if value is None:
        return None
    return value.isoformat()


def _audit_text(value: Any) -> Optional[str]:
    """Normalize values for audit history storage."""
    if value is None:
        return None
    return str(value)


def check_case_insensitive_duplicate(
    table: str, name: str, exclude_id: Optional[int] = None
) -> Tuple[bool, Optional[str]]:
    """Check if a case-insensitive duplicate exists in the given table.

    Per beta test requirement A.2: Prevent duplicates that differ only in
    capitalization (e.g., '10ml' vs '10mL', '50kg' vs '50KG').

    Args:
        table: Table name to check (Categories, Suppliers, Sizes, Brands)
        name: Name to check for duplicates
        exclude_id: ID to exclude from check (for updates)

    Returns:
        Tuple of (has_duplicate, existing_name) where existing_name is the
        matching name if a duplicate exists
    """
    try:
        target_key = build_reference_compare_key(name)
        if not target_key:
            return False, None

        if exclude_id:
            query = f"SELECT id, name FROM {table} WHERE id != ?"
            rows = db.execute_query(query, (exclude_id,), use_cache=False)
        else:
            query = f"SELECT id, name FROM {table}"
            rows = db.execute_query(query, use_cache=False)

        for row in rows:
            existing_name = row.get("name")
            if build_reference_compare_key(existing_name) == target_key:
                return True, existing_name

        return False, None
    except Exception as e:
        logger.error(f"Error checking for duplicate in {table}: {e}")
        return False, None


@dataclass
class Category:
    """Represents an item category.

    Categories are fixed in the system and defined in category_config.py.
    This model is read-only - categories cannot be added, edited, or deleted
    through the application.
    """

    id: Optional[int] = None
    name: str = ""

    @classmethod
    def get_all(cls) -> List["Category"]:
        """Get all categories."""
        try:
            rows = db.execute_query("SELECT * FROM Categories ORDER BY name")
            return [cls(**dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get categories: {e}")
            return []

    @classmethod
    def get_by_id(cls, category_id: int) -> Optional["Category"]:
        """Get category by ID."""
        try:
            rows = db.execute_query(
                "SELECT * FROM Categories WHERE id = ?", (category_id,)
            )
            return cls(**dict(rows[0])) if rows else None
        except Exception as e:
            logger.error(f"Failed to get category {category_id}: {e}")
            return None

    @classmethod
    def get_by_name(cls, name: str) -> Optional["Category"]:
        """Get category by name (case-insensitive)."""
        try:
            rows = db.execute_query(
                "SELECT * FROM Categories WHERE LOWER(name) = LOWER(?)", (name,)
            )
            return cls(**dict(rows[0])) if rows else None
        except Exception as e:
            logger.error(f"Failed to get category by name {name}: {e}")
            return None


@dataclass
class Supplier:
    """Represents a supplier."""

    id: Optional[int] = None
    name: str = ""

    def save(self) -> Tuple[bool, str]:
        """Save or update the supplier.

        Returns:
            Tuple of (success, message) where message contains error info if failed
        """
        try:
            self.name = normalize_whitespace(self.name)
            if not self.name:
                return False, "Supplier name is required"

            # Check for case-insensitive duplicate (beta test requirement A.2)
            has_dup, existing = check_case_insensitive_duplicate(
                "Suppliers", self.name, self.id
            )
            if has_dup:
                return (
                    False,
                    f"A supplier with similar name already exists: '{existing}'",
                )

            if self.id:
                query = "UPDATE Suppliers SET name = ? WHERE id = ?"
                db.execute_update(query, (self.name, self.id))
            else:
                query = "INSERT INTO Suppliers (name) VALUES (?)"
                result = db.execute_update(query, (self.name,), return_last_id=True)
                if isinstance(result, tuple):
                    _, self.id = result
                else:
                    logger.error("Failed to obtain last insert id for Supplier")
            return True, "Supplier saved successfully"
        except Exception as e:
            logger.error(f"Failed to save supplier: {e}")
            return False, str(e)

    @classmethod
    def get_all(cls) -> List["Supplier"]:
        """Get all suppliers."""
        try:
            rows = db.execute_query("SELECT * FROM Suppliers ORDER BY name")
            return [cls(**dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get suppliers: {e}")
            return []

    def get_usage_count(self) -> int:
        """Return number of items currently using this supplier."""
        if not self.id:
            return 0

        try:
            usage_check = db.execute_query(
                "SELECT COUNT(*) as count FROM Items WHERE supplier_id = ?", (self.id,)
            )
            return usage_check[0]["count"] if usage_check else 0
        except Exception as e:
            logger.error(f"Failed to count usage for supplier {self.id}: {e}")
            return 0

    def delete(self) -> Tuple[bool, str, int]:
        """Delete the supplier if it is not used by any item.

        Returns:
            Tuple of (success, message, usage_count)
        """
        try:
            if not self.id:
                return False, "Supplier has no ID", 0

            items_using = self.get_usage_count()

            if items_using > 0:
                logger.warning(
                    f"Cannot delete supplier {self.id}: supplier is being used by items"
                )
                return (
                    False,
                    f"Cannot delete supplier '{self.name}' because it is currently used by {items_using} item(s).",
                    items_using,
                )

            db.execute_update("DELETE FROM Suppliers WHERE id = ?", (self.id,))
            return True, "Supplier deleted successfully", 0
        except Exception as e:
            logger.error(f"Failed to delete supplier {self.id}: {e}")
            return False, str(e), 0

    @classmethod
    def get_by_id(cls, supplier_id: int) -> Optional["Supplier"]:
        """Get supplier by ID."""
        try:
            rows = db.execute_query(
                "SELECT * FROM Suppliers WHERE id = ?", (supplier_id,)
            )
            return cls(**dict(rows[0])) if rows else None
        except Exception as e:
            logger.error(f"Failed to get supplier {supplier_id}: {e}")
            return None


@dataclass
class Size:
    """Represents a size option."""

    id: Optional[int] = None
    name: str = ""

    def save(self) -> Tuple[bool, str]:
        """Save or update the size.

        Returns:
            Tuple of (success, message) where message contains error info if failed
        """
        try:
            normalized_name = normalize_metric_size_value(self.name)
            self.name = normalized_name or ""
            if not self.name:
                return False, "Size name is required"

            # Check for case-insensitive duplicate (beta test requirement A.2)
            has_dup, existing = check_case_insensitive_duplicate(
                "Sizes", self.name, self.id
            )
            if has_dup:
                return False, f"A size with similar name already exists: '{existing}'"

            if self.id:
                query = "UPDATE Sizes SET name = ? WHERE id = ?"
                db.execute_update(query, (self.name, self.id))
            else:
                query = "INSERT INTO Sizes (name) VALUES (?)"
                result = db.execute_update(query, (self.name,), return_last_id=True)
                if isinstance(result, tuple):
                    _, self.id = result
                else:
                    logger.error("Failed to obtain last insert id for Size")
            return True, "Size saved successfully"
        except Exception as e:
            logger.error(f"Failed to save size: {e}")
            return False, str(e)

    @classmethod
    def get_all(cls) -> List["Size"]:
        """Get all sizes."""
        try:
            rows = db.execute_query("SELECT * FROM Sizes ORDER BY name")
            return [cls(**dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get sizes: {e}")
            return []

    def get_usage_count(self) -> int:
        """Return number of items currently using this size (case-insensitive)."""
        if not self.name:
            return 0

        try:
            usage_check = db.execute_query(
                "SELECT COUNT(*) as count FROM Items WHERE LOWER(COALESCE(size, '')) = LOWER(?)",
                (self.name,),
            )
            return usage_check[0]["count"] if usage_check else 0
        except Exception as e:
            logger.error(f"Failed to count usage for size {self.id}: {e}")
            return 0

    def delete(self) -> Tuple[bool, str, int]:
        """Delete the size if it is not used by any item.

        Returns:
            Tuple of (success, message, usage_count)
        """
        try:
            if not self.id:
                return False, "Size has no ID", 0

            usage_count = self.get_usage_count()
            if usage_count > 0:
                logger.warning(
                    f"Cannot delete size {self.id}: size is being used by items"
                )
                return (
                    False,
                    f"Cannot delete size '{self.name}' because it is currently used by {usage_count} item(s).",
                    usage_count,
                )

            db.execute_update("DELETE FROM Sizes WHERE id = ?", (self.id,))
            return True, "Size deleted successfully", 0
        except Exception as e:
            logger.error(f"Failed to delete size {self.id}: {e}")
            return False, str(e), 0

    @classmethod
    def get_by_id(cls, size_id: int) -> Optional["Size"]:
        """Get size by ID."""
        try:
            rows = db.execute_query("SELECT * FROM Sizes WHERE id = ?", (size_id,))
            return cls(**dict(rows[0])) if rows else None
        except Exception as e:
            logger.error(f"Failed to get size {size_id}: {e}")
            return None


@dataclass
class Brand:
    """Represents a brand option."""

    id: Optional[int] = None
    name: str = ""

    def save(self) -> Tuple[bool, str]:
        """Save or update the brand.

        Returns:
            Tuple of (success, message) where message contains error info if failed
        """
        try:
            self.name = normalize_whitespace(self.name)
            if not self.name:
                return False, "Brand name is required"

            # Check for case-insensitive duplicate (beta test requirement A.2)
            has_dup, existing = check_case_insensitive_duplicate(
                "Brands", self.name, self.id
            )
            if has_dup:
                return False, f"A brand with similar name already exists: '{existing}'"

            if self.id:
                query = "UPDATE Brands SET name = ? WHERE id = ?"
                db.execute_update(query, (self.name, self.id))
            else:
                query = "INSERT INTO Brands (name) VALUES (?)"
                result = db.execute_update(query, (self.name,), return_last_id=True)
                if isinstance(result, tuple):
                    _, self.id = result
                else:
                    logger.error("Failed to obtain last insert id for Brand")
            return True, "Brand saved successfully"
        except Exception as e:
            logger.error(f"Failed to save brand: {e}")
            return False, str(e)

    @classmethod
    def get_all(cls) -> List["Brand"]:
        """Get all brands."""
        try:
            rows = db.execute_query("SELECT * FROM Brands ORDER BY name")
            return [cls(**dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get brands: {e}")
            return []

    def get_usage_count(self) -> int:
        """Return number of items currently using this brand (case-insensitive)."""
        if not self.name:
            return 0

        try:
            usage_check = db.execute_query(
                "SELECT COUNT(*) as count FROM Items WHERE LOWER(COALESCE(brand, '')) = LOWER(?)",
                (self.name,),
            )
            return usage_check[0]["count"] if usage_check else 0
        except Exception as e:
            logger.error(f"Failed to count usage for brand {self.id}: {e}")
            return 0

    def delete(self) -> Tuple[bool, str, int]:
        """Delete the brand if it is not used by any item.

        Returns:
            Tuple of (success, message, usage_count)
        """
        try:
            if not self.id:
                return False, "Brand has no ID", 0

            usage_count = self.get_usage_count()
            if usage_count > 0:
                logger.warning(
                    f"Cannot delete brand {self.id}: brand is being used by items"
                )
                return (
                    False,
                    f"Cannot delete brand '{self.name}' because it is currently used by {usage_count} item(s).",
                    usage_count,
                )

            db.execute_update("DELETE FROM Brands WHERE id = ?", (self.id,))
            return True, "Brand deleted successfully", 0
        except Exception as e:
            logger.error(f"Failed to delete brand {self.id}: {e}")
            return False, str(e), 0

    @classmethod
    def get_by_id(cls, brand_id: int) -> Optional["Brand"]:
        """Get brand by ID."""
        try:
            rows = db.execute_query("SELECT * FROM Brands WHERE id = ?", (brand_id,))
            return cls(**dict(rows[0])) if rows else None
        except Exception as e:
            logger.error(f"Failed to get brand {brand_id}: {e}")
            return None


@dataclass
class Item:
    """Represents an inventory item."""

    id: Optional[int] = None
    name: str = ""
    category_id: int = 0
    item_type: Optional[str] = None
    size: Optional[str] = None
    brand: Optional[str] = None
    other_specifications: Optional[str] = None
    po_number: Optional[str] = None
    supplier_id: Optional[int] = None
    expiration_date: Optional[date] = None
    calibration_date: Optional[date] = None
    is_consumable: int = 1
    acquisition_date: Optional[date] = None
    last_modified: Optional[datetime] = None

    @staticmethod
    def _normalize_optional_fk(value: Optional[int | str]) -> Optional[int]:
        """Normalize optional FK-like values to an int or None."""
        if value in (None, "", 0):
            return None

        if isinstance(value, int):
            return value if value > 0 else None

        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return None
            if stripped.isdigit():
                parsed = int(stripped)
                return parsed if parsed > 0 else None

        return None

    @staticmethod
    def _normalize_required_fk(value: Optional[int | str]) -> Optional[int]:
        """Normalize required FK-like values to a positive int, else None."""
        if isinstance(value, int):
            return value if value > 0 else None

        if isinstance(value, str):
            stripped = value.strip()
            if stripped.isdigit():
                parsed = int(stripped)
                return parsed if parsed > 0 else None

        return None

    def save(self, editor_name: str, batch_quantity: int = 0) -> bool:
        """Save or update the item with history tracking and batch creation."""
        try:
            self.name = normalize_whitespace(self.name)
            if not self.name:
                logger.error("Failed to save item: name is required")
                return False

            self.size = normalize_metric_size_value(self.size)
            self.brand = normalize_whitespace(self.brand) or None

            if not (editor_name or "").strip():
                logger.error("Failed to save item: editor_name is required")
                return False

            normalized_category_id = self._normalize_required_fk(self.category_id)
            if normalized_category_id is None:
                logger.error(
                    f"Failed to save item: invalid category_id '{self.category_id}'"
                )
                return False

            if Category.get_by_id(normalized_category_id) is None:
                logger.error(
                    f"Failed to save item: category_id {normalized_category_id} does not exist"
                )
                return False

            normalized_supplier_id = self._normalize_optional_fk(self.supplier_id)
            if normalized_supplier_id is not None:
                if Supplier.get_by_id(normalized_supplier_id) is None:
                    logger.error(
                        f"Failed to save item: supplier_id {normalized_supplier_id} does not exist"
                    )
                    return False

            self.category_id = normalized_category_id
            self.supplier_id = normalized_supplier_id

            current_time = datetime.now()
            # Wrap the entire save operation in a single transaction so that
            # creating the item and its initial batch (if any) are committed
            # atomically.
            with db.transaction():
                if self.id:
                    existing_rows = db.execute_query(
                        "SELECT * FROM Items WHERE id = ?",
                        (self.id,),
                        use_cache=False,
                    )
                    if not existing_rows:
                        logger.error(f"Failed to save item: item {self.id} not found")
                        return False

                    existing = dict(existing_rows[0])

                    new_values = {
                        "name": self.name,
                        "category_id": self.category_id,
                        "item_type": self.item_type,
                        "size": self.size,
                        "brand": self.brand,
                        "other_specifications": self.other_specifications,
                        "po_number": self.po_number,
                        "supplier_id": self.supplier_id,
                        "expiration_date": _to_iso(self.expiration_date),
                        "calibration_date": _to_iso(self.calibration_date),
                        "is_consumable": self.is_consumable,
                        "acquisition_date": _to_iso(self.acquisition_date),
                    }

                    field_changes = []
                    for field_name, new_value in new_values.items():
                        old_value = existing.get(field_name)
                        if old_value != new_value:
                            field_changes.append(
                                (
                                    self.id,
                                    editor_name,
                                    "Item field updated",
                                    field_name,
                                    _audit_text(old_value),
                                    _audit_text(new_value),
                                )
                            )

                    if field_changes:
                        db.execute_many(
                            """
                            INSERT INTO Update_History (
                                item_id, editor_name, reason, field_name, old_value, new_value
                            ) VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            field_changes,
                        )
                    else:
                        db.execute_update(
                            """
                            INSERT INTO Update_History (item_id, editor_name, reason)
                            VALUES (?, ?, ?)
                            """,
                            (self.id, editor_name, "Item update saved"),
                        )

                    # Update item
                    query = """
                    UPDATE Items SET name = ?, category_id = ?, item_type = ?, size = ?, brand = ?,
                    other_specifications = ?, po_number = ?, supplier_id = ?,
                    expiration_date = ?, calibration_date = ?, is_consumable = ?,
                    acquisition_date = ?, last_modified = ? WHERE id = ?
                    """
                    params = (
                        self.name,
                        self.category_id,
                        self.item_type,
                        self.size,
                        self.brand,
                        self.other_specifications,
                        self.po_number,
                        self.supplier_id,
                        _to_iso(self.expiration_date),
                        _to_iso(self.calibration_date),
                        self.is_consumable,
                        _to_iso(self.acquisition_date),
                        current_time.isoformat(),
                        self.id,
                    )
                    db.execute_update(query, params)

                    # Log activity
                    activity_logger.log_activity(
                        activity_logger.ITEM_EDITED,
                        f"Updated item: {self.name}",
                        self.id,
                        "item",
                        editor_name,
                    )
                else:
                    # Insert new item
                    query = """
                    INSERT INTO Items (name, category_id, item_type, size, brand, other_specifications,
                    po_number, supplier_id, expiration_date, calibration_date, is_consumable,
                    acquisition_date, last_modified) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    params = (
                        self.name,
                        self.category_id,
                        self.item_type,
                        self.size,
                        self.brand,
                        self.other_specifications,
                        self.po_number,
                        self.supplier_id,
                        _to_iso(self.expiration_date),
                        _to_iso(self.calibration_date),
                        self.is_consumable,
                        _to_iso(self.acquisition_date),
                        current_time.isoformat(),
                    )
                    result = db.execute_update(query, params, return_last_id=True)
                    if isinstance(result, tuple):
                        _, self.id = result
                    else:
                        logger.error("Failed to obtain last insert id for Item")
                    self.last_modified = current_time

                    # Create batches if batch_quantity is specified
                    if not self.id:
                        # In the insert path set last_modified
                        self.last_modified = current_time

                    if batch_quantity > 0 and self.id:
                        self._create_batches(batch_quantity)

                    # Log activity
                    activity_logger.log_activity(
                        activity_logger.ITEM_ADDED,
                        f"Added new item: {self.name} ({batch_quantity} batches)",
                        self.id,
                        "item",
                        editor_name,
                    )

                return True
        except Exception as e:
            logger.error(f"Failed to save item: {e}")
            return False

    def _create_batches(self, quantity: int) -> None:
        """Create a single batch with the specified total quantity for this item."""
        try:
            if not self.id:
                logger.error("Cannot create batch: item ID is None")
                return

            logger.info(
                f"Creating batch with {quantity} total units for item {self.id} ({self.name})"
            )
            batch_date = (
                self.acquisition_date.isoformat()
                if isinstance(self.acquisition_date, date)
                else datetime.now().date().isoformat()
            )

            # Create ONE batch with the total quantity
            query = """
            INSERT INTO Item_Batches (item_id, batch_number, date_received, quantity_received)
            VALUES (?, ?, ?, ?)
            """
            result = db.execute_update(query, (self.id, 1, batch_date, quantity))
            if result is None:
                logger.error(f"Failed to insert batch for item {self.id}")
            else:
                logger.debug(f"Inserted batch with {quantity} units for item {self.id}")

            # Verify batch was created with correct quantity
            verify_query = """
            SELECT quantity_received FROM Item_Batches
            WHERE item_id = ? AND batch_number = 1
            """
            verify_result = db.execute_query(verify_query, (self.id,))
            if verify_result:
                actual_quantity = verify_result[0]["quantity_received"]
                logger.info(
                    f"Verification: Created batch with {actual_quantity} units for item {self.id}"
                )
                if actual_quantity != quantity:
                    logger.error(
                        f"Batch quantity mismatch: expected {quantity}, got {actual_quantity}"
                    )
            else:
                logger.error(f"Could not verify batch creation for item {self.id}")

        except Exception as e:
            logger.error(f"Failed to create batch for item {self.id}: {e}")
            logger.error(f"Error details: {str(e)}")

    @classmethod
    def get_batches_for_item(cls, item_id: int) -> List[Dict[str, Any]]:
        """Return item batches ordered by batch number with movement stats."""
        try:
            query = """
            SELECT
                ib.id,
                ib.item_id,
                ib.batch_number,
                ib.date_received,
                ib.quantity_received,
                ib.disposal_date,
                COALESCE(SUM(
                    CASE
                        WHEN sm.movement_type IN ('CONSUMPTION', 'DISPOSAL', 'RESERVATION', 'REQUEST')
                        THEN sm.quantity
                        WHEN sm.movement_type = 'RETURN'
                        THEN -sm.quantity
                        ELSE 0
                    END
                ), 0) AS committed_quantity,
                COALESCE(COUNT(sm.id), 0) AS movement_count
            FROM Item_Batches ib
            LEFT JOIN Stock_Movements sm ON sm.batch_id = ib.id
            WHERE ib.item_id = ?
            GROUP BY ib.id, ib.item_id, ib.batch_number, ib.date_received, ib.quantity_received, ib.disposal_date
            ORDER BY ib.batch_number ASC
            """
            return [
                dict(row)
                for row in db.execute_query(query, (item_id,), use_cache=False)
            ]
        except Exception as e:
            logger.error(f"Failed to get batches for item {item_id}: {e}")
            return []

    @classmethod
    def sync_batches_for_item(
        cls,
        item_id: int,
        batches: List[Dict[str, Any]],
        editor_name: str,
    ) -> Tuple[bool, str]:
        """Create/update/delete item batches to match provided list."""
        try:
            if not item_id:
                return False, "Invalid item ID."

            if not (editor_name or "").strip():
                return False, "Editor name is required for batch updates."

            normalized_batches: List[Dict[str, Any]] = []
            seen_numbers = set()
            for raw in batches:
                batch_number = int(raw.get("batch_number") or 0)
                quantity_received = int(raw.get("quantity_received") or 0)
                date_received = str(raw.get("date_received") or "").strip()
                disposal_date_raw = raw.get("disposal_date")
                disposal_date = (
                    str(disposal_date_raw).strip() if disposal_date_raw else None
                )

                if batch_number <= 0:
                    return False, "Batch numbers must be positive integers."
                if batch_number in seen_numbers:
                    return (
                        False,
                        f"Duplicate batch label B{batch_number} is not allowed.",
                    )
                seen_numbers.add(batch_number)

                if quantity_received <= 0:
                    return (
                        False,
                        f"Batch B{batch_number} quantity must be greater than zero.",
                    )

                try:
                    parsed_date = date.fromisoformat(date_received)
                except Exception:
                    return False, f"Batch B{batch_number} has an invalid received date."

                if disposal_date:
                    try:
                        date.fromisoformat(disposal_date)
                    except Exception:
                        return (
                            False,
                            f"Batch B{batch_number} has an invalid disposal date.",
                        )

                normalized_batches.append(
                    {
                        "id": raw.get("id"),
                        "batch_number": batch_number,
                        "quantity_received": quantity_received,
                        "date_received": parsed_date.isoformat(),
                        "disposal_date": disposal_date,
                    }
                )

            if not normalized_batches:
                return False, "At least one batch is required."

            normalized_batches.sort(key=lambda b: b["batch_number"])

            existing_rows = cls.get_batches_for_item(item_id)
            existing_by_id = {row["id"]: row for row in existing_rows}
            incoming_ids = {
                int(batch["id"])
                for batch in normalized_batches
                if batch.get("id") not in (None, "", 0)
            }

            def _format_batch_snapshot(batch_row: Dict[str, Any]) -> str:
                batch_number = batch_row.get("batch_number")
                date_received = batch_row.get("date_received") or ""
                quantity_received = batch_row.get("quantity_received")
                disposal_date = batch_row.get("disposal_date") or "none"
                return (
                    f"B{batch_number}: date_received={date_received}, "
                    f"quantity_received={quantity_received}, disposal_date={disposal_date}"
                )

            with db.transaction():
                history_rows: List[Tuple[Any, ...]] = []

                # Validate quantity updates against committed movements.
                for batch in normalized_batches:
                    batch_id = batch.get("id")
                    if batch_id in (None, "", 0):
                        continue

                    existing = existing_by_id.get(int(batch_id))
                    if not existing:
                        return (
                            False,
                            "One or more batches no longer exist. Please refresh and try again.",
                        )

                    committed_qty = int(existing.get("committed_quantity") or 0)
                    if batch["quantity_received"] < committed_qty:
                        return (
                            False,
                            f"Batch B{batch['batch_number']} quantity cannot be below committed usage ({committed_qty}).",
                        )

                # Validate removals: do not remove batches with movement history.
                removable = [
                    row for row in existing_rows if row["id"] not in incoming_ids
                ]
                for row in removable:
                    if int(row.get("movement_count") or 0) > 0:
                        return (
                            False,
                            f"Batch B{row['batch_number']} has stock movement history and cannot be removed.",
                        )

                # Upsert incoming batches.
                for batch in normalized_batches:
                    batch_id = batch.get("id")
                    if batch_id in (None, "", 0):
                        db.execute_update(
                            """
                            INSERT INTO Item_Batches (item_id, batch_number, date_received, quantity_received, disposal_date)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (
                                item_id,
                                batch["batch_number"],
                                batch["date_received"],
                                batch["quantity_received"],
                                batch["disposal_date"],
                            ),
                        )
                        history_rows.append(
                            (
                                item_id,
                                editor_name,
                                "Batch created during sync",
                                "batch",
                                None,
                                _format_batch_snapshot(batch),
                            )
                        )
                    else:
                        existing = existing_by_id.get(int(batch_id)) or {}
                        changes = [
                            (
                                "batch_number",
                                existing.get("batch_number"),
                                batch["batch_number"],
                            ),
                            (
                                "date_received",
                                existing.get("date_received"),
                                batch["date_received"],
                            ),
                            (
                                "quantity_received",
                                existing.get("quantity_received"),
                                batch["quantity_received"],
                            ),
                            (
                                "disposal_date",
                                existing.get("disposal_date"),
                                batch["disposal_date"],
                            ),
                        ]

                        for field_name, old_value, new_value in changes:
                            if old_value != new_value:
                                history_rows.append(
                                    (
                                        item_id,
                                        editor_name,
                                        "Batch field updated during sync",
                                        field_name,
                                        _audit_text(old_value),
                                        _audit_text(new_value),
                                    )
                                )

                        db.execute_update(
                            """
                            UPDATE Item_Batches
                            SET batch_number = ?, date_received = ?, quantity_received = ?, disposal_date = ?
                            WHERE id = ? AND item_id = ?
                            """,
                            (
                                batch["batch_number"],
                                batch["date_received"],
                                batch["quantity_received"],
                                batch["disposal_date"],
                                int(batch_id),
                                item_id,
                            ),
                        )

                # Remove eligible batches that were omitted from incoming set.
                for row in removable:
                    history_rows.append(
                        (
                            item_id,
                            editor_name,
                            "Batch removed during sync",
                            "batch",
                            _format_batch_snapshot(row),
                            None,
                        )
                    )
                    db.execute_update(
                        "DELETE FROM Item_Batches WHERE id = ?", (row["id"],)
                    )

                # Keep item-level acquisition_date aligned as compatibility fallback.
                min_batch_date_row = db.execute_query(
                    "SELECT MIN(date_received) AS first_date FROM Item_Batches WHERE item_id = ?",
                    (item_id,),
                    use_cache=False,
                )
                first_batch_date = None
                if min_batch_date_row:
                    first_batch_date = min_batch_date_row[0].get("first_date")

                db.execute_update(
                    "UPDATE Items SET acquisition_date = ?, last_modified = ? WHERE id = ?",
                    (first_batch_date, datetime.now().isoformat(), item_id),
                )

                if history_rows:
                    db.execute_many(
                        """
                        INSERT INTO Update_History (item_id, editor_name, reason, field_name, old_value, new_value)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        history_rows,
                    )

            return True, "Batch records saved."
        except Exception as e:
            logger.error(f"Failed to sync batches for item {item_id}: {e}")
            return False, f"Failed to save batches: {str(e)}"

    def delete(self, editor_name: str, reason: str) -> bool:
        """Delete the item and all related records if not currently requested."""
        try:
            if not self.id:
                return False

            # Check if item is currently requested (has unreturned requisitions)
            requested_check = """
            SELECT COUNT(*) as requested_count
            FROM Requisition_Items ri
            JOIN Requisitions r ON ri.requisition_id = r.id
            WHERE ri.item_id = ?
            AND NOT EXISTS (
                SELECT 1 FROM Stock_Movements sm
                WHERE sm.item_id = ri.item_id
                AND sm.movement_type = ?
                AND sm.source_id = r.id
            )
            """
            from inventory_app.services.movement_types import MovementType

            requested_result = db.execute_query(
                requested_check, (self.id, MovementType.RETURN.value)
            )
            if requested_result and requested_result[0]["requested_count"] > 0:
                logger.warning(
                    f"Cannot delete item {self.id}: item is currently requested"
                )
                return False

            # Log to disposal history FIRST (before deleting related records)
            disposal_query = """
            INSERT INTO Disposal_History (item_id, reason, editor_name)
            VALUES (?, ?, ?)
            """
            db.execute_update(disposal_query, (self.id, reason, editor_name))
            logger.info(f"Logged disposal history for item {self.id}")

            # Perform deletions in a single transaction to ensure atomicity and
            # remove fragile timing-based hacks. This relies on foreign keys
            # to enforce constraints and will rollback on any failure.
            with db.transaction():
                # 1. Delete requisition items first (has dual dependencies: item + requisition)
                logger.info(f"Deleting Requisition_Items for item {self.id}")
                db.execute_update(
                    "DELETE FROM Requisition_Items WHERE item_id = ?", (self.id,)
                )

                # 2. Delete stock movements (references both items and batches)
                logger.info(f"Deleting Stock_Movements for item {self.id}")
                db.execute_update(
                    "DELETE FROM Stock_Movements WHERE item_id = ?", (self.id,)
                )

                # 3. Delete item batches (only depends on items, safe after movements deleted)
                logger.info(f"Deleting Item_Batches for item {self.id}")
                db.execute_update(
                    "DELETE FROM Item_Batches WHERE item_id = ?", (self.id,)
                )

                # 4. Delete update history (only depends on items)
                logger.info(f"Deleting Update_History for item {self.id}")
                db.execute_update(
                    "DELETE FROM Update_History WHERE item_id = ?", (self.id,)
                )

                # 5. PRESERVE disposal history (per beta test #16: disposal history profile must persist)
                logger.info(
                    f"Preserving Disposal_History for item {self.id} (required for historical reports)"
                )

                # 6. Finally delete the item itself (no dependencies remain)
                logger.info(f"Deleting main Items record {self.id}")
                db.execute_update("DELETE FROM Items WHERE id = ?", (self.id,))

                activity_logger.log_activity(
                    activity_logger.ITEM_DELETED,
                    f"Deleted item: {self.name}",
                    self.id,
                    "item",
                    editor_name,
                )

            logger.info(f"Successfully deleted item {self.id} and all related records")
            return True

        except Exception as e:
            logger.error(f"Failed to delete item {self.id}: {e}")
            logger.error(f"Error details: {str(e)}")
            return False

    @classmethod
    def get_all(cls) -> List["Item"]:
        """Get all items."""
        try:
            rows = db.execute_query("SELECT * FROM Items ORDER BY name")
            items = []
            for row in rows:
                item_dict = dict(row)
                # Convert date strings back to date objects
                if item_dict.get("expiration_date"):
                    item_dict["expiration_date"] = date.fromisoformat(
                        item_dict["expiration_date"]
                    )
                if item_dict.get("calibration_date"):
                    item_dict["calibration_date"] = date.fromisoformat(
                        item_dict["calibration_date"]
                    )
                if item_dict.get("acquisition_date"):
                    item_dict["acquisition_date"] = date.fromisoformat(
                        item_dict["acquisition_date"]
                    )
                if item_dict.get("last_modified"):
                    item_dict["last_modified"] = datetime.fromisoformat(
                        item_dict["last_modified"]
                    )
                items.append(cls(**item_dict))
            return items
        except Exception as e:
            logger.error(f"Failed to get items: {e}")
            return []

    @classmethod
    def find_likely_duplicates(
        cls,
        name: str,
        category_id: int,
        exclude_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Find likely duplicate items by normalized name within a category."""
        try:
            compare_name = build_reference_compare_key(name)
            if not compare_name:
                return []

            normalized_category_id = cls._normalize_required_fk(category_id)
            if normalized_category_id is None:
                return []

            query = """
            SELECT
                i.id,
                i.name,
                c.name AS category_name,
                i.size,
                i.brand,
                s.name AS supplier_name
            FROM Items i
            JOIN Categories c ON c.id = i.category_id
            LEFT JOIN Suppliers s ON s.id = i.supplier_id
            WHERE i.category_id = ?
            """
            params: List[Any] = [normalized_category_id]

            if exclude_id is not None:
                query += " AND i.id != ?"
                params.append(exclude_id)

            query += " ORDER BY i.name"
            rows = db.execute_query(query, tuple(params), use_cache=False)

            matches: List[Dict[str, Any]] = []
            for row in rows:
                row_name = row.get("name")
                if build_reference_compare_key(row_name) == compare_name:
                    matches.append(dict(row))

            return matches
        except Exception as e:
            logger.error(f"Failed to find likely duplicates for item '{name}': {e}")
            return []

    @classmethod
    def get_by_id(cls, item_id: int) -> Optional["Item"]:
        """Get item by ID."""
        try:
            rows = db.execute_query("SELECT * FROM Items WHERE id = ?", (item_id,))
            if not rows:
                return None

            item_dict = dict(rows[0])
            # Convert date strings
            if item_dict.get("expiration_date"):
                item_dict["expiration_date"] = date.fromisoformat(
                    item_dict["expiration_date"]
                )
            if item_dict.get("calibration_date"):
                item_dict["calibration_date"] = date.fromisoformat(
                    item_dict["calibration_date"]
                )
            if item_dict.get("acquisition_date"):
                item_dict["acquisition_date"] = date.fromisoformat(
                    item_dict["acquisition_date"]
                )
            if item_dict.get("last_modified"):
                item_dict["last_modified"] = datetime.fromisoformat(
                    item_dict["last_modified"]
                )

            return cls(**item_dict)
        except Exception as e:
            logger.error(f"Failed to get item {item_id}: {e}")
            return None

    @classmethod
    def search(cls, search_term: str) -> List["Item"]:
        """Search items by name."""
        try:
            query = "SELECT * FROM Items WHERE name LIKE ? ORDER BY name"
            rows = db.execute_query(query, (f"%{search_term}%",))
            items = []
            for row in rows:
                item_dict = dict(row)
                # Convert dates (same as above)
                if item_dict.get("expiration_date"):
                    item_dict["expiration_date"] = date.fromisoformat(
                        item_dict["expiration_date"]
                    )
                if item_dict.get("calibration_date"):
                    item_dict["calibration_date"] = date.fromisoformat(
                        item_dict["calibration_date"]
                    )
                if item_dict.get("acquisition_date"):
                    item_dict["acquisition_date"] = date.fromisoformat(
                        item_dict["acquisition_date"]
                    )
                if item_dict.get("last_modified"):
                    item_dict["last_modified"] = datetime.fromisoformat(
                        item_dict["last_modified"]
                    )
                items.append(cls(**item_dict))
            return items
        except Exception as e:
            logger.error(f"Failed to search items: {e}")
            return []


@dataclass
class ItemSDS:
    """Represents SDS metadata linked to a single inventory item."""

    id: Optional[int] = None
    item_id: int = 0
    stored_filename: Optional[str] = None
    original_filename: Optional[str] = None
    file_path: Optional[str] = None
    mime_type: Optional[str] = None
    sds_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None

    @staticmethod
    def _get_item_label(item_id: int) -> str:
        """Return a human-friendly item label for activity text."""
        try:
            rows = db.execute_query("SELECT name FROM Items WHERE id = ?", (item_id,))
            if rows and (rows[0].get("name") or "").strip():
                return rows[0]["name"].strip()
        except Exception:
            pass
        return "item"

    @classmethod
    def get_by_item_id(cls, item_id: int) -> Optional["ItemSDS"]:
        """Get SDS metadata for a specific item."""
        try:
            rows = db.execute_query(
                "SELECT * FROM Item_SDS WHERE item_id = ?", (item_id,)
            )
            if not rows:
                return None

            data = dict(rows[0])
            if data.get("created_at"):
                data["created_at"] = datetime.fromisoformat(data["created_at"])
            if data.get("updated_at"):
                data["updated_at"] = datetime.fromisoformat(data["updated_at"])
            return cls(**data)
        except Exception as e:
            logger.error(f"Failed to load SDS for item {item_id}: {e}")
            return None

    def save(self, editor_name: str, reason: str = "SDS updated") -> bool:
        """Insert or update SDS metadata and write an audit history entry."""
        if not self.item_id:
            logger.error("Cannot save SDS without a valid item_id")
            return False

        try:
            current_time = datetime.now().isoformat()
            is_new_record = False
            with db.transaction():
                existing = db.execute_query(
                    "SELECT id FROM Item_SDS WHERE item_id = ?",
                    (self.item_id,),
                    use_cache=False,
                )

                if existing:
                    self.id = existing[0]["id"]
                    db.execute_update(
                        """
                        UPDATE Item_SDS
                        SET stored_filename = ?, original_filename = ?, file_path = ?,
                            mime_type = ?, sds_notes = ?, updated_at = ?, updated_by = ?
                        WHERE item_id = ?
                        """,
                        (
                            self.stored_filename,
                            self.original_filename,
                            self.file_path,
                            self.mime_type,
                            self.sds_notes,
                            current_time,
                            editor_name,
                            self.item_id,
                        ),
                    )
                else:
                    is_new_record = True
                    result = db.execute_update(
                        """
                        INSERT INTO Item_SDS (
                            item_id, stored_filename, original_filename, file_path,
                            mime_type, sds_notes, created_at, updated_at, updated_by
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            self.item_id,
                            self.stored_filename,
                            self.original_filename,
                            self.file_path,
                            self.mime_type,
                            self.sds_notes,
                            current_time,
                            current_time,
                            editor_name,
                        ),
                        return_last_id=True,
                    )
                    if isinstance(result, tuple):
                        _, self.id = result

                db.execute_update(
                    """
                    INSERT INTO Update_History (item_id, editor_name, reason)
                    VALUES (?, ?, ?)
                    """,
                    (self.item_id, editor_name, reason),
                )

                activity_logger.log_activity(
                    activity_logger.SDS_UPLOADED,
                    (
                        f"Uploaded SDS for {self._get_item_label(self.item_id)}"
                        if is_new_record
                        else f"Updated SDS for {self._get_item_label(self.item_id)}"
                    ),
                    self.item_id,
                    "item_sds",
                    editor_name,
                )

            return True
        except Exception as e:
            logger.error(f"Failed to save SDS for item {self.item_id}: {e}")
            return False

    @classmethod
    def delete_for_item(
        cls, item_id: int, editor_name: str, reason: str = "SDS removed"
    ) -> bool:
        """Delete SDS metadata for an item and write an audit entry."""
        try:
            with db.transaction():
                db.execute_update("DELETE FROM Item_SDS WHERE item_id = ?", (item_id,))
                db.execute_update(
                    """
                    INSERT INTO Update_History (item_id, editor_name, reason)
                    VALUES (?, ?, ?)
                    """,
                    (item_id, editor_name, reason),
                )
                activity_logger.log_activity(
                    activity_logger.SDS_REMOVED,
                    f"Removed SDS for {cls._get_item_label(item_id)}",
                    item_id,
                    "item_sds",
                    editor_name,
                )
            return True
        except Exception as e:
            logger.error(f"Failed to delete SDS for item {item_id}: {e}")
            return False


class RequesterType(Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    FACULTY = "faculty"


@dataclass
class Requester:
    """Represents a requester.

    Requesters have a type that determines which additional fields are required:
    - Student: Requires grade_level and section
    - Teacher: Requires department
    - Faculty/Individual: Simplified mode with name only
    """

    id: Optional[int] = None
    name: str = ""
    requester_type: str = "teacher"
    grade_level: Optional[str] = None
    section: Optional[str] = None
    department: Optional[str] = None
    created_at: Optional[datetime] = None

    def save(self, editor_name: str, reason: Optional[str] = None) -> bool:
        """Save or update the requester with mandatory editor attribution."""
        try:
            if not (editor_name or "").strip():
                logger.error("Failed to save requester: editor_name is required")
                return False

            if self.id:
                query = """UPDATE Requesters SET name = ?, requester_type = ?,
                           grade_level = ?, section = ?, department = ? WHERE id = ?"""
                db.execute_update(
                    query,
                    (
                        self.name,
                        self.requester_type,
                        self.grade_level,
                        self.section,
                        self.department,
                        self.id,
                    ),
                )
            else:
                current_time = datetime.now()
                query = """INSERT INTO Requesters (name, requester_type, grade_level, section,
                           department, created_at) VALUES (?, ?, ?, ?, ?, ?)"""
                result = db.execute_update(
                    query,
                    (
                        self.name,
                        self.requester_type,
                        self.grade_level,
                        self.section,
                        self.department,
                        current_time.isoformat(),
                    ),
                    return_last_id=True,
                )
                if isinstance(result, tuple):
                    _, self.id = result
                else:
                    logger.error("Failed to obtain last insert id for Requester")
                self.created_at = current_time
            return True
        except Exception as e:
            logger.error(f"Failed to save requester: {e}")
            return False

    @classmethod
    def get_all(cls) -> List["Requester"]:
        """Get all requesters."""
        try:
            rows = db.execute_query("SELECT * FROM Requesters ORDER BY name")
            requesters = []
            for row in rows:
                req_dict = dict(row)
                # Convert datetime string to datetime object
                if req_dict.get("created_at"):
                    req_dict["created_at"] = datetime.fromisoformat(
                        req_dict["created_at"]
                    )
                requesters.append(cls(**req_dict))
            return requesters
        except Exception as e:
            logger.error(f"Failed to get requesters: {e}")
            return []

    @classmethod
    def get_by_id(cls, requester_id: int) -> Optional["Requester"]:
        """Get requester by ID."""
        try:
            rows = db.execute_query(
                "SELECT * FROM Requesters WHERE id = ?", (requester_id,)
            )
            if not rows:
                return None

            req_dict = dict(rows[0])
            # Convert datetime string to datetime object
            if req_dict.get("created_at"):
                req_dict["created_at"] = datetime.fromisoformat(req_dict["created_at"])

            return cls(**req_dict)
        except Exception as e:
            logger.error(f"Failed to get requester {requester_id}: {e}")
            return None

    def delete(self, editor_name: str) -> bool:
        """Delete the requester with mandatory editor attribution."""
        try:
            if not self.id:
                return False

            if not (editor_name or "").strip():
                logger.error("Failed to delete requester: editor_name is required")
                return False

            # Check if requester has any associated requisitions
            usage_check = db.execute_query(
                "SELECT COUNT(*) as count FROM Requisitions WHERE requester_id = ?",
                (self.id,),
            )
            if usage_check and usage_check[0]["count"] > 0:
                logger.warning(
                    f"Cannot delete requester {self.id}: requester has associated requisitions"
                )
                return False

            db.execute_update("DELETE FROM Requesters WHERE id = ?", (self.id,))
            return True
        except Exception as e:
            logger.error(f"Failed to delete requester {self.id}: {e}")
            return False


@dataclass
class Requisition:
    """Represents a requesting requisition."""

    id: Optional[int] = None
    requester_id: int = 0
    expected_request: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    expected_return: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    status: str = "requested"  # 'requested', 'active', 'returned', 'overdue'
    lab_activity_name: str = ""
    lab_activity_description: Optional[str] = (
        None  # For detailed activity information stored for reports
    )
    lab_activity_date: date = field(default_factory=date.today)
    num_students: Optional[int] = None
    num_groups: Optional[int] = None
    # Individual request fields
    is_individual: int = 0
    individual_name: Optional[str] = None
    individual_contact: Optional[str] = None
    individual_purpose: Optional[str] = None

    def save(self, editor_name: str) -> bool:
        """Save or update the requisition with history tracking."""
        try:
            if not (editor_name or "").strip():
                logger.error("Failed to save requisition: editor_name is required")
                return False

            if self.id:
                existing_rows = db.execute_query(
                    "SELECT * FROM Requisitions WHERE id = ?",
                    (self.id,),
                    use_cache=False,
                )
                if not existing_rows:
                    logger.error(
                        f"Failed to save requisition: requisition {self.id} not found"
                    )
                    return False

                existing = dict(existing_rows[0])

                new_values = {
                    "requester_id": self.requester_id,
                    "expected_request": self.expected_request.isoformat(),
                    "expected_return": self.expected_return.isoformat(),
                    "status": self.status,
                    "lab_activity_name": self.lab_activity_name,
                    "lab_activity_description": self.lab_activity_description,
                    "lab_activity_date": self.lab_activity_date.isoformat(),
                    "num_students": self.num_students,
                    "num_groups": self.num_groups,
                    "is_individual": self.is_individual,
                    "individual_name": self.individual_name,
                    "individual_contact": self.individual_contact,
                    "individual_purpose": self.individual_purpose,
                }

                field_changes = []
                for field_name, new_value in new_values.items():
                    old_value = existing.get(field_name)
                    if old_value != new_value:
                        field_changes.append(
                            (
                                self.id,
                                editor_name,
                                "Requisition field updated",
                                field_name,
                                _audit_text(old_value),
                                _audit_text(new_value),
                            )
                        )

                if field_changes:
                    db.execute_many(
                        """
                        INSERT INTO Requisition_History (
                            requisition_id, editor_name, reason, field_name, old_value, new_value
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        field_changes,
                    )
                else:
                    db.execute_update(
                        """
                        INSERT INTO Requisition_History (requisition_id, editor_name, reason)
                        VALUES (?, ?, ?)
                        """,
                        (self.id, editor_name, "Requisition update saved"),
                    )

                # Update requisition
                query = """
                UPDATE Requisitions SET requester_id = ?,
                expected_request = ?, expected_return = ?, status = ?,
                lab_activity_name = ?, lab_activity_description = ?, lab_activity_date = ?,
                num_students = ?, num_groups = ?,
                is_individual = ?, individual_name = ?,
                individual_contact = ?, individual_purpose = ? WHERE id = ?
                """
                db.execute_update(
                    query,
                    (
                        self.requester_id,
                        self.expected_request.isoformat(),
                        self.expected_return.isoformat(),
                        self.status,
                        self.lab_activity_name,
                        self.lab_activity_description,
                        self.lab_activity_date.isoformat(),
                        self.num_students,
                        self.num_groups,
                        self.is_individual,
                        self.individual_name,
                        self.individual_contact,
                        self.individual_purpose,
                        self.id,
                    ),
                )
            else:
                # Insert new
                query = """
                INSERT INTO Requisitions (requester_id, expected_request,
                expected_return, status, lab_activity_name, lab_activity_description, lab_activity_date,
                num_students, num_groups, is_individual, individual_name,
                individual_contact, individual_purpose) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                result = db.execute_update(
                    query,
                    (
                        self.requester_id,
                        self.expected_request.isoformat(),
                        self.expected_return.isoformat(),
                        self.status,
                        self.lab_activity_name,
                        self.lab_activity_description,
                        self.lab_activity_date.isoformat(),
                        self.num_students,
                        self.num_groups,
                        self.is_individual,
                        self.individual_name,
                        self.individual_contact,
                        self.individual_purpose,
                    ),
                    return_last_id=True,
                )
                if isinstance(result, tuple):
                    _, self.id = result
                else:
                    logger.error("Failed to obtain last insert id for Requisition")

                if self.id:
                    db.execute_update(
                        """
                        INSERT INTO Requisition_History (requisition_id, editor_name, reason)
                        VALUES (?, ?, ?)
                        """,
                        (self.id, editor_name, "Requisition created"),
                    )

            return True
        except Exception as e:
            logger.error(f"Failed to save requisition: {e}")
            return False

    def delete(self, editor_name: str) -> bool:
        """Delete the requisition and handle related records."""
        try:
            if not self.id:
                return False
            with db.transaction():
                # Delete related stock movements first
                from inventory_app.services.movement_types import MovementType

                db.execute_update(
                    "DELETE FROM Stock_Movements WHERE source_id = ? AND movement_type = ?",
                    (self.id, MovementType.CONSUMPTION.value),
                )

                # Delete requisition items
                db.execute_update(
                    "DELETE FROM Requisition_Items WHERE requisition_id = ?", (self.id,)
                )

                # Delete history records (to avoid foreign key constraint)
                db.execute_update(
                    "DELETE FROM Requisition_History WHERE requisition_id = ?",
                    (self.id,),
                )

                # Log the deletion after cleaning up references
                history_query = """
                INSERT INTO Requisition_History (requisition_id, editor_name, reason)
                VALUES (?, ?, ?)
                """
                db.execute_update(
                    history_query, (self.id, editor_name, "Requisition deleted")
                )

                requester_name = "requester"
                requester_rows = db.execute_query(
                    "SELECT name FROM Requesters WHERE id = ?",
                    (self.requester_id,),
                )
                if requester_rows and (requester_rows[0].get("name") or "").strip():
                    requester_name = requester_rows[0]["name"].strip()

                activity_logger.log_activity(
                    activity_logger.REQUISITION_DELETED,
                    f"Deleted requisition for {requester_name}",
                    self.id,
                    "requisition",
                    editor_name,
                )

                # Finally delete the requisition
                db.execute_update("DELETE FROM Requisitions WHERE id = ?", (self.id,))
            return True
        except Exception as e:
            logger.error(f"Failed to delete requisition {self.id}: {e}")
            return False

    @classmethod
    def get_all(cls) -> List["Requisition"]:
        """Get all requisitions."""
        try:
            rows = db.execute_query(
                "SELECT * FROM Requisitions ORDER BY expected_request DESC"
            )
            requisitions = []
            for row in rows:
                req_dict = dict(row)
                # Convert dates; do not silently fall back to 'now' on parse errors
                if req_dict.get("expected_request"):
                    val = req_dict["expected_request"]
                    try:
                        req_dict["expected_request"] = datetime.fromisoformat(val)
                    except (ValueError, TypeError) as e:
                        logger.error(
                            f"Invalid expected_request format for requisition {req_dict.get('id')}: {val}"
                        )
                        raise ValueError(
                            f"Invalid expected_request format for requisition {req_dict.get('id')}: {val}"
                        ) from e
                if req_dict.get("expected_return"):
                    val = req_dict["expected_return"]
                    try:
                        req_dict["expected_return"] = datetime.fromisoformat(val)
                    except (ValueError, TypeError) as e:
                        logger.error(
                            f"Invalid expected_return format for requisition {req_dict.get('id')}: {val}"
                        )
                        raise ValueError(
                            f"Invalid expected_return format for requisition {req_dict.get('id')}: {val}"
                        ) from e
                if req_dict.get("lab_activity_date"):
                    val = req_dict["lab_activity_date"]
                    try:
                        req_dict["lab_activity_date"] = date.fromisoformat(val)
                    except (ValueError, TypeError) as e:
                        logger.error(
                            f"Invalid lab_activity_date format for requisition {req_dict.get('id')}: {val}"
                        )
                        raise ValueError(
                            f"Invalid lab_activity_date format for requisition {req_dict.get('id')}: {val}"
                        ) from e
                requisitions.append(cls(**req_dict))
            return requisitions
        except Exception as e:
            # If parsing error was raised intentionally (ValueError), re-raise it so
            # callers and tests can catch and handle it; otherwise log database
            # or unexpected errors and return an empty list as before.
            if isinstance(e, ValueError):
                raise
            logger.error(f"Failed to get requisitions: {e}")
            return []


@dataclass
class RequisitionItem:
    """Represents an item in a requisition."""

    id: Optional[int] = None
    requisition_id: int = 0
    item_id: int = 0
    quantity_requested: int = 0

    def save(self) -> bool:
        """Save or update the requisition item."""
        try:
            if self.id:
                query = """
                UPDATE Requisition_Items SET requisition_id = ?, item_id = ?, quantity_requested = ?
                WHERE id = ?
                """
                db.execute_update(
                    query,
                    (
                        self.requisition_id,
                        self.item_id,
                        self.quantity_requested,
                        self.id,
                    ),
                )
            else:
                query = "INSERT INTO Requisition_Items (requisition_id, item_id, quantity_requested) VALUES (?, ?, ?)"
                result = db.execute_update(
                    query,
                    (self.requisition_id, self.item_id, self.quantity_requested),
                    return_last_id=True,
                )
                if isinstance(result, tuple):
                    _, self.id = result
                else:
                    logger.error("Failed to obtain last insert id for RequisitionItem")
            return True
        except Exception as e:
            logger.error(f"Failed to save requisition item: {e}")
            return False

    @classmethod
    def get_by_requisition(cls, requisition_id: int) -> List["RequisitionItem"]:
        """Get all items for a requisition."""
        try:
            rows = db.execute_query(
                "SELECT * FROM Requisition_Items WHERE requisition_id = ?",
                (requisition_id,),
            )
            return [cls(**dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get requisition items for {requisition_id}: {e}")
            return []

    @classmethod
    def bulk_create(
        cls, requisition_id: int, items_data: List[dict]
    ) -> List["RequisitionItem"]:
        """Bulk create requisition items in a single transaction.

        Args:
            requisition_id: The requisition to attach items to
            items_data: List of dicts with item_id and quantity_requested

        Returns:
            List of created RequisitionItem objects
        """
        if not items_data:
            return []

        created_items = []
        query = "INSERT INTO Requisition_Items (requisition_id, item_id, quantity_requested) VALUES (?, ?, ?)"

        try:
            with db.transaction():
                ids = db.execute_many_return_ids(
                    query,
                    [
                        (requisition_id, item["item_id"], item["quantity_requested"])
                        for item in items_data
                    ],
                )

                for i, item_data in enumerate(items_data):
                    ri = cls(
                        id=ids[i] if i < len(ids) else None,
                        requisition_id=requisition_id,
                        item_id=item_data["item_id"],
                        quantity_requested=item_data["quantity_requested"],
                    )
                    created_items.append(ri)

            return created_items
        except Exception as e:
            logger.error(f"Failed to bulk create requisition items: {e}")
            return []


@dataclass
class ItemBulkCreator:
    """Bulk operations for Items - use as standalone functions, not mixed in."""

    @classmethod
    def bulk_create(
        cls, items_data: List[dict], editor_name: str = "bulk"
    ) -> List["Item"]:
        """Bulk create items with their initial batches.

        Args:
            items_data: List of dicts containing item fields and optional 'batch_quantity'
            editor_name: Name of the admin user creating items

        Returns:
            List of created Item objects
        """
        if not items_data:
            return []

        current_time = datetime.now()
        created_items = []

        try:
            with db.transaction():
                item_query = """
                INSERT INTO Items (name, category_id, item_type, size, brand, other_specifications,
                po_number, supplier_id, expiration_date, calibration_date, is_consumable,
                acquisition_date, last_modified) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                item_params = []
                for item in items_data:
                    item_params.append(
                        (
                            item.get("name"),
                            item.get("category_id"),
                            item.get("item_type"),
                            item.get("size"),
                            item.get("brand"),
                            item.get("other_specifications"),
                            item.get("po_number"),
                            item.get("supplier_id"),
                            _to_iso(item.get("expiration_date")),
                            _to_iso(item.get("calibration_date")),
                            item.get("is_consumable", 0),
                            _to_iso(item.get("acquisition_date")),
                            current_time.isoformat(),
                        )
                    )

                item_ids = db.execute_many_return_ids(item_query, item_params)

                batch_query = """
                INSERT INTO Item_Batches (item_id, batch_number, date_received, quantity_received)
                VALUES (?, ?, ?, ?)
                """
                batch_params = []
                for i, item in enumerate(items_data):
                    if item.get("batch_quantity", 0) > 0:
                        batch_params.append(
                            (
                                item_ids[i],
                                1,
                                current_time.date().isoformat(),
                                item["batch_quantity"],
                            )
                        )

                if batch_params:
                    db.execute_many(batch_query, batch_params)

                for i, item_data in enumerate(items_data):
                    item = Item(
                        id=item_ids[i],
                        name=item_data.get("name", ""),
                        category_id=item_data.get("category_id", 0),
                        item_type=item_data.get("item_type"),
                        size=item_data.get("size"),
                        brand=item_data.get("brand"),
                        other_specifications=item_data.get("other_specifications"),
                        po_number=item_data.get("po_number"),
                        supplier_id=item_data.get("supplier_id"),
                        expiration_date=item_data.get("expiration_date"),
                        calibration_date=item_data.get("calibration_date"),
                        is_consumable=item_data.get("is_consumable", 0),
                        acquisition_date=item_data.get("acquisition_date"),
                        last_modified=current_time,
                    )
                    created_items.append(item)

                for item in created_items:
                    activity_logger.log_activity(
                        activity_logger.ITEM_ADDED,
                        f"Added new item: {item.name}",
                        item.id,
                        "item",
                        editor_name,
                    )

            return created_items
        except Exception as e:
            logger.error(f"Failed to bulk create items: {e}")
            return []


@dataclass
class RequesterBulkCreator:
    """Bulk operations for Requesters."""

    @classmethod
    def bulk_create(cls, requesters_data: List[dict]) -> List["Requester"]:
        """Bulk create requesters.

        Args:
            requesters_data: List of dicts containing requester fields

        Returns:
            List of created Requester objects
        """
        if not requesters_data:
            return []

        current_time = datetime.now()
        created_requesters = []

        try:
            with db.transaction():
                query = """
                INSERT INTO Requesters (name, requester_type, grade_level, section,
                department, created_at) VALUES (?, ?, ?, ?, ?, ?)
                """
                params = []
                for req in requesters_data:
                    params.append(
                        (
                            req.get("name"),
                            req.get("requester_type", "teacher"),
                            req.get("grade_level"),
                            req.get("section"),
                            req.get("department"),
                            current_time.isoformat(),
                        )
                    )

                ids = db.execute_many_return_ids(query, params)

                for i, req_data in enumerate(requesters_data):
                    req = Requester(
                        name=req_data.get("name", ""),
                        requester_type=req_data.get("requester_type", "teacher"),
                        grade_level=req_data.get("grade_level"),
                        section=req_data.get("section"),
                        department=req_data.get("department"),
                        created_at=current_time,
                    )
                    req.id = ids[i]
                    created_requesters.append(req)

            return created_requesters
        except Exception as e:
            logger.error(f"Failed to bulk create requesters: {e}")
            return []


@dataclass
class RequisitionBulkCreator:
    """Bulk operations for Requisitions."""

    @classmethod
    def bulk_create(
        cls, requisitions_data: List[dict], editor_name: str = "bulk"
    ) -> List["Requisition"]:
        """Bulk create requisitions.

        Args:
            requisitions_data: List of dicts containing requisition fields
            editor_name: Name of the admin user

        Returns:
            List of created Requisition objects
        """
        if not requisitions_data:
            return []

        created_requisitions = []

        try:
            with db.transaction():
                query = """
                INSERT INTO Requisitions (requester_id, expected_request,
                expected_return, status, lab_activity_name, lab_activity_description, lab_activity_date,
                num_students, num_groups) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                params = []
                for req in requisitions_data:
                    params.append(
                        (
                            req.get("requester_id"),
                            _to_iso(req.get("expected_request"))
                            or datetime.now().isoformat(),
                            _to_iso(req.get("expected_return"))
                            or datetime.now().isoformat(),
                            req.get("status", "returned"),
                            req.get("lab_activity_name", ""),
                            req.get("lab_activity_description"),
                            _to_iso(req.get("lab_activity_date"))
                            or date.today().isoformat(),
                            req.get("num_students"),
                            req.get("num_groups"),
                        )
                    )

                ids = db.execute_many_return_ids(query, params)

                for i, req_data in enumerate(requisitions_data):
                    req = Requisition(
                        requester_id=req_data.get("requester_id", 0),
                        expected_request=req_data.get(
                            "expected_request", datetime.now()
                        ),
                        expected_return=req_data.get("expected_return", datetime.now()),
                        status=req_data.get("status", "returned"),
                        lab_activity_name=req_data.get("lab_activity_name", ""),
                        lab_activity_description=req_data.get(
                            "lab_activity_description"
                        ),
                        lab_activity_date=req_data.get(
                            "lab_activity_date", date.today()
                        ),
                        num_students=req_data.get("num_students"),
                        num_groups=req_data.get("num_groups"),
                    )
                    req.id = ids[i]
                    created_requisitions.append(req)

            return created_requisitions
        except Exception as e:
            logger.error(f"Failed to bulk create requisitions: {e}")
            return []


@dataclass
class RequisitionItemBulkCreator:
    """Bulk operations for RequisitionItems."""

    @classmethod
    def bulk_create(
        cls, requisition_id: int, items_data: List[dict]
    ) -> List["RequisitionItem"]:
        """Bulk create requisition items.

        Args:
            requisition_id: The requisition to attach items to
            items_data: List of dicts with item_id and quantity_requested

        Returns:
            List of created RequisitionItem objects
        """
        if not items_data:
            return []

        created_items = []
        query = "INSERT INTO Requisition_Items (requisition_id, item_id, quantity_requested) VALUES (?, ?, ?)"

        try:
            with db.transaction():
                ids = db.execute_many_return_ids(
                    query,
                    [
                        (requisition_id, item["item_id"], item["quantity_requested"])
                        for item in items_data
                    ],
                )

                for i, item_data in enumerate(items_data):
                    ri = RequisitionItem(
                        id=ids[i] if i < len(ids) else None,
                        requisition_id=requisition_id,
                        item_id=item_data["item_id"],
                        quantity_requested=item_data["quantity_requested"],
                    )
                    created_items.append(ri)

            return created_items
        except Exception as e:
            logger.error(f"Failed to bulk create requisition items: {e}")
            return []
