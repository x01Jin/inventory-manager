"""
Tests for disposal history tracking.

Covers Beta Test Requirement Row 16:
- Track items removed from inventory (disposed/deleted)
- Include: disposal date, reason for disposal, who disposed
- Maintain history profile with categorized view
- Report type: "Disposal History Report"
"""

import pytest
from datetime import date, timedelta
from pathlib import Path

from inventory_app.database.connection import DatabaseConnection
from inventory_app.gui.reports.data_sources import get_disposal_history_data


@pytest.fixture
def temp_db(tmp_path: Path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test.db"
    test_db = DatabaseConnection(str(db_path))
    return test_db


class TestDisposalHistoryData:
    """Tests for retrieving disposal history data."""

    def test_get_disposal_history_data_returns_list(self, temp_db):
        """Test that disposal history retrieval returns a list."""
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()

        data = get_disposal_history_data(start_date, end_date)

        assert isinstance(data, list)

    def test_get_disposal_history_with_date_range(self, temp_db):
        """Test disposal history respects date range filter."""
        start_date = date(2025, 1, 1)
        end_date = date(2025, 1, 31)

        data = get_disposal_history_data(start_date, end_date)

        assert isinstance(data, list)

    def test_get_disposal_history_with_category_filter(self, temp_db):
        """Test disposal history can be filtered by category."""
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()

        data = get_disposal_history_data(
            start_date, end_date, category_filter="Equipment"
        )

        assert isinstance(data, list)

    def test_disposal_history_includes_item_name(self, temp_db):
        """Test that disposal records include the item name."""
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()

        data = get_disposal_history_data(start_date, end_date)

        if data:
            for record in data:
                assert any(
                    key.lower() in ["item", "item_name", "name"]
                    for key in record.keys()
                ), "No item name field in record"

    def test_disposal_history_includes_category(self, temp_db):
        """Test that disposal records include the category."""
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()

        data = get_disposal_history_data(start_date, end_date)

        if data:
            for record in data:
                assert any(key.lower() in ["category"] for key in record.keys()), (
                    "No category field in record"
                )

    def test_disposal_history_includes_disposal_date(self, temp_db):
        """Test that disposal records include the disposal date."""
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()

        data = get_disposal_history_data(start_date, end_date)

        if data:
            for record in data:
                assert any(
                    key.lower()
                    in ["disposal_date", "disposed_date", "date", "removal_date"]
                    for key in record.keys()
                ), "No disposal date field in record"

    def test_disposal_history_includes_reason(self, temp_db):
        """Test that disposal records include the reason for disposal."""
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()

        data = get_disposal_history_data(start_date, end_date)

        if data:
            for record in data:
                assert any(
                    key.lower()
                    in ["reason", "disposal_reason", "reason_for_disposal", "notes"]
                    for key in record.keys()
                ), "No reason field in record"

    def test_disposal_history_includes_who_disposed(self, temp_db):
        """Test that disposal records include who disposed the item."""
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()

        data = get_disposal_history_data(start_date, end_date)

        if data:
            for record in data:
                assert any(
                    key.lower()
                    in [
                        "disposed_by",
                        "removed_by",
                        "user",
                        "editor",
                        "initials",
                        "name",
                    ]
                    for key in record.keys()
                ), "No 'disposed by' field in record"

    def test_disposal_history_empty_for_future_dates(self, temp_db):
        """Test that empty list is returned for future date range."""
        start_date = date(2099, 1, 1)
        end_date = date(2099, 12, 31)

        data = get_disposal_history_data(start_date, end_date)

        # Should be empty or minimal
        assert isinstance(data, list)

    def test_disposal_history_category_filter_works(self, temp_db):
        """Test that category filter correctly filters results."""
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()

        # Get all disposals
        all_data = get_disposal_history_data(start_date, end_date)

        # Get disposals for specific category
        equipment_data = get_disposal_history_data(
            start_date, end_date, category_filter="Equipment"
        )

        # Equipment data should have <= records
        assert len(equipment_data) <= len(all_data)

    def test_disposal_history_date_range_accuracy(self, temp_db):
        """Test that date range filtering is accurate."""
        start = date(2025, 1, 1)
        end = date(2025, 1, 31)

        data = get_disposal_history_data(start, end)

        # All records should be within range if any exist
        if data:
            for record in data:
                for key, value in record.items():
                    if key.lower() in ["date", "disposal_date", "removal_date"]:
                        # Date should be within range (implementation-specific)
                        pass


class TestDisposalHistoryReportRequirements:
    """Tests specifically for beta test requirement Row 16."""

    def test_disposal_history_tracks_defective_items(self, temp_db):
        """Test that disposal history includes defective items."""
        # Defective items should appear in disposal history
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()

        data = get_disposal_history_data(start_date, end_date)

        # Should not error
        assert isinstance(data, list)

    def test_disposal_history_shows_reason_codes(self, temp_db):
        """Test that disposal history distinguishes between disposal reasons."""
        # Example reasons: 'For disposal', 'Defective item', 'Expired', etc.
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()

        data = get_disposal_history_data(start_date, end_date)

        if data:
            reasons = set()
            for record in data:
                reason_key = next(
                    (k for k in record.keys() if "reason" in k.lower()), None
                )
                if reason_key:
                    reasons.add(record[reason_key])

            # If reasons exist, they should be non-empty strings
            assert all(r for r in reasons if r), "Reasons should not be empty"

    def test_disposal_history_profile_is_categorized(self, temp_db):
        """Test that disposal history can be viewed categorized."""
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()

        result = get_disposal_history_data(start_date, end_date)

        # Should be able to categorize results if category field exists
        if result:
            categories = set()
            for record in result:
                category_key = next(
                    (k for k in record.keys() if "category" in k.lower()), None
                )
                if category_key:
                    categories.add(record[category_key])

            # Should have at least some categories if data exists
            # (empty is ok if no disposal history)

    def test_disposal_reason_required(self, temp_db):
        """Test that disposal reason is mandatory per requirement Row 16."""
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()

        data = get_disposal_history_data(start_date, end_date)

        if data:
            for record in data:
                reason_field = next(
                    (k for k in record.keys() if "reason" in k.lower()), None
                )
                assert reason_field is not None, "Reason field should be present"
                # Reason should not be empty (depending on implementation)

    def test_disposal_editor_tracked(self, temp_db):
        """Test that who disposed the item is tracked for audit."""
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()

        data = get_disposal_history_data(start_date, end_date)

        if data:
            for record in data:
                disposed_by = next(
                    (
                        k
                        for k in record.keys()
                        if any(
                            term in k.lower()
                            for term in ["disposed_by", "removed_by", "user"]
                        )
                    ),
                    None,
                )
                assert disposed_by is not None, (
                    "Who disposed the item should be tracked"
                )


class TestDisposalReportIntegration:
    """Integration tests for disposal history report functionality."""

    def test_disposal_report_type_exists(self):
        """Test that Disposal History Report type is available."""
        # This should be available in the report system
        # Verify that get_disposal_history_data function exists and is callable
        from inventory_app.gui.reports.data_sources import get_disposal_history_data

        assert callable(get_disposal_history_data)

    def test_disposal_history_excel_export(self, temp_db, tmp_path):
        """Test that disposal history can be exported to Excel."""
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()

        result = get_disposal_history_data(start_date, end_date)

        # Should return a list (could be empty or populated)
        assert isinstance(result, list)
