import time
import psutil
import pytest
import sys
import os

# Add parent directory to path so inventory_app can be imported
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from PyQt6.QtWidgets import QApplication  # noqa: E402
from inventory_app.gui.inventory.inventory_page import InventoryPage  # noqa: E402

@pytest.fixture(scope="module")
def app():
    """Ensure a QApplication exists for widget tests."""
    import sys
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    yield app

@pytest.fixture
def inventory_page(qtbot, mocker):
    """Fixture for InventoryPage with mocked controller DB calls."""
    # Patch controller to avoid real DB access
    mocker.patch("inventory_app.gui.inventory.inventory_controller.InventoryController.load_inventory_data", return_value=[
        {
            "id": 1,
            "name": "Test Item",
            "category_name": "Test Category",
            "size": "M",
            "brand": "BrandX",
            "supplier_name": "SupplierY",
            "other_specifications": "",
            "po_number": "PO123",
            "expiration_date": None,
            "calibration_date": None,
            "is_consumable": 1,
            "acquisition_date": None,
            "last_modified": None,
            "first_batch_date": None,
            "total_stock": 100,
            "available_stock": 90,
            "is_requested": 0,
        }
    ])
    page = InventoryPage()
    qtbot.addWidget(page)
    return page

def profile_performance(func, *args, **kwargs):
    """Profile CPU, memory, and execution time for a function."""
    process = psutil.Process()
    mem_before = process.memory_info().rss
    cpu_before = process.cpu_times()
    t0 = time.perf_counter()
    result = func(*args, **kwargs)
    t1 = time.perf_counter()
    cpu_after = process.cpu_times()
    mem_after = process.memory_info().rss
    return {
        "result": result,
        "duration_sec": t1 - t0,
        "cpu_user_delta": cpu_after.user - cpu_before.user,
        "cpu_system_delta": cpu_after.system - cpu_before.system,
        "mem_rss_delta": mem_after - mem_before,
        "mem_rss_after": mem_after,
    }

def test_inventory_page_refresh_performance(inventory_page):
    """Test performance of inventory page data refresh."""
    metrics = profile_performance(inventory_page.refresh_data)
    print(f"InventoryPage.refresh_data: {metrics}")
    # Example thresholds (adjust as needed)
    assert metrics["duration_sec"] < 1.0, "Data refresh took too long"
    assert metrics["mem_rss_delta"] < 10 * 1024 * 1024, "Excessive memory usage"

def test_inventory_page_filter_performance(inventory_page):
    """Test performance of filtering."""
    # Simulate a filter operation
    def filter_op():
        inventory_page._on_search_changed("Test")
    metrics = profile_performance(filter_op)
    print(f"InventoryPage._on_search_changed: {metrics}")
    assert metrics["duration_sec"] < 0.5, "Filtering took too long"
    assert metrics["mem_rss_delta"] < 5 * 1024 * 1024, "Excessive memory usage"
