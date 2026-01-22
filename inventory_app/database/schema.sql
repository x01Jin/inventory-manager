-- Database schema for Laboratory Inventory Monitoring Tool
-- SQLite database with all tables and views for inventory management

-- Enable foreign key enforcement
PRAGMA foreign_keys = ON;

-- 1. Categories: Fixed item categories (not user-customizable)
-- These are the default categories with predefined alert thresholds
CREATE TABLE Categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

-- Default categories (fixed, cannot be modified by users)
INSERT INTO Categories (name) VALUES
('Chemicals-Solid'),
('Chemicals-Liquid'),
('Prepared Slides'),
('Consumables'),
('Equipment'),
('Apparatus'),
('Lab Models'),
('Others'),
('Uncategorized');

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
    movement_type TEXT NOT NULL CHECK (movement_type IN ('CONSUMPTION','RESERVATION','DISPOSAL','RETURN','REQUEST')),
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

-- Trigger: Prevent movements that would oversubscribe a batch's received quantity
CREATE TRIGGER IF NOT EXISTS trg_stock_movement_batch_before_insert
BEFORE INSERT ON Stock_Movements
WHEN NEW.batch_id IS NOT NULL AND NEW.movement_type IN ('CONSUMPTION','RESERVATION','DISPOSAL')
BEGIN
    SELECT CASE
        WHEN (COALESCE((SELECT SUM(quantity) FROM Stock_Movements WHERE batch_id = NEW.batch_id AND movement_type IN ('CONSUMPTION','RESERVATION','DISPOSAL')),0) + NEW.quantity)
             > (SELECT quantity_received FROM Item_Batches WHERE id = NEW.batch_id)
        THEN RAISE(ABORT, 'Insufficient batch stock for this movement')
    END;
END;

CREATE TRIGGER IF NOT EXISTS trg_stock_movement_batch_before_update
BEFORE UPDATE OF quantity, batch_id, movement_type ON Stock_Movements
WHEN NEW.batch_id IS NOT NULL AND NEW.movement_type IN ('CONSUMPTION','RESERVATION','DISPOSAL')
BEGIN
    SELECT CASE
        WHEN (COALESCE((SELECT SUM(quantity) FROM Stock_Movements WHERE batch_id = NEW.batch_id AND movement_type IN ('CONSUMPTION','RESERVATION','DISPOSAL') AND id != OLD.id),0) + NEW.quantity)
             > (SELECT quantity_received FROM Item_Batches WHERE id = NEW.batch_id)
        THEN RAISE(ABORT, 'Insufficient batch stock for this movement (update)')
    END;
END;

-- Trigger: Prevent movements without a batch_id that would oversubscribe the item's total received quantity
CREATE TRIGGER IF NOT EXISTS trg_stock_movement_item_before_insert
BEFORE INSERT ON Stock_Movements
WHEN NEW.batch_id IS NULL AND NEW.movement_type IN ('CONSUMPTION','RESERVATION','DISPOSAL')
BEGIN
    SELECT CASE
        WHEN (COALESCE((SELECT SUM(quantity) FROM Stock_Movements WHERE item_id = NEW.item_id AND movement_type IN ('CONSUMPTION','RESERVATION','DISPOSAL')),0) + NEW.quantity)
             > (COALESCE((SELECT SUM(quantity_received) FROM Item_Batches WHERE item_id = NEW.item_id),0))
        THEN RAISE(ABORT, 'Insufficient item stock for this movement')
    END;
END;

CREATE TRIGGER IF NOT EXISTS trg_stock_movement_item_before_update
BEFORE UPDATE OF quantity, batch_id, movement_type ON Stock_Movements
WHEN NEW.batch_id IS NULL AND NEW.movement_type IN ('CONSUMPTION','RESERVATION','DISPOSAL')
BEGIN
    SELECT CASE
        WHEN (COALESCE((SELECT SUM(quantity) FROM Stock_Movements WHERE item_id = NEW.item_id AND movement_type IN ('CONSUMPTION','RESERVATION','DISPOSAL') AND id != OLD.id),0) + NEW.quantity)
             > (COALESCE((SELECT SUM(quantity_received) FROM Item_Batches WHERE item_id = NEW.item_id),0))
        THEN RAISE(ABORT, 'Insufficient item stock for this movement (update)')
    END;
END;

-- 8. Requesters: Requester information with type-specific fields
-- requester_type: 'student', 'teacher', or 'faculty'
-- Students require grade_level and section
-- Teachers require department
-- Faculty are simplified (name + requester_type only)
CREATE TABLE Requesters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    requester_type TEXT NOT NULL DEFAULT 'teacher',
    -- Student-specific fields
    grade_level TEXT,             -- Grade level (e.g., 'Grade 7', 'Grade 8', 'Grade 9', 'Grade 10')
    section TEXT,                 -- Section name (e.g., 'Section A', 'Einstein')
    -- Teacher/Faculty fields
    department TEXT,              -- Department (for teachers)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 9. Requisitions: Requesting records with reservation support
-- Individual requests (is_individual=1) store requester info directly
-- and skip the activity section entirely
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
    -- Individual request fields
    is_individual INTEGER NOT NULL DEFAULT 0,
    individual_name TEXT,
    individual_contact TEXT,
    individual_purpose TEXT,
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
    item_id INTEGER,
    reason TEXT NOT NULL,
    disposal_timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    editor_name TEXT NOT NULL
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

-- 15. Defective_Items: Track defective/broken items returned
-- Per beta test requirement: Add info for defective/broken items returned
CREATE TABLE Defective_Items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    requisition_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    notes TEXT,
    reported_by TEXT NOT NULL,
    reported_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (item_id) REFERENCES Items(id) ON DELETE CASCADE,
        FOREIGN KEY (requisition_id) REFERENCES Requisitions(id) ON DELETE CASCADE
);

-- Indexes for defective items
CREATE INDEX idx_defective_item ON Defective_Items(item_id);
CREATE INDEX idx_defective_requisition ON Defective_Items(requisition_id);
CREATE INDEX idx_defective_date ON Defective_Items(reported_date);

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

-- Defective_Items_Summary View: Defective items report
CREATE VIEW Defective_Items_Summary AS
SELECT
    i.name AS item_name,
    c.name AS category,
    di.quantity AS defective_quantity,
    di.notes,
    di.reported_by,
    di.reported_date,
    r.lab_activity_name AS activity,
    req.name AS requester_name
FROM Defective_Items di
JOIN Items i ON i.id = di.item_id
JOIN Categories c ON c.id = i.category_id
JOIN Requisitions r ON r.id = di.requisition_id
JOIN Requesters req ON req.id = r.requester_id;

-- Stock Summary Table: Pre-computed stock data per item
-- Updated via triggers and periodic refresh
CREATE TABLE IF NOT EXISTS Stock_Summary (
    item_id INTEGER PRIMARY KEY,
    item_name TEXT NOT NULL,
    category_name TEXT NOT NULL,
    total_batches INTEGER DEFAULT 0,
    original_stock INTEGER DEFAULT 0,
    consumed_qty INTEGER DEFAULT 0,
    disposed_qty INTEGER DEFAULT 0,
    returned_qty INTEGER DEFAULT 0,
    total_stock INTEGER DEFAULT 0,
    low_stock_threshold INTEGER DEFAULT 5,
    is_low_stock INTEGER DEFAULT 0,
    is_out_of_stock INTEGER DEFAULT 0,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (item_id) REFERENCES Items(id) ON DELETE CASCADE
);

-- Requisition Summary Table: Denormalized requisition data for fast loading
-- Includes individual request fields for quick display
CREATE TABLE IF NOT EXISTS Requisition_Summary (
    requisition_id INTEGER PRIMARY KEY,
    requester_name TEXT NOT NULL,
    requester_type TEXT,              -- Requester type: student, teacher, faculty
    requester_group TEXT,             -- Can be NULL if requester has no group (deprecated, use grade_level/section)
    grade_level TEXT,
    section TEXT,
    status TEXT NOT NULL,
    lab_activity_name TEXT NOT NULL,
    lab_activity_date TEXT,
    expected_return TEXT,
    item_count INTEGER DEFAULT 0,
    item_summary_json TEXT DEFAULT '[]',
    total_quantity_requested INTEGER DEFAULT 0,
    num_students INTEGER,
    num_groups INTEGER,
    -- Individual request display fields
    is_individual INTEGER DEFAULT 0,
    individual_name TEXT,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (requisition_id) REFERENCES Requisitions(id) ON DELETE CASCADE
);

-- Statistics Aggregate Table: Single-row aggregate for dashboard
CREATE TABLE IF NOT EXISTS Statistics_Aggregate (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    total_items INTEGER DEFAULT 0,
    total_batches INTEGER DEFAULT 0,
    total_original_stock INTEGER DEFAULT 0,
    total_consumed INTEGER DEFAULT 0,
    total_disposed INTEGER DEFAULT 0,
    total_returned INTEGER DEFAULT 0,
    total_stock INTEGER DEFAULT 0,
    low_stock_count INTEGER DEFAULT 0,
    out_of_stock_count INTEGER DEFAULT 0,
    active_requisitions INTEGER DEFAULT 0,
    overdue_requisitions INTEGER DEFAULT 0,
    expiring_soon_count INTEGER DEFAULT 0,
    calibration_due_count INTEGER DEFAULT 0,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Initialize Statistics_Aggregate with default row
INSERT OR IGNORE INTO Statistics_Aggregate (id) VALUES (1);

-- Schema version tracking for migrations
CREATE TABLE IF NOT EXISTS Schema_Versions (
    migration_id TEXT PRIMARY KEY,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- Index for fast lookup
CREATE INDEX IF NOT EXISTS idx_schema_versions_id ON Schema_Versions(migration_id);

-- Indexes for summary tables
CREATE INDEX IF NOT EXISTS idx_stock_summary_stock ON Stock_Summary(total_stock);
CREATE INDEX IF NOT EXISTS idx_stock_summary_low_stock ON Stock_Summary(is_low_stock);
CREATE INDEX IF NOT EXISTS idx_stock_summary_out_of_stock ON Stock_Summary(is_out_of_stock);
CREATE INDEX IF NOT EXISTS idx_requisition_summary_status ON Requisition_Summary(status);
CREATE INDEX IF NOT EXISTS idx_requisition_summary_date ON Requisition_Summary(lab_activity_date);

-- TRIGGERS FOR SUMMARY TABLES (Auto-update)

-- Stock Summary Triggers
CREATE TRIGGER IF NOT EXISTS trg_stock_summary_after_item_insert
AFTER INSERT ON Items
BEGIN
    INSERT INTO Stock_Summary (item_id, item_name, category_name)
    VALUES (NEW.id, NEW.name, (SELECT name FROM Categories WHERE id = NEW.category_id));
END;

CREATE TRIGGER IF NOT EXISTS trg_stock_summary_after_item_update
AFTER UPDATE ON Items
BEGIN
    UPDATE Stock_Summary SET
        item_name = NEW.name,
        category_name = (SELECT name FROM Categories WHERE id = NEW.category_id),
        last_updated = CURRENT_TIMESTAMP
    WHERE item_id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_stock_summary_after_batch
AFTER INSERT ON Item_Batches
BEGIN
    UPDATE Stock_Summary SET
        total_batches = total_batches + 1,
        original_stock = original_stock + NEW.quantity_received,
        total_stock = total_stock + NEW.quantity_received,
        is_low_stock = CASE
            WHEN (total_stock + NEW.quantity_received) BETWEEN 1 AND low_stock_threshold THEN 1
            ELSE 0
        END,
        is_out_of_stock = CASE
            WHEN (total_stock + NEW.quantity_received) <= 0 THEN 1
            ELSE 0
        END,
        last_updated = CURRENT_TIMESTAMP
    WHERE item_id = NEW.item_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_stock_summary_after_movement
AFTER INSERT ON Stock_Movements
BEGIN
    UPDATE Stock_Summary SET
        consumed_qty = consumed_qty + CASE WHEN NEW.movement_type = 'CONSUMPTION' THEN NEW.quantity ELSE 0 END,
        disposed_qty = disposed_qty + CASE WHEN NEW.movement_type = 'DISPOSAL' THEN NEW.quantity ELSE 0 END,
        returned_qty = returned_qty + CASE WHEN NEW.movement_type = 'RETURN' THEN NEW.quantity ELSE 0 END,
        total_stock = total_stock
            - CASE WHEN NEW.movement_type IN ('CONSUMPTION', 'DISPOSAL', 'RESERVATION') THEN NEW.quantity ELSE 0 END
            + CASE WHEN NEW.movement_type = 'RETURN' THEN NEW.quantity ELSE 0 END,
        is_low_stock = CASE
            WHEN (total_stock
                - CASE WHEN NEW.movement_type IN ('CONSUMPTION', 'DISPOSAL', 'RESERVATION') THEN NEW.quantity ELSE 0 END
                + CASE WHEN NEW.movement_type = 'RETURN' THEN NEW.quantity ELSE 0 END) BETWEEN 1 AND low_stock_threshold THEN 1
            ELSE 0
        END,
        is_out_of_stock = CASE
            WHEN (total_stock
                - CASE WHEN NEW.movement_type IN ('CONSUMPTION', 'DISPOSAL', 'RESERVATION') THEN NEW.quantity ELSE 0 END
                + CASE WHEN NEW.movement_type = 'RETURN' THEN NEW.quantity ELSE 0 END) <= 0 THEN 1
            ELSE 0
        END,
        last_updated = CURRENT_TIMESTAMP
    WHERE item_id = NEW.item_id;
END;

-- Requisition Summary Triggers
CREATE TRIGGER IF NOT EXISTS trg_requisition_summary_after_insert
AFTER INSERT ON Requisitions
BEGIN
    INSERT INTO Requisition_Summary (
        requisition_id, requester_name, requester_type, requester_group, grade_level, section,
        status, lab_activity_name, lab_activity_date, expected_return,
        num_students, num_groups, is_individual, individual_name
    )
    SELECT
        NEW.id, r.name, r.requester_type, r.grade_level, r.grade_level, r.section,
        NEW.status, NEW.lab_activity_name, NEW.lab_activity_date, NEW.expected_return,
        NEW.num_students, NEW.num_groups,
        NEW.is_individual, NEW.individual_name
    FROM Requesters r WHERE r.id = NEW.requester_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_requisition_summary_after_update
AFTER UPDATE ON Requisitions
BEGIN
    UPDATE Requisition_Summary SET
        status = NEW.status,
        lab_activity_name = NEW.lab_activity_name,
        lab_activity_date = NEW.lab_activity_date,
        expected_return = NEW.expected_return,
        num_students = NEW.num_students,
        num_groups = NEW.num_groups,
        is_individual = NEW.is_individual,
        individual_name = NEW.individual_name,
        last_updated = CURRENT_TIMESTAMP
    WHERE requisition_id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_requisition_summary_after_item
AFTER INSERT ON Requisition_Items
BEGIN
    UPDATE Requisition_Summary SET
        item_count = item_count + 1,
        total_quantity_requested = total_quantity_requested + NEW.quantity_requested,
        last_updated = CURRENT_TIMESTAMP
    WHERE requisition_id = NEW.requisition_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_requisition_summary_after_req_update
AFTER UPDATE ON Requesters
BEGIN
    UPDATE Requisition_Summary SET
        requester_name = NEW.name,
        requester_type = NEW.requester_type,
        requester_group = NEW.grade_level,
        grade_level = NEW.grade_level,
        section = NEW.section,
        last_updated = CURRENT_TIMESTAMP
    WHERE requisition_id IN (SELECT id FROM Requisitions WHERE requester_id = NEW.id);
END;

CREATE TRIGGER IF NOT EXISTS trg_requisition_summary_after_req_delete
AFTER DELETE ON Requisitions
BEGIN
    DELETE FROM Requisition_Summary WHERE requisition_id = OLD.id;
END;

