# Importing Inventory Items ✅

This document describes the Excel import feature for adding inventory items in bulk and explains how the importer parses, validates, and saves rows.

## Quick summary

- File: Excel (.xlsx)
- Minimum required columns: **name**, **stocks**, **item type** (accepts many human variants; header matching is case- and space-insensitive)
- Optional columns: **category**, **size**, **brand**, **supplier**, **other specifications**, **po number**, **expiration date**, **calibration date**, **acquisition date**

---

## Import Process

The import runs in a background thread to prevent UI freezing during large imports:

1. Select an Excel file (.xlsx)
2. Enter editor name for audit trail
3. Click Import - the operation runs in the background
4. A progress bar displays real-time status: `[current/total], skipped: X`
5. A completion message shows total imported and skipped counts

The import can be cancelled while in progress by clicking the Cancel button.

---

## Header detection & normalization 🔎

- The importer scans the first 40 rows of the active worksheet to *find the header row* — this lets you include a top title block (report title, notes, etc.) above the table and still import the data.
- Header matching is **case-insensitive** and **space/underscore-insensitive**. For example, the following headers are all accepted and treated equivalently:
  - `Item Name`, `itemname`, `names`, `ITEMS` → mapped to `name`
  - `stocks`, `Stock` → mapped to `stocks`
  - `item type`, `item_type`, `type` → mapped to `item type`
- If the importer cannot find a header row containing the required groups (name + stocks + item type) within the scan window, import fails with a clear message telling you which required columns are missing.

## Accepted header variants (examples)

- Name: `name`, `item`, `items`, `item name`, `names` (and other variant spellings that normalize to the same key)
- Stocks: `stocks`, `stock`
- Item type: `item type`, `item_type`, `type`

---

## Row parsing rules & defaults 🧾

- **Name**: Required — rows with missing or empty names are skipped and reported.
- **Stocks**: The importer accepts a variety of free-form `stocks` values. Parsing rules are:
  - **Numeric counts** (e.g., `2`, `10`) are parsed as integer quantities (floats coerced to int).
  - **Size-bearing entries** containing volume/mass units (e.g., `900ml`, `1.1 L`, `2 liters`, `125 g`, `500ml`) are treated as **single containers**: the importer sets `quantity = 1` and records the matched `size` (the parsed size will be used as the item `size` when the explicit `size` column is empty).

  - **Supported size units** include common volume/mass units such as: `ml`, `l`, `g`, `kg`, `mg`, `gal`, `liter`, `litre`, and `ltr` (case-insensitive). The importer preserves the matched substring so the resulting `size` field closely resembles the input text.

  - **Leading counts with extra info** (e.g., `10 boxes (100pcs)`, `1 set of 8 pieces`) — the leading integer is used as the quantity; parenthetical or "of N pieces" style details are recorded as notes and appended to `other_specifications`.
  - **Empty / missing** stocks values result in `quantity = 0`.
  - **Invalid values** (no parseable number or recognized size) cause the row to be skipped and an explanatory message is included in the import log.
  - **Case & spacing**: size units are matched case-insensitively. They are space-sensitive except when attached to a number (both `900ml` and `900 ml` are accepted).

Notes

- The importer uses `inventory_app.utils.stock_parser.parse_stock_value` for parsing logic and is covered by unit tests (see `tests/test_item_importer_types.py`).
- **Item type**: The importer normalizes and cleans the `item type` cell before classification:
  - Leading vendor prefixes like `TA,` are stripped when present (case-insensitive).
  - Values containing `consum`, `consumable`, `consumables`, `reagent`, `reagents`, or `chemical` are treated as **Consumable**.
  - Values containing `non` or `not` together with `consum` (e.g., `non consumable`, `TA, non consumable`) are treated as **Non-Consumable**. When ambiguous, the importer conservatively defaults to **Non-Consumable**.
- **Text fields** (category, size, brand, supplier, other specifications, po number): If empty, they are stored as `N/A` (or left blank in the DB where appropriate). Note: if `stocks` contains a size and the explicit `size` column is empty the parsed size will be used instead.
- **Dates** (expiration, calibration, acquisition): Parsed to date objects when possible; unparseable or empty values become `None` (displayed as `N/A` in the UI).

---

### Stocks parsing examples

- `900ml` → quantity=1, size=`900ml`
- `1.1 L` → quantity=1, size=`1.1 L`
- `10 boxes (100pcs)` → quantity=10, notes=`(100pcs)` appended to `other_specifications`
- `1 set of 8 pieces` → quantity=1, notes captured as `of 8 pieces`

---

## Category handling 🗂️

- If the `category` column is present and contains a value, the importer tries to find an existing Category by name (case-insensitive). If not found, it creates a new Category with that name.
- If the `category` column is empty or contains `N/A`, the importer will use (and create if necessary) the `Uncategorized` category.
- This approach prevents foreign-key constraint failures and ensures items always have a valid `category_id` in the `Items` table.

---

## What the importer does on success ✅

- Creates a new `Item` record and an initial batch in `Item_Batches` whose `quantity_received` is the `stocks` value (one batch per imported row).
- Logs row-level success messages; the dialog shows a summary with the number of imported rows and any rows skipped along with reasons.

---

## Audit & logging 🧾

- The import dialog asks for an **Editor name** (used for audit records just like manual add/edit flows).
- The importer logs detailed debug information including the parameters used when attempting to save each item — these logs are useful for debugging errors such as FK constraint violations or parse failures.

---

## Error handling & messages ⚠️

- If the header row is missing required columns the import will abort and show a helpful error indicating the missing columns.
- Rows with invalid values (e.g., bad stock numbers, missing required fields) are skipped and included in the import log with an explanation.
- On unexpected DB errors the row is reported as failed; the importer continues processing subsequent rows where possible.

---

## Example header row (any of these variants will work)

```example
name | stocks | item type | category | size | brand | supplier | expiration date
```

---

## Notes & guidance 💡

- Use this tool for fast bulk creation of simple items and an initial batch. If you need advanced batch data (multiple batches per item, per-batch dates, or custom batch numbers), import minimal rows and then edit the items/batches with the UI or use the programmatic APIs.
- If an import fails repeatedly, share the **debug logs** (look for lines that show the save parameters and the error) and I can help diagnose the exact issue.
