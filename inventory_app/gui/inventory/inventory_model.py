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
    item_type: Optional[str]
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

        # Active filter state.
        self.search_term: str = ""
        self.category_filter: str = ""
        self.supplier_filter: str = ""
        self.item_type_filter: str = ""
        self.date_from_filter: Optional[date] = None
        self.date_to_filter: Optional[date] = None

    def set_items(self, items: List[ItemRow]) -> None:
        """Set the full inventory items list."""
        self.items = items
        self._apply_filters()
        logger.debug(f"Set {len(items)} inventory items")

    def get_filtered_items(self) -> List[ItemRow]:
        """Get currently filtered items."""
        return self.filtered_items

    def filter_by_search(self, search_term: str) -> None:
        """Filter items by search term (name, category, supplier)."""
        self.search_term = search_term.strip()
        self._apply_filters()

    def filter_by_category(self, category: str) -> None:
        """Filter items by category."""
        self.category_filter = category.strip()
        self._apply_filters()

    def filter_by_supplier(self, supplier: str) -> None:
        """Filter items by supplier."""
        self.supplier_filter = supplier.strip()
        self._apply_filters()

    def filter_by_item_type(self, item_type: str) -> None:
        """Filter items by item type."""
        self.item_type_filter = item_type.strip()
        self._apply_filters()

    def filter_by_date_range(
        self,
        start_date: Optional[date],
        end_date: Optional[date],
    ) -> None:
        """Filter items by acquisition date range."""
        self.date_from_filter = start_date
        self.date_to_filter = end_date
        self._apply_filters()

    def apply_current_filters(
        self,
        search_term: str = "",
        category: str = "",
        supplier: str = "",
        item_type: str = "",
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> None:
        """Update active filters and apply them together."""
        self.search_term = search_term.strip()
        self.category_filter = category.strip()
        self.supplier_filter = supplier.strip()
        self.item_type_filter = item_type.strip()
        self.date_from_filter = date_from
        self.date_to_filter = date_to
        self._apply_filters()

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

    def get_unique_item_types(self) -> List[str]:
        """Get list of unique item types."""
        item_types = set()
        for item in self.items:
            if item.item_type:
                item_types.add(item.item_type)
            else:
                item_types.add("Consumable" if item.is_consumable else "Non-consumable")
        return sorted(list(item_types))

    def get_statistics(self) -> Dict[str, Any]:
        """Get complete statistics about the inventory including alerts."""

        from inventory_app.gui.inventory.inventory_controller import InventoryController

        controller = InventoryController()
        return controller.get_inventory_statistics()

    def clear_filters(self) -> None:
        """Clear all filters and show all items."""
        self.search_term = ""
        self.category_filter = ""
        self.supplier_filter = ""
        self.item_type_filter = ""
        self.date_from_filter = None
        self.date_to_filter = None
        self.filtered_items = self.items.copy()
        logger.debug("Cleared all filters")

    def _apply_filters(self) -> None:
        """Apply all active filters to the full item set."""
        filtered = self.items

        if self.search_term:
            search_lower = self.search_term.lower()
            filtered = [
                item
                for item in filtered
                if (
                    search_lower in item.name.lower()
                    or search_lower in item.category_name.lower()
                    or (
                        item.supplier_name
                        and search_lower in item.supplier_name.lower()
                    )
                )
            ]

        if self.category_filter:
            filtered = [
                item for item in filtered if item.category_name == self.category_filter
            ]

        if self.supplier_filter:
            filtered = [
                item for item in filtered if item.supplier_name == self.supplier_filter
            ]

        if self.item_type_filter:
            filtered = [
                item
                for item in filtered
                if (
                    (
                        item.item_type
                        or ("Consumable" if item.is_consumable else "Non-consumable")
                    )
                    == self.item_type_filter
                )
            ]

        if self.date_from_filter or self.date_to_filter:
            filtered = [item for item in filtered if self._matches_date_range(item)]

        self.filtered_items = filtered
        logger.debug(
            "Applied filters: search='%s', category='%s', supplier='%s', item_type='%s', "
            "date_from=%s, date_to=%s -> %s items",
            self.search_term,
            self.category_filter,
            self.supplier_filter,
            self.item_type_filter,
            self.date_from_filter,
            self.date_to_filter,
            len(self.filtered_items),
        )

    def _matches_date_range(self, item: ItemRow) -> bool:
        """Check whether item acquisition date matches active date-range filters."""
        if item.acquisition_date is None:
            return False

        if self.date_from_filter and item.acquisition_date < self.date_from_filter:
            return False

        if self.date_to_filter and item.acquisition_date > self.date_to_filter:
            return False

        return True
