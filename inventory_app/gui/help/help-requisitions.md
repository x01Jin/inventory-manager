# Requisitions Help

The Requisitions page is where you create, manage, and finalize requests for inventory items used in laboratory activities. It supports the full lifecycle for a request: creation → requested → active → returned (final) or overdue. This page describes every user-facing control, the meanings of the statuses, and step‑by‑step recipes for the most common tasks.

## **Top controls (header)**

- **➕ New Requisition:** Open the Create dialog to build a new requisition. Requires selecting a **Requester**, adding one or more **Items**, and setting activity and schedule details. Creation uses an immediate transaction to reserve stock atomically.
- **✏️ Edit Requisition:** Enabled when a requisition row is selected. Opens the Edit dialog to change requester, items, schedule, and activity details. Editing is disabled for fully processed (returned) requisitions.
- **↩️ Return Items:** Opens the one-time Final Return dialog for the selected requisition. Use this to record returned quantities, lost/damaged non-consumables, and defective items, then finalize and lock the requisition.
- **🖨️ Print:** Enabled when a requisition row is selected. Generates an HTML report of the selected requisition with all details for printing or archival.
- **🗑️ Delete Requisition:** Permanently deletes the selected requisition (prompt + editor name required). Deletion cannot be undone and removes related records.
- **🔄 Refresh:** Reloads requisition data, updates statuses (requested/active/overdue) and requester options.

## **Filters & Search**

- **🔍 Search:** Matches text inside `requester name`, `affiliation`, `group`, `activity name`, and requested `item names` (case-insensitive substring match). Typing updates results immediately.
- **📂 Requester:** Dropdown of requesters that currently have requisitions (choose **All Requesters** to show everything).
- **📌 Status:** Filter by `Requested`, `Active`, `Returned`, or `Overdue`.
- **📅 From / To:** Filter by the activity date. Defaults to 30 days ago → 1 week ahead.
- **🗑️ Clear Filters:** Resets search, requester, status, and date range to defaults and refreshes
- **Summary:** The filters panel shows a short summary (e.g., “Showing 5 of 23 requisitions (21.7%)”).

## **Requisitions Table (columns & meanings)**

- **Status:** Requisition lifecycle state: `Requested`, `Active`, `Overdue`, or `Returned`. Color-coded in the table for fast scanning (requested=warning, active=success, overdue=error, returned=returned color).
- **Requester:** The requester name (and affiliation shown in preview). Click a row to select; double-click or use **Edit** to change a requisition.
- **Request Date:** Expected request datetime (shown as date + time). Table default sort orders are queued sensibly (status priority, or request date recent-first).

Notes:

- Click any column header to sort (default sensible ordering applied on first click).
- Selecting a row populates the right-hand **Requisition Details** preview and enables the **Edit / Return / Delete** buttons according to the requisition's status.

## **Preview panel (Requisition Details)**

The right-hand preview shows a clear, read-only summary of the selected requisition:

- **Status:** Big, color-coded status badge.
- **Requester Information:** Name, affiliation, group.
- **Timeline:** Expected Request and Expected Return datetimes (if set).
- **Activity Details:** Activity name, activity date, students/groups.
- **Requested Items:** One line per requested item with requested quantities.
- **Final Return Details:** Once a requisition is processed (returned), the preview shows a breakdown of returned consumables, consumed items, non-consumables returned, lost/damaged quantities, and any defective items with notes.

## **Status meanings & automatic updates**

- **Requested:** The expected request time is in the future.
- **Active:** Now between expected request and expected return.
- **Overdue:** Expected return datetime is in the past and the requisition is not returned.
- **Returned:** Final return processing has been completed (final state). Edit and Return actions are disabled when `Returned`.

Status updates occur automatically on **Refresh** and are recalculated in the background for accuracy. The system records status changes to history for audit.

## **Create a Requisition — Step-by-step**

1. Click **➕ New Requisition**.
2. **Select Requester**: use the selector to find or choose an existing requester ( requester name and affiliation shown ).
3. **Add Items**: select items and quantities. The item selector provides available batches and enforces stock rules.
4. **Activity details**: enter a descriptive Activity name (required), optional description, activity date, number of students/groups.
5. **Schedule**: set **Expected Request** and **Expected Return** datetimes (both required). These determine the requisition status timeline.
6. Click **✅ Create Requisition** — you will be prompted for your editor name/initials (required). The system validates inputs and uses an IMMEDIATE transaction to reserve stock; if validation or stock checks fail, you will be shown errors and the creation will be blocked.

After creation the requisition is visible in the table and requests/reservations are recorded in stock movements.

## **Edit a Requisition**

- Select a requisition and click **✏️ Edit Requisition** (or double-click a row).
- Fully returned requisitions cannot be edited. Partially-active or requested requisitions can be edited.
- Changing items replaces existing items and recreates stock reservations atomically; you are asked for editor name before updates are saved.

## **Return / Finalize (one-time process)**

1. Select the requisition and click **↩️ Return Items**.
2. Wait for item rows to finish loading in the dialog (loading is asynchronous on large requisitions). **Process Returns** stays disabled until data is ready.
3. Read the warning: this is a ONE-TIME, FINAL process. Once you click 'Process Returns' the requisition will be LOCKED and cannot be edited.
4. For **Consumables:** specify how many were returned unused (any remainder is considered consumed). Quantities are integer-based, so volume/mass consumables should use usable stock units (examples: `900ml` import becomes quantity `900`, `1 L` becomes `1000`) to allow partial amounts like `100` or `250`.
5. For **Non-Consumables:** specify how many were lost/damaged and how many were defective/broken. For defective items:
   - Enter the quantity of defective/broken items
   - Add notes describing the defect (required when defective quantity > 0)
6. Confirm and enter editor name when prompted. The system records stock movements (returns/consumption), defective items (if any), and locks the requisition.

Stock result summary:

- Consumables permanently deplete by the quantity consumed.
- Non-consumables remain at baseline when borrowed and returned; only lost/disposed quantity permanently reduces stock.

Tips:

- Ensure every requested quantity is accounted for before processing (returned + lost + defective = requested). The dialog summarizes these counts to help.
- Defective/broken items are recorded separately in the system and can be tracked in the Defective Items Report.

## **Delete a Requisition**

- Select a requisition and click **🗑️ Delete Requisition**. You will be asked to confirm and enter your name/initials. Deletion is permanent and removes associated requisition items and related records.

## **Print a Requisition**

- Select a requisition and click **🖨️ Print**. An HTML file will be generated containing a professional, formatted report of the requisition with:
  - Requisition ID and status
  - Requester information (name, affiliation, group)
  - Timeline (expected request and return dates)
  - Activity details (name, date, students, groups)
  - Complete list of requested items and quantities
  - For returned requisitions: return details showing consumables returned/consumed, non-consumables returned/lost, and defective items
- You will be prompted to choose a save location and filename for the HTML file. You can open the file in any web browser and use the browser's print function (Ctrl+P) to print or save as PDF.

## **Validation & common warnings**

- **Required fields:** Requester, Activity Name, At least one item, Expected Request and Expected Return, Editor name at save/delete/process time.
- **Date validation:** Request and return must be valid datetimes. If invalid you will be asked to correct them.
- **Stock validation:** If available stock is insufficient the system will prevent creating or updating a requisition or will show a clear validation error.
- **Transaction safety:** Creates/updates use atomic transactions to avoid oversubscription of stock.

## **Search, filtering & exact behavior**

- The **Search** box performs a case-insensitive substring match across requester name, affiliation, group, activity name, and item names.
- **Requester** and **Status** filters are exact matches based on options shown in the UI.
- **Date range** filters the activity date.

## **Statistics & status line**

- The status line at the bottom shows counts: Total | Requested | Active | Overdue | Returned. These reflect the current filters and update on **Refresh**.

## **Common tasks / quick recipes**

- **Create a requisition:** Click **➕ New Requisition** → select requester → add items and quantities → set activity and schedule → Create.
- **Edit a requisition:** Select row → **✏️ Edit Requisition** → change fields → Update.
- Requisition updates write field-level audit details (field name, old value, new value) when changes are saved.
- **Process returns:** Select row → **↩️ Return Items** → enter returned/lost quantities → Process (final).
- **Find requisitions:** Use **🔍 Search** with requester name, activity name, or item; use status or date range to narrow.

## **Limitations & notes**

- **Finality:** Final return processing is irreversible — requisitions become locked and cannot be edited; only deletion remains as an admin action.
- **Deletion:** Permanently removes requisition and related records; editor name is required.
- **Report/Export:** Use the `Reports` section for advanced exports; developers may also use table export helpers to retrieve table data programmatically.
- **Dashboard integration:** Upcoming requisitions appear on the Dashboard schedule chart and small summary widgets.

## **Troubleshooting & support**

- If you see **Data Load Error** or **Data Reload Error**, try refreshing again; if it persists, contact your administrator and include the time and action you took.
- Validation errors (e.g., stock, missing fields) provide specific messages — correct fields and retry.

-- End of Requisitions Help --
