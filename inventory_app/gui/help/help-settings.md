# Settings Help

The Settings page controls app-wide preferences and lookup lists used in forms.

## Tabs You Will See

- Preferences: theme selection (Light or Dark).
- Sizes: manage size labels.
- Brands: manage brand labels.
- Suppliers: manage supplier records.

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

- Size and Brand deletion is blocked if any item is using that value.
- Supplier deletion can be force-confirmed; the app sets affected item suppliers to `None`.

## Categories Note

Categories are fixed system values and are not editable in Settings. They are used during item editing to auto-calculate item type and default dates.

Calibration applies to Equipment only.

## Practical Tips

- Keep naming consistent (`250 mL` vs `250ml`) so search/filter results stay clean.
- Prefer editing existing values instead of deleting and recreating.
- If delete fails, find and update dependent items first.

## Troubleshooting

- If an operation fails, read the dialog message first.
- For repeated failures, review `logs/logs.txt` and include timestamp + action details when reporting.

-- End of Settings Help --
