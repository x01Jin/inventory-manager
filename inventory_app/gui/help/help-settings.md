# Settings Help

The Settings page lets you manage the small sets of reference data used throughout the app: Categories, Sizes, Brands and Suppliers. These values populate dropdowns and filters across Inventory, Requisitions, and related dialogs — keeping this data accurate makes finding and recording items consistent and reliable.

## **Top controls (page layout)**

- **Tabs:** The page has one tab for each type: **Categories**, **Sizes**, **Brands**, **Suppliers**. Each tab shows a list of existing values and three action buttons.
- **List:** Shows all saved entries for the selected tab (sorted A→Z).
- **Add / Edit / Delete:** Buttons below the list. `Add` opens a small dialog to enter a name; `Edit` opens the dialog pre-filled for the selected row; `Delete` prompts for confirmation.

Notes about selection and focus:

- You must select a row to enable **Edit** or **Delete**. If no row is selected, the app will warn you.
- All changes are saved immediately to the database when you confirm an Add or Edit.

## **Tabs & behavior (what each tab does)**

- **Categories:** Categories are required when creating or editing an Item. Categories are stored by id and are used in filters and reports.
- **Sizes:** Size values are free-form labels (e.g., `250mL`, `1L`) and appear in Item records as a text field.
- **Brands:** Brand values are free-form labels and appear in Item records as a text field.
- **Suppliers:** Supplier entries are stored as separate records (referenced from Items by id) and populate the Supplier selector in the Item editor.

## **Add / Edit — exact behavior**

- **Add:** Click `Add <Type>`, enter a name, and click OK. Names are trimmed and must not be blank.
- **Edit:** Select a row → click `Edit <Type>` → change the name → click OK. The dialog is the same small name dialog used for Add.
- **Uniqueness & validation:** Names must be unique. Attempts to add or change a name to a duplicate will fail (the database enforces uniqueness) and an error will be shown.
- **Success messages:** A short confirmation (e.g., "Size added successfully!") appears on success.

## **Delete — what to expect**

- **Confirmation:** Deleting requires confirming an explicit Yes/No dialog.
- **Blocked deletes:** A delete will fail if the value is currently used by Items. For example:
  - Categories cannot be deleted while any Item references that category (Categories are required for Items).
  - Suppliers cannot be deleted while any Item references that supplier.
  - Sizes and Brands cannot be deleted if any Items use that value.
- **If delete fails:** You will see an error dialog. To resolve, reassign or remove the Items that reference the value (use the Inventory page to find and edit those items), then retry the delete.

## **How Settings values are used across the app**

- **Item Editor:** Category, Supplier, Size and Brand selectors are populated from Settings. Categories and Supplier IDs are stored as references; Size and Brand are stored on the Item record as text.
- **Inventory filters & reports:** Categories are used in the Category filter and in reports. Suppliers also appear in supplier filters and exports.
- **When changes take effect:** Changes are saved immediately. Other dialogs refresh their dropdowns when they open — if a dialog is already open, close and re-open it to see updates.

## **Common tasks / quick recipes**

- **Add a new supplier:** Settings → Suppliers tab → Add Supplier → enter supplier name → OK. The new supplier will appear in the Item editor supplier dropdown.
- **Edit an existing category:** Select the category → Edit Category → change name → OK. Existing Items keep pointing to the same category id; the label changes everywhere.
- **Delete an unused size:** Select size → Delete Size → Confirm. If deletion is blocked, open Inventory and search for items using that size.

## **Validation & common warnings**

- **Required / non-empty:** Names cannot be blank — empty input is ignored.
- **Duplicate names:** The database enforces uniqueness; you’ll get an error if the name already exists.
- **Deletion prevented if in-use:** If a value is referenced by Items the delete will be blocked and a failure message shown. Reassign or remove the dependent items first.

## **Tips & best practices**

- Use clear, descriptive names (e.g., `250 mL` vs `250mL`) and a consistent format so filters and reporting are consistent.
- Prefer a small, curated set of categories and suppliers — fewer, well-defined values make filtering and reporting easier.
- When renaming a value, prefer **Edit** over deleting and re-adding; renaming preserves references on existing Items.

## **Troubleshooting & support**

- **Add/Edit failed:** Likely causes are an empty name or a duplicate. Check the exact error message and pick a unique name.
- **Delete failed:** This usually means the value is in use by Items. Use the Inventory page to find related items (filter/sort by category, supplier, size or brand) and update or delete them before retrying.
- **Still stuck:** If operations keep failing, check the application logs (`logs/logs.txt`) and contact your administrator with the action and timestamp.

## **Limitations & notes**

- Settings changes are applied directly to the database; they are not recorded as Item edit history entries. Renaming preserves references; deleting removes the value only if nothing depends on it.
- Categories are required for Items; removing categories in use is intentionally blocked to avoid orphaned Items.
- If you need bulk changes (many items to reassign), use the Item editor and reports to plan updates — there is no bulk reassign UI on the Settings page.

--
End of Settings Help
