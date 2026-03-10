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

Delete behavior differs by type:

- Sizes and Brands: deletion is blocked if currently used by any item.
- Suppliers: if in use, the app can force-delete and set affected item supplier values to `None`.

## Fixed Categories

Categories are not managed in Settings and are fixed by system configuration (`inventory_app/services/category_config.py`).

| Category | Item Type | Auto Date Rule | Calibration |
| --- | --- | --- | --- |
| Chemicals-Solid | Consumable | Expiration = acquisition + 24 months | No |
| Chemicals-Liquid | Consumable | Expiration = acquisition + 24 months | No |
| Prepared Slides | Consumable | Expiration = acquisition + 36 months | No |
| Consumables | Consumable | Expiration = acquisition + 12 months | No |
| Equipment | Non-consumable | Disposal = acquisition + 5 years | Yes, yearly |
| Apparatus | Non-consumable | Disposal = acquisition + 3 years | No |
| Lab Models | Non-consumable | Disposal = acquisition + 5 years | No |
| Others | Non-consumable | Disposal = acquisition + 5 years | No |
| Uncategorized | Non-consumable | No auto date rule | No |

When creating or editing an item, category selection auto-fills item type and date defaults. Users can still manually adjust dates before saving.
