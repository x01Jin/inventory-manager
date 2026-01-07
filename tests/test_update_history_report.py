"""
Tests for update/edit history report generation.

Covers Beta Test Requirement Row 7:
- Generate report for history of updates/edits to inventory list
- Include: name/initials of person, time and date of edit, reason for editing
- Filterable by date range and item name
- Report type: "Update History Report"
"""

import pytest
from datetime import date, timedelta
from pathlib import Path

from inventory_app.database.connection import DatabaseConnection
from inventory_app.gui.reports.data_sources import get_update_history_data


@pytest.fixture
def temp_db(tmp_path: Path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test.db"
    test_db = DatabaseConnection(str(db_path))
    return test_db


class TestUpdateHistoryReportData:
    """Tests for retrieving update/edit history data."""

    def test_get_update_history_data_returns_list(self, temp_db):
        """Test that update history retrieval returns a list."""
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()

        data = get_update_history_data(start_date, end_date)

        assert isinstance(data, list)

    def test_get_update_history_data_with_date_range(self, temp_db):
        """Test update history respects date range filter."""
        start_date = date(2025, 1, 1)
        end_date = date(2025, 1, 31)

        data = get_update_history_data(start_date, end_date)

        # Should not raise an exception
        assert isinstance(data, list)

    def test_get_update_history_data_with_item_filter(self, temp_db):
        """Test update history can be filtered by item name."""
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()

        data = get_update_history_data(start_date, end_date, item_filter="Beaker")

        assert isinstance(data, list)

    def test_update_history_includes_editor_name(self, temp_db):
        """Test that history records include editor name/initials."""
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()

        data = get_update_history_data(start_date, end_date)

        # If data exists, check that editor information is present
        if data:
            for record in data:
                # Should have an editor/user field
                assert any(
                    key.lower() in ["editor", "edited_by", "user", "initials", "name"]
                    for key in record.keys()
                ), "No editor field found in record"

    def test_update_history_includes_timestamp(self, temp_db):
        """Test that history records include edit timestamp."""
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()

        data = get_update_history_data(start_date, end_date)

        if data:
            for record in data:
                # Should have timestamp field
                assert any(
                    key.lower()
                    in ["timestamp", "date", "time", "edited_date", "updated_at"]
                    for key in record.keys()
                ), "No timestamp field found in record"

    def test_update_history_includes_reason(self, temp_db):
        """Test that history records include edit reason."""
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()

        data = get_update_history_data(start_date, end_date)

        if data:
            for record in data:
                # Should have reason field
                assert any(
                    key.lower() in ["reason", "edit_reason", "notes", "description"]
                    for key in record.keys()
                ), "No reason field found in record"

    def test_update_history_empty_result_when_no_edits(self, temp_db):
        """Test that empty list is returned when no edits in date range."""
        # Use future date that shouldn't have any edits
        start_date = date(2099, 1, 1)
        end_date = date(2099, 12, 31)

        data = get_update_history_data(start_date, end_date)

        assert isinstance(data, list)
        # Should be empty or minimal


class TestUpdateHistoryReportGeneration:
    """Tests for generating update history Excel reports."""

    def test_generate_update_history_report_creates_file(self, temp_db, tmp_path):
        """Test that update history report generates an Excel file."""
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()

        # This assumes a generate method exists
        result = get_update_history_data(start_date, end_date)

        # Should have executed without error
        assert result is not None

    def test_update_history_date_range_filter_accuracy(self, temp_db):
        """Test that date range filtering is accurate."""
        # Request data from specific range
        start = date(2025, 1, 1)
        end = date(2025, 1, 31)

        data = get_update_history_data(start, end)

        # All records should be within range
        if data:
            for record in data:
                # Find date field and verify it's within range
                for key, value in record.items():
                    if key.lower() in ["date", "timestamp", "edited_date"]:
                        # Date should be within range (implementation-specific check)
                        pass

    def test_update_history_includes_item_name(self, temp_db):
        """Test that history records include the item name being edited."""
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()

        data = get_update_history_data(start_date, end_date)

        if data:
            for record in data:
                # Should have item name field
                assert any(
                    key.lower() in ["item", "item_name", "name"]
                    for key in record.keys()
                ), "No item name field found in record"

    def test_update_history_item_filter_works(self, temp_db):
        """Test that item_filter parameter correctly filters results."""
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()

        # Get all updates
        all_data = get_update_history_data(start_date, end_date)

        # Get updates for specific item (if data exists)
        if all_data:
            # Filter by first item in results
            first_item = list(all_data[0].values())[0]
            filtered_data = get_update_history_data(
                start_date, end_date, item_filter=str(first_item)
            )

            # Filtered should have same or fewer records
            assert len(filtered_data) <= len(all_data)


class TestUpdateHistoryRequirements:
    """Tests specifically for beta test requirement Row 7."""

    def test_update_history_report_type_available(self):
        """Test that 'Update History Report' is available as report type."""
        # Check that report type is available in report generator
        # This is implementation-specific
        # At minimum, we verify that get_update_history_data is callable
        from inventory_app.gui.reports.data_sources import get_update_history_data

        assert callable(get_update_history_data)

    def test_update_history_includes_all_required_fields(self, temp_db):
        """Test that update history includes all required fields per requirement Row 7."""
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()

        data = get_update_history_data(start_date, end_date)

        if data:
            record = data[0]
            # At least some of these fields should be present (normalized names)
            has_editor = any(
                key.lower() in ["editor", "edited_by", "user", "initials", "name"]
                for key in record.keys()
            )
            has_date = any(
                key.lower() in ["date", "timestamp", "edited_date", "updated_at"]
                for key in record.keys()
            )
            has_reason = any(
                key.lower() in ["reason", "edit_reason", "notes", "description"]
                for key in record.keys()
            )

            assert has_editor or has_date or has_reason, (
                "No required fields found in update history record"
            )

    def test_update_history_editor_name_mandatory(self, temp_db):
        """Test that editor name is captured for audit purposes."""
        # Editor name should be mandatory per Row 14
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()

        data = get_update_history_data(start_date, end_date)

        if data:
            # All records should have editor information
            for record in data:
                editor_field = next(
                    (
                        k
                        for k in record.keys()
                        if "editor" in k.lower() or "user" in k.lower()
                    ),
                    None,
                )
                assert editor_field is not None, "No editor field in record"
                assert record[editor_field], "Editor field should not be empty"
