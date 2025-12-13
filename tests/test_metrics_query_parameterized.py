from inventory_app.gui.dashboard.metrics import MetricsManager
from inventory_app.database.connection import db
# datetime/time helpers removed - not required in this test


def setup_temp_db(tmp_path):
    tmp_db_path = tmp_path / "test_inventory.db"
    tmp_db_path.parent.mkdir(parents=True, exist_ok=True)
    if tmp_db_path.exists():
        tmp_db_path.unlink()
    db.db_path = tmp_db_path
    assert db.create_database() is True
    return tmp_db_path


def test_metrics_date_queries_use_parameterization(tmp_path):
    setup_temp_db(tmp_path)
    mgr = MetricsManager()

    # Monkeypatch db.execute_query to capture calls and validate parameterization
    orig = db.execute_query
    queries = []

    def fake_execute_query(query, params=()):
        queries.append((query, params))
        return orig(query, params)

    db.execute_query = fake_execute_query

    try:
        # Execute metrics retrieval to exercise the queries
        metrics = mgr.get_all_metrics()

        assert isinstance(metrics, dict)

        # Add a small check for the metrics keys
        assert "total_items" in metrics

        # Look for our metric queries that should use parameter placeholders
        found_expiry = any("expiration_date <= ?" in q for q, _ in queries)
        found_recent = any("last_modified >= ?" in q for q, _ in queries)
        assert found_expiry and found_recent

        expiry_params = [p for q, p in queries if "expiration_date <= ?" in q]
        recent_params = [p for q, p in queries if "last_modified >= ?" in q]
        assert expiry_params and len(expiry_params[0]) == 1
        assert recent_params and len(recent_params[0]) == 1
    finally:
        db.execute_query = orig
