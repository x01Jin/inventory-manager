# Laboratory Inventory Manager — Instruction Manual

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Dashboard Overview](#dashboard-overview)
4. [Managing Inventory](#managing-inventory)
5. [Managing Requisitions](#managing-requisitions)
6. [Managing Requesters](#managing-requesters)
7. [Generating Reports](#generating-reports)
8. [Settings and Configuration](#settings-and-configuration)
9. [Data Management](#data-management)
10. [Troubleshooting](#troubleshooting)

---

## Introduction

The Laboratory Inventory Manager is a desktop application for tracking and managing laboratory inventory, requisitions, and usage. It provides:

- **Inventory Tracking**: Monitor items, batches, stock levels, and expiration/calibration dates
- **Requisition Management**: Create and track requests for laboratory materials
- **Reporting**: Generate Excel-based reports for usage, stock, and compliance
- **Activity Logging**: Maintain audit trails for all inventory changes

### Intended Users

- Laboratory managers and technicians
- Teachers and department heads
- Administrative staff responsible for inventory

### System Requirements

- Windows 10/11 (primary platform)
- Python 3.10+ (for development)
- 4GB RAM minimum
- 100MB disk space for application and database

---

## Getting Started

### Starting the Application

**Packaged Executable:**

1. Double-click `laboratory-inventory-manager-<version>.exe`
2. Wait for the application to initialize

**Python Source:**

```powershell
# Activate virtual environment
& .venv\Scripts\Activate.ps1

# Run application
python -m inventory_app.main
```

### First Run Setup

On first launch, the application:

1. Creates the SQLite database (`inventory.db`)
2. Initializes the `logs/` directory
3. Seeds default reference data (categories, suppliers, sizes, brands)
4. Displays the Dashboard

### Initial Configuration Checklist

1. **Add Suppliers** (Settings → Suppliers)
   - Default suppliers are pre-loaded
   - Add your laboratory's regular suppliers

2. **Add Sizes and Brands** (Settings)
   - Review and add common sizes for your items
   - Add brands you regularly use

3. **Add Requesters** (Requesters page)
   - Add teachers, departments, or groups
   - Include grade level and section for school settings

4. **Import or Add Inventory** (Inventory page)
   - Use Excel import for large initial inventory
   - Add critical items manually

---

## Dashboard Overview

The Dashboard is your operational command center, providing real-time visibility into system status.

### Understanding the Dashboard

**Key Metrics Grid (3×3):**

- **Total Items**: Number of distinct inventory items
- **Total Stock**: Aggregate quantity across all batches
- **Recent Adds**: Items modified in the last 7 days
- **Low Stock**: Items with 1-9 units remaining
- **Expiring Soon**: Items expiring/disposing within 30 days
- **Ongoing Reqs**: Active + Requested + Overdue requisitions
- **Requested Reqs**: Awaiting fulfillment
- **Active Reqs**: Currently checked out
- **Overdue Reqs**: Past expected return date

**Activity Panel:**

- Shows recent system events (item additions, requisitions, edits)
- Limited to ~20 most recent entries
- Click entries to navigate to related records

**Schedule Chart:**

- Upcoming requisitions (next 5-7 items)
- Shows requester, expected dates, and status
- Helps plan for returns and fulfillments

**Critical Alerts:**

- Items requiring immediate attention
- Color-coded: Red (Critical/Overdue), Yellow (Warning)
- Categories: Expired, Calibration Due, Low Stock

### Taking Action from the Dashboard

1. **See a low stock alert?**
   - Click the metric or navigate to Inventory
   - Use filters to identify affected items
   - Consider creating purchase requisitions

2. **See expiring items?**
   - Review the alert list for details
   - Plan usage or disposal
   - Update stock if items are already used

3. **See overdue requisitions?**
   - Contact the requester
   - Process returns promptly

---

## Managing Inventory

The Inventory page is where you view, add, edit, and manage all inventory items.

### Understanding Inventory Data

**Item Fields:**

- **Name**: Display name for the item
- **Category**: Classification (determines type and dates)
- **Stock**: Total/Available quantities
- **Size**: Container/package size
- **Brand**: Manufacturer or brand
- **Supplier**: Where the item was purchased
- **Expiration/Disposal Date**: When item expires or should be disposed
- **Calibration Date**: For equipment requiring calibration
- **Acquisition Date**: When item was received
- **Last Modified**: When item was last edited

**Stock Calculations:**

- **Total Stock** = Received - Consumed - Disposed + Returned
- **Available Stock** = Total Stock - Active Reservations

### Adding New Items

1. Click **+ Add Item**
2. Fill required fields:
   - **Name**: Descriptive item name
   - **Category**: Select from predefined list
   - **Batch Quantity**: Initial quantity (default: 1)
3. Optional fields:
   - Supplier, Size, Brand, PO Number
   - Other Specifications (notes, model numbers)
4. Review auto-calculated dates:
   - Consumables: Expiration set based on category
   - Non-consumables: Disposal and Calibration dates
5. Enter Editor Name
6. Click **Save**

### Editing Items

1. Select item row
2. Click **Edit Item** or double-click
3. Modify fields as needed
4. Enter Editor Name and Reason
5. Click **Save**

### Deleting Items

1. Select item row
2. Click **Delete Item**
3. Confirm deletion
4. Enter Editor Name and Reason
5. Click **Delete**

**Note:** Cannot delete items with requisition history.

### Importing Items from Excel

1. Click **Import Items**
2. Select `.xlsx` file
3. Enter Editor Name
4. Click **Import**
5. Review import summary

**Required Columns:**

- `name` (or `item`, `items`, `item name`)
- `stocks` (quantity)
- `item type` (`Consumable` or `Non-Consumable`)

**Optional Columns:**

- `category`, `size`, `brand`, `supplier`
- `other specifications`, `po number`
- `expiration date`, `calibration date`, `acquisition date`

### Filtering and Searching

**Search Box:**

- Searches name, category, and supplier
- Case-insensitive substring match

**Category Filter:**

- Show items in specific category
- "All Categories" shows everything

**Supplier Filter:**

- Show items from specific supplier
- "All Suppliers" shows everything

### Understanding Color Coding

**Row Background Colors:**

| Color | Meaning | Threshold |
| ------- | --------- | ----------- |
| **Red/Pink** | Overdue/Expired | Date has passed |
| **Yellow** | Warning | Within 30-90 days of deadline |
| **Default** | Normal | No immediate action needed |

**Example:**

- Chemical with 6-month shelf life: Yellow at 5 months, Red at 7 months
- Equipment calibration: Yellow at 11 months, Red at 13 months

---

## Managing Requisitions

Requisitions track the borrowing and return of inventory items for laboratory activities.

### Requisition Lifecycle

```flow
Requested → Active → Returned (Final)
                 → Overdue (if not returned on time)
```

**Status Meanings:**

- **Requested**: Reservation created, awaiting pickup
- **Active**: Items checked out, in use
- **Overdue**: Past expected return date
- **Returned**: Finalized, items accounted for

### Creating a Requisition

1. Click **+ New Requisition**
2. **Select Requester**: Choose from registered requesters
3. **Add Items**: Search and select items with quantities
4. **Activity Details**:
   - Activity Name (required): Description of the lab activity
   - Activity Date (required): When the activity occurs
   - Description: Additional notes
   - Students/Groups: Number of participants
5. **Schedule**:
   - Expected Request: When items will be picked up
   - Expected Return: When items will be returned
6. Enter Editor Name
7. Click **Create Requisition**

**Validation:**

- System checks stock availability
- Items are reserved atomically
- Insufficient stock prevents creation

### Editing a Requisition

1. Select requisition (cannot be Returned)
2. Click **Edit Requisition**
3. Modify fields as needed
4. Enter Editor Name
5. Click **Save**

### Processing Returns

1. Select Active or Overdue requisition
2. Click **Return Items**
3. **Important**: This is final and irreversible
4. For each item:
   - **Consumables**: Enter quantity returned unused
   - **Non-Consumables**: Enter returned, lost, and defective quantities
5. For defective items, add condition and notes
6. Enter Editor Name
7. Click **Process Returns**

**Return Summary:**

- Consumables returned = Available again
- Consumables consumed = Permanently removed
- Non-consumables returned = Available for next requisition
- Non-consumables lost = Removed from stock
- Defective items = Tracked for replacement/repair

### Printing Requisitions

1. Select requisition
2. Click **Print**
3. Choose save location for HTML file
4. Open in browser and print (Ctrl+P)
5. Save as PDF if needed

### Deleting Requisitions

1. Select requisition (cannot be Returned)
2. Click **Delete Requisition**
3. Confirm deletion
4. Enter Editor Name
5. Click **Delete**

---

## Managing Requesters

Requesters are personnel authorized to create requisitions.

### Adding Requesters

1. Click **+ Add Requester**
2. Fill fields:
   - **Name**: Full name
   - **Affiliation**: Department, role, or grade
   - **Group**: Class, team, or section
   - **Grade Level**: Educational level (optional)
   - **Section**: Section identifier (optional)
3. Enter Editor Name
4. Click **Save**

### Using Grade Level and Section

These fields enable "Usage by Grade Level" reports:

- Track consumption by educational level
- Analyze usage patterns by class section
- Generate compliance reports by grade

### Editing Requesters

1. Select requester
2. Click **Edit Requester**
3. Modify fields
4. Enter Editor Name
5. Click **Save**

### Deleting Requesters

1. Select requester with **0 requisitions**
2. Click **Delete Requester**
3. Confirm deletion
4. Enter Editor Name
5. Click **Delete**

**Cannot delete** requesters with requisition history.

---

## Generating Reports

The Reports page generates Excel-compatible exports for analysis and auditing.

### Report Types

**Usage Reports:**

- **Monthly Usage**: Category-grouped weekly breakdown
- **Date Range Usage**: Flexible time-series by day/week/month/quarter

**Inventory Reports:**

- Stock Levels
- Expiration Report
- Calibration Due
- Low Stock Alert
- Update History
- Disposal History
- Usage by Grade Level
- Defective Items

**Trends Reports:**

- Time-series analysis grouped by item or category

### Creating a Report

1. Select report tab (Usage/Inventory/Trends)
2. Choose specific report type
3. Configure options:
   - Date range (manual or presets)
   - Category/Supplier filters
   - Report-specific settings
4. Click **Generate Report**
5. Excel file saves and may open automatically

### Understanding Report Output

**File Naming:**

- Monthly Usage: `monthly_usage_report_[MONTH]_YYYYMMDD_HHMMSS.xlsx`
- Date Range: `usage_report_[granularity]_YYYYMMDD_HHMMSS.xlsx`
- Inventory: `inventory_[report_type]_YYYYMMDD_HHMMSS.xlsx`

**Features:**

- Formatted headers with bold styling
- Auto-filter enabled on headers
- Frozen header rows
- Numeric formatting for quantities

### Common Report Tasks

**Monthly Usage Report:**

1. Select Usage Reports → Monthly Usage
2. Choose Year and Month
3. (Optional) Filter by Category
4. Generate

**Low Stock Alert:**

1. Select Inventory Reports → Low Stock Alert
2. (Optional) Toggle absolute/percentage threshold
3. Generate

**Usage by Grade Level:**

1. Select Inventory Reports → Usage by Grade Level
2. Set date range
3. Generate

---

## Settings and Configuration

The Settings page manages reference data used throughout the application.

### Understanding Settings Tabs

**Categories (View Only):**
Predefined categories with built-in thresholds:

| Category | Type | Threshold |
| ------- | ------ | ----------- |
| Chemicals-Solid | Consumable | 2 years expiry |
| Chemicals-Liquid | Consumable | 2 years expiry |
| Prepared Slides | Consumable | 3 years expiry |
| Consumables | Consumable | 1 year expiry |
| Equipment | Non-Consumable | 5 years disposal, Yearly calibration |
| Apparatus | Non-Consumable | 3 years disposal |
| Lab Models | Non-Consumable | 5 years disposal |
| Others | Non-Consumable | 5 years disposal |
| Uncategorized | Non-Consumable | No threshold |

**Sizes:**

- Free-form text values for item sizes
- Used in Inventory dropdown and reporting

**Brands:**

- Free-form text for manufacturer names
- Used in Inventory dropdown and reporting

**Suppliers:**

- Stored as database records
- Referenced from Items
- Can be force-deleted (nullifies references)

### Adding Settings Values

1. Select appropriate tab
2. Click **Add [Type]**
3. Enter name
4. Click **OK**

### Editing Settings Values

1. Select value
2. Click **Edit [Type]**
3. Modify name
4. Click **OK**

**Note:** Renaming preserves references on existing items.

### Deleting Settings Values

**Sizes/Brands:**

- Cannot delete if in use by items
- Delete blocked with error message

**Suppliers:**

- Cannot delete while items reference them
- Force-delete option: removes references (sets to null)

---

## Data Management

### Backup and Restore

**Manual Backup:**

1. Close the application
2. Copy `inventory.db` to backup location
3. Optionally copy `logs/logs.txt`
4. Restart application

**Restore:**

1. Close application
2. Rename/delete current `inventory.db`
3. Copy backup to `inventory.db`
4. Restart application

**Backup Schedule Recommendation:**

- Daily backups for active use
- Weekly backups for low-activity periods
- Keep multiple backup versions

### Data Retention

**Activity Log:**

- Auto-deleted after 90 days
- Maximum 20 entries retained
- Managed by database triggers

**Historical Data:**

- Items remain in database even at 0 stock
- Disposal history preserved
- Requisition history preserved

### Exporting Data

**Via Reports:**

- Use Reports page for formatted Excel exports
- Export specific date ranges
- Filter by category/supplier

**Via Database:**

- Use SQLite tools to query `inventory.db`
- Export to CSV for further processing
- Requires SQL knowledge

---

## Troubleshooting

### Common Issues

**Application Won't Start:**

- Check `logs/logs.txt` for errors
- Ensure PyQt6 is installed
- Verify virtual environment activated
- Check for another running instance

**Data Won't Load:**

- Click Refresh to retry
- Restart application
- Check database file integrity
- Review logs for specific errors

**Import Fails:**

- Verify Excel file format (.xlsx)
- Check required columns present
- Ensure file not open in Excel
- Review logs for row-specific errors

**Report Generation Fails:**

- Check disk space
- Verify write permissions
- Close open Excel files
- Widen date range if "no data found"

**Cannot Delete Item/Requester:**

- Item has requisition history → Cannot delete
- Requester has requisitions → Cannot delete
- Size/Brand in use → Cannot delete

### Getting Help

**Before Contacting Support:**

1. Note the exact error message
2. Note the action you were performing
3. Note the time of occurrence
4. Gather relevant logs

**Contact Information:**

- Open issue on GitHub repository
- Include `logs/logs.txt` with issue description
- Describe expected vs actual behavior

### Log File Location

Logs are in: `logs/logs.txt`

Include relevant log excerpts when reporting issues.

---

## Quick Reference

### Navigation

| Page | Purpose | Key Actions |
| ------- | --------- | ----------- |
| Dashboard | System overview | View metrics, alerts, schedule |
| Inventory | Item management | Add, edit, delete, import items |
| Requisitions | Borrowing workflow | Create, edit, return, print |
| Requesters | Personnel management | Add, edit, delete requesters |
| Reports | Exports and analysis | Generate usage, inventory reports |
| Settings | Reference data | Manage sizes, brands, suppliers |
| Help | Documentation | Contextual help and guides |

### Keyboard Shortcuts

- **Ctrl+F**: Focus search box (where available)
- **Ctrl+P**: Print (in requisition preview)
- **F5**: Refresh current page
- **Double-click**: Edit selected item/requisition

### Common Terms

| Term | Definition |
| ------- | ------------ |
| Batch | A received quantity of items with same characteristics |
| Consumable | Item consumed when used (stock decreases permanently) |
| Non-Consumable | Item returned after use (stock maintained) |
| Reservation | Stock held for a pending requisition |
| Movement | Any change to stock (consumption, return, disposal) |
| Calibration | Periodic equipment verification |

---

## Support

For bugs, feature requests, or questions:

- Open an issue on GitHub: <https://github.com/x01Jin/inventory-manager/issues>
- Check existing issues first
- Include relevant logs and error messages

For documentation feedback:

- Submit issues with "documentation" label
- Suggest improvements or corrections

---

*Last updated: January 2026*
*Version: 1.0*
