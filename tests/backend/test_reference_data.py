import pytest
from inventory_app.database.connection import db
from inventory_app.database.models import Supplier, Size, Brand, Item

@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for each test and ensure schema is applied."""
    db_file = tmp_path / "test_inventory.db"
    db.db_path = db_file
    assert db.create_database() is True
    yield db_file

def test_supplier_deletion_logic(temp_db):
    """Verify supplier deletion behavior (force vs no-force)."""
    # Create supplier and item
    s = Supplier(name="Unique Test Supplier")
    s.save()
    assert s.id is not None

    item = Item(name="Test Item", category_id=1, supplier_id=s.id)
    item.save(editor_name="tester", batch_quantity=10)

    # 1. Deletion without force should fail if used
    success, msg = s.delete(force=False)
    assert success is False
    assert "being used" in msg.lower()

    # Verify supplier still exists
    assert Supplier.get_by_id(s.id) is not None

    # 2. Deletion with force should succeed and nullify item reference
    success, msg = s.delete(force=True)
    assert success is True
    
    # Verify supplier is gone
    assert Supplier.get_by_id(s.id) is None
    
    # Verify item's supplier_id is NULL
    retrieved_item = Item.get_by_id(item.id)
    assert retrieved_item.supplier_id is None

def test_size_deletion_logic(temp_db):
    """Verify size deletion is blocked when in use."""
    sz = Size(name="999ml")
    sz.save()
    assert sz.id is not None

    # Use size in item
    item = Item(name="Sized Item", category_id=1, size="999ml")
    item.save(editor_name="tester")

    # Deletion should be blocked
    success = sz.delete()
    assert success is False
    assert Size.get_by_id(sz.id) is not None

    # Unlink size from item
    item.size = None
    item.save(editor_name="tester")

    # Deletion should succeed now
    success = sz.delete()
    assert success is True
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
    success = b.delete()
    assert success is False
    assert Brand.get_by_id(b.id) is not None

    # Unlink brand
    item.brand = None
    item.save(editor_name="tester")

    # Deletion should succeed
    success = b.delete()
    assert success is True
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
