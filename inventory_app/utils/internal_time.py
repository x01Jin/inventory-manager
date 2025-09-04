"""
Simple date/time utilities and manual status checking for the inventory application.
Provides clean date/time display functionality and manual database status updates.
"""

from datetime import datetime
from inventory_app.database.connection import db
from inventory_app.utils.logger import logger


def get_current_datetime_string() -> str:
    """Get current date and time as formatted string for navigation display."""
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")


def get_current_date_string() -> str:
    """Get current date as formatted string."""
    now = datetime.now()
    return now.strftime("%Y-%m-%d")


def get_current_time_string() -> str:
    """Get current time as formatted string."""
    now = datetime.now()
    return now.strftime("%H:%M:%S")


def check_and_update_requisition_statuses():
    """
    Manual status check - updates requisition statuses based on current time.
    Called during manual refresh operations to ensure status accuracy.
    """
    try:
        now = datetime.now()

        # Get all requisitions that might need status updates
        query = """
        SELECT id, status, expected_return, expected_request, datetime_requested
        FROM Requisitions
        WHERE status IN ('requested', 'active', 'overdue')
        AND (expected_return IS NOT NULL OR expected_request IS NOT NULL)
        """
        rows = db.execute_query(query)

        if not rows:
            return 0

        updated_count = 0

        for row in rows:
            req_id = row['id']
            current_status = row['status']

            # Determine expected status
            expected_status = _calculate_expected_status(row, now)

            if expected_status and expected_status != current_status:
                # Update status in database
                _update_requisition_status(req_id, expected_status)
                updated_count += 1

        return updated_count

    except Exception as e:
        logger.error(f"💥 Failed to perform manual status check: {e}")
        import traceback
        logger.error(f"💥 Traceback: {traceback.format_exc()}")
        return 0


def _calculate_expected_status(requisition: dict, current_time: datetime) -> str | None:
    """Calculate what the status should be based on current time."""
    status = requisition['status']

    if status == 'requested':
        # Check if reservation should become active
        expected_request = requisition.get('expected_request')
        if expected_request:
            if isinstance(expected_request, str):
                expected_request = datetime.fromisoformat(expected_request)
            if current_time >= expected_request:
                return 'active'

    elif status == 'active':
        # Check if active requisition should go back to requested (if expected_request is extended)
        expected_request = requisition.get('expected_request')
        if expected_request:
            if isinstance(expected_request, str):
                expected_request = datetime.fromisoformat(expected_request)
            if current_time < expected_request:
                return 'requested'

        # Check if active requisition should become overdue
        expected_return = requisition.get('expected_return')
        if expected_return:
            if isinstance(expected_return, str):
                expected_return = datetime.fromisoformat(expected_return)

            # Check if all items have been returned
            if not _check_all_items_returned(requisition['id']) and current_time >= expected_return:
                return 'overdue'

    elif status == 'overdue':
        # Check if overdue requisition should become active again
        expected_return = requisition.get('expected_return')
        if expected_return:
            if isinstance(expected_return, str):
                expected_return = datetime.fromisoformat(expected_return)

            # If expected_return is now in the future and items not fully returned
            if current_time < expected_return and not _check_all_items_returned(requisition['id']):
                return 'active'

    return None


def _check_all_items_returned(req_id: int) -> bool:
    """Check if all items in a requisition have been returned."""
    try:
        query = """
        SELECT COUNT(*) as total_items,
               COUNT(CASE WHEN returned_qty >= requested_qty THEN 1 END) as returned_items
        FROM (
            SELECT ri.item_id, ri.quantity_requested as requested_qty,
                   COALESCE(SUM(sm.quantity), 0) as returned_qty
            FROM Requisition_Items ri
            LEFT JOIN Stock_Movements sm ON sm.item_id = ri.item_id
                AND sm.source_id = ri.requisition_id
                AND sm.movement_type = 'RETURN'
            WHERE ri.requisition_id = ?
            GROUP BY ri.item_id, ri.quantity_requested
        )
        """
        rows = db.execute_query(query, (req_id,))
        if rows:
            return rows[0]['returned_items'] == rows[0]['total_items']
        return True
    except Exception as e:
        logger.error(f"Error checking returned items for requisition {req_id}: {e}")
        return False


def _update_requisition_status(req_id: int, new_status: str) -> None:
    """Update the status of a requisition in the database."""
    try:
        # Update status
        update_query = """
        UPDATE Requisitions
        SET status = ?
        WHERE id = ?
        """
        db.execute_update(update_query, (new_status, req_id))

        # If activating a reservation, also set datetime_requested
        if new_status == 'active':
            request_update = """
            UPDATE Requisitions
            SET datetime_requested = ?
            WHERE id = ? AND datetime_requested IS NULL
            """
            db.execute_update(request_update, (datetime.now(), req_id))

        # If setting back to requested, clear datetime_requested
        if new_status == 'requested':
            request_clear = """
            UPDATE Requisitions
            SET datetime_requested = NULL
            WHERE id = ?
            """
            db.execute_update(request_clear, (req_id,))

        # Log the status change
        reason = f"Manual status update to {new_status}"
        history_query = """
        INSERT INTO Requisition_History (requisition_id, editor_name, reason)
        VALUES (?, 'System', ?)
        """
        db.execute_update(history_query, (req_id, reason))

    except Exception as e:
        logger.error(f"Error updating status for requisition {req_id}: {e}")
