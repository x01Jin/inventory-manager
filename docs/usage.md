# Usage Guide

## Quick Start

1. **Activate your virtual environment** (see installation docs for details)
2. **Run the application**: `python -m inventory_app.main`
3. The database initializes automatically on first run
4. The GUI launches with the Dashboard as the landing page

## User Interface Overview

The application uses a left-navigation sidebar with the following pages:

### Dashboard

The landing page providing real-time metrics, activity feed, schedule chart, and critical alerts. Use this for quick system status checks.

### Inventory

Core inventory management page displaying all items with:

- Table view with sortable columns (Stock, Name, Category, Supplier, Dates)
- Search and filter controls (Category, Supplier)
- Add/Edit/Delete item operations
- Bulk import from Excel
- Quick statistics panel

### Requisitions

Full requisition lifecycle management:

- Create new requisitions with requester and item selection
- Track requisition status (Requested → Active → Returned/Overdue)
- Process returns with consumable/lost/defective tracking
- Print requisition receipts
- Filter by requester, status, and date range

### Requesters

Personnel management for requisition creation:

- Add/Edit/Delete registered requesters
- Track requester affiliations and groups
- View requisition counts per requester

### Reports

Generate Excel-based reports for analysis and auditing:

- **Usage Reports**: Monthly and date-range usage with category grouping
- **Inventory Reports**: Stock levels, expiration, calibration, update/disposal history
- **Trends Reports**: Time-series analysis by item or category
- **Usage by Grade Level**: Educational tracking across grade levels

### Settings

Reference data management:

- **Sizes**: Manage item size options (e.g., 250mL, 1L)
- **Brands**: Manage brand options
- **Suppliers**: Manage supplier list with force-delete option
- **Categories**: View-only display of predefined categories and thresholds

### Help

Contextual documentation including this guide and troubleshooting.

## Common Workflows

### Adding a New Item

1. Navigate to **Inventory** page
2. Click **Add Item** button
3. Fill required fields:
   - **Name**: Item display name
   - **Category**: Select from predefined categories (determines type and dates)
   - **Batch Quantity**: Number of units in initial batch
4. Optional fields:
   - **Supplier**: Select from existing suppliers
   - **Size**: Select or type size value
   - **Brand**: Select or type brand value
   - **PO Number**: Purchase order reference
   - **Other Specifications**: Additional details
   - **Acquisition Date**: Defaults to today
5. Review auto-calculated dates (expiration/disposal/calibration)
6. Enter Editor Name (required for audit)
7. Click **Save**

**Auto-Date Calculation:**

- Consumables: Expiration = Acquisition + category-specific months
- Non-consumables: Disposal = Acquisition + category-specific years
- Equipment: Calibration = Acquisition + 1 year

### Creating a Requisition

1. Navigate to **Requisitions** page
2. Click **New Requisition**
3. **Select Requester**: Choose from registered requesters
4. **Add Items**: Search and select items with quantities
5. **Activity Details**:
   - Activity Name (required)
   - Activity Date (required)
   - Description (optional)
   - Number of Students/Groups
6. **Schedule**:
   - Expected Request datetime
   - Expected Return datetime
7. Enter Editor Name
8. Click **Create Requisition**

The system validates stock availability and reserves items atomically.

### Processing Returns

1. Select a requisition with status **Active** or **Overdue**
2. Click **Return Items**
3. For each requested item:
   - **Consumables**: Enter quantity returned unused (remainder = consumed)
   - **Non-Consumables**: Enter returned, lost, and defective quantities
4. For defective items, add condition type and notes
5. Confirm and process (this is final - requisition becomes locked)

### Generating Reports

1. Navigate to **Reports** page
2. Select report type tab (Usage, Inventory, or Trends)
3. Configure options:
   - Date range (manual or presets)
   - Category/Supplier filters
   - Report-specific options
4. Click **Generate Report**
5. Excel file is saved and may open automatically

### Importing Items from Excel

1. Navigate to **Inventory** page
2. Click **Import Items**
3. Select `.xlsx` file
4. Enter Editor Name
5. Click **Import**
6. Monitor progress bar
7. Review import summary (imported/skipped counts)

**Required Columns:** `name`, `stocks`, `item type`
**Optional Columns:** `category`, `size`, `brand`, `supplier`, etc.

## Navigation Shortcuts

- **Double-click** table rows to open edit dialogs
- **Search boxes** provide instant filtering
- **Tooltips** explain button states and disabled controls
- **Refresh buttons** reload data from database
- **Clear filters** resets search and filter controls

## Data Entry Requirements

### Required Editor Name

Most write operations require an Editor Name for audit purposes:

- Adding/editing/deleting items
- Creating/editing/deleting requisitions
- Adding/editing/deleting requesters
- Processing returns

The editor name is recorded in history tables and activity logs.

### Required Fields by Operation

| Operation | Required Fields |
| ----------- | ---------------- |
| Add Item | Name, Category, Batch Quantity, Editor |
| Edit Item | Changed fields, Editor |
| Delete Item | Editor, Reason |
| New Requisition | Requester, Items (1+), Activity Name, Activity Date, Expected Request, Expected Return, Editor |
| Return Items | Return quantities, Editor |
| Add Requester | Name, Affiliation, Group, Editor |
| Edit Requester | Changed fields, Editor |
| Delete Requester | Editor |

## Status Indicators

### Requisition Status Colors

- **Requested** (Yellow/Warning): Awaiting fulfillment
- **Active** (Green/Success): Items checked out
- **Overdue** (Red/Error): Past expected return date
- **Returned** (Blue/Neutral): Finalized and locked

### Inventory Row Colors

- **Red/Pink (Overdue)**: Expired, disposal overdue, or calibration overdue
- **Yellow (Warning)**: Expiring/disposing/calibrating within threshold period
- **Default**: No immediate attention needed

### Alert Severity

- **Critical**: Already past deadline (expired, overdue calibration, etc.)
- **Warning**: Approaching deadline (within 30/90 days depending on type)
- **Info**: Informational status

## Best Practices

1. **Regular Backups**: Copy `inventory.db` regularly
2. **Review Alerts**: Check Dashboard daily for expiring/calibration items
3. **Process Returns Promptly**: Return requisitions on time to avoid overdue status
4. **Use Reports**: Generate monthly usage reports for inventory planning
5. **Document Edits**: Always provide meaningful edit reasons
6. **Maintain Requesters**: Keep requester records up-to-date with current groups/sections

## First-Time Setup Checklist

- [ ] Run application to initialize database
- [ ] Add initial suppliers (Settings → Suppliers)
- [ ] Add initial sizes and brands (Settings)
- [ ] Import existing inventory items or add manually
- [ ] Add requesters (teachers, students, departments)
- [ ] Generate a test report to verify functionality
- [ ] Review Dashboard and alerts
- [ ] Configure backup schedule for `inventory.db`
