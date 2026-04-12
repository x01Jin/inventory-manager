from pathlib import Path

import pytest

from inventory_app.database.connection import db
from inventory_app.database.models import ItemSDS
from inventory_app.services.sds_storage_service import SDSStorageService


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_sds.db"
    db.db_path = db_file
    assert db.create_database() is True
    yield db_file


def test_sds_table_exists_in_baseline_schema(temp_db):
    tables = db.execute_query(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'Item_SDS'"
    )
    assert len(tables) == 1


def test_item_sds_save_and_delete_with_history(temp_db):
    item_id = db.execute_update(
        "INSERT INTO Items (name, category_id, is_consumable) VALUES (?, ?, ?)",
        ("Hydrochloric Acid", 1, 1),
        return_last_id=True,
    )[1]
    assert item_id is not None

    sds = ItemSDS(
        item_id=item_id,
        stored_filename="item_1_hcl.pdf",
        original_filename="hcl.pdf",
        file_path="C:/tmp/hcl.pdf",
        mime_type="application/pdf",
        sds_notes="Corrosive. Use gloves and goggles.",
    )

    assert sds.save("JIN", reason="SDS uploaded") is True

    loaded = ItemSDS.get_by_item_id(item_id)
    assert loaded is not None
    assert loaded.original_filename == "hcl.pdf"
    assert loaded.sds_notes == "Corrosive. Use gloves and goggles."

    history = db.execute_query(
        "SELECT editor_name, reason FROM Update_History WHERE item_id = ? ORDER BY id DESC LIMIT 1",
        (item_id,),
    )
    assert history
    assert history[0]["editor_name"] == "JIN"
    assert history[0]["reason"] == "SDS uploaded"

    activity = db.execute_query(
        """
        SELECT activity_type, entity_type, user_name
        FROM Activity_Log
        WHERE entity_id = ?
        ORDER BY id DESC
        """,
        (item_id,),
    )
    assert activity
    assert activity[0]["activity_type"] == "SDS_UPLOADED"
    assert activity[0]["entity_type"] == "item_sds"
    assert activity[0]["user_name"] == "JIN"

    assert ItemSDS.delete_for_item(item_id, "JIN", reason="SDS removed") is True
    assert ItemSDS.get_by_item_id(item_id) is None

    remove_activity = db.execute_query(
        """
        SELECT activity_type, entity_type, user_name
        FROM Activity_Log
        WHERE entity_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (item_id,),
    )
    assert remove_activity
    assert remove_activity[0]["activity_type"] == "SDS_REMOVED"
    assert remove_activity[0]["entity_type"] == "item_sds"
    assert remove_activity[0]["user_name"] == "JIN"


def test_sds_storage_service_store_and_remove(tmp_path):
    service = SDSStorageService(base_dir=tmp_path / "sds")

    source = tmp_path / "sodium_hydroxide.pdf"
    source.write_text("dummy-pdf-content", encoding="utf-8")

    metadata = service.store_file(77, str(source))
    assert metadata is not None

    stored_path = Path(metadata["file_path"])
    assert stored_path.exists() is True
    assert metadata["stored_filename"].startswith("item_77_")

    assert service.remove_file(metadata["file_path"]) is True
    assert stored_path.exists() is False
