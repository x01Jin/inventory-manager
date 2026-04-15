import pytest
from datetime import datetime
from inventory_app.database.connection import db
from inventory_app.database.models import Requester


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for each test and ensure schema is applied."""
    db_file = tmp_path / "test_inventory.db"
    db.db_path = db_file
    assert db.create_database() is True
    yield db_file


def test_requester_crud(temp_db):
    """Verify CRUD operations for Requesters."""
    # Create
    req = Requester(
        name="John Doe", requester_type="student", grade_level="12", section="A"
    )
    assert req.save(editor_name="tester") is True
    assert req.id is not None

    # Read
    retrieved = Requester.get_by_id(req.id)
    assert retrieved.name == "John Doe"
    assert retrieved.requester_type == "student"

    # Update
    retrieved.name = "Jane Doe"
    assert retrieved.save(editor_name="tester") is True

    updated = Requester.get_by_id(req.id)
    assert updated.name == "Jane Doe"

    # Delete (Manual delete via DB since model might not have delete() with logic yet)
    db.execute_update("DELETE FROM Requesters WHERE id = ?", (req.id,))
    assert Requester.get_by_id(req.id) is None


def test_requester_types_persistence(temp_db):
    """Verify different requester types and their fields are persisted incorrectly."""
    # Teacher with department
    teacher = Requester(
        name="Prof. Smith", requester_type="teacher", department="Science"
    )
    assert teacher.save(editor_name="tester") is True

    # Student with grade/section
    student = Requester(
        name="Student 1", requester_type="student", grade_level="10", section="B"
    )
    assert student.save(editor_name="tester") is True

    all_reqs = Requester.get_all()
    assert len(all_reqs) == 2

    t = next(r for r in all_reqs if r.name == "Prof. Smith")
    assert t.department == "Science"

    s = next(r for r in all_reqs if r.name == "Student 1")
    assert s.grade_level == "10"
    assert s.section == "B"
