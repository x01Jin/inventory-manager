# Settings Help

The Settings page controls app-wide preferences and lookup lists used in forms.

## Tabs You Will See

- Preferences: theme selection (Light or Dark).
- Sizes: manage size labels.
- Brands: manage brand labels.
- Suppliers: manage supplier records.
- Categories: read-only lifecycle rules and category policy reference.

## Preferences Tab

- Theme changes are applied right away.
- Some UI elements may need a restart to fully refresh.

## Sizes, Brands, and Suppliers

Each tab has Add, Edit, and Delete actions.

General behavior:

- Names are trimmed and cannot be blank.
- Duplicate names are blocked (case-insensitive).
- You must select an entry before Edit/Delete.

Delete behavior:

- Size, Brand, and Supplier deletion is blocked if any item is using that value.
- Entries that are in use are tagged as `NON-DELETABLE` and display the usage count.
- Delete buttons are disabled when the selected entry is currently in use.

## Categories Note

Categories are fixed system values and are not editable in Settings. They are used during item editing to auto-calculate item type and default dates.

The Categories tab includes this fixed policy note:

"these categories are fixed and is essential on how an item's lifecycle is categorized. changing or adding categories would require a calculation of it's life cycle and and other core functions to become a proper item category. please contact the developer if you want to change or add categories as it is not a simple addition and it requires a deep understanding of the program's core functions and data structure."

Calibration applies to Equipment only.

## Practical Tips

- Keep naming consistent (`250 mL` vs `250ml`) so search/filter results stay clean.
- Prefer editing existing values instead of deleting and recreating.
- If delete is disabled or fails, find and update dependent items first.

## Troubleshooting

- If an operation fails, read the dialog message first.
- For repeated failures, review `logs/logs.txt` and include timestamp + action details when reporting.

-- End of Settings Help --
