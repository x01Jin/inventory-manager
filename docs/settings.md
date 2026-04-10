# Settings

The Settings page controls app-wide lookup values and appearance preferences.

## What You Can Configure

- Preferences tab: switch between Light and Dark theme.
- Sizes tab: add, rename, or delete size values.
- Brands tab: add, rename, or delete brand values.
- Suppliers tab: add, rename, or delete suppliers.

These values are reused across Inventory forms, filters, and related dialogs.

## Preferences Tab

- Theme can be changed directly in Settings.
- The theme is applied immediately.
- Some UI elements may still need an app restart to fully refresh.

## Sizes, Brands, and Suppliers

All three tabs support Add, Edit, and Delete.

Behavior is consistent across tabs:

- Input is trimmed and cannot be blank.
- Case-insensitive duplicate checks are enforced (for example, `250ml` and `250mL` are treated as duplicates).
- Edit/Delete requires selecting an existing entry first.
- Entries are displayed in a 3-column table: `Name`, `Usage`, and `Status`.
- You can double-click a row to open the Edit dialog for that entry.

Delete behavior differs by type:

- Sizes, Brands, and Suppliers: deletion is blocked if currently used by any item.
- Each table row shows usage count in `Usage` and either `Unused` or `NON-DELETABLE` in `Status`.
- Rows that are in use are marked `NON-DELETABLE`, and the delete button is disabled for the selected row.

## Fixed Categories

Settings includes a read-only Categories tab. Categories are fixed by system configuration (`inventory_app/services/category_config.py`) and cannot be added, edited, or deleted in the UI.

| Category | Item Type | Auto Date Rule | Calibration |
| --- | --- | --- | --- |
| Chemicals-Solid | Consumable | Expiration = acquisition + 24 months | No |
| Chemicals-Liquid | Consumable | Expiration = acquisition + 24 months | No |
| Prepared Slides | Consumable | Expiration = acquisition + 36 months | No |
| Consumables | Consumable | Expiration = acquisition + 12 months | No |
| Equipment | Non-consumable | Disposal = acquisition + 5 years | Yes, yearly |
| Apparatus | Non-consumable | Disposal = acquisition + 3 years | No |
| Lab Models | Non-consumable | Disposal = acquisition + 5 years | No |
| Others | N/A | No auto date rule | No |
| Uncategorized | N/A | No auto date rule | No |

When creating or editing an item, category selection auto-fills item type and date defaults. Users can still manually adjust dates before saving.

The Settings page includes this fixed-category note:

"these categories are fixed and is essential on how an item's lifecycle is categorized. changing or adding categories would require a calculation of it's life cycle and and other core functions to become a proper item category. please contact the developer if you want to change or add categories as it is not a simple addition and it requires a deep understanding of the program's core functions and data structure."
