# Requesters Help

The Requesters page is where you add, edit, and manage the people who can request inventory items. Requesters are organized into three tabs based on their type: **Students**, **Teachers**, and **Faculty/Individuals**. Each tab shows only the fields relevant to that requester type.

## **Top controls (header)**

- **Tabs Bar:** Switch between Students, Teachers, and Faculty/Individuals. Each tab shows only requesters of that type with appropriate columns.
- **➕ Add Requester:** Opens the Add Requester dialog. Choose the correct tab (Student/Teacher/Faculty) and fill in the required fields. Your editor name is required for audit tracking.
- **✏️ Edit Requester:** Edit the selected requester. Works within the current tab. You must provide your editor name to save changes.
- **🗑️ Delete Requester:** Permanently deletes the selected requester. Disabled if the requester has any associated requisitions. Requires confirmation and your editor name.
- **🔄 Refresh:** Reloads all requester data and updates counts.

## **Search & Filters**

- **🔍 Search box:** Type to filter requesters in the current tab only. Search behavior varies by tab:
  - **Students:** Searches name, grade level, and section
  - **Teachers:** Searches name and department
  - **Faculty/Individuals:** Searches name only
- **Clear:** Clears the search and shows all requesters in the current tab.

## **Requesters Tables**

The page has three separate tables, one for each requester type:

### Students Tab

- Requisitions: Number of requisitions for this student
- Name: Student full name
- Grade Level: Educational level (e.g., Grade 7, Grade 10)
- Section: Class section or group identifier
- Created: Date and time when the record was created

### Teachers Tab

- Requisitions: Number of requisitions for this teacher
- Name: Teacher full name
- Department: Department or organizational unit
- Created: Date and time when the record was created

### Faculty/Individuals Tab

- Requisitions: Number of requisitions for this person
- Name: Full name
- Created: Date and time when the record was created

**Notes:**

- Click any column header to sort by that column (sorts are preserved until changed).
- Selecting a row enables Edit; selecting a row with zero requisitions enables Delete.
- The table shows alternating row colors for readability.

## **Adding a Requester — Step-by-step**

1. Click **➕ Add Requester**.
2. Select the appropriate tab for the requester type:
   - **Student Tab:** Requires Name. Grade Level and Section are optional.
   - **Teacher Tab:** Requires Name and Department.
   - **Faculty/Individual Tab:** Requires Name only.
3. Fill in the fields for the selected type.
4. Enter **Your Name/Initials** in the Editor Information section (required for audit).
5. Click **Save Requester**.
6. If a requester with the same name and type already exists, you will be warned. You can continue or cancel to avoid duplicates.
7. On success, the requester is added, the list refreshes, and the requester becomes available in requisition selectors.

## **Editing a Requester**

- Select a requester row in the appropriate tab and click **✏️ Edit Requester** (or double-click the row).
- You can only edit fields for the requester's original type (e.g., cannot add a department to a student).
- Update any editable fields and enter your editor name to save.
- If an identical requester exists, you will be warned before saving.

## **Deleting a Requester**

- Deletion is only allowed for requesters with no associated requisitions. If a requester has requisitions, the **Delete** button is disabled.
- To delete: select a requester (with zero requisitions), click **🗑️ Delete Requester**, confirm the action, and provide your editor name. Deletion is permanent.

## **Validation & common warnings**

- **Required fields vary by type:** Students need a name; Teachers need a name and department; Faculty/Individuals need only a name.
- **Editor name required:** You must enter your name/initials to save or delete any requester.
- **Duplicate detection:** Creating a requester with the same name and type prompts a warning; you may cancel to avoid duplicates.
- **Cannot delete with requisitions:** If deletion fails, check whether the requester has associated requisitions — deletion is blocked to preserve historical data.
- **Cannot change requester type:** Once created, a requester's type cannot be changed. To reassign a requester to a different type, delete and re-create them.

## **Status & statistics**

- The status line shows the total number of requesters in the current tab.
- Tab counts are displayed on the tab labels, so you can quickly see how many students, teachers, and faculty/individuals are registered.
- Use the search box to filter the current tab; the status line updates to show filtered results.

## **How Requesters are used**

- When creating a requisition, you select a requester from a searchable list organized by type.
- Requester records are part of the audit trail: creations, edits, and deletions are recorded with the editor name you supply.
- Choose the correct requester type when adding new people — this determines which fields are tracked and how they appear in reports.

## **Common tasks / quick recipes**

- **Add a student:** Click **➕ Add Requester** → Select **Student** tab → Enter name (optional grade/section) → Save.
- **Add a teacher:** Click **➕ Add Requester** → Select **Teacher** tab → Enter name and department → Save.
- **Add a faculty/individual:** Click **➕ Add Requester** → Select **Faculty/Individual** tab → Enter name → Save.
- **Edit a requester:** Select row in appropriate tab → **✏️ Edit Requester** → Change fields → Save.
- **Delete a requester:** Select row (must have 0 requisitions) in appropriate tab → **🗑️ Delete Requester** → Confirm and enter editor name → Delete.
- **Find a requester:** Switch to the appropriate tab → Use **🔍 Search** with relevant fields → Select from filtered results.

## **Limitations & notes**

- Requester records are not a user authentication system — they are person records used to label requisitions.
- Deleting requesters with associated requisitions is blocked to maintain data integrity.
- Requester type cannot be changed after creation — delete and re-create if needed.
- Created timestamps are recorded and shown for audit purposes.
- Each tab operates independently — actions in one tab do not affect others.

## **Troubleshooting & support**

- **Cannot save a requester:** Ensure all required fields for the selected type are filled, including editor name.
- **Delete button is disabled:** The requester has associated requisitions. This is intentional to protect data integrity.
- **Cannot find a requester:** Use the search box in the correct tab. Students are only in the Students tab, teachers only in Teachers tab.
- **Data load errors:** Use **🔄 Refresh** to reload. If errors persist, contact support with the error details and timestamp.

---

End of Requesters Help
