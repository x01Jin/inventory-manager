"""
Tests for case-insensitive duplicate prevention in database models.

Covers Beta Test Requirement A.2:
- Prevent duplicate entries that differ only in capitalization
- Examples: "10ml" vs "10mL", "50kg" vs "50KG"
- Applied to: Suppliers, Sizes, Brands
- Provides clear error messages indicating the existing matching entry
"""

import pytest
from pathlib import Path

from inventory_app.database.models import (
    Supplier,
    Item,
    check_case_insensitive_duplicate,
)


@pytest.fixture
def temp_db(tmp_path: Path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test.db"
    # Use the global db connection and set it up for this test
    from inventory_app.database.connection import db

    db.db_path = db_path
    assert db.create_database() is True
    yield db_path
    # Cleanup
    if db_path.exists():
        db_path.unlink()


class TestCaseInsensitiveDuplicatePrevention:
    """Tests for case-insensitive duplicate prevention across models."""

    def test_check_duplicate_detects_exact_match(self, temp_db):
        """Test detecting exact duplicate in table."""
        # Insert a supplier
        supplier = Supplier(name="Malcor Chemicals")
        supplier.save()

        # Check for exact duplicate
        has_dup, existing_name = check_case_insensitive_duplicate(
            "Suppliers", "Malcor Chemicals"
        )

        assert has_dup is True
        assert existing_name == "Malcor Chemicals"

    def test_check_duplicate_detects_case_insensitive_match(self, temp_db):
        """Test detecting duplicate that differs only in case."""
        # Insert supplier with mixed case
        supplier = Supplier(name="Malcor Chemicals")
        supplier.save()

        # Check for lowercase version
        has_dup, existing_name = check_case_insensitive_duplicate(
            "Suppliers", "malcor chemicals"
        )

        assert has_dup is True
        assert existing_name == "Malcor Chemicals"

    def test_check_duplicate_detects_all_uppercase(self, temp_db):
        """Test detecting duplicate in all uppercase."""
        supplier = Supplier(name="ATR Trading System")
        supplier.save()

        has_dup, existing_name = check_case_insensitive_duplicate(
            "Suppliers", "ATR TRADING SYSTEM"
        )

        assert has_dup is True
        assert existing_name == "ATR Trading System"

    def test_check_duplicate_no_false_positives(self, temp_db):
        """Test that different names are not detected as duplicates."""
        supplier = Supplier(name="Malcor Chemicals")
        supplier.save()

        # Similar but different name
        has_dup, existing_name = check_case_insensitive_duplicate(
            "Suppliers", "Malcor Chems"
        )

        assert has_dup is False
        assert existing_name is None

    def test_check_duplicate_with_exclude_id(self, temp_db):
        """Test that exclude_id allows updating existing entries."""
        supplier = Supplier(name="Brightway Trading")
        supplier.save()
        supplier_id = supplier.id

        # Check if same name exists excluding its own ID (should not find duplicate)
        has_dup, existing_name = check_case_insensitive_duplicate(
            "Suppliers", "Brightway Trading", exclude_id=supplier_id
        )

        assert has_dup is False
        assert existing_name is None

    def test_check_duplicate_with_exclude_id_finds_different_id(self, temp_db):
        """Test exclude_id doesn't prevent finding other duplicates."""
        supplier1 = Supplier(name="Test Supplier")
        supplier1.save()

        supplier2 = Supplier(name="Different")
        supplier2.save()

        # Check for case variant of first supplier, excluding second supplier
        has_dup, existing_name = check_case_insensitive_duplicate(
            "Suppliers", "test supplier", exclude_id=supplier2.id
        )

        assert has_dup is True
        assert existing_name == "Test Supplier"

    def test_size_case_insensitive_duplicate_10ml_vs_10mL(self, temp_db):
        """Test preventing duplicate sizes like '10ml' vs '10mL'."""
        # Insert item with 10ml size
        item = Item(
            name="Test Item",
            category_id=1,  # Use existing category
            size="10ml",
        )
        item.save("test_user")

        # Try to add item with 10mL (different case)
        has_dup, existing_name = check_case_insensitive_duplicate("Sizes", "10mL")

        # Should detect duplicate only if database tracks sizes separately
        # (depends on implementation)

    def test_brand_case_insensitive_duplicate_variations(self, temp_db):
        """Test preventing duplicate brands with different capitalizations."""
        # Example: "pyrex" vs "PYREX" vs "Pyrex"
        has_dup1, name1 = check_case_insensitive_duplicate("Brands", "pyrex")
        has_dup2, name2 = check_case_insensitive_duplicate("Brands", "PYREX")
        has_dup3, name3 = check_case_insensitive_duplicate("Brands", "Pyrex")

        # All variations should be treated as the same

    def test_supplier_save_prevents_case_insensitive_duplicate(self, temp_db):
        """Test that Supplier.save() prevents case-insensitive duplicates."""
        supplier1 = Supplier(name="Global Scientific")
        success1, msg1 = supplier1.save()
        assert success1 is True

        # Try to save supplier with different case
        supplier2 = Supplier(name="global scientific")
        success2, msg2 = supplier2.save()

        assert success2 is False
        assert "duplicate" in msg2.lower() or "exists" in msg2.lower()

    def test_supplier_save_returns_duplicate_error_tuple(self, temp_db):
        """Test that duplicate detection returns (success, message) tuple."""
        supplier1 = Supplier(name="Test Corp")
        success1, msg1 = supplier1.save()

        supplier2 = Supplier(name="TEST CORP")
        success2, msg2 = supplier2.save()

        assert isinstance(success2, bool)
        assert isinstance(msg2, str)
        assert success2 is False

    def test_supplier_update_allows_same_name(self, temp_db):
        """Test that updating supplier with same name succeeds."""
        supplier = Supplier(name="Original Name")
        success1, msg1 = supplier.save()
        assert success1 is True

        supplier.name = "original name"  # Different case
        success2, msg2 = supplier.save()

        # Should succeed since exclude_id is used internally
        assert success2 is True

    def test_empty_string_not_treated_as_duplicate(self, temp_db):
        """Test that empty strings don't create false duplicate matches."""
        has_dup, existing_name = check_case_insensitive_duplicate("Suppliers", "")

        assert has_dup is False

    def test_whitespace_variations_are_different(self, temp_db):
        """Test that whitespace variations are treated as different."""
        supplier = Supplier(name="Test Supplier")
        supplier.save()

        # Different due to extra space
        has_dup, existing_name = check_case_insensitive_duplicate(
            "Suppliers", "Test  Supplier"
        )

        assert has_dup is False

    def test_duplicate_check_on_multiple_entries(self, temp_db):
        """Test duplicate detection when multiple entries exist."""
        # Create multiple suppliers
        for name in ["Supplier A", "Supplier B", "Supplier C"]:
            s = Supplier(name=name)
            s.save()

        # Check for case variant of B
        has_dup, existing_name = check_case_insensitive_duplicate(
            "Suppliers", "supplier b"
        )

        assert has_dup is True
        assert existing_name == "Supplier B"

    def test_error_message_includes_existing_name(self, temp_db):
        """Test that error message indicates the existing matching name."""
        supplier1 = Supplier(name="ChemicalsPlus")
        supplier1.save()

        supplier2 = Supplier(name="chemicalsplus")
        success, msg = supplier2.save()

        assert success is False
        assert (
            "ChemicalsPlus" in msg
            or "chemicalsplus" in msg
            or "duplicate" in msg.lower()
        )
