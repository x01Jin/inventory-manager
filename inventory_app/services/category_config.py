"""
Category configuration for the inventory application.

Defines the default categories available in the system with their associated
alert thresholds. Categories are fixed and cannot be customized by users.

Each category has:
- name: Display name
- is_consumable: Whether items in this category are consumable
- expiry_months: Months before expiration warning (for consumables)
- disposal_years: Years until disposal date (for non-consumables)
- has_calibration: Whether items need calibration tracking
"""

from dataclasses import dataclass
from typing import Optional, List, Dict
from datetime import date
from dateutil.relativedelta import relativedelta


@dataclass
class CategoryConfig:
    """Configuration for a default category."""

    name: str
    is_consumable: bool
    expiry_months: Optional[int] = None  # For consumables
    disposal_years: Optional[int] = None  # For non-consumables
    has_calibration: bool = False

    def calculate_expiration_date(self, acquisition_date: date) -> Optional[date]:
        """Calculate expiration/disposal date based on acquisition date.

        Args:
            acquisition_date: The date the item was acquired

        Returns:
            Calculated expiration/disposal date or None if not applicable
        """
        if self.is_consumable and self.expiry_months:
            # Consumables: expiry based on months from acquisition
            return acquisition_date + relativedelta(months=self.expiry_months)
        elif not self.is_consumable and self.disposal_years:
            # Non-consumables: disposal based on years from acquisition
            return acquisition_date + relativedelta(years=self.disposal_years)
        return None

    def calculate_calibration_date(self, acquisition_date: date) -> Optional[date]:
        """Calculate initial calibration due date.

        Args:
            acquisition_date: The date the item was acquired

        Returns:
            Calibration date (1 year from acquisition) or None if not applicable
        """
        if self.has_calibration:
            return acquisition_date + relativedelta(years=1)
        return None


# Default categories with their alert thresholds
# These are the only categories available in the system
DEFAULT_CATEGORIES: List[CategoryConfig] = [
    # Consumable categories (expiry-based)
    CategoryConfig(
        name="Chemicals-Solid",
        is_consumable=True,
        expiry_months=24,  # 2 years shelf life, 6 month warning
    ),
    CategoryConfig(
        name="Chemicals-Liquid",
        is_consumable=True,
        expiry_months=24,  # 2 years shelf life, 6 month warning
    ),
    CategoryConfig(
        name="Prepared Slides",
        is_consumable=True,
        expiry_months=36,  # 3 years shelf life
    ),
    CategoryConfig(
        name="Consumables",
        is_consumable=True,
        expiry_months=12,  # 1 year default
    ),
    # Non-consumable categories (disposal-based)
    CategoryConfig(
        name="Equipment",
        is_consumable=False,
        disposal_years=5,
        has_calibration=True,
    ),
    CategoryConfig(
        name="Apparatus",
        is_consumable=False,
        disposal_years=3,  # Glassware/apparatus: 3 years
        has_calibration=False,
    ),
    CategoryConfig(
        name="Lab Models",
        is_consumable=False,
        disposal_years=5,
        has_calibration=False,
    ),
    # Generic category
    CategoryConfig(
        name="Others",
        is_consumable=False,
        disposal_years=None,
        has_calibration=False,
    ),
    # For imports without category
    CategoryConfig(
        name="Uncategorized",
        is_consumable=False,
        disposal_years=None,
        has_calibration=False,
    ),
]


def get_category_config(category_name: str) -> Optional[CategoryConfig]:
    """Get the configuration for a category by name.

    Args:
        category_name: Name of the category

    Returns:
        CategoryConfig if found, None otherwise
    """
    for cat in DEFAULT_CATEGORIES:
        if cat.name.lower() == category_name.lower():
            return cat
    return None


def get_all_category_names() -> List[str]:
    """Get all available category names.

    Returns:
        List of category names
    """
    return [cat.name for cat in DEFAULT_CATEGORIES]


def get_category_map() -> Dict[str, CategoryConfig]:
    """Get a dictionary mapping category names to configs.

    Returns:
        Dictionary of category name -> CategoryConfig
    """
    return {cat.name: cat for cat in DEFAULT_CATEGORIES}


def is_valid_category(name: str) -> bool:
    """Check if a category name is valid (exists in defaults).

    Args:
        name: Category name to check

    Returns:
        True if valid, False otherwise
    """
    return get_category_config(name) is not None
