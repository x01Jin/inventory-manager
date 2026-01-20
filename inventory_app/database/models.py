"""
Data models for the inventory application.
Provides classes for database entities with CRUD operations.
Uses composition pattern with DatabaseConnection.
"""

from typing import List, Optional, Tuple
from datetime import datetime, date, timezone
from dataclasses import dataclass, field

from inventory_app.database.connection import db
from inventory_app.utils.logger import logger
from inventory_app.utils.activity_logger import activity_logger


def _to_iso(value: Optional[date | datetime]) -> Optional[str]:
    """Return ISO string for date/datetime or None if value is None."""
    if value is None:
        return None
    return value.isoformat()


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
        if exclude_id:
            query = f"SELECT name FROM {table} WHERE LOWER(name) = LOWER(?) AND id != ?"
            rows = db.execute_query(query, (name, exclude_id))
        else:
            query = f"SELECT name FROM {table} WHERE LOWER(name) = LOWER(?)"
            rows = db.execute_query(query, (name,))

        if rows:
            return True, rows[0]["name"]
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

    def delete(self, force: bool = False) -> Tuple[bool, str]:
        """Delete the supplier.

        Per beta test requirement #18: Suppliers can be deleted from dropdown.
        When force=True, nullifies the supplier_id on any items using this supplier.

        Args:
            force: If True, remove supplier references from items before deletion

        Returns:
            Tuple of (success, message)
        """
        try:
            if not self.id:
                return False, "Supplier has no ID"

            # Check if supplier is being used by any items
            usage_check = db.execute_query(
                "SELECT COUNT(*) as count FROM Items WHERE supplier_id = ?", (self.id,)
            )
            items_using = usage_check[0]["count"] if usage_check else 0

            if items_using > 0:
                if not force:
                    return (
                        False,
                        f"Supplier is being used by {items_using} item(s). "
                        "Would you like to remove this supplier from those items and delete it?",
                    )

                # Force deletion: nullify supplier_id on items first
                db.execute_update(
                    "UPDATE Items SET supplier_id = NULL WHERE supplier_id = ?",
                    (self.id,),
                )
                logger.info(
                    f"Nullified supplier_id on {items_using} items before deleting supplier {self.id}"
                )

            db.execute_update("DELETE FROM Suppliers WHERE id = ?", (self.id,))
            return True, "Supplier deleted successfully"
        except Exception as e:
            logger.error(f"Failed to delete supplier {self.id}: {e}")
            return False, str(e)

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

    def delete(self) -> bool:
        """Delete the size."""
        try:
            if not self.id:
                return False

            # Check if size is being used by any items
            usage_check = db.execute_query(
                "SELECT COUNT(*) as count FROM Items WHERE size = ?", (self.name,)
            )
            if usage_check and usage_check[0]["count"] > 0:
                logger.warning(
                    f"Cannot delete size {self.id}: size is being used by items"
                )
                return False

            db.execute_update("DELETE FROM Sizes WHERE id = ?", (self.id,))
            return True
        except Exception as e:
            logger.error(f"Failed to delete size {self.id}: {e}")
            return False

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

    def delete(self) -> bool:
        """Delete the brand."""
        try:
            if not self.id:
                return False

            # Check if brand is being used by any items
            usage_check = db.execute_query(
                "SELECT COUNT(*) as count FROM Items WHERE brand = ?", (self.name,)
            )
            if usage_check and usage_check[0]["count"] > 0:
                logger.warning(
                    f"Cannot delete brand {self.id}: brand is being used by items"
                )
                return False

            db.execute_update("DELETE FROM Brands WHERE id = ?", (self.id,))
            return True
        except Exception as e:
            logger.error(f"Failed to delete brand {self.id}: {e}")
            return False

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

    def save(self, editor_name: str, batch_quantity: int = 0) -> bool:
        """Save or update the item with history tracking and batch creation."""
        try:
            current_time = datetime.now()
            # Wrap the entire save operation in a single transaction so that
            # creating the item and its initial batch (if any) are committed
            # atomically.
            with db.transaction():
                if self.id:
                    # Update existing - log to history first
                    history_query = """
                    INSERT INTO Update_History (item_id, editor_name, reason)
                    VALUES (?, ?, ?)
                    """
                    db.execute_update(
                        history_query, (self.id, editor_name, "Item updated")
                    )

                    # Update item
                    query = """
                    UPDATE Items SET name = ?, category_id = ?, size = ?, brand = ?,
                    other_specifications = ?, po_number = ?, supplier_id = ?,
                    expiration_date = ?, calibration_date = ?, is_consumable = ?,
                    acquisition_date = ?, last_modified = ? WHERE id = ?
                    """
                    params = (
                        self.name,
                        self.category_id,
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
                    INSERT INTO Items (name, category_id, size, brand, other_specifications,
                    po_number, supplier_id, expiration_date, calibration_date, is_consumable,
                    acquisition_date, last_modified) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    params = (
                        self.name,
                        self.category_id,
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
            current_time = datetime.now().date().isoformat()

            # Create ONE batch with the total quantity
            query = """
            INSERT INTO Item_Batches (item_id, batch_number, date_received, quantity_received)
            VALUES (?, ?, ?, ?)
            """
            result = db.execute_update(query, (self.id, 1, current_time, quantity))
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
class Requester:
    """Represents a requester.

    Attributes:
        grade_level: The grade level of the requester (e.g., 'Grade 7', 'Grade 8')
                     Used for tracking usage by grade level per beta test requirements.
        section: The section name (e.g., 'Section A', 'Einstein')
                 Used for tracking usage by section per beta test requirements.
    """

    id: Optional[int] = None
    name: str = ""
    affiliation: str = ""
    group_name: str = ""
    grade_level: Optional[str] = None
    section: Optional[str] = None
    created_at: Optional[datetime] = None

    def save(self) -> bool:
        """Save or update the requester."""
        try:
            if self.id:
                query = """UPDATE Requesters SET name = ?, affiliation = ?, group_name = ?,
                           grade_level = ?, section = ? WHERE id = ?"""
                db.execute_update(
                    query,
                    (
                        self.name,
                        self.affiliation,
                        self.group_name,
                        self.grade_level,
                        self.section,
                        self.id,
                    ),
                )
            else:
                # For new requesters, explicitly set created_at to local time
                current_time = datetime.now()
                query = """INSERT INTO Requesters (name, affiliation, group_name,
                           grade_level, section, created_at) VALUES (?, ?, ?, ?, ?, ?)"""
                result = db.execute_update(
                    query,
                    (
                        self.name,
                        self.affiliation,
                        self.group_name,
                        self.grade_level,
                        self.section,
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

    def delete(self) -> bool:
        """Delete the requester."""
        try:
            if not self.id:
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

    def save(self, editor_name: str) -> bool:
        """Save or update the requisition with history tracking."""
        try:
            if self.id:
                # Log to history
                history_query = """
                INSERT INTO Requisition_History (requisition_id, editor_name, reason)
                VALUES (?, ?, ?)
                """
                db.execute_update(
                    history_query, (self.id, editor_name, "Requisition updated")
                )

                # Update requisition
                query = """
                UPDATE Requisitions SET requester_id = ?,
                expected_request = ?, expected_return = ?, status = ?,
                lab_activity_name = ?, lab_activity_description = ?, lab_activity_date = ?,
                num_students = ?, num_groups = ? WHERE id = ?
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
                        self.id,
                    ),
                )
            else:
                # Insert new
                query = """
                INSERT INTO Requisitions (requester_id, expected_request,
                expected_return, status, lab_activity_name, lab_activity_description, lab_activity_date,
                num_students, num_groups) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    ),
                    return_last_id=True,
                )
                if isinstance(result, tuple):
                    _, self.id = result
                else:
                    logger.error("Failed to obtain last insert id for Requisition")

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
                INSERT INTO Items (name, category_id, size, brand, other_specifications,
                po_number, supplier_id, expiration_date, calibration_date, is_consumable,
                acquisition_date, last_modified) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                item_params = []
                for item in items_data:
                    item_params.append(
                        (
                            item.get("name"),
                            item.get("category_id"),
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
                INSERT INTO Requesters (name, affiliation, group_name,
                grade_level, section, created_at) VALUES (?, ?, ?, ?, ?, ?)
                """
                params = []
                for req in requesters_data:
                    params.append(
                        (
                            req.get("name"),
                            req.get("affiliation"),
                            req.get("group_name"),
                            req.get("grade_level"),
                            req.get("section"),
                            current_time.isoformat(),
                        )
                    )

                ids = db.execute_many_return_ids(query, params)

                for i, req_data in enumerate(requesters_data):
                    req = Requester(
                        name=req_data.get("name", ""),
                        affiliation=req_data.get("affiliation", ""),
                        group_name=req_data.get("group_name", ""),
                        grade_level=req_data.get("grade_level"),
                        section=req_data.get("section"),
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
