# General Help & FAQ

## Frequently Asked Questions

### What happens when the database schema updates?

On startup, the application automatically checks for and applies any pending database updates. A progress screen may briefly appear showing migration progress. No user action is required, and no data is lost during this process.

### How do I create a requisition?

1. Navigate to the Requisitions page
2. Click "New Requisition"
3. Select a requester from the dropdown or choose "Individual Request" for ad-hoc requisitions
4. Add items from the inventory
5. Set expected return date
6. Click "Create Requisition"

### Can I edit a requisition after creation?

Yes. Select a requisition from the list and click "Edit". You can modify items, dates, and requester information. Changes are logged in the requisition history.

### How do returns work?

1. Find the active requisition in the list
2. Click "Return" to process the return
3. Mark items as returned or defective
4. Add notes for defective items
5. Confirm the return

### What are the alert thresholds?

| Category | Alert Timing |
| ---------- | ------------- |
| Chemicals | 6 months before expiration |
| Glassware/Apparatus | 3 years after first use |
| Equipment | 5 years after first use |
| Equipment Calibration | 3 months before due date |

### How are grade levels used?

Grade levels are associated with requesters and used for usage tracking reports. When creating a requester, you can specify their grade level (Grade 7, Grade 8, etc.) and section (Section A, Einstein, etc.).

### Can I track who made changes to items?

Yes. When editing items, you must provide an editor name. All edits are logged in the Update History with the editor name, timestamp, and reason for the change.

### How do I generate reports?

1. Navigate to the Reports page
2. Select a report type from the sidebar
3. Set date range and filtering options
4. Click "Generate Report"
5. Use the Export button to save as Excel or print

### What is virtual scrolling?

Virtual scrolling allows the application to handle large datasets efficiently by only rendering visible rows. Enable it in Settings for better performance with thousands of items.

### How do I import items from Excel?

1. Go to Settings → Import Items
2. Select an Excel file with item data
3. Map the columns to fields
4. Click Import

Required columns: Name, Category. Optional: Size, Brand, PO Number, Supplier, Expiration Date, Quantity Received.
