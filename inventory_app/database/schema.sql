-- Database schema for Laboratory Inventory Monitoring Tool
-- SQLite database with all tables and views for inventory management

-- Enable foreign key enforcement
PRAGMA foreign_keys = ON;

-- 1. Category_Types: High-level types for lifecycle rules
CREATE TABLE Category_Types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

-- Insert initial category types
INSERT INTO Category_Types (name) VALUES
('Chemical'),
('Glassware'),
('Equipment'),
('Apparatus'),
('Material');

-- 2. Categories: Item categories linked to category types
CREATE TABLE Categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    category_type_id INTEGER,
    FOREIGN KEY (category_type_id) REFERENCES Category_Types(id)
);

INSERT INTO Categories (name, category_type_id) VALUES
('Hydrochloric Acid', 1),
('Sodium Hydroxide', 1),
('Beaker', 2),
('Volumetric Flask', 2),
('Microscope', 3),
('Centrifuge', 3),
('Bunsen Burner', 4),
('Pipette', 4),
('Plastic Tubes', 5),
('Filter Paper', 5);

-- Index for performance
CREATE INDEX idx_categories_type ON Categories(category_type_id);

-- 3. Lifecycle_Rules: Alert rules per category type
CREATE TABLE Lifecycle_Rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_type_id INTEGER NOT NULL,
    expiry_lead_months INTEGER,            -- e.g., 6 for Chemicals; NULL for non-expiring types
    lifespan_years INTEGER,                -- e.g., 3 for Glassware, 5 for Equipment/Apparatus; NULL for chemicals
    calibration_interval_months INTEGER,   -- e.g., 12 for Equipment; NULL otherwise
    calibration_lead_months INTEGER,       -- e.g., 3
    UNIQUE(category_type_id),
    FOREIGN KEY (category_type_id) REFERENCES Category_Types(id)
);

-- Insert initial lifecycle rules
INSERT INTO Lifecycle_Rules (category_type_id, expiry_lead_months, lifespan_years, calibration_interval_months, calibration_lead_months) VALUES
(1, 6, NULL, NULL, NULL),  -- Chemical: 6 months expiration
(2, NULL, 3, NULL, NULL),  -- Glassware: 3 years lifespan
(3, NULL, 5, 12, 3),      -- Equipment: 5 years lifespan + yearly calibration
(4, NULL, 5, NULL, NULL),  -- Apparatus: 5 years lifespan
(5, NULL, 2, NULL, NULL);  -- Material: 2 years lifespan

-- 4. Suppliers: Supplier names for dropdown selection
CREATE TABLE Suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

-- Insert initial suppliers
INSERT INTO Suppliers (name) VALUES ('Malcor Chemicals'), ('ATR Trading System'), ('Brightway Trading School');

-- Sizes: Size options for dropdown
CREATE TABLE Sizes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

-- Insert initial sizes
INSERT INTO Sizes (name) VALUES ('250mL');

-- Brands: Brand options for dropdown
CREATE TABLE Brands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

-- Insert initial brands
INSERT INTO Brands (name) VALUES ('LabCorp');

-- 5. Items: Core inventory table
CREATE TABLE Items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category_id INTEGER NOT NULL,
    size TEXT,
    brand TEXT,
    other_specifications TEXT,
    po_number TEXT,
    supplier_id INTEGER,
    expiration_date DATE,
    calibration_date DATE,
    is_consumable INTEGER NOT NULL DEFAULT 1,  -- 1=true, 0=false
    acquisition_date DATE,
    last_modified DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES Categories(id),
    FOREIGN KEY (supplier_id) REFERENCES Suppliers(id)
);

-- Indexes for performance
CREATE INDEX idx_items_category ON Items(category_id);
CREATE INDEX idx_items_name ON Items(name);
CREATE INDEX idx_items_expiration ON Items(expiration_date);
CREATE INDEX idx_items_calibration ON Items(calibration_date);
CREATE INDEX idx_items_supplier ON Items(supplier_id);
CREATE INDEX idx_items_last_modified ON Items(last_modified);

-- 6. Item_Batches: Multiple receipt dates and quantities
CREATE TABLE Item_Batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    batch_number INTEGER NOT NULL,
    date_received DATE NOT NULL,
    quantity_received INTEGER NOT NULL CHECK (quantity_received > 0),
    disposal_date DATE,
    FOREIGN KEY (item_id) REFERENCES Items(id),
    UNIQUE(item_id, batch_number)
);

-- Indexes
CREATE INDEX idx_batches_item_date ON Item_Batches(item_id, date_received);
CREATE INDEX idx_batches_disposal ON Item_Batches(disposal_date);

-- 7. Stock_Movements: Ledger for accurate on-hand counts
CREATE TABLE Stock_Movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    batch_id INTEGER,              -- Nullable for non-batch items
    movement_type TEXT NOT NULL,   -- 'RECEIPT','CONSUMPTION','ADJUSTMENT','DISPOSAL','RETURN'
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    movement_date DATE NOT NULL,
    source_id INTEGER,             -- e.g., requisition_id for usage
    note TEXT,
    FOREIGN KEY (item_id) REFERENCES Items(id),
    FOREIGN KEY (batch_id) REFERENCES Item_Batches(id)
);

-- Indexes
CREATE INDEX idx_movements_item_date ON Stock_Movements(item_id, movement_date);

-- 8. Borrowers: Borrower information
CREATE TABLE Borrowers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    affiliation TEXT NOT NULL,
    group_name TEXT NOT NULL
);

-- 9. Requisitions: Borrowing records
CREATE TABLE Requisitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    borrower_id INTEGER NOT NULL,
    date_borrowed DATE NOT NULL,
    lab_activity_name TEXT NOT NULL,
    lab_activity_date DATE NOT NULL,
    num_students INTEGER,
    num_groups INTEGER,
    FOREIGN KEY (borrower_id) REFERENCES Borrowers(id)
);

-- Indexes
CREATE INDEX idx_requisitions_activity_date ON Requisitions(lab_activity_date);
CREATE INDEX idx_requisitions_borrower ON Requisitions(borrower_id);

-- 10. Requisition_Items: Items in requisitions
CREATE TABLE Requisition_Items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requisition_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    quantity_borrowed INTEGER NOT NULL CHECK (quantity_borrowed > 0),
    FOREIGN KEY (requisition_id) REFERENCES Requisitions(id),
    FOREIGN KEY (item_id) REFERENCES Items(id)
);

-- Indexes
CREATE INDEX idx_req_items_req ON Requisition_Items(requisition_id);
CREATE INDEX idx_req_items_item ON Requisition_Items(item_id);

-- 11. Update_History: Item edit history
CREATE TABLE Update_History (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    editor_name TEXT NOT NULL,
    edit_timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reason TEXT NOT NULL,
    FOREIGN KEY (item_id) REFERENCES Items(id)
);

-- Index
CREATE INDEX idx_history_item ON Update_History(item_id);

-- 12. Requisition_History: Requisition edit history
CREATE TABLE Requisition_History (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requisition_id INTEGER NOT NULL,
    editor_name TEXT NOT NULL,
    edit_timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reason TEXT NOT NULL,
    FOREIGN KEY (requisition_id) REFERENCES Requisitions(id)
);

-- Index
CREATE INDEX idx_req_history_req ON Requisition_History(requisition_id);

-- 13. Disposal_History: Disposed items
CREATE TABLE Disposal_History (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    reason TEXT NOT NULL,
    disposal_timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor_name TEXT NOT NULL,
    FOREIGN KEY (item_id) REFERENCES Items(id)
);

-- Index
CREATE INDEX idx_disposal_item ON Disposal_History(item_id);

-- Activity_Log: Recent activity tracking for dashboard
CREATE TABLE Activity_Log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_type TEXT NOT NULL,  -- 'ITEM_ADDED', 'ITEM_EDITED', 'ITEM_DELETED', 'REQUISITION_CREATED', 'BORROWER_ADDED', etc.
    description TEXT NOT NULL,
    entity_id INTEGER,            -- ID of the related entity (item, requisition, borrower, etc.)
    entity_type TEXT,             -- 'item', 'requisition', 'borrower', etc.
    user_name TEXT,               -- Name of the user who performed the action
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Index for performance
CREATE INDEX idx_activity_timestamp ON Activity_Log(timestamp DESC);
CREATE INDEX idx_activity_type ON Activity_Log(activity_type);

-- VIEWS FOR REPORTS AND ALERTS

-- Item_Start_Dates View: Helper for alerts
CREATE VIEW Item_Start_Dates AS
SELECT
    i.id AS item_id,
    MIN(ib.date_received) AS first_batch_received,
    i.acquisition_date
FROM Items i
LEFT JOIN Item_Batches ib ON ib.item_id = i.id
GROUP BY i.id;

-- Item_Calibration_Due View: Helper for alerts
CREATE VIEW Item_Calibration_Due AS
SELECT
    i.id AS item_id,
    lr.calibration_interval_months,
    lr.calibration_lead_months,
    i.calibration_date AS last_calibration_date,
    CASE
        WHEN lr.calibration_interval_months IS NOT NULL AND i.calibration_date IS NOT NULL
        THEN DATE(i.calibration_date, '+' || lr.calibration_interval_months || ' months')
        ELSE NULL
    END AS next_calibration_date
FROM Items i
JOIN Categories c ON i.category_id = c.id
LEFT JOIN Lifecycle_Rules lr ON c.category_type_id = lr.category_type_id;

-- Alerts View: Combined alerts for expiration, lifecycle, calibration
CREATE VIEW Alerts AS
WITH starts AS (
  SELECT
    s.item_id,
    COALESCE(s.first_batch_received, s.acquisition_date) AS start_date
  FROM Item_Start_Dates s
),
cal AS (
  SELECT * FROM Item_Calibration_Due
)
SELECT
  i.id AS item_id,
  i.name,
  'Expiration Alert' AS alert_type,
  i.expiration_date AS reference_date
FROM Items i
JOIN Categories c ON i.category_id = c.id
JOIN Lifecycle_Rules lr ON c.category_type_id = lr.category_type_id
WHERE i.expiration_date IS NOT NULL
  AND lr.expiry_lead_months IS NOT NULL
  AND i.expiration_date <= DATE('now', '+' || lr.expiry_lead_months || ' months')

UNION ALL

SELECT
  i.id,
  i.name,
  'Lifecycle Alert' AS alert_type,
  DATE(s.start_date, '+' || lr.lifespan_years || ' years') AS reference_date
FROM Items i
JOIN Categories c ON i.category_id = c.id
JOIN Lifecycle_Rules lr ON c.category_type_id = lr.category_type_id
JOIN starts s ON s.item_id = i.id
WHERE lr.lifespan_years IS NOT NULL
  AND s.start_date IS NOT NULL
  AND DATE(s.start_date, '+' || lr.lifespan_years || ' years') <= DATE('now')

UNION ALL

SELECT
  i.id,
  i.name,
  'Calibration Alert' AS alert_type,
  cal.next_calibration_date AS reference_date
FROM Items i
JOIN Categories c ON i.category_id = c.id
JOIN Lifecycle_Rules lr ON c.category_type_id = lr.category_type_id
JOIN cal ON cal.item_id = i.id
WHERE cal.next_calibration_date IS NOT NULL
  AND DATE('now') >= DATE(cal.next_calibration_date, '-' || COALESCE(lr.calibration_lead_months, 0) || ' months');

-- Item_Usage View: Usage tracking
CREATE VIEW Item_Usage AS
SELECT
    ri.item_id,
    i.name AS item_name,
    r.lab_activity_date,
    SUM(ri.quantity_borrowed) AS total_used
FROM Requisition_Items ri
JOIN Requisitions r ON ri.requisition_id = r.id
JOIN Items i ON ri.item_id = i.id
GROUP BY ri.item_id, r.lab_activity_date;

-- Dynamic Report Query Template (supports daily, weekly, monthly, quarterly granularity)
-- Replace ? placeholders with actual values in order:
-- 1. start_date, 2. end_date, 3. granularity ('daily', 'weekly', 'monthly', 'quarterly')
-- Optional filters: 4. grade_filter, 5. section_filter, 6. include_consumables (0/1)
/*
WITH base AS (
  SELECT
    i.id AS item_id,
    i.name AS item_name,
    c.name AS category_name,
    i.size,
    i.brand,
    i.other_specifications,
    SUM(ri.quantity_borrowed) AS qty,
    r.lab_activity_date
  FROM Requisition_Items ri
  JOIN Requisitions r ON r.id = ri.requisition_id
  JOIN Items i ON i.id = ri.item_id
  JOIN Categories c ON c.id = i.category_id
  WHERE r.lab_activity_date BETWEEN ? AND ?
  -- Add optional grade filter
  AND (? IS NULL OR r.borrower_id IN (SELECT id FROM Borrowers WHERE affiliation = ?))
  -- Add optional section filter
  AND (? IS NULL OR r.borrower_id IN (SELECT id FROM Borrowers WHERE group_name = ?))
  -- Add optional consumables filter
  AND (? = 1 OR i.is_consumable = 0)
  GROUP BY i.id, r.lab_activity_date
),
dynamic_periods AS (
  SELECT
    *,
    CASE ?
      WHEN 'daily' THEN strftime('%Y-%m-%d', lab_activity_date)
      WHEN 'weekly' THEN strftime('%Y-%W', lab_activity_date)
      WHEN 'monthly' THEN strftime('%Y-%m', lab_activity_date)
      WHEN 'quarterly' THEN strftime('%Y', lab_activity_date) || '-Q' ||
                          CAST(((CAST(strftime('%m', lab_activity_date) AS INTEGER) - 1) / 3) + 1 AS TEXT)
    END AS period_key
  FROM base
),
pivoted_data AS (
  SELECT
    item_id,
    item_name,
    category_name,
    size,
    brand,
    other_specifications,
    period_key,
    SUM(qty) AS period_qty
  FROM dynamic_periods
  GROUP BY item_id, period_key
)
SELECT
  item_name AS ITEMS,
  category_name AS CATEGORIES,
  size AS SIZE,
  brand AS BRAND,
  other_specifications AS SPECIFICATIONS,
  -- Dynamic period columns will be generated here based on granularity
  -- Example for monthly: "2023-01", "2023-02", etc.
  SUM(period_qty) AS "TOTAL QUANTITY"
FROM pivoted_data
GROUP BY item_id
ORDER BY category_name, item_name;
*/
