"""
Data model for inventory management.
Handles data structures and formatting for inventory items.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, date
from dataclasses import dataclass
from inventory_app.utils.logger import logger


@dataclass
class ItemRow:
    """Data structure for a single inventory item row in the table."""
    id: Optional[int]
    name: str
    category_name: str
    size: Optional[str]
    brand: Optional[str]
    supplier_name: Optional[str]
    other_specifications: Optional[str]
    po_number: Optional[str]
    expiration_date: Optional[date]
    calibration_date: Optional[date]
    is_consumable: bool
    acquisition_date: Optional[date]
    last_modified: Optional[datetime]
    total_stock: int = 0
    available_stock: int = 0

    def format_expiration_date(self) -> str:
        """Format expiration date for display."""
        if not self.expiration_date:
            return "N/A"
        return self.expiration_date.strftime("%m/%d/%Y")

    def format_calibration_date(self) -> str:
        """Format calibration date for display."""
        if not self.calibration_date:
            return "N/A"
        return self.calibration_date.strftime("%m/%d/%Y")

    def format_acquisition_date(self) -> str:
        """Format acquisition date for display."""
        if not self.acquisition_date:
            return "N/A"
        return self.acquisition_date.strftime("%m/%d/%Y")

    def format_last_modified(self) -> str:
        """Format last modified timestamp for display."""
        if not self.last_modified:
            return "N/A"
        return self.last_modified.strftime("%m/%d/%Y %H:%M")

    def format_consumable(self) -> str:
        """Format consumable flag for display."""
        return "Yes" if self.is_consumable else "No"


class InventoryModel:
    """Model for managing inventory data and business logic."""

    def __init__(self):
        self.items: List[ItemRow] = []
        self.filtered_items: List[ItemRow] = []
        self.categories: List[str] = []
        self.suppliers: List[str] = []
        self.sizes: List[str] = []
        self.brands: List[str] = []

    def set_items(self, items: List[ItemRow]) -> None:
        """Set the full inventory items list."""
        self.items = items
        self.filtered_items = items.copy()
        logger.debug(f"Set {len(items)} inventory items")

    def get_filtered_items(self) -> List[ItemRow]:
        """Get currently filtered items."""
        return self.filtered_items

    def filter_by_search(self, search_term: str) -> None:
        """Filter items by search term (name, category, supplier)."""
        if not search_term:
            self.filtered_items = self.items.copy()
            return

        search_lower = search_term.lower()
        self.filtered_items = [
            item for item in self.items
            if (search_lower in item.name.lower() or
                search_lower in item.category_name.lower() or
                (item.supplier_name and search_lower in item.supplier_name.lower()))
        ]
        logger.debug(f"Filtered to {len(self.filtered_items)} items with search term: {search_term}")

    def filter_by_category(self, category: str) -> None:
        """Filter items by category."""
        if not category:
            self.filtered_items = self.items.copy()
            return

        self.filtered_items = [
            item for item in self.items
            if item.category_name == category
        ]
        logger.debug(f"Filtered to {len(self.filtered_items)} items in category: {category}")

    def filter_by_supplier(self, supplier: str) -> None:
        """Filter items by supplier."""
        if not supplier:
            self.filtered_items = self.items.copy()
            return

        self.filtered_items = [
            item for item in self.items
            if item.supplier_name == supplier
        ]
        logger.debug(f"Filtered to {len(self.filtered_items)} items from supplier: {supplier}")

    def get_unique_categories(self) -> List[str]:
        """Get list of unique category names."""
        return sorted(list(set(item.category_name for item in self.items)))

    def get_unique_suppliers(self) -> List[str]:
        """Get list of unique supplier names."""
        suppliers = set()
        for item in self.items:
            if item.supplier_name:
                suppliers.add(item.supplier_name)
        return sorted(list(suppliers))

    def get_statistics(self) -> Dict[str, Any]:
        """Get complete statistics about the inventory including alerts."""

        from inventory_app.gui.inventory.inventory_controller import InventoryController

        controller = InventoryController()
        return controller.get_inventory_statistics()

    def clear_filters(self) -> None:
        """Clear all filters and show all items."""
        self.filtered_items = self.items.copy()
        logger.debug("Cleared all filters")
