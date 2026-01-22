# Requesters Management

## Overview

The Requesters page manages personnel who are authorized to create requisitions and borrow inventory. Requesters are associated with requisitions to track inventory usage by person, class, and organizational unit.

## Requester Types

Requesters are categorized into three types, each with specific required fields:

| Type | Description | Required Fields |
| ------ | ------------- | ----------------- |
| **Student** | Educational institution students | Name, Grade Level, Section |
| **Teacher** | Faculty or staff members | Name, Department |
| **Faculty** | External or simplified requests | Name, Affiliation |

### Student Fields

- **Name**: Full name of the student
- **Grade Level**: Educational level (e.g., "Grade 7", "Grade 10")
- **Section**: Class section or group (e.g., "Section A", "Einstein")

### Teacher Fields

- **Name**: Full name of the teacher/staff
- **Department**: Department or unit (e.g., "Science", "Mathematics")

### Faculty Fields

- **Name**: Full name of the requester
- **Affiliation**: Organization or lab (e.g., "Physics Lab", "Biology Dept")

## Data Loading

- Requester data loads asynchronously in a background thread
- A progress indicator displays during loading
- The table populates progressively as data becomes available
- Buttons are disabled during data load to prevent conflicts

## Usage in Reports

Requester type-specific fields enable specialized reporting:

- **Usage by Grade Level Report**: Groups consumption by grade level and section (students only)
- **Usage by Department Report**: Groups consumption by department (teachers only)
- **Activity Tracking**: Associates usage with specific requester types

## Key Components

- **Requesters Table**: Displays all registered requesters with columns:
  - Requisitions Count: Number of associated requisitions (determines delete eligibility)
  - Type: Student, Teacher, or Faculty
  - Name: Requester full name
  - Grade/Section or Department: Type-specific details
  - Affiliation: For faculty members
  - Created: Record creation timestamp

- **Add Requester Dialog**: Form for creating new requester records with type selection
- **Edit Requester Dialog**: Form for modifying existing requester records
- **Search Box**: Filters requesters by name, grade level, section, department, or affiliation

## Common Operations

### Adding a Requester

1. Click **Add Requester** button
2. Select the requester type from the dropdown (Student/Teacher/Faculty)
3. Fill the required fields based on type
4. Enter Editor Name (for audit trail)
5. Click **Save Requester**

### Editing a Requester

1. Select a requester row in the table
2. Click **Edit Requester** or double-click the row
3. Modify fields as needed (can also change requester type)
4. Enter Editor Name
5. Click **Save**

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
- Grade Level (partial match, case-insensitive)
- Section (partial match, case-insensitive)
- Department (partial match, case-insensitive)
- Affiliation (partial match, case-insensitive)

Results update instantly as you type.

## Validation Rules

| Rule | Behavior |
| ------ | ---------- |
| Required Fields | Name and type-specific fields are required based on requester type |
| Duplicate Check | Warning shown if requester with same name and type exists |
| Delete Protection | Cannot delete requesters with requisition history |
| Case Sensitivity | Search and display are case-insensitive; storage preserves input |

## Integration with Requisitions

Requesters are linked to requisitions through:

- **Requester Selection**: Available requesters appear in requisition creation dialog
- **Type Display**: Requester type shown alongside name for disambiguation
- **Type-Specific Fields**: Validation based on requester type during requisition creation
- **Requisition Count**: Displayed in requesters table
- **Audit Trail**: Requester creation/edits tracked in activity log

## Best Practices

1. **Use Consistent Naming**: Establish naming conventions for departments and affiliations
2. **Include Grade/Section**: For educational settings, always include grade level and section for students
3. **Regular Cleanup**: Remove obsolete requesters (no active requisitions) periodically
4. **Type Selection**: Choose the correct requester type to enable proper reporting

## Limitations

- Requester records are not a user authentication system
- No password or access control associated with requesters
- Cannot restore deleted requesters (consider deactivating instead)
- Requester deletion is permanent

## Related Documentation

- See `docs/requisitions.md` for requisition creation workflows
- See `docs/reports.md` for Usage by Grade Level and Department report details
- See `docs/architecture.md` for database schema (Requesters table)
