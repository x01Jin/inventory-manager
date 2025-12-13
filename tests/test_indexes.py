from inventory_app.database.connection import db


def setup_temp_db(tmp_path):
    tmp_db_path = tmp_path / "test_inventory.db"
    tmp_db_path.parent.mkdir(parents=True, exist_ok=True)
    if tmp_db_path.exists():
        tmp_db_path.unlink()
    db.db_path = tmp_db_path
    assert db.create_database() is True
    return tmp_db_path


def test_stock_movements_has_source_index(tmp_path):
    setup_temp_db(tmp_path)

    # Ensure the index is registered in the SQLite schema
    idxs = db.execute_query("PRAGMA index_list('Stock_Movements')")
    names = [r["name"] for r in idxs]
    assert "idx_movements_source" in names

    # Verify index is defined on `source_id`
    info = db.execute_query("PRAGMA index_info('idx_movements_source')")
    assert info and info[0]["name"] == "source_id"
