import pytest
from PyQt6.QtWidgets import QMessageBox

from inventory_app.database.connection import db
from inventory_app.database.models import Item
from inventory_app.gui.inventory.item_editor import ItemEditor


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for each GUI test."""
    db_file = tmp_path / "test_inventory.db"
    db.db_path = db_file
    assert db.create_database() is True
    yield db_file


def _select_category(editor: ItemEditor, category_id: int = 1) -> None:
    index = editor.category_combo.findData(category_id)
    assert index >= 0
    editor.category_combo.setCurrentIndex(index)


def test_item_editor_size_field_is_editable_with_suggestions(qtbot, temp_db):
    """Task 3: size field should accept typed values while preserving suggestions."""
    editor = ItemEditor()
    qtbot.addWidget(editor)

    assert editor.size_combo.isEditable() is True


def test_item_editor_duplicate_warning_can_cancel_save(qtbot, monkeypatch, temp_db):
    """Task 3: duplicate warning should allow users to cancel creating a duplicate."""
    existing = Item(name="Beaker", category_id=1)
    assert existing.save(editor_name="tester") is True

    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.No,
    )

    editor = ItemEditor()
    qtbot.addWidget(editor)

    editor.name_input.setText("beaker")
    _select_category(editor, 1)
    editor.editor_input.setText("AB")

    editor.save_item()

    rows = db.execute_query(
        """
        SELECT COUNT(*) AS count
        FROM Items
        WHERE LOWER(name) = LOWER(?) AND category_id = ?
        """,
        ("beaker", 1),
    )
    assert rows[0]["count"] == 1


def test_item_editor_typed_size_creates_new_reference_entry(
    qtbot, monkeypatch, temp_db
):
    """Task 3: typed size values should normalize and be added to Size references."""
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)

    editor = ItemEditor()
    qtbot.addWidget(editor)

    editor.name_input.setText("Task3 Typed Size")
    _select_category(editor, 1)
    editor.editor_input.setText("AB")
    editor.size_combo.setCurrentText("750ml")

    editor.save_item()

    item_rows = db.execute_query(
        "SELECT size FROM Items WHERE name = ?",
        ("Task3 Typed Size",),
    )
    assert item_rows
    assert item_rows[0]["size"] == "750 mL"

    size_rows = db.execute_query(
        "SELECT name FROM Sizes WHERE name = ?",
        ("750 mL",),
    )
    assert len(size_rows) == 1
