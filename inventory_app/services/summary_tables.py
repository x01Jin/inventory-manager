"""
Summary tables and materialized views service for pre-computed statistics.
Provides instant statistics and reduced query complexity through denormalized data.
"""

import threading
import time
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass

from inventory_app.database.connection import db
from inventory_app.utils.logger import logger
from inventory_app.services.movement_types import MovementType


@dataclass
class StockSummary:
    """Pre-computed stock summary for an item."""

    item_id: int
    item_name: str
    category_name: str
    total_batches: int
    original_stock: int
    consumed_qty: int
    disposed_qty: int
    returned_qty: int
    total_stock: int
    low_stock_threshold: int = 10
    is_low_stock: bool = False
    is_out_of_stock: bool = False
    last_updated: Optional[datetime] = None


@dataclass
class RequisitionSummary:
    """Pre-computed requisition summary for fast loading."""

    requisition_id: int
    requester_name: str
    requester_group: str
    grade_level: Optional[str]
    section: Optional[str]
    status: str
    lab_activity_name: str
    lab_activity_date: Optional[str]
    expected_return: Optional[str]
    item_count: int
    item_summary_json: str
    total_quantity_requested: int
    num_students: Optional[int]
    num_groups: Optional[int]
    last_updated: Optional[datetime] = None


@dataclass
class StatisticsAggregate:
    """Pre-computed statistics aggregate."""

    total_items: int = 0
    total_batches: int = 0
    total_original_stock: int = 0
    total_consumed: int = 0
    total_disposed: int = 0
    total_returned: int = 0
    total_stock: int = 0
    low_stock_count: int = 0
    out_of_stock_count: int = 0
    active_requisitions: int = 0
    overdue_requisitions: int = 0
    expiring_soon_count: int = 0
    calibration_due_count: int = 0
    last_updated: Optional[datetime] = None


class SummaryTablesService:
    """
    Service for managing summary tables and materialized views.
    Provides pre-computed data for instant statistics and reduced query complexity.
    """

    _instance: Optional["SummaryTablesService"] = None
    _lock = threading.Lock()

    REFRESH_INTERVAL_SECONDS = 60.0
    SUMMARY_TTL_SECONDS = 120.0

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._last_refresh: Optional[datetime] = None
        self._refresh_thread: Optional[threading.Thread] = None
        self._stop_refresh = threading.Event()
        self._stats_cache: Optional[StatisticsAggregate] = None
        self._stats_cache_time: float = 0.0

    def initialize(self) -> bool:
        """
        Initialize summary tables and triggers.

        Returns:
            True if successful, False otherwise
        """
        try:
            self._create_summary_tables()
            self._create_triggers()
            self._start_refresh_thread()
            logger.info("Summary tables service initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize summary tables service: {e}")
            return False

    def shutdown(self) -> None:
        """Stop refresh thread and cleanup."""
        self._stop_refresh.set()
        if self._refresh_thread and self._refresh_thread.is_alive():
            self._refresh_thread.join(timeout=5.0)
        logger.info("Summary tables service shutdown complete")

    def _create_summary_tables(self) -> None:
        """Create summary tables if they don't exist (for fresh installs)."""
        create_stock_summary = """
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
            low_stock_threshold INTEGER DEFAULT 10,
            is_low_stock INTEGER DEFAULT 0,
            is_out_of_stock INTEGER DEFAULT 0,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES Items(id) ON DELETE CASCADE
        )
        """
        create_requisition_summary = """
        CREATE TABLE IF NOT EXISTS Requisition_Summary (
            requisition_id INTEGER PRIMARY KEY,
            requester_name TEXT NOT NULL,
            requester_group TEXT NOT NULL,
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
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (requisition_id) REFERENCES Requisitions(id) ON DELETE CASCADE
        )
        """
        create_statistics_aggregate = """
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
        )
        """
        create_indexes = [
            "CREATE INDEX IF NOT EXISTS idx_stock_summary_stock ON Stock_Summary(total_stock)",
            "CREATE INDEX IF NOT EXISTS idx_stock_summary_low_stock ON Stock_Summary(is_low_stock)",
            "CREATE INDEX IF NOT EXISTS idx_requisition_summary_status ON Requisition_Summary(status)",
            "CREATE INDEX IF NOT EXISTS idx_requisition_summary_date ON Requisition_Summary(lab_activity_date)",
        ]

        with db.get_connection() as conn:
            conn.execute(create_stock_summary)
            conn.execute(create_requisition_summary)
            conn.execute(create_statistics_aggregate)
            conn.execute("INSERT OR IGNORE INTO Statistics_Aggregate (id) VALUES (1)")
            for idx in create_indexes:
                try:
                    conn.execute(idx)
                except Exception:
                    pass  # Index may already exist
            conn.commit()

        logger.debug("Summary tables created (if not exists)")

    def _create_triggers(self) -> None:
        """Create triggers to keep summary tables updated."""
        triggers = [
            (
                "trg_stock_summary_after_item_insert",
                """
                CREATE TRIGGER IF NOT EXISTS trg_stock_summary_after_item_insert
                AFTER INSERT ON Items
                BEGIN
                    INSERT INTO Stock_Summary (item_id, item_name, category_name)
                    VALUES (NEW.id, NEW.name, (SELECT name FROM Categories WHERE id = NEW.category_id));
                END
                """,
            ),
            (
                "trg_stock_summary_after_item_update",
                """
                CREATE TRIGGER IF NOT EXISTS trg_stock_summary_after_item_update
                AFTER UPDATE ON Items
                BEGIN
                    UPDATE Stock_Summary SET
                        item_name = NEW.name,
                        category_name = (SELECT name FROM Categories WHERE id = NEW.category_id),
                        last_updated = CURRENT_TIMESTAMP
                    WHERE item_id = NEW.id;
                END
                """,
            ),
            (
                "trg_stock_summary_after_batch",
                """
                CREATE TRIGGER IF NOT EXISTS trg_stock_summary_after_batch
                AFTER INSERT ON Item_Batches
                BEGIN
                    UPDATE Stock_Summary SET
                        total_batches = total_batches + 1,
                        original_stock = original_stock + NEW.quantity_received,
                        total_stock = total_stock + NEW.quantity_received,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE item_id = NEW.item_id;
                END
                """,
            ),
            (
                "trg_stock_summary_after_movement",
                """
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
                        is_low_stock = CASE WHEN (total_stock
                            - CASE WHEN NEW.movement_type IN ('CONSUMPTION', 'DISPOSAL', 'RESERVATION') THEN NEW.quantity ELSE 0 END
                            + CASE WHEN NEW.movement_type = 'RETURN' THEN NEW.quantity ELSE 0 END) BETWEEN 1 AND low_stock_threshold THEN 1 ELSE 0 END,
                        is_out_of_stock = CASE WHEN (total_stock
                            - CASE WHEN NEW.movement_type IN ('CONSUMPTION', 'DISPOSAL', 'RESERVATION') THEN NEW.quantity ELSE 0 END
                            + CASE WHEN NEW.movement_type = 'RETURN' THEN NEW.quantity ELSE 0 END) <= 0 THEN 1 ELSE 0 END,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE item_id = NEW.item_id;
                END
                """,
            ),
            (
                "trg_requisition_summary_after_insert",
                """
                CREATE TRIGGER IF NOT EXISTS trg_requisition_summary_after_insert
                AFTER INSERT ON Requisitions
                BEGIN
                    INSERT INTO Requisition_Summary (
                        requisition_id, requester_name, requester_group, grade_level, section,
                        status, lab_activity_name, lab_activity_date, expected_return,
                        num_students, num_groups
                    )
                    SELECT
                        NEW.id, r.name, COALESCE(r.grade_level, r.department, ''),
                        r.grade_level, r.section,
                        NEW.status, NEW.lab_activity_name, NEW.lab_activity_date, NEW.expected_return,
                        NEW.num_students, NEW.num_groups
                    FROM Requesters r WHERE r.id = NEW.requester_id;
                END
                """,
            ),
            (
                "trg_requisition_summary_after_update",
                """
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
                        last_updated = CURRENT_TIMESTAMP
                    WHERE requisition_id = NEW.id;
                END
                """,
            ),
            (
                "trg_requisition_summary_after_item",
                """
                CREATE TRIGGER IF NOT EXISTS trg_requisition_summary_after_item
                AFTER INSERT ON Requisition_Items
                BEGIN
                    UPDATE Requisition_Summary SET
                        item_count = item_count + 1,
                        total_quantity_requested = total_quantity_requested + NEW.quantity_requested,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE requisition_id = NEW.requisition_id;
                END
                """,
            ),
            (
                "trg_requisition_summary_after_req_update",
                """
                CREATE TRIGGER IF NOT EXISTS trg_requisition_summary_after_req_update
                AFTER UPDATE ON Requesters
                BEGIN
                    UPDATE Requisition_Summary SET
                        requester_name = NEW.name,
                        requester_group = COALESCE(NEW.grade_level, NEW.department, ''),
                        grade_level = NEW.grade_level,
                        section = NEW.section,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE requisition_id IN (SELECT id FROM Requisitions WHERE requester_id = NEW.id);
                END
                """,
            ),
            (
                "trg_requisition_summary_after_req_delete",
                """
                CREATE TRIGGER IF NOT EXISTS trg_requisition_summary_after_req_delete
                AFTER DELETE ON Requisitions
                BEGIN
                    DELETE FROM Requisition_Summary WHERE requisition_id = OLD.id;
                END
                """,
            ),
        ]

        with db.get_connection() as conn:
            for name, sql in triggers:
                try:
                    conn.execute(sql)
                except Exception:
                    pass  # Tables may not exist yet - triggers will be created by schema.sql
            conn.commit()

        logger.debug("Summary table triggers created (if tables exist)")

    def _start_refresh_thread(self) -> None:
        """Start the background refresh thread."""
        self._refresh_thread = threading.Thread(
            target=self._refresh_loop,
            daemon=True,
            name="SummaryTablesRefresh",
        )
        self._refresh_thread.start()

    def _refresh_loop(self) -> None:
        """Background loop for periodic refresh."""
        while not self._stop_refresh.is_set():
            try:
                time.sleep(self.REFRESH_INTERVAL_SECONDS)
                if not self._stop_refresh.is_set():
                    self.refresh_all()
            except Exception as e:
                logger.error(f"Error in summary tables refresh loop: {e}")

    def refresh_all(self) -> bool:
        """
        Refresh all summary tables from source data.

        Returns:
            True if successful, False otherwise
        """
        try:
            self._refresh_stock_summary()
            self._refresh_requisition_summary()
            self._refresh_statistics_aggregate()
            self._last_refresh = datetime.now()
            self._stats_cache = None
            logger.debug("All summary tables refreshed successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to refresh summary tables: {e}")
            return False

    def _refresh_stock_summary(self) -> None:
        """Refresh stock summary table from source data."""
        query = """
        INSERT OR REPLACE INTO Stock_Summary (
            item_id, item_name, category_name, total_batches,
            original_stock, consumed_qty, disposed_qty, returned_qty,
            total_stock, is_low_stock, is_out_of_stock, last_updated
        )
        SELECT
            i.id,
            i.name,
            COALESCE(c.name, 'Uncategorized'),
            COALESCE(batch_info.total_batches, 0),
            COALESCE(batch_info.original_stock, 0),
            COALESCE(movements.consumed_qty, 0),
            COALESCE(movements.disposed_qty, 0),
            COALESCE(movements.returned_qty, 0),
            COALESCE(batch_info.original_stock, 0)
                - COALESCE(movements.consumed_qty, 0)
                - COALESCE(movements.disposed_qty, 0)
                + COALESCE(movements.returned_qty, 0) as total_stock,
            CASE
                WHEN COALESCE(batch_info.original_stock, 0)
                    - COALESCE(movements.consumed_qty, 0)
                    - COALESCE(movements.disposed_qty, 0)
                    + COALESCE(movements.returned_qty, 0) BETWEEN 1 AND 10 THEN 1
                ELSE 0
            END as is_low_stock,
            CASE
                WHEN COALESCE(batch_info.original_stock, 0)
                    - COALESCE(movements.consumed_qty, 0)
                    - COALESCE(movements.disposed_qty, 0)
                    + COALESCE(movements.returned_qty, 0) <= 0 THEN 1
                ELSE 0
            END as is_out_of_stock,
            CURRENT_TIMESTAMP
        FROM Items i
        LEFT JOIN Categories c ON i.category_id = c.id
        LEFT JOIN (
            SELECT
                item_id,
                COUNT(*) as total_batches,
                SUM(quantity_received) as original_stock
            FROM Item_Batches
            WHERE disposal_date IS NULL
            GROUP BY item_id
        ) batch_info ON i.id = batch_info.item_id
        LEFT JOIN (
            SELECT
                item_id,
                SUM(CASE WHEN movement_type = ? THEN quantity ELSE 0 END) as consumed_qty,
                SUM(CASE WHEN movement_type = ? THEN quantity ELSE 0 END) as disposed_qty,
                SUM(CASE WHEN movement_type = ? THEN quantity ELSE 0 END) as returned_qty
            FROM Stock_Movements
            GROUP BY item_id
        ) movements ON i.id = movements.item_id
        """
        params = (
            MovementType.CONSUMPTION.value,
            MovementType.DISPOSAL.value,
            MovementType.RETURN.value,
        )

        db.execute_update(query, params)

        query_missing = """
        DELETE FROM Stock_Summary WHERE item_id NOT IN (SELECT id FROM Items)
        """
        db.execute_update(query_missing)

    def _refresh_requisition_summary(self) -> None:
        """Refresh requisition summary table from source data."""
        query = """
        INSERT OR REPLACE INTO Requisition_Summary (
            requisition_id, requester_name, requester_group, grade_level, section,
            status, lab_activity_name, lab_activity_date, expected_return,
            item_count, total_quantity_requested, num_students, num_groups, last_updated
        )
        SELECT
            r.id,
            COALESCE(req.name, 'Unknown'),
            COALESCE(req.grade_level, req.department, ''),
            req.grade_level,
            req.section,
            r.status,
            r.lab_activity_name,
            r.lab_activity_date,
            r.expected_return,
            COALESCE(ri.item_count, 0),
            COALESCE(ri.total_qty, 0),
            r.num_students,
            r.num_groups,
            CURRENT_TIMESTAMP
        FROM Requisitions r
        LEFT JOIN Requesters req ON r.requester_id = req.id
        LEFT JOIN (
            SELECT
                requisition_id,
                COUNT(*) as item_count,
                SUM(quantity_requested) as total_qty
            FROM Requisition_Items
            GROUP BY requisition_id
        ) ri ON r.id = ri.requisition_id
        """

        db.execute_update(query)

        query_missing = """
        DELETE FROM Requisition_Summary WHERE requisition_id NOT IN (SELECT id FROM Requisitions)
        """
        db.execute_update(query_missing)

    def _refresh_statistics_aggregate(self) -> None:
        """Refresh statistics aggregate table."""
        query = """
        UPDATE Statistics_Aggregate SET
            total_items = (SELECT COUNT(*) FROM Items WHERE id NOT IN (SELECT item_id FROM Disposal_History)),
            total_batches = (SELECT COUNT(*) FROM Item_Batches WHERE disposal_date IS NULL),
            total_original_stock = COALESCE((SELECT SUM(quantity_received) FROM Item_Batches WHERE disposal_date IS NULL), 0),
            total_consumed = COALESCE((SELECT SUM(quantity) FROM Stock_Movements WHERE movement_type = ?), 0),
            total_disposed = COALESCE((SELECT SUM(quantity) FROM Stock_Movements WHERE movement_type = ?), 0),
            total_returned = COALESCE((SELECT SUM(quantity) FROM Stock_Movements WHERE movement_type = ?), 0),
            total_stock = (
                COALESCE((SELECT SUM(quantity_received) FROM Item_Batches WHERE disposal_date IS NULL), 0)
                - COALESCE((SELECT SUM(quantity) FROM Stock_Movements WHERE movement_type = ?), 0)
                - COALESCE((SELECT SUM(quantity) FROM Stock_Movements WHERE movement_type = ?), 0)
                + COALESCE((SELECT SUM(quantity) FROM Stock_Movements WHERE movement_type = ?), 0)
            ),
            low_stock_count = (SELECT COUNT(*) FROM Stock_Summary WHERE is_low_stock = 1),
            out_of_stock_count = (SELECT COUNT(*) FROM Stock_Summary WHERE is_out_of_stock = 1),
            active_requisitions = (SELECT COUNT(*) FROM Requisitions WHERE status IN ('requested', 'active')),
            overdue_requisitions = (SELECT COUNT(*) FROM Requisitions WHERE status != 'returned' AND expected_return < date('now')),
            expiring_soon_count = (
                SELECT COUNT(DISTINCT i.id) FROM Items i
                INNER JOIN Item_Batches ib ON ib.item_id = i.id
                WHERE ib.disposal_date IS NULL
                AND i.expiration_date IS NOT NULL
                AND i.expiration_date BETWEEN date('now') AND date('now', '+30 days')
            ),
            calibration_due_count = (
                SELECT COUNT(*) FROM Items
                WHERE calibration_date IS NOT NULL
                AND calibration_date BETWEEN date('now') AND date('now', '+30 days')
            ),
            last_updated = CURRENT_TIMESTAMP
        WHERE id = 1
        """
        params = (
            MovementType.CONSUMPTION.value,
            MovementType.DISPOSAL.value,
            MovementType.RETURN.value,
            MovementType.CONSUMPTION.value,
            MovementType.DISPOSAL.value,
            MovementType.RETURN.value,
        )

        db.execute_update(query, params)

    def get_stock_summary(self, item_id: int) -> Optional[StockSummary]:
        """
        Get stock summary for a single item.

        Args:
            item_id: The item ID

        Returns:
            StockSummary object or None if not found
        """
        query = "SELECT * FROM Stock_Summary WHERE item_id = ?"
        rows = db.execute_query(query, (item_id,))

        if not rows:
            return None

        row = rows[0]
        return StockSummary(
            item_id=row["item_id"],
            item_name=row["item_name"],
            category_name=row["category_name"],
            total_batches=row["total_batches"],
            original_stock=row["original_stock"],
            consumed_qty=row["consumed_qty"],
            disposed_qty=row["disposed_qty"],
            returned_qty=row["returned_qty"],
            total_stock=row["total_stock"],
            low_stock_threshold=row["low_stock_threshold"],
            is_low_stock=bool(row["is_low_stock"]),
            is_out_of_stock=bool(row["is_out_of_stock"]),
            last_updated=datetime.fromisoformat(row["last_updated"])
            if row["last_updated"]
            else None,
        )

    def get_all_stock_summaries(
        self,
        low_stock_only: bool = False,
        out_of_stock_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> List[StockSummary]:
        """
        Get all stock summaries with optional filtering.

        Args:
            low_stock_only: Filter for low stock items only
            out_of_stock_only: Filter for out of stock items only
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of StockSummary objects
        """
        conditions = []
        if low_stock_only:
            conditions.append("is_low_stock = 1")
        if out_of_stock_only:
            conditions.append("is_out_of_stock = 1")

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        query = f"""
        SELECT * FROM Stock_Summary
        {where_clause}
        ORDER BY total_stock ASC
        LIMIT ? OFFSET ?
        """
        rows = db.execute_query(query, (limit, offset))

        summaries = []
        for row in rows:
            summaries.append(
                StockSummary(
                    item_id=row["item_id"],
                    item_name=row["item_name"],
                    category_name=row["category_name"],
                    total_batches=row["total_batches"],
                    original_stock=row["original_stock"],
                    consumed_qty=row["consumed_qty"],
                    disposed_qty=row["disposed_qty"],
                    returned_qty=row["returned_qty"],
                    total_stock=row["total_stock"],
                    low_stock_threshold=row["low_stock_threshold"],
                    is_low_stock=bool(row["is_low_stock"]),
                    is_out_of_stock=bool(row["is_out_of_stock"]),
                    last_updated=datetime.fromisoformat(row["last_updated"])
                    if row["last_updated"]
                    else None,
                )
            )
        return summaries

    def get_requisition_summary(
        self, requisition_id: int
    ) -> Optional[RequisitionSummary]:
        """
        Get requisition summary for a single requisition.

        Args:
            requisition_id: The requisition ID

        Returns:
            RequisitionSummary object or None if not found
        """
        query = "SELECT * FROM Requisition_Summary WHERE requisition_id = ?"
        rows = db.execute_query(query, (requisition_id,))

        if not rows:
            return None

        row = rows[0]
        return RequisitionSummary(
            requisition_id=row["requisition_id"],
            requester_name=row["requester_name"],
            requester_group=row["requester_group"],
            grade_level=row["grade_level"],
            section=row["section"],
            status=row["status"],
            lab_activity_name=row["lab_activity_name"],
            lab_activity_date=row["lab_activity_date"],
            expected_return=row["expected_return"],
            item_count=row["item_count"],
            item_summary_json=row["item_summary_json"] or "[]",
            total_quantity_requested=row["total_quantity_requested"],
            num_students=row["num_students"],
            num_groups=row["num_groups"],
            last_updated=datetime.fromisoformat(row["last_updated"])
            if row["last_updated"]
            else None,
        )

    def get_statistics_aggregate(self, use_cache: bool = True) -> StatisticsAggregate:
        """
        Get pre-computed statistics aggregate.

        Args:
            use_cache: Use cached result if available (TTL: 30 seconds)

        Returns:
            StatisticsAggregate object
        """
        if use_cache and self._stats_cache is not None:
            age = time.monotonic() - self._stats_cache_time
            if age < 30.0:
                return self._stats_cache

        query = "SELECT * FROM Statistics_Aggregate WHERE id = 1"
        rows = db.execute_query(query)

        if rows:
            row = rows[0]
            result = StatisticsAggregate(
                total_items=row["total_items"],
                total_batches=row["total_batches"],
                total_original_stock=row["total_original_stock"],
                total_consumed=row["total_consumed"],
                total_disposed=row["total_disposed"],
                total_returned=row["total_returned"],
                total_stock=row["total_stock"],
                low_stock_count=row["low_stock_count"],
                out_of_stock_count=row["out_of_stock_count"],
                active_requisitions=row["active_requisitions"],
                overdue_requisitions=row["overdue_requisitions"],
                expiring_soon_count=row["expiring_soon_count"],
                calibration_due_count=row["calibration_due_count"],
                last_updated=datetime.fromisoformat(row["last_updated"])
                if row["last_updated"]
                else None,
            )
        else:
            result = StatisticsAggregate()

        self._stats_cache = result
        self._stats_cache_time = time.monotonic()
        return result

    def backfill_summaries(self) -> Dict[str, int]:
        """
        Backfill summary tables with existing data.
        Use this when summary tables are created after data exists.

        Returns:
            Dictionary with counts of processed records
        """
        results = {"stock_summaries": 0, "requisition_summaries": 0}

        try:
            self._refresh_stock_summary()
            results["stock_summaries"] = db.execute_query(
                "SELECT COUNT(*) as cnt FROM Stock_Summary"
            )[0]["cnt"]

            self._refresh_requisition_summary()
            results["requisition_summaries"] = db.execute_query(
                "SELECT COUNT(*) as cnt FROM Requisition_Summary"
            )[0]["cnt"]

            self._refresh_statistics_aggregate()

            logger.info(f"Summary tables backfilled: {results}")
        except Exception as e:
            logger.error(f"Failed to backfill summaries: {e}")

        return results

    def get_last_refresh_time(self) -> Optional[datetime]:
        """Get the last time summary tables were refreshed."""
        return self._last_refresh

    def get_service_status(self) -> Dict[str, Any]:
        """Get service status for monitoring."""
        try:
            stats = self.get_statistics_aggregate()
            stock_count = db.execute_query("SELECT COUNT(*) as cnt FROM Stock_Summary")[
                0
            ]["cnt"]
            requisition_count = db.execute_query(
                "SELECT COUNT(*) as cnt FROM Requisition_Summary"
            )[0]["cnt"]

            return {
                "initialized": self._initialized,
                "refresh_thread_alive": self._refresh_thread.is_alive()
                if self._refresh_thread
                else False,
                "last_refresh": self._last_refresh.isoformat()
                if self._last_refresh
                else None,
                "stock_summaries_count": stock_count,
                "requisition_summaries_count": requisition_count,
                "statistics": {
                    "total_items": stats.total_items,
                    "total_stock": stats.total_stock,
                    "low_stock_count": stats.low_stock_count,
                    "out_of_stock_count": stats.out_of_stock_count,
                    "active_requisitions": stats.active_requisitions,
                },
            }
        except Exception as e:
            logger.error(f"Failed to get service status: {e}")
            return {"error": str(e)}


summary_tables_service = SummaryTablesService()
