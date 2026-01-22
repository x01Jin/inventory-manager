# Laboratory Inventory Manager — Instruction Manual

## System Requirements

- Windows 10/11 (primary platform)
- 4GB RAM minimum
- 100MB disk space for application and database

---

## Getting Started

### Starting the Application

**Packaged Executable:**

1. Double-click `laboratory-inventory-manager-<version>.exe`
2. Wait for the application to initialize

### First Run Setup

On first launch, the application:

1. Creates the SQLite database (`inventory.db`)
2. Initializes the `logs/` directory
3. Seeds default reference data (categories, suppliers, sizes, brands)
4. Displays the Dashboard

### From this point on Please Read the HELP page in the system

- Read it pleaseeeee.

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
*Version: 2.0*
