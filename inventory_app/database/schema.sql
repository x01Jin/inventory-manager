-- Database schema for Laboratory Inventory Monitoring Tool
-- SQLite database with all tables and views for inventory management

-- Enable foreign key enforcement
PRAGMA foreign_keys = ON;

-- 1. Categories: Item categories
CREATE TABLE Categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

INSERT INTO Categories (name) VALUES
('Hydrochloric Acid'),
('Sodium Hydroxide'),
('Beaker'),
('Volumetric Flask'),
('Microscope'),
('Centrifuge'),
('Bunsen Burner'),
('Pipette'),
('Plastic Tubes'),
('Filter Paper');

-- 2. Suppliers: Supplier names for dropdown selection
CREATE TABLE Suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

-- Insert initial suppliers
INSERT INTO Suppliers (name) VALUES ('Malcor Chemicals'), ('ATR Trading System'), ('Brightway Trading School'), ('Sigma-Aldrich'), ('Thermo Fisher Scientific');

-- 3. Sizes: Size options for dropdown
CREATE TABLE Sizes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

-- Insert initial sizes
INSERT INTO Sizes (name) VALUES ('250mL'), ('500mL'), ('1L'), ('100mL'), ('50mL');

-- 4. Brands: Brand options for dropdown
CREATE TABLE Brands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

-- Insert initial brands
INSERT INTO Brands (name) VALUES ('LabCorp'), ('Fisher Scientific'), ('Merck'), ('Sigma'), ('VWR');

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
        FOREIGN KEY (item_id) REFERENCES Items(id) ON DELETE CASCADE,
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
    movement_type TEXT NOT NULL CHECK (movement_type IN ('CONSUMPTION','RESERVATION','DISPOSAL','RETURN','REQUEST','LOST')),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    movement_date DATE NOT NULL,
    source_id INTEGER,             -- e.g., requisition_id for usage
    note TEXT,
        FOREIGN KEY (item_id) REFERENCES Items(id) ON DELETE CASCADE,
        FOREIGN KEY (batch_id) REFERENCES Item_Batches(id) ON DELETE CASCADE,
        FOREIGN KEY (source_id) REFERENCES Requisitions(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_movements_item_date ON Stock_Movements(item_id, movement_date);

-- 8. Requesters: Requester information
CREATE TABLE Requesters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    affiliation TEXT NOT NULL,
    group_name TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 9. Requisitions: Requesting records with reservation support
CREATE TABLE Requisitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requester_id INTEGER NOT NULL,
    expected_request DATETIME NOT NULL,
    expected_return DATETIME NOT NULL,
    status TEXT NOT NULL DEFAULT 'requested',  -- 'requested', 'active', 'returned', 'overdue'
    lab_activity_name TEXT NOT NULL,
    lab_activity_description TEXT,  -- For detailed activity information stored for reports
    lab_activity_date DATE NOT NULL,
    num_students INTEGER,
    num_groups INTEGER,
    FOREIGN KEY (requester_id) REFERENCES Requesters(id)
);

-- Indexes
CREATE INDEX idx_requisitions_activity_date ON Requisitions(lab_activity_date);
CREATE INDEX idx_requisitions_requester ON Requisitions(requester_id);

-- 10. Requisition_Items: Items in requisitions
CREATE TABLE Requisition_Items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requisition_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    quantity_requested INTEGER NOT NULL CHECK (quantity_requested > 0),
        FOREIGN KEY (requisition_id) REFERENCES Requisitions(id) ON DELETE CASCADE,
        FOREIGN KEY (item_id) REFERENCES Items(id) ON DELETE CASCADE
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
        FOREIGN KEY (item_id) REFERENCES Items(id) ON DELETE CASCADE
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
        FOREIGN KEY (requisition_id) REFERENCES Requisitions(id) ON DELETE CASCADE
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
        FOREIGN KEY (item_id) REFERENCES Items(id) ON DELETE CASCADE
);
CREATE INDEX idx_movements_source ON Stock_Movements(source_id);

-- Index
CREATE INDEX idx_disposal_item ON Disposal_History(item_id);

-- 14. Activity_Log: Recent activity tracking for dashboard
CREATE TABLE Activity_Log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_type TEXT NOT NULL,  -- 'ITEM_ADDED', 'ITEM_EDITED', 'ITEM_DELETED', 'REQUISITION_CREATED', 'REQUESTER_ADDED', etc.
    description TEXT NOT NULL,
    entity_id INTEGER,            -- ID of the related entity (item, requisition, requester, etc.)
    entity_type TEXT,             -- 'item', 'requisition', 'requester', etc.
    user_name TEXT,               -- Name of the user who performed the action
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Index for performance
CREATE INDEX idx_activity_timestamp ON Activity_Log(timestamp DESC);
CREATE INDEX idx_activity_type ON Activity_Log(activity_type);

-- Triggers to automatically enforce activity log retention policies
-- 1) Remove activities older than 90 days on insert
CREATE TRIGGER IF NOT EXISTS trg_activity_log_cleanup_after_insert
AFTER INSERT ON Activity_Log
BEGIN
    DELETE FROM Activity_Log WHERE timestamp < datetime('now', '-90 days');
END;

-- 2) Maintain a maximum of 20 recent activities by deleting older ones on insert
CREATE TRIGGER IF NOT EXISTS trg_activity_log_maintain_limit_after_insert
AFTER INSERT ON Activity_Log
WHEN (SELECT COUNT(*) FROM Activity_Log) > 20
BEGIN
    DELETE FROM Activity_Log WHERE id NOT IN (SELECT id FROM Activity_Log ORDER BY timestamp DESC LIMIT 20);
END;

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

-- Item_Usage View: Usage tracking
CREATE VIEW Item_Usage AS
SELECT
    ri.item_id,
    i.name AS item_name,
    r.lab_activity_date,
    SUM(ri.quantity_requested) AS total_used
FROM Requisition_Items ri
JOIN Requisitions r ON ri.requisition_id = r.id
JOIN Items i ON ri.item_id = i.id
GROUP BY ri.item_id, r.lab_activity_date;
