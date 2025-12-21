"""
Async inventory model for background data loading.

Implements AsyncTableModel for inventory data with background
loading via QThreadPool workers.
"""

from typing import Any, Dict, List
from inventory_app.gui.utils.async_table import AsyncTableModel
from inventory_app.gui.inventory.inventory_controller import InventoryController
from inventory_app.utils.logger import logger


class AsyncInventoryModel(AsyncTableModel):
    """
    Async model for inventory data loading.

    Loads inventory items from database in background thread
    and emits signals for progressive table population.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._controller = InventoryController()
        self.set_batch_size(50)  # 50 rows per batch

    def load_data(self) -> List[Dict[str, Any]]:
        """
        Load inventory data from database.

        This runs in a background thread. Returns raw dict data
        that will be processed for table display.
        """
        try:
            data = self._controller.load_inventory_data()
            logger.debug(f"AsyncInventoryModel loaded {len(data)} items")
            return data
        except Exception as e:
            logger.error(f"AsyncInventoryModel load error: {e}")
            raise

    def search_items(self, search_term: str) -> List[Dict[str, Any]]:
        """
        Search items by term.

        This should be called from a worker for async operation.
        """
        try:
            return self._controller.search_items(search_term)
        except Exception as e:
            logger.error(f"AsyncInventoryModel search error: {e}")
            raise

    def get_categories(self) -> List[str]:
        """Get available categories."""
        return self._controller.get_categories()

    def get_suppliers(self) -> List[str]:
        """Get available suppliers."""
        return self._controller.get_suppliers()

    def get_statistics(self) -> Dict[str, Any]:
        """Get inventory statistics."""
        return self._controller.get_inventory_statistics()
