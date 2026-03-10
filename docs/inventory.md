# Inventory Page

The Inventory page is the main workspace for item records, stock visibility, and item-level maintenance.

## What This Page Handles

- View inventory rows with stock and alert context.
- Add, edit, delete, and import items.
- Search and filter by text, category, and supplier.
- Surface date-based alert states through row coloring.

Underlying tables involved are `Items`, `Item_Batches`, and `Stock_Movements`.

## Loading and Performance

- Data loads asynchronously to keep the UI responsive.
- Loading indicators are shown while refresh is in progress.
- Action buttons are temporarily guarded during critical load phases.
- Virtual scrolling exists as an internal feature flag and is not currently exposed as a user setting.

## Importing Items

Use `Inventory -> Import Items` for bulk creation from `.xlsx` files.

Required input fields (with flexible header matching):

- item name
- stock value
- item type

The importer supports case-insensitive and spacing-tolerant header matching and can detect headers below title rows. For full details, see `docs/importing_items.md`.

## Item Lifecycle

- Create: stores item data and initial batch quantity.
- Edit: updates item data and writes update history.
- Delete: requires editor attribution and reason; blocked for currently requested items.

Categories are fixed by system configuration and determine default item type/date behavior.

## Auto-Calculated Dates

When category and acquisition date are set, default dates are auto-filled:

- Consumables: expiration date from category shelf-life rule.
- Non-consumables: disposal date from category lifespan rule.
- Equipment only: calibration date (initially one year from acquisition).

Users can manually override dates before saving.

## Alert and Color Rules

Status computation rules:

- Consumable expiration warning: within 180 days.
- Non-consumable disposal warning: within 90 days.
- Equipment calibration warning: within 90 days of next due date.
- Overdue when the relevant due date is already in the past.

Row coloring:

- Red/pink: overdue.
- Yellow: warning.
- Default: no current alert.

If multiple statuses apply, the most critical one determines row color.

## Zero-Stock Behavior

Items with `0` current stock remain stored for history and requisition integrity, but they are excluded from active alert calculations.

## Stock Computation Summary

- Consumables: stock changes with issue/return/disposal movements.
- Non-consumables: item count is effectively retained while movement history tracks usage and returns.

The system prevents stock from going negative.

## Standard Categories

- Chemicals-Solid
- Chemicals-Liquid
- Prepared Slides
- Consumables
- Equipment
- Apparatus
- Lab Models
- Others
- Uncategorized
