"""
Inventory management GUI modules.
Provides scalable, modular inventory page components using composition pattern.
"""

from .inventory_page import InventoryPage
from .inventory_controller import InventoryController
from .inventory_model import InventoryModel, ItemRow
from .inventory_table import InventoryTable
from .inventory_filters import InventoryFilters
from .inventory_stats import InventoryStats
from .item_editor import ItemEditor
from .alert_system import AlertSystem

__all__ = [
    'InventoryPage',
    'InventoryController',
    'InventoryModel',
    'ItemRow',
    'InventoryTable',
    'InventoryFilters',
    'InventoryStats',
    'ItemEditor',
    'AlertSystem'
]
