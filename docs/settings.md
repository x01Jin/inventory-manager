# Settings

Overview

- The Settings page manages core reference data: Sizes, Brands, and Suppliers.
- **Categories are fixed** and cannot be modified through the Settings page. They are predefined in the system with specific alert thresholds.

Behavior

- Sizes, Brands, and Suppliers provide CRUD operations with validation and dependency checks.
- **Supplier deletion**: Suppliers can be deleted even when in use by items. When deleting a supplier that is being used, the system prompts to confirm - items will have their supplier set to 'None'.
- **Size/Brand deletion** is blocked when currently being used by items. An error message explains why and what action is needed.
- **Case-insensitive duplicate prevention**: The system prevents adding entries that differ only in capitalization (e.g., "10ml" vs "10mL", "50kg" vs "50KG"). When attempting to add a duplicate, an error message shows the existing matching entry.

## Fixed Categories

Categories are fixed in the system and cannot be added, edited, or deleted. Each category has predefined alert thresholds that automatically calculate expiration/disposal dates when adding items.

| Category | Type | Alert Threshold | Has Calibration |
| -------- | ---- | --------------- | --------------- |
| Chemicals-Solid | Consumable | 2 years expiry | No |
| Chemicals-Liquid | Consumable | 2 years expiry | No |
| Prepared Slides | Consumable | 3 years expiry | No |
| Consumables | Consumable | 1 year expiry | No |
| Equipment | Non-Consumable | 5 years disposal | Yes (yearly) |
| Apparatus | Non-Consumable | 3 years disposal | No |
| Lab Models | Non-Consumable | 5 years disposal | No |
| Others | Non-Consumable | 5 years disposal | No |
| Uncategorized | Non-Consumable | No threshold | No |

When adding an item:

1. Select a category from the dropdown
2. The item type (consumable/non-consumable) is automatically set based on the category
3. Expiration/disposal dates are automatically calculated based on the acquisition date and category threshold
4. All dates remain editable if manual adjustment is needed

The "Uncategorized" category is reserved for items imported without a category specification.

Integration

- Settings values populate dropdowns and selection widgets across Inventory forms and other dialogs.
- Category configuration is defined in `inventory_app/services/category_config.py`.
