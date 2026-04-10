import pytest
from inventory_app.database.connection import db
from inventory_app.database.models import Supplier, Size, Brand, Item
from inventory_app.services.reference_merge_service import merge_suppliers, merge_brands


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for each test and ensure schema is applied."""
    db_file = tmp_path / "test_inventory.db"
    db.db_path = db_file
    assert db.create_database() is True
    yield db_file


def test_supplier_deletion_logic(temp_db):
    """Verify supplier deletion is blocked while in use and allowed when unused."""
    # Create supplier and item
    s = Supplier(name="Unique Test Supplier")
    s.save()
    assert s.id is not None

    item = Item(name="Test Item", category_id=1, supplier_id=s.id)
    item.save(editor_name="tester", batch_quantity=10)

    # 1. Deletion should fail if used
    success, msg, usage_count = s.delete()
    assert success is False
    assert "currently used" in msg.lower()
    assert usage_count == 1

    # Verify supplier still exists
    assert Supplier.get_by_id(s.id) is not None

    # 2. Unlink supplier, then deletion should succeed
    item.supplier_id = None
    item.save(editor_name="tester")

    success, msg, usage_count = s.delete()
    assert success is True
    assert usage_count == 0

    # Verify supplier is gone
    assert Supplier.get_by_id(s.id) is None


def test_size_deletion_logic(temp_db):
    """Verify size deletion is blocked when in use."""
    sz = Size(name="999ml")
    sz.save()
    assert sz.id is not None

    # Use size in item
    item = Item(name="Sized Item", category_id=1, size="999ml")
    item.save(editor_name="tester")

    # Deletion should be blocked
    success, msg, usage_count = sz.delete()
    assert success is False
    assert usage_count == 1
    assert "currently used" in msg.lower()
    assert Size.get_by_id(sz.id) is not None

    # Unlink size from item
    item.size = None
    item.save(editor_name="tester")

    # Deletion should succeed now
    success, msg, usage_count = sz.delete()
    assert success is True
    assert usage_count == 0
    assert Size.get_by_id(sz.id) is None


def test_brand_deletion_logic(temp_db):
    """Verify brand deletion is blocked when in use."""
    b = Brand(name="UniqueBrand")
    b.save()
    assert b.id is not None

    # Use brand in item
    item = Item(name="Branded Item", category_id=1, brand="UniqueBrand")
    item.save(editor_name="tester")

    # Deletion should be blocked
    success, msg, usage_count = b.delete()
    assert success is False
    assert usage_count == 1
    assert "currently used" in msg.lower()
    assert Brand.get_by_id(b.id) is not None

    # Unlink brand
    item.brand = None
    item.save(editor_name="tester")

    # Deletion should succeed
    success, msg, usage_count = b.delete()
    assert success is True
    assert usage_count == 0
    assert Brand.get_by_id(b.id) is None


def test_reference_data_duplicate_prevention(temp_db):
    """Verify case-insensitive duplicate prevention for all reference data."""
    # Sizes
    Size(name="10L").save()
    success, msg = Size(name="10l").save()
    assert success is False
    assert "already exists" in msg.lower()

    # Brands
    Brand(name="Pyrex").save()
    success, msg = Brand(name="PYREX").save()
    assert success is False
    assert "already exists" in msg.lower()


def test_item_save_rejects_invalid_category_fk(temp_db):
    """Item save should fail fast when category FK is invalid/missing."""
    item_missing = Item(name="NoCategory", category_id=0)
    assert item_missing.save(editor_name="tester") is False

    item_unknown = Item(name="UnknownCategory", category_id=999999)
    assert item_unknown.save(editor_name="tester") is False


def test_item_save_supplier_fk_validation_and_blank_normalization(temp_db):
    """Blank supplier values should normalize to None; unknown supplier FK should fail."""
    blank_supplier_item = Item(name="BlankSupplier", category_id=1)
    blank_supplier_item.supplier_id = ""  # type: ignore[assignment]
    assert blank_supplier_item.save(editor_name="tester") is True

    assert blank_supplier_item.id is not None
    reloaded = Item.get_by_id(blank_supplier_item.id)
    assert reloaded is not None
    assert reloaded.supplier_id is None

    unknown_supplier_item = Item(
        name="UnknownSupplier", category_id=1, supplier_id=999999
    )
    assert unknown_supplier_item.save(editor_name="tester") is False


def test_merge_suppliers_reassigns_items_and_logs_activity(temp_db):
    """Supplier merge should move item FK references and remove source records."""
    target = Supplier(name="Task8 Supplier Main")
    source = Supplier(name="Task8 Supplier Duplicate")
    assert target.save()[0] is True
    assert source.save()[0] is True
    assert target.id is not None
    assert source.id is not None

    item = Item(name="Hydrochloric Acid", category_id=1, supplier_id=source.id)
    assert item.save(editor_name="tester") is True

    success, message, updated = merge_suppliers(
        target.id, [source.id], editor_name="Jin"
    )
    assert success is True
    assert "updated 1 item" in message.lower()
    assert updated == 1

    refreshed = Item.get_by_id(item.id or 0)
    assert refreshed is not None
    assert refreshed.supplier_id == target.id
    assert Supplier.get_by_id(source.id) is None

    activity_rows = db.execute_query(
        """
        SELECT activity_type, entity_type, user_name, description
        FROM Activity_Log
        WHERE activity_type = 'REFERENCE_MERGED'
        ORDER BY id DESC
        LIMIT 1
        """
    )
    assert len(activity_rows) == 1
    assert activity_rows[0]["entity_type"] == "supplier"
    assert activity_rows[0]["user_name"] == "Jin"
    assert "task8 supplier duplicate" in activity_rows[0]["description"].lower()


def test_merge_brands_updates_item_text_and_logs_activity(temp_db):
    """Brand merge should rewrite item text values case-insensitively."""
    target = Brand(name="Pyrex")
    source = Brand(name="PYREX-Legacy")
    assert target.save()[0] is True
    assert source.save()[0] is True
    assert target.id is not None
    assert source.id is not None

    item = Item(name="Beaker", category_id=1, brand="pyrex-legacy")
    assert item.save(editor_name="tester") is True

    success, message, updated = merge_brands(target.id, [source.id], editor_name="Jin")
    assert success is True
    assert "updated 1 item" in message.lower()
    assert updated == 1

    refreshed = Item.get_by_id(item.id or 0)
    assert refreshed is not None
    assert refreshed.brand == "Pyrex"
    assert Brand.get_by_id(source.id) is None

    activity_rows = db.execute_query(
        """
        SELECT activity_type, entity_type, user_name, description
        FROM Activity_Log
        WHERE activity_type = 'REFERENCE_MERGED'
        ORDER BY id DESC
        LIMIT 1
        """
    )
    assert len(activity_rows) == 1
    assert activity_rows[0]["entity_type"] == "brand"
    assert activity_rows[0]["user_name"] == "Jin"
    assert "pyrex-legacy" in activity_rows[0]["description"].lower()
