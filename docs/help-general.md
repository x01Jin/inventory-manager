# General Help and FAQ

This page answers common questions in plain language. Use it as a quick reference before opening detailed feature pages.

## What happens when the database updates?

At startup, the app checks and applies available schema updates automatically. You may briefly see a migration progress screen.

## How do I create a requisition?

1. Open `Requisitions`.
2. Click `New Requisition`.
3. Select a requester (or individual request mode).
4. Add one or more items and quantities.
5. Set expected request/return schedule details.
6. Save.

## Can I edit a requisition later?

Yes, as long as it is not finalized/returned. Changes are recorded in requisition history.

## How do returns work?

1. Open an active requisition.
2. Click `Return`.
3. Enter returned, consumed, and defective quantities.
4. Add notes for defects if needed.
5. Confirm.

After return processing, the requisition becomes finalized and is no longer editable.

## How do defective items affect stock?

- Reported defective quantities reduce Current Stock (usable stock) immediately.
- Defective review is done in Item Usage History for that item.
- `Disposed` and `Not Defective` confirmations are tracked separately in history.
- `Not Defective` quantity is returned to Current Stock.
- `Disposed` confirmations will deduct it from Total Stock.

## Where do I confirm defective outcomes?

1. Open Inventory.
2. Open item usage history (double-click row, or click DEF badge).
3. Use `Show Defective Events Only` when needed.
4. Select a `Defective` row with pending quantity.
5. Enter quantity and confirm as `Disposed` or `Not Defective`.

The defective controls are always available in Item Usage History, not only when opening from DEF.

## What are the active alert rules?

| Rule | Warning Window | Overdue Condition |
| --- | --- | --- |
| Consumable expiration | 180 days before expiration | Date is in the past |
| Non-consumable disposal (all configured non-consumables) | 90 days before disposal | Date is in the past |
| Equipment calibration | 90 days before next due date | Next due date is in the past |

Notes:

- Next calibration due date is calculated as 1 year after the last calibration date.
- Items with `0` current stock are excluded from status alerts.

## How are grade levels used?

Requester grade/section data is used by reports such as usage-by-grade summaries.

## Is there an audit trail?

Yes. Item edits and requisition updates require editor attribution and are logged with timestamps.

## How do I generate reports?

1. Open `Reports`.
2. Choose a report type.
3. Set date range and filters.
4. Click `Generate Report`.
5. Export to Excel (or print where supported).

## What about virtual scrolling?

Virtual scrolling exists as an internal performance feature flag, but it is currently not user-configurable in Settings.

## How do I import items from Excel?

1. Open `Inventory`.
2. Click `Import Items`.
3. Select an `.xlsx` file.
4. Enter editor name.
5. Start import and review imported/skipped row counts.

For full import rules (header variants, parsing behavior, and validation), see `docs/importing_items.md`.
