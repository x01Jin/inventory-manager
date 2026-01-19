# Requesters Management

## Overview

The Requesters page manages personnel who are authorized to create requisitions and borrow inventory. Requesters are associated with requisitions to track inventory usage by person, class, and organizational unit.

## Data Loading

- Requester data loads asynchronously in a background thread
- A progress indicator displays during loading
- The table populates progressively as data becomes available
- Buttons are disabled during data load to prevent conflicts

## Requester Fields

| Field | Required | Description | Example |
| ------- | ---------- | ------------- | --------- |
| **Name** | Yes | Full name of the requester | John Smith |
| **Affiliation** | Yes | Department, role, or organizational unit | Science Department, Grade 10 |
| **Group Name** | Yes | Class, team, or group identifier | Class 10-A, Biology Lab |
| **Grade Level** | No | Educational grade level | Grade 7, Grade 8, Grade 10 |
| **Section** | No | Section or class identifier | Section A, Einstein, Blue Team |

### Field Details

#### Name

- Full name of the person making the request
- Displayed in requisition records and reports
- Used in requester search and filtering

#### Affiliation

- General organizational unit or role
- Common values: Teacher, Student, Lab Assistant, Department
- Used for filtering and usage tracking by organizational unit

#### Group Name

- Class, team, or project group identifier
- Links requesters to specific groups for activity tracking
- Useful for school settings (class sections) or department teams

#### Grade Level

- Educational level (primarily for school settings)
- Supports usage tracking by grade in reports
- Optional field; leave blank for non-educational contexts

#### Section

- Further subdivision within a grade or group
- Example: "Section A", "Einstein", "Team Alpha"
- Used in "Usage by Grade Level" reports for detailed breakdowns

## Usage in Reports

The Grade Level and Section fields enable specialized reporting:

- **Usage by Grade Level Report**: Groups consumption by grade level and section
- **Usage by Requester**: Filter reports by requester affiliation or group
- **Activity Tracking**: Associates usage with specific classes and groups

## Key Components

- **Requesters Table**: Displays all registered requesters with columns:
  - Requisitions Count: Number of associated requisitions (determines delete eligibility)
  - Name: Requester full name
  - Affiliation: Organizational unit
  - Group: Class or group identifier
  - Grade Level: Educational grade (if applicable)
  - Section: Section identifier (if applicable)
  - Created: Record creation timestamp

- **Add Requester Dialog**: Form for creating new requester records
- **Edit Requester Dialog**: Form for modifying existing requester records
- **Search Box**: Filters requesters by name, affiliation, or group

## Common Operations

### Adding a Requester

1. Click **Add Requester** button
2. Fill required fields (Name, Affiliation, Group)
3. Optionally fill Grade Level and Section
4. Enter Editor Name (for audit trail)
5. Click **Save Requester**

The new requester is immediately available for requisition creation.

### Editing a Requester

1. Select a requester row in the table
2. Click **Edit Requester** or double-click the row
3. Modify fields as needed
4. Enter Editor Name
5. Click **Save**

All edits are logged with timestamp and editor name.

### Deleting a Requester

1. Select a requester with **0 requisitions**
2. Click **Delete Requester**
3. Confirm deletion
4. Enter Editor Name
5. Click **Delete**

#### Delete Protection

- Requesters with associated requisitions cannot be deleted
- Delete button is disabled for requesters with requisitions
- Tooltip explains why deletion is blocked

### Finding a Requester

Use the search box to filter by:

- Name (partial match, case-insensitive)
- Affiliation (partial match, case-insensitive)
- Group (partial match, case-insensitive)

Results update instantly as you type.

## Validation Rules

| Rule | Behavior |
| ------ | ---------- |
| Required Fields | Name, Affiliation, Group, Editor Name must not be empty |
| Duplicate Check | Warning shown if requester with same name+affiliation+group exists |
| Delete Protection | Cannot delete requesters with requisition history |
| Case Sensitivity | Search and display are case-insensitive; storage preserves input |

## Integration with Requisitions

Requesters are linked to requisitions through:

- **Requester Dropdown**: Available requesters appear in requisition creation dialog
- **Affiliation Display**: Shown alongside name for disambiguation
- **Requisition Count**: Displayed in requesters table
- **Audit Trail**: Requester creation/edits tracked in activity log

## Best Practices

1. **Use Consistent Naming**: Establish naming conventions for affiliations and groups
2. **Include Grade/Section**: For educational settings, always include grade level and section
3. **Regular Cleanup**: Remove obsolete requesters (no active requisitions) periodically
4. **Meaningful Groups**: Use descriptive group names for easy filtering and reporting

## Limitations

- Requester records are not a user authentication system
- No password or access control associated with requesters
- Cannot restore deleted requesters (consider deactivating instead)
- Requester deletion is permanent

## Related Documentation

- See `docs/requisitions.md` for requisition creation workflows
- See `docs/reports.md` for Usage by Grade Level report details
- See `docs/architecture.md` for database schema (Requesters table)
