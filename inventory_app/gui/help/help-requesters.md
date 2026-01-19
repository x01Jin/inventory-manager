# Requesters Help

The Requesters page is where you add, edit, and manage the people (or groups) who may create requisitions and request inventory. It provides a simple, searchable list of registered requesters and the tools you need to keep requester records accurate and audit-ready.

## **Top controls (header)**

- **➕ Add Requester:** Opens the Add Requester dialog. Required fields: **Full Name**, **Affiliation**, **Group**, and **Your Name/Initials** (editor). New requesters are immediately available when creating requisitions.
- **✏️ Edit Requester:** Enabled when a requester row is selected (or double-click a row). Edit their name, affiliation, or group; you must provide your editor name when saving so the change is recorded for audit.
- **🗑️ Delete Requester:** Permanently deletes the selected requester. Deletion is disabled when the requester has any associated requisitions (to protect data integrity). Deleting requires confirmation and your editor name; this action cannot be undone.
- **🔄 Refresh:** Reloads requester data from the database and updates the status line.

## **Search & Filters**

- **🔍 Search box:** Type any text to filter requesters by **name**, **affiliation**, or **group** (case-insensitive substring match). Results update immediately as you type.
- **Clear:** Clears the search and shows all requesters again.

## **Requesters Table (columns & meanings)**

- **Requisitions:** Number of requisitions recorded for this requester. If >0, deletion is disabled.
- **Name:** Requester full name. Double-click to edit.
- **Affiliation:** Department / grade / section / organizational unit.
- **Group:** Class group, team, or other grouping for the requester.
- **Created:** When the requester record was created (date and time).

Notes:

- Click any column header to sort by that column (sorts are preserved until you change them).
- Selecting a row enables **Edit**; selecting a row with zero requisitions enables **Delete**. The table supports single-selection and shows alternating row colors for readability.

## **Adding a Requester — Step-by-step**

1. Click **➕ Add Requester**.
2. Fill **Full Name** (required), **Affiliation** (required), **Group** (required), **Grade Level** (optional), and **Section** (optional).
   - **Grade Level:** Educational level (e.g., Grade 7, Grade 10) or department level. Used for filtering usage reports by grade level.
   - **Section:** Class section or organizational section identifier. Also used in "Usage by Grade Level" reports.
3. Enter **Your Name/Initials** in the **Editor Information** section (this is required and recorded for audit).
4. Click **Save Requester**. If a requester with the same name, affiliation and group already exists you will be warned and asked if you want to continue.
5. On success the requester is added, the list refreshes, and the requester becomes available in requisition selectors.

## **Editing a Requester**

- Select a requester row and click **✏️ Edit Requester** (or double-click the row).
- Update any of the fields. You must enter **Your Name/Initials** to save changes.
- Duplicate detection: if an identical requester (same name/affiliation/group) exists you will be warned before saving.

## **Deleting a Requester**

- Deletion is only allowed for requesters that have no associated requisitions. If a requester has any requisitions recorded, the **Delete** button is disabled and hovering shows a tooltip explaining why.
- To delete: select a requester (with zero requisitions), click **🗑️ Delete Requester**, confirm the action, and provide your **Name/Initials** when prompted. Deletion is permanent and will remove the requester record.

## **Validation & common warnings**

- **Required fields:** Full Name, Affiliation, Group, and Editor name for save/delete.
- **Duplicate requester:** Creating a requester with the same name/affiliation/group will prompt a duplicate warning; you may cancel to avoid duplicates.
- **Cannot delete with requisitions:** If delete fails, check whether the requester has associated requisitions — deletion will be blocked to preserve historical data.
- **Data Load Error:** If the page cannot load data, use **🔄 Refresh**; if the error persists, contact your administrator with the error details and time.

## **Status & statistics**

- The status line at the bottom shows the total number of requesters currently displayed (reflects any active search/filtering).
- Use the **Affiliation** grouping in the statistics to get a quick sense of requester distribution by department or grade.

## **How Requesters are used**

- Requesters are referenced when creating requisitions — the requisition dialog lists registered requesters and shows their affiliation/group to help you pick the correct person.
- Requester records are part of the audit trail: creations, edits, and deletions are recorded in the activity log with the editor name you supply.

## **Common tasks / quick recipes**

- **Add a requester:** Click **➕ Add Requester** → fill required fields → Save.
- **Edit requester details:** Select row → **✏️ Edit Requester** → change fields → Save.
- **Delete a requester:** Select row (must have 0 requisitions) → **🗑️ Delete Requester** → confirm and enter editor name → Delete.
- **Find a requester:** Use **🔍 Search** with name, affiliation, or group to quickly narrow the list.

## **Limitations & notes**

- Requester records are not a user authentication system — they are simply person/group records used to label requisitions.
- Deleting requesters with associated requisitions is blocked to maintain data integrity — if you need to correct historical data, contact your administrator.
- Created timestamps are recorded and shown in the table for auditing when records were added.

## **Troubleshooting & support**

- If you cannot save a requester, ensure all required fields (including editor name) are filled correctly.
- If deletion is blocked unexpectedly, check for hidden requisitions or cached data, then **🔄 Refresh** the page. If problems persist, include the action time and any on-screen error messages when contacting support.

-- End of Requesters Help --
