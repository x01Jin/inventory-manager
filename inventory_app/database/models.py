"""
Data models for the inventory application.
Provides classes for database entities with CRUD operations.
Uses composition pattern with DatabaseConnection.
"""

from typing import List, Optional
from datetime import datetime, date
from dataclasses import dataclass

from inventory_app.database.connection import db
from inventory_app.utils.logger import logger
from inventory_app.services.movement_types import MovementType
from inventory_app.utils.activity_logger import activity_logger


@dataclass
class Category:
    """Represents an item category."""

    id: Optional[int] = None
    name: str = ""

    def save(self) -> bool:
        """Save or update the category."""
        try:
            if self.id:
                query = "UPDATE Categories SET name = ? WHERE id = ?"
                db.execute_update(query, (self.name, self.id))
            else:
                query = "INSERT INTO Categories (name) VALUES (?)"
                result = db.execute_update(query, (self.name,), return_last_id=True)
                if isinstance(result, tuple):
                    _, self.id = result
                else:
                    logger.error("Failed to obtain last insert id for Category")
            return True
        except Exception as e:
            logger.error(f"Failed to save category: {e}")
            return False

    @classmethod
    def get_all(cls) -> List["Category"]:
        """Get all categories."""
        try:
            rows = db.execute_query("SELECT * FROM Categories ORDER BY name")
            return [cls(**dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get categories: {e}")
            return []

    def delete(self) -> bool:
        """Delete the category."""
        try:
            if not self.id:
                return False

            # Check if category is being used by any items
            usage_check = db.execute_query(
                "SELECT COUNT(*) as count FROM Items WHERE category_id = ?", (self.id,)
            )
            if usage_check and usage_check[0]["count"] > 0:
                logger.warning(
                    f"Cannot delete category {self.id}: category is being used by items"
                )
                return False

            db.execute_update("DELETE FROM Categories WHERE id = ?", (self.id,))
            return True
        except Exception as e:
            logger.error(f"Failed to delete category {self.id}: {e}")
            return False

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


@dataclass
class Supplier:
    """Represents a supplier."""

    id: Optional[int] = None
    name: str = ""

    def save(self) -> bool:
        """Save or update the supplier."""
        try:
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
            return True
        except Exception as e:
            logger.error(f"Failed to save supplier: {e}")
            return False

    @classmethod
    def get_all(cls) -> List["Supplier"]:
        """Get all suppliers."""
        try:
            rows = db.execute_query("SELECT * FROM Suppliers ORDER BY name")
            return [cls(**dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get suppliers: {e}")
            return []

    def delete(self) -> bool:
        """Delete the supplier."""
        try:
            if not self.id:
                return False

            # Check if supplier is being used by any items
            usage_check = db.execute_query(
                "SELECT COUNT(*) as count FROM Items WHERE supplier_id = ?", (self.id,)
            )
            if usage_check and usage_check[0]["count"] > 0:
                logger.warning(
                    f"Cannot delete supplier {self.id}: supplier is being used by items"
                )
                return False

            db.execute_update("DELETE FROM Suppliers WHERE id = ?", (self.id,))
            return True
        except Exception as e:
            logger.error(f"Failed to delete supplier {self.id}: {e}")
            return False

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

    def save(self) -> bool:
        """Save or update the size."""
        try:
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
            return True
        except Exception as e:
            logger.error(f"Failed to save size: {e}")
            return False

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

    def save(self) -> bool:
        """Save or update the brand."""
        try:
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
            return True
        except Exception as e:
            logger.error(f"Failed to save brand: {e}")
            return False

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
                        self.expiration_date.isoformat()
                        if self.expiration_date
                        else None,
                        self.calibration_date.isoformat()
                        if self.calibration_date
                        else None,
                        self.is_consumable,
                        self.acquisition_date.isoformat()
                        if self.acquisition_date
                        else None,
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
                        self.expiration_date.isoformat()
                        if self.expiration_date
                        else None,
                        self.calibration_date.isoformat()
                        if self.calibration_date
                        else None,
                        self.is_consumable,
                        self.acquisition_date.isoformat()
                        if self.acquisition_date
                        else None,
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
                    "DELETE FROM Stock_MovEMENTS WHERE item_id = ?", (self.id,)
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

                # 5. Delete disposal history (only depends on items)
                logger.info(f"Deleting Disposal_History for item {self.id}")
                db.execute_update(
                    "DELETE FROM Disposal_History WHERE item_id = ?", (self.id,)
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
    """Represents a requester."""

    id: Optional[int] = None
    name: str = ""
    affiliation: str = ""
    group_name: str = ""
    created_at: Optional[datetime] = None

    def save(self) -> bool:
        """Save or update the requester."""
        try:
            if self.id:
                query = "UPDATE Requesters SET name = ?, affiliation = ?, group_name = ? WHERE id = ?"
                db.execute_update(
                    query, (self.name, self.affiliation, self.group_name, self.id)
                )
            else:
                # For new requesters, explicitly set created_at to local time
                current_time = datetime.now()
                query = "INSERT INTO Requesters (name, affiliation, group_name, created_at) VALUES (?, ?, ?, ?)"
                result = db.execute_update(
                    query,
                    (
                        self.name,
                        self.affiliation,
                        self.group_name,
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
    expected_request: datetime = datetime.now()
    expected_return: datetime = datetime.now()
    status: str = "requested"  # 'requested', 'active', 'returned', 'overdue'
    lab_activity_name: str = ""
    lab_activity_description: Optional[str] = (
        None  # For detailed activity information stored for reports
    )
    lab_activity_date: date = date.today()
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
                # Convert dates with error handling
                if req_dict.get("expected_request"):
                    try:
                        req_dict["expected_request"] = datetime.fromisoformat(
                            req_dict["expected_request"]
                        )
                    except (ValueError, TypeError):
                        logger.warning(
                            f"Invalid expected_request format: {req_dict['expected_request']}"
                        )
                        req_dict["expected_request"] = datetime.now()
                if req_dict.get("expected_return"):
                    try:
                        req_dict["expected_return"] = datetime.fromisoformat(
                            req_dict["expected_return"]
                        )
                    except (ValueError, TypeError):
                        logger.warning(
                            f"Invalid expected_return format: {req_dict['expected_return']}"
                        )
                        req_dict["expected_return"] = datetime.now()
                if req_dict.get("lab_activity_date"):
                    try:
                        req_dict["lab_activity_date"] = date.fromisoformat(
                            req_dict["lab_activity_date"]
                        )
                    except (ValueError, TypeError):
                        logger.warning(
                            f"Invalid lab_activity_date format: {req_dict['lab_activity_date']}"
                        )
                        req_dict["lab_activity_date"] = date.today()
                requisitions.append(cls(**req_dict))
            return requisitions
        except Exception as e:
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
