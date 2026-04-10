# User Guide

## Quick Start

1. Activate your virtual environment.
2. Run `python -m inventory_app.main`.
3. The app opens on the Dashboard.
4. The local database is created automatically on first run.

## Main Pages

- Dashboard: Snapshot of alerts, recent activity, and high-level metrics.
- Inventory: Add, edit, import, search, and monitor stock items.
- Requisitions: Create requests, track status, and process returns.
- Requesters: Manage people or groups who can request items.
- Reports: Export usage, inventory, and trend reports to Excel.
- Settings: Manage sizes, brands, suppliers, and theme preference.
- Help: In-app markdown help pages.

## Common Workflows

### Add an Item

1. Open Inventory.
2. Click Add Item.
3. Enter the basic fields (name, category, and quantity).
4. Add optional details (supplier, size, brand, dates).
5. Save with your editor/user name.

### Create a Requisition

1. Open Requisitions.
2. Select a requester.
3. Add one or more items and quantities.
4. Fill schedule and activity details.
5. Save.

The system updates inventory in one save flow to avoid partial changes.

### Process a Return

1. Open a requisition that is still open.
2. Enter what was returned and what was consumed or lost.
3. Submit return processing.

After return processing, the requisition is finalized and treated as closed.

Stock behavior after returns:

- Consumables: returned-unused quantity is added back and used quantity is permanently deducted.
- Non-consumables: borrow/return does not permanently deduct stock; only lost or disposed quantity is permanently deducted.

### Import Items from Excel

1. Open Inventory.
2. Click Import Items.
3. Select an `.xlsx` file.
4. Enter editor name and start import.
5. Review imported and skipped rows.

Required header groups (header matching is flexible):

- Name: `name`, `item`, `item name`, and similar variants
- Stock count: `stocks` or `stock`
- Item type: `item type`, `item_type`, `type`, or equivalent

## Practical Tips

- Back up `inventory.db` regularly.
- Check Dashboard alerts before creating new requisitions.
- Keep requester data current to improve report quality.
- Use reports for monthly planning and audits.
