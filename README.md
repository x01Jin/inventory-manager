# Inventory Manager

Inventory Manager is a Python-based system for streamlined inventory tracking and management. Designed for efficiency, it allows users to monitor, update, and audit inventory levels with precision and speed.

## Features

### Dashboard

The dashboard serves as the central hub of the Inventory Manager application, providing a comprehensive at-a-glance view of key inventory metrics, recent activities, alerts, and scheduling information. It's designed with a clean, compact layout using a 2x2 grid system for optimal space utilization.

#### Key Metrics Section
This section displays 9 critical inventory metrics in a compact 3x3 grid of metric cards:

- **📦 Total Items**: Shows the complete count of all items in the inventory database
- **📊 Total Stock**: Displays the current total stock across all items, calculated by summing received quantities minus consumed, disposed, and adding returned quantities
- **🆕 Recent Adds**: Counts items added or modified within the last 7 days
- **⚠️ Low Stock**: Identifies items with current stock levels below 10 units but above 0
- **⏰ Expiring Soon**: Counts items with expiration dates within the next 30 days
- **📋 Ongoing Reqs**: Total count of requisitions with status 'requested', 'active', or 'overdue'
- **📝 Requested Reqs**: Number of requisitions currently in 'requested' status
- **🔄 Active Reqs**: Count of requisitions in 'active' status
- **🚨 Overdue Reqs**: Number of requisitions marked as 'overdue'

Each metric card is styled with a dark theme, bold values, and minimal padding for a professional, condensed appearance.

#### Recent Activity Section
This section tracks system activities in two parts:

- **Latest Activity Table**: Displays the most recent single activity with columns for Description, User, and Time
- **Activity History Table**: Shows the previous 50 activities in a scrollable format

Activities are displayed with word-wrapping descriptions, user information, and formatted timestamps. The tables use alternating row colors, compact styling with 8pt font, and tooltips for full descriptions on hover.

#### Schedule Chart Section
This section displays scheduling information in a table format, providing an overview of inventory-related schedules and timelines.

#### Critical Alerts Section
This section displays important system alerts in a table format, including stock warnings, expiration notices, and requisition alerts. While the alert system could be enhanced, it currently provides essential notifications for inventory management.

#### Technical Features
- **Real-time Updates**: All sections refresh data dynamically through dedicated manager classes
- **Responsive Layout**: Uses QGridLayout with equal column/row stretches for balanced sizing
- **Dark Theme Integration**: Consistent styling with the application's dark theme, including custom fonts and colors
- **Compact Design**: Reduced margins (10px), spacing (10px), and component sizes for efficient screen usage
- **Error Handling**: Comprehensive logging for failed data refreshes with fallback to default values
- **Database Integration**: Direct queries to SQLite database for metrics calculation and activity retrieval

The dashboard emphasizes quick access to critical information while maintaining a clean, professional interface suitable for laboratory inventory management.

### Inventory

The Inventory page provides a comprehensive interface for managing laboratory inventory items with advanced features for tracking, searching, and maintaining stock levels.

#### Core Interface
- **Header Section**: Title "📦 Inventory" with action buttons (Add Item, Edit Item, Delete Item, Refresh)
- **Layout**: Vertical splitter design with top section for filters/stats and bottom for inventory table
- **Styling**: Dark theme integration with responsive design and proper spacing

#### Inventory Table
- **Columns**: Stock/Available, Name, Category, Size, Brand, Supplier, Expiration Date, Calibration Date, Acquisition Date, Consumable, Last Modified, Alert Status
- **Functionality**:
  - Sortable on all columns
  - Row selection with alternating colors
  - Double-click to edit items
  - Automatic column resizing
- **Visual Indicators**:
  - Stock status styling: Red for out of stock, yellow for partial availability, green for fully available
  - Alert indicators: Red dots for expiration alerts, yellow for calibration alerts
  - Alert status column with "expiration", "calibration", or "None"

#### Search & Filtering
- **Search Bar**: Real-time search by item name, category, or supplier
- **Category Filter**: Dropdown with all available categories
- **Supplier Filter**: Dropdown with all available suppliers
- **Clear Filters**: Button to reset all filters instantly
- **Dynamic Updates**: Table updates immediately as filters change

#### Statistics Dashboard
- **Total Batches**: Count of all item batches
- **Total Stock**: Sum of all stock across items
- **Available Stock**: Total stock minus requested quantities
- **Total Alerts**: Count of items with active alerts
- **Expiring Alerts**: Items expiring within 6 months
- **Calibration Alerts**: Items due for calibration within 12 months

#### Item Management
- **Add Item**: Comprehensive form with:
  - Basic info: Name, Category, Supplier, Size, Brand
  - Specifications: PO Number, Other Specifications, Batch Quantity
  - Dates: Acquisition, Expiration, Calibration
  - Status: Consumable checkbox
  - Editor name (required for audit trail)
- **Edit Item**: Same form pre-populated with existing data
- **Delete Item**: Confirmation dialog with reason logging and editor name
- **Validation**: Required fields validation and error messages

#### Alert System
- **Expiration Alerts**: Items expiring within 6 months
- **Calibration Alerts**: Items needing calibration 12+ months after last calibration
- **Alert Detection**: Automatic calculation based on current date
- **Visual Alerts**: Color-coded rows and indicator dots in table

#### Data Management
- **Stock Calculations**:
  - Total Stock = Received - Consumed - Disposed + Returned
  - Available Stock = Total Stock - Active Requisitions
- **Real-time Refresh**: Button to reload all data from database
- **Database Integration**: Direct SQLite queries with error handling
- **Audit Trail**: Editor names logged for all changes (Spec #14)

#### Technical Features
- **Composition Pattern**: Modular components (table, filters, stats, controller)
- **Signal/Slot System**: Proper component communication
- **Error Handling**: Comprehensive logging and user-friendly error messages
- **Performance**: Efficient queries with JOINs for related data
- **Data Persistence**: All changes saved to SQLite database

The inventory page provides a complete inventory management interface with advanced filtering, real-time statistics, comprehensive item editing, and robust alert system for laboratory inventory tracking.

### Requisitions

The Requisitions page is a comprehensive laboratory requesting system that provides full CRUD operations for managing inventory requisitions with advanced filtering, detailed preview, and complete workflow management.

#### Main Interface Layout
- **Header Section**: Displays "📋 Laboratory Requisitions" title with a 🔄 Refresh button for real-time data updates
- **Action Buttons Row**: Four main action buttons:
  - ➕ New Requisition: Creates new laboratory requests
  - ✏️ Edit Requisition: Modifies existing requisitions
  - ↩️ Return Items: Processes item returns from requisitions
  - 🗑️ Delete Requisition: Removes requisitions with confirmation
- **Layout Design**: Horizontal splitter dividing the interface into left panel (filters + table) and right panel (preview details)
- **Status Bar**: Shows real-time statistics including total, active, returned, and overdue requisition counts

#### Requisitions Table
- **Three-Column Display**:
  - **Status Column**: Shows requisition status with color coding:
    - 🔸 Active: Light yellow background (#FFF3CD) with dark yellow text
    - 🔹 Returned: Light blue background (#D1ECF1) with dark blue text
    - 🔺 Overdue: Light red background (#F8D7DA) with dark red text
  - **Requester Column**: Displays requester name with word wrapping support
  - **Requested Date Column**: Shows actual request datetime or "Reserved" for pending requests
- **Interactive Features**:
  - Sortable on all columns
  - Single row selection with alternating row colors
  - Double-click to edit selected requisition
  - Automatic column resizing with constraints (fixed widths for status/date, interactive for requester)

#### Advanced Filtering System
- **Search Functionality**: Real-time search across:
  - Requester names
  - Activity descriptions
  - Item names in requests
- **Requester Filter**: Dropdown populated with all requesters who have active requisitions
- **Status Filter**: Options for All Statuses, Active, Returned, Overdue
- **Date Range Filter**: From/To date selectors with calendar popup for filtering by activity dates
- **Clear Filters Button**: Instantly resets all filters to show complete dataset
- **Filter Summary**: Dynamic display showing "X of Y requisitions" with percentage when filtered

#### Detailed Preview Panel
- **Status Section**: Prominent status display with color-coded indicators at the top
- **Requester Information**: Complete requester details including name, affiliation, and group
- **Timeline Section**: Comprehensive date tracking:
  - Expected Request datetime
  - Actual Requested datetime (highlighted in green when processed)
  - Expected Return datetime
- **Activity Details**:
  - Activity name and description
  - Activity date
  - Number of students and groups
- **Requested Items List**: Shows all items with quantities requested
- **Return Details** (for processed requisitions):
  - ✅ Consumables Returned: Items returned to inventory
  - 🔥 Consumables Consumed: Items used up during activity
  - ↩️ Non-Consumables Returned: Equipment returned
  - ❌ Non-Consumables Lost/Damaged: Equipment not returned or damaged
  - 📊 Summary totals with counts for each category

#### Requisition Creation (New Requisition Dialog)
- **Requester Selection**: Interactive requester picker with search/filter capabilities
- **Activity Details**:
  - Activity name (required)
  - Activity description (optional)
  - Activity date selector
  - Number of students/groups (optional)
- **Item Selection**: Comprehensive item picker with:
  - Category filtering
  - Search functionality
  - Stock availability checking
  - Quantity selection
- **Scheduling**: Request and return time selectors with validation
- **Validation**: Ensures all required fields and logical constraints are met
- **Stock Movement**: Automatic stock reservation upon creation

#### Requisition Editing (Edit Requisition Dialog)
- **Full Edit Capability**: All fields editable, allowing complete requisition modification
- **Requester Reassignment**: Change requester if needed
- **Item Modification**: Add/remove/modify requested items with stock validation
- **Schedule Updates**: Modify request and return times
- **Activity Updates**: Change activity details and dates
- **Stock Reconciliation**: Updates stock movements to reflect changes

#### Item Return Processing (Return Items Dialog)
- **Selective Returns**: Process partial or complete returns
- **Item Categorization**:
  - Consumables: Mark as returned or consumed
  - Non-consumables: Mark as returned, lost, or damaged
- **Quantity Tracking**: Specify exact quantities for each return type
- **Validation**: Ensures return quantities don't exceed requested amounts
- **Status Updates**: Automatically updates requisition status based on return completion

#### Data Management Features
- **Real-time Refresh**: Updates all data from database with status recalculation
- **Automatic Status Updates**: Background process updates overdue and active statuses
- **Audit Trail**: Logs all changes with editor names and timestamps
- **Stock Integration**: Real-time stock level checking and movement tracking
- **Error Handling**: Comprehensive error messages and fallback displays
- **Performance Optimization**: Efficient database queries with proper indexing

#### Security and Validation
- **Editor Name Requirement**: All changes require editor identification for audit trail
- **Data Validation**: Prevents invalid dates, negative quantities, and logical inconsistencies
- **Status Protection**: Returned requisitions are locked from editing
- **Confirmation Dialogs**: Delete operations require explicit confirmation
- **Activity Logging**: All operations logged to activity system

The requisitions system provides a complete laboratory inventory requesting workflow with professional-grade features for managing the entire lifecycle of inventory requisitions from creation through return processing.

### Requesters

The Requesters page is a dedicated interface for managing laboratory personnel who can make inventory requisitions. It provides comprehensive CRUD operations for requester management with advanced filtering, detailed requester information display, and integration with the requisition system.

#### Main Interface Layout
- **Header Section**: Displays "👥 Laboratory Requesters" title with a 🔄 Refresh button for real-time data updates
- **Action Buttons Row**: Three main action buttons:
  - ➕ Add Requester: Creates new laboratory personnel records
  - ✏️ Edit Requester: Modifies existing requester information
  - 🗑️ Delete Requester: Removes requesters (disabled if they have active requisitions)
- **Layout Design**: Vertical layout with header, action buttons, search/filter section, and main content area
- **Status Bar**: Shows real-time statistics including total requester count

#### Requesters Table
- **Five-Column Display**:
  - **Requisitions Column**: Shows the count of requisitions associated with each requester
  - **Name Column**: Displays requester's full name with selection capability
  - **Affiliation Column**: Shows requester's affiliation (grade/section or department)
  - **Group Column**: Displays group name (class group or team)
  - **Created Column**: Shows creation date and time in formatted display
- **Interactive Features**:
  - Sortable on all columns for easy organization
  - Single row selection with alternating row colors
  - Double-click to edit selected requester
  - Automatic column resizing with predefined widths

#### Advanced Search and Filtering
- **Real-time Search**: Instant filtering by name, affiliation, or group as you type
- **Search Input Field**: Placeholder text guides users on search capabilities
- **Clear Search Button**: Instantly resets search filter to show all requesters
- **Dynamic Filtering**: Table updates immediately as search terms change
- **Visual Feedback**: Search input highlights when filter is active

#### Requester Management Features
- **Add Requester Dialog**: Comprehensive form with:
  - Full Name (required field)
  - Affiliation (required, e.g., grade/section or department)
  - Group Name (required, e.g., class group or team name)
  - Editor Name/Initials (required for audit trail - Spec #14)
- **Edit Requester Dialog**: Pre-populated form with existing data for modifications
- **Delete Requester**: Confirmation dialog with:
  - Prevention of deletion if requester has associated requisitions
  - Editor name requirement for audit trail
  - Confirmation message with requester details
- **Duplicate Prevention**: Warns users when creating requesters with identical details

#### Requester Selector Integration
- **Selection Dialog**: Separate interface for choosing requesters during requisition creation
- **Search Functionality**: Find requesters by name, affiliation, or group
- **Filter Options**: Option to hide requesters with no requisitions
- **Table Display**: Four-column view optimized for selection workflow
- **Selection Confirmation**: Clear display of selected requester before confirmation

#### Data Management and Validation
- **Real-time Data Refresh**: Button to reload all requester data from database
- **Automatic Filtering**: Search terms applied instantly to table display
- **Database Integration**: Direct SQLite queries with error handling
- **Audit Trail**: Editor names logged for all modifications (Spec #14)
- **Error Handling**: Comprehensive error messages and user-friendly notifications
- **Validation Checks**: Required field validation and logical constraint enforcement

#### Technical Features
- **Composition Pattern**: Modular components (page, table, model, editor) for maintainability
- **Signal/Slot System**: Proper component communication for responsive UI updates
- **Database Constraints**: Prevents deletion of requesters with active requisitions
- **Performance Optimization**: Efficient queries with proper filtering and indexing
- **Data Persistence**: All changes saved to SQLite database with transaction safety
- **Activity Logging**: Integration with requesters activity manager for audit logging

The requesters management system provides a complete workflow for laboratory personnel management with professional-grade features for maintaining accurate requester information and ensuring proper audit trails for all inventory requisition activities.

### Report

The Report page is a comprehensive reporting system designed for generating detailed laboratory inventory usage and inventory reports. It provides multiple report types with advanced filtering, date range selection, and automatic Excel export functionality. The page features a modern, user-friendly interface with real-time progress updates and background processing to ensure smooth operation.

#### Main Interface Layout
- **Header Section**: Displays "📊 Reports" title with a 🔄 Refresh button for data updates
- **Tabbed Report Types**: Four main report categories organized in tabs:
  - 📈 Usage Reports: Dynamic usage analysis based on requisition data
  - 📦 Inventory Reports: Comprehensive inventory status and history reports
  - 📋 Requisition Reports: Requisition-based analytics (coming soon)
  - 📊 Statistics: Advanced statistical analysis (coming soon)
- **Split-Panel Layout**: Left panel for configuration, right panel for status and results
- **Progress Tracking**: Real-time progress bar and status updates during report generation
- **Results Management**: Generated reports list and recent reports history

#### Usage Reports Tab
The Usage Reports tab generates dynamic Excel reports showing item usage patterns across specified date ranges with automatic granularity selection.

##### Date Range Configuration
- **Date Range Selector**: Interactive calendar widget for start and end date selection
- **Preset Options**: Quick-select buttons for common ranges:
  - Last 7 Days
  - Last 30 Days
  - Last 90 Days
  - This Month
  - Last Month
  - This Year
  - Last Year
- **Custom Range**: Manual date selection for any period
- **Automatic Granularity**: Smart detection of optimal time breakdown:
  - Daily: ≤7 days
  - Weekly: 8-30 days
  - Monthly: 31-180 days
  - Quarterly: 181-365 days
  - Yearly: 366-730 days
  - Multi-year: >730 days

##### Filtering Options
- **Category Filter**: Dropdown populated with all available item categories
- **Supplier Filter**: Dropdown with all item suppliers
- **Consumables Toggle**: Checkbox to include/exclude consumable items
- **Real-time Updates**: Filters apply instantly without additional processing

##### Report Structure
- **Item Details**: Name, category, size, brand, specifications
- **Stock Information**: Current inventory levels
- **Usage Columns**: Dynamic period columns showing usage by selected granularity
- **Total Quantity**: Sum of all usage across the report period
- **Excel Formatting**: Professional styling with headers, borders, and auto-sized columns

#### Inventory Reports Tab
The Inventory Reports tab provides various inventory-specific reports with detailed item information and status tracking.

##### Report Types
- **Stock Levels Report**: Current stock quantities for all items
- **Expiration Report**: Items expiring within specified date range
- **Low Stock Alert**: Items with stock levels below 10 units
- **Acquisition History**: Item acquisition records within date range
- **Calibration Due Report**: Items requiring calibration within date range

##### Configuration Options
- **Date Range**: Applicable for history and expiration reports
- **Category Filter**: Limit reports to specific item categories
- **Automatic Data Retrieval**: Direct database queries for real-time accuracy

##### Report Contents
- **Item Information**: Name, category, size, brand, specifications
- **Stock Data**: Current stock, received quantities, movement history
- **Date Information**: Acquisition dates, expiration dates, calibration dates
- **Status Indicators**: Stock levels, alert statuses, expiration warnings

#### Requisition Reports Tab
- **Coming Soon**: Advanced requisition analytics including:
  - Requisition Summary
  - Requester Analysis
  - Activity Patterns
  - Overdue Items
  - Return History

#### Statistics Tab
- **Coming Soon**: Statistical analysis including:
  - Usage Statistics
  - Top Items Report
  - Category Analysis
  - Monthly Trends
  - Yearly Summary

#### Technical Features
- **Background Processing**: Multi-threaded report generation to prevent UI freezing
- **Excel Export**: Automatic Excel file creation with professional formatting
- **Real-time Status**: Live progress updates and generation status
- **Error Handling**: Comprehensive error messages and fallback displays
- **File Management**: Automatic file naming with timestamps and auto-opening
- **Database Integration**: Direct SQLite queries with optimized performance
- **Memory Management**: Efficient data processing for large report ranges
- **Audit Trail**: Logging of all report generation activities

#### Report Generation Process
1. **Configuration**: Select report type and parameters
2. **Validation**: Date range and filter validation
3. **Background Processing**: Report generation in separate thread
4. **Progress Updates**: Real-time status messages
5. **File Creation**: Excel file generation with formatted data
6. **Auto-Opening**: Automatic opening of generated Excel files
7. **Results Tracking**: Addition to generated reports list and recent history

The reports system provides laboratory staff with powerful tools for analyzing inventory usage patterns, tracking stock levels, and generating comprehensive reports for management and compliance purposes. All reports are exported in Excel format for easy sharing and further analysis.

### Settings

The Settings page is a comprehensive administrative interface for managing the core metadata used throughout the inventory management system. It provides centralized control over the dropdown options and categorical data that populate forms across the application, ensuring consistency and ease of maintenance for sizes, brands, suppliers, and categories.

#### Main Interface Layout
- **Header Section**: Displays "Settings" title in large, bold font for clear page identification
- **Tabbed Organization**: Four dedicated tabs for each metadata type, allowing organized access without cluttering the interface
- **Clean Layout**: Vertical layout with consistent margins (20px) and spacing (15px) for professional appearance
- **Responsive Design**: Automatically adjusts to window size while maintaining usability

#### Sizes Management Tab
The Sizes tab provides full CRUD operations for managing item sizes used in inventory entries.

##### Core Functionality
- **Sizes List**: Scrollable list widget displaying all available sizes alphabetically
- **Real-time Population**: Automatically loads and displays sizes from the database on page load
- **Selection Interface**: Single-click selection for editing/deleting operations

##### Management Actions
- **Add Size**: Opens a simple dialog for entering new size names with validation
- **Edit Size**: Pre-populates dialog with selected size for modification
- **Delete Size**: Confirmation dialog prevents accidental deletions
- **Input Validation**: Trims whitespace and prevents empty entries
- **Success/Error Feedback**: QMessageBox notifications for all operations

##### Technical Features
- **Database Integration**: Direct interaction with Size model for data persistence
- **Automatic Refresh**: List updates immediately after successful operations
- **Error Handling**: Comprehensive error messages for failed database operations

#### Brands Management Tab
The Brands tab mirrors the Sizes tab functionality for managing manufacturer/brand information.

##### Core Functionality
- **Brands List**: Alphabetical display of all registered brands
- **Consistent Interface**: Same layout and interaction patterns as Sizes tab
- **Selection and Actions**: Identical add/edit/delete workflow with brand-specific dialogs

##### Management Actions
- **Add Brand**: New brand creation with duplicate prevention
- **Edit Brand**: In-place modification of existing brand names
- **Delete Brand**: Safe deletion with confirmation prompts
- **Validation**: Name uniqueness and required field validation

##### Technical Features
- **Model Integration**: Uses Brand model for database operations
- **List Management**: Dynamic population and real-time updates
- **User Feedback**: Clear success/error messaging for all actions

#### Suppliers Management Tab
The Suppliers tab provides comprehensive supplier/vendor management capabilities.

##### Core Functionality
- **Suppliers List**: Organized display of all supplier names
- **Standard Operations**: Consistent add/edit/delete functionality
- **Dialog Integration**: Supplier-specific dialogs with proper validation

##### Management Actions
- **Add Supplier**: New supplier registration with name validation
- **Edit Supplier**: Modify existing supplier information
- **Delete Supplier**: Controlled deletion with confirmation
- **Data Integrity**: Prevents deletion of suppliers with active inventory items

##### Technical Features
- **Database Constraints**: Checks for dependent records before deletion
- **Error Prevention**: Validation prevents invalid operations
- **Audit Trail**: Logs all changes for accountability

#### Categories Management Tab
The Categories tab manages the item categorization system used throughout the application.

##### Core Functionality
- **Categories List**: Hierarchical or alphabetical display of item categories
- **Category Selection**: Enables filtering and organization in other modules
- **Management Workflow**: Standard CRUD operations with category-specific dialogs

##### Management Actions
- **Add Category**: Create new item categories for better organization
- **Edit Category**: Modify category names and properties
- **Delete Category**: Remove unused categories with safety checks
- **Validation**: Ensures category names are unique and properly formatted

##### Technical Features
- **Dependency Checks**: Prevents deletion of categories in use
- **Cross-Module Integration**: Categories populate dropdowns in inventory forms
- **Consistency Enforcement**: Maintains data integrity across the system

#### Common Features Across All Tabs
- **Unified User Experience**: Consistent button layouts and dialog designs
- **Keyboard Navigation**: Full keyboard accessibility for power users
- **Visual Feedback**: Hover effects and selection highlighting
- **Confirmation Dialogs**: Prevents accidental data loss
- **Real-time Updates**: Immediate reflection of changes in the interface

#### Technical Architecture
- **Composition Pattern**: Modular tab structure for maintainability
- **Signal/Slot System**: Proper event handling for responsive interactions
- **Database Abstraction**: Uses model classes for data operations
- **Error Handling**: Comprehensive logging and user-friendly error messages
- **Memory Management**: Efficient data loading and cleanup

The Settings page serves as the administrative backbone of the inventory system, providing essential tools for maintaining the metadata that drives the application's functionality. Its intuitive tabbed interface and consistent operation patterns make it easy for administrators to manage the core data elements that support inventory tracking and requisition workflows.

## Latest Release

[View the latest release](https://github.com/x01Jin/inventory-manager/releases/latest)
