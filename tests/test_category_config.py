"""
Tests for category configuration and auto-calculated dates.

Covers Beta Test Requirement A.1:
- Fixed category system with predefined categories
- Auto-calculated expiration/disposal dates based on acquisition date
- Auto-calculated calibration dates for equipment
- Case-insensitive category lookups
"""

from datetime import date

from inventory_app.services.category_config import (
    get_category_config,
    get_all_category_names,
    get_category_map,
    is_valid_category,
    DEFAULT_CATEGORIES,
)


class TestCategoryConfiguration:
    """Tests for category configuration system."""

    def test_all_default_categories_exist(self):
        """Test that all standard categories are defined."""
        expected_categories = {
            "Chemicals-Solid",
            "Chemicals-Liquid",
            "Prepared Slides",
            "Consumables",
            "Equipment",
            "Apparatus",
            "Lab Models",
            "Others",
            "Uncategorized",
        }
        actual_categories = set(get_all_category_names())
        assert actual_categories == expected_categories

    def test_get_category_config_by_name(self):
        """Test retrieving category config by exact name."""
        config = get_category_config("Chemicals-Solid")
        assert config is not None
        assert config.name == "Chemicals-Solid"
        assert config.is_consumable is True
        assert config.expiry_months == 24

    def test_get_category_config_case_insensitive(self):
        """Test category lookup is case-insensitive."""
        config = get_category_config("chemicals-solid")
        assert config is not None
        assert config.name == "Chemicals-Solid"

    def test_get_category_config_returns_none_for_invalid(self):
        """Test that invalid category name returns None."""
        config = get_category_config("InvalidCategory")
        assert config is None

    def test_is_valid_category(self):
        """Test category validation function."""
        assert is_valid_category("Equipment") is True
        assert is_valid_category("chemicals-liquid") is True  # Case insensitive
        assert is_valid_category("NonExistent") is False

    def test_get_category_map_structure(self):
        """Test category map contains all categories."""
        cat_map = get_category_map()
        assert len(cat_map) == len(DEFAULT_CATEGORIES)
        assert "Equipment" in cat_map
        assert "Chemicals-Solid" in cat_map

    def test_consumable_categories_identified(self):
        """Test consumable categories are correctly identified."""
        consumables = [c for c in DEFAULT_CATEGORIES if c.is_consumable]
        consumable_names = {c.name for c in consumables}
        assert "Chemicals-Solid" in consumable_names
        assert "Chemicals-Liquid" in consumable_names
        assert "Prepared Slides" in consumable_names
        assert "Consumables" in consumable_names
        assert "Equipment" not in consumable_names

    def test_non_consumable_categories_identified(self):
        """Test non-consumable categories are correctly identified."""
        non_consumables = [c for c in DEFAULT_CATEGORIES if not c.is_consumable]
        non_consumable_names = {c.name for c in non_consumables}
        assert "Equipment" in non_consumable_names
        assert "Apparatus" in non_consumable_names
        assert "Lab Models" in non_consumable_names


class TestAutoCalculatedDates:
    """Tests for automatic date calculation based on category and acquisition date."""

    def test_consumable_expiration_date_calculation(self):
        """Test expiration date calculation for consumables."""
        config = get_category_config("Chemicals-Solid")
        assert config is not None
        acq_date = date(2025, 1, 1)

        exp_date = config.calculate_expiration_date(acq_date)

        # Chemicals-Solid expires 24 months from acquisition
        expected = date(2027, 1, 1)
        assert exp_date == expected

    def test_liquid_chemical_expiration_calculation(self):
        """Test liquid chemical specific expiration date."""
        config = get_category_config("Chemicals-Liquid")
        assert config is not None
        acq_date = date(2025, 6, 15)

        exp_date = config.calculate_expiration_date(acq_date)

        # 24 months from June 15, 2025
        expected = date(2027, 6, 15)
        assert exp_date == expected

    def test_prepared_slides_expiration_calculation(self):
        """Test prepared slides expiration (3 years)."""
        config = get_category_config("Prepared Slides")
        assert config is not None
        acq_date = date(2025, 3, 20)

        exp_date = config.calculate_expiration_date(acq_date)

        # 36 months from acquisition
        expected = date(2028, 3, 20)
        assert exp_date == expected

    def test_non_consumable_disposal_date_calculation(self):
        """Test disposal date calculation for non-consumables."""
        config = get_category_config("Equipment")
        assert config is not None
        acq_date = date(2025, 1, 1)

        disp_date = config.calculate_expiration_date(acq_date)

        # Equipment disposed after 5 years
        expected = date(2030, 1, 1)
        assert disp_date == expected

    def test_apparatus_disposal_calculation(self):
        """Test apparatus disposal date (3 years)."""
        config = get_category_config("Apparatus")
        assert config is not None
        acq_date = date(2025, 8, 10)

        disp_date = config.calculate_expiration_date(acq_date)

        # 3 years from acquisition
        expected = date(2028, 8, 10)
        assert disp_date == expected

    def test_lab_models_disposal_calculation(self):
        """Test lab models disposal date (5 years)."""
        config = get_category_config("Lab Models")
        assert config is not None
        acq_date = date(2024, 12, 25)

        disp_date = config.calculate_expiration_date(acq_date)

        # 5 years from acquisition
        expected = date(2029, 12, 25)
        assert disp_date == expected

    def test_calibration_date_for_equipment(self):
        """Test calibration date calculation for equipment."""
        config = get_category_config("Equipment")
        assert config is not None
        acq_date = date(2025, 2, 1)

        cal_date = config.calculate_calibration_date(acq_date)

        # Equipment calibration due 1 year from acquisition
        expected = date(2026, 2, 1)
        assert cal_date == expected

    def test_no_calibration_for_non_equipment(self):
        """Test that non-equipment items have no calibration date."""
        config = get_category_config("Apparatus")
        assert config is not None
        acq_date = date(2025, 1, 1)

        cal_date = config.calculate_calibration_date(acq_date)

        assert cal_date is None

    def test_calibration_false_returns_none(self):
        """Test items without calibration requirement return None."""
        config = get_category_config("Lab Models")
        assert config is not None
        acq_date = date(2025, 1, 1)

        cal_date = config.calculate_calibration_date(acq_date)

        assert cal_date is None
        assert config.has_calibration is False

    def test_leap_year_expiration_calculation(self):
        """Test date calculation handles leap years correctly."""
        config = get_category_config("Chemicals-Solid")
        assert config is not None
        acq_date = date(2024, 2, 29)  # Leap day

        exp_date = config.calculate_expiration_date(acq_date)

        # 24 months from Feb 29, 2024
        expected = date(2026, 2, 28)  # Normalizes to Feb 28
        assert exp_date == expected

    def test_uncategorized_no_expiration(self):
        """Test uncategorized items have no auto-expiration."""
        config = get_category_config("Uncategorized")
        assert config is not None
        acq_date = date(2025, 1, 1)

        exp_date = config.calculate_expiration_date(acq_date)

        assert exp_date is None

    def test_consumables_generic_expiration(self):
        """Test generic consumables category (1 year default)."""
        config = get_category_config("Consumables")
        assert config is not None
        acq_date = date(2025, 1, 1)

        exp_date = config.calculate_expiration_date(acq_date)

        # 12 months from acquisition
        expected = date(2026, 1, 1)
        assert exp_date == expected

    def test_date_calculations_with_mid_month_dates(self):
        """Test calculations work correctly with mid-month dates."""
        config = get_category_config("Equipment")
        assert config is not None
        acq_date = date(2025, 3, 15)

        disp_date = config.calculate_expiration_date(acq_date)

        # 5 years from March 15
        expected = date(2030, 3, 15)
        assert disp_date == expected

    def test_all_consumable_categories_have_expiry_months(self):
        """Test all consumables have expiry_months configured."""
        for category in DEFAULT_CATEGORIES:
            if category.is_consumable:
                assert category.expiry_months is not None
                assert category.expiry_months > 0

    def test_all_non_consumables_have_disposal_years(self):
        """Test all non-consumables have disposal_years configured (except Uncategorized)."""
        for category in DEFAULT_CATEGORIES:
            if not category.is_consumable and category.name != "Uncategorized":
                assert category.disposal_years is not None
                assert category.disposal_years > 0
