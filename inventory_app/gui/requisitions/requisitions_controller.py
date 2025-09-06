"""
Requisitions controller - handles business logic for requisition management.
Provides CRUD operations for requisitions, requesters, and requisition items.
Uses composition pattern with DatabaseConnection.
"""

from typing import List, Dict, Optional
from datetime import date, datetime
from dataclasses import dataclass
import time

from inventory_app.database.connection import db
from inventory_app.database.models import Requester, Requisition
from inventory_app.services import ItemService
from inventory_app.utils.logger import logger


@dataclass
class RequisitionSummary:
    """Summary data for a requisition including requester and items."""
    requisition: Requisition
    requester: Requester
    items: List[Dict]  # List of item details with quantities
    total_items: int
    status: str  # 'Active', 'Returned', 'Overdue'

class RequisitionsController:
    """
    Controller for requisition management operations.
    Handles business logic for requesting workflow.
    """

    def __init__(self):
        """Initialize controller with composed services."""
        # Compose with services using composition pattern
        self.item_service = ItemService()

        logger.info("Requisitions controller initialized with services")

    def get_all_requisitions(self) -> List[RequisitionSummary]:
        """
        Get all requisitions with requester and item details.
        OPTIMIZED: Uses single query with JOINs instead of N+1 queries.

        Returns:
            List of requisition summaries
        """
        try:
            # Single optimized query to get all requisitions with items and requesters
            query = """
            SELECT
                r.id as req_id,
                r.requester_id,
                r.lab_activity_name,
                r.lab_activity_date,
                r.datetime_requested,
                r.expected_request,
                r.expected_return,
                r.num_students,
                r.num_groups,
                r.status as req_status,
                req.name as requester_name,
                req.affiliation,
                req.group_name,
                ri.item_id,
                ri.quantity_requested,
                i.name as item_name,
                i.category_id,
                i.size,
                i.brand,
                c.name as category_name,
                s.name as supplier_name
            FROM Requisitions r
            JOIN Requesters req ON r.requester_id = req.id
            LEFT JOIN Requisition_Items ri ON r.id = ri.requisition_id
            LEFT JOIN Items i ON ri.item_id = i.id
            LEFT JOIN Categories c ON i.category_id = c.id
            LEFT JOIN Suppliers s ON i.supplier_id = s.id
            ORDER BY r.datetime_requested DESC, r.id, ri.item_id
            """

            rows = db.execute_query(query)
            if not rows:
                logger.info("No requisitions found")
                return []

            # Group results by requisition
            requisition_groups = {}
            for row in rows:
                req_id = row['req_id']

                if req_id not in requisition_groups:
                    # Create requisition object with proper date conversion
                    req_dict = {
                        'id': req_id,
                        'requester_id': row['requester_id'],
                        'lab_activity_name': row['lab_activity_name'],
                        'lab_activity_date': date.fromisoformat(row['lab_activity_date']) if row['lab_activity_date'] else date.today(),
                        'datetime_requested': datetime.fromisoformat(row['datetime_requested']) if row['datetime_requested'] else None,
                        'expected_request': datetime.fromisoformat(row['expected_request']) if row['expected_request'] else datetime.now(),
                        'expected_return': datetime.fromisoformat(row['expected_return']) if row['expected_return'] else datetime.now(),
                        'num_students': row['num_students'],
                        'num_groups': row['num_groups'],
                        'status': row['req_status']
                    }
                    requisition = Requisition(**req_dict)

                    # Create requester object
                    requester_dict = {
                        'id': row['requester_id'],
                        'name': row['requester_name'],
                        'affiliation': row['affiliation'],
                        'group_name': row['group_name']
                    }
                    requester = Requester(**requester_dict)

                    requisition_groups[req_id] = {
                        'requisition': requisition,
                        'requester': requester,
                        'items': [],
                        'status': row['req_status'] or "Active"
                    }

                # Add item if it exists (some requisitions might have no items)
                if row['item_id']:
                    item_dict = {
                        'item_id': row['item_id'],
                        'quantity_requested': row['quantity_requested'],
                        'name': row['item_name'],
                        'category_id': row['category_id'],
                        'size': row['size'],
                        'brand': row['brand'],
                        'category_name': row['category_name'],
                        'supplier_name': row['supplier_name']
                    }
                    requisition_groups[req_id]['items'].append(item_dict)

            # Convert to RequisitionSummary objects
            summaries = []
            for req_data in requisition_groups.values():
                summary = RequisitionSummary(
                    requisition=req_data['requisition'],
                    requester=req_data['requester'],
                    items=req_data['items'],
                    total_items=sum(item['quantity_requested'] for item in req_data['items']),
                    status=req_data['status']
                )
                summaries.append(summary)

            logger.info(f"Retrieved {len(summaries)} requisitions with optimized single query")
            return summaries

        except Exception as e:
            logger.error(f"Failed to get requisitions: {e}")
            return []

    def delete_requisition(self, requisition_id: int, editor_name: str) -> bool:
        """
        Delete a requisition and all its dependent records in proper order.

        Args:
            requisition_id: ID of requisition to delete
            editor_name: Name of person deleting

        Returns:
            bool: True if successful
        """
        try:
            # Step 1: Delete requisition history records first (simple DELETE)
            self._delete_requisition_history(requisition_id)
            time.sleep(0.1)

            # Step 2: Delete requisition items (removes FK references to requisition)
            db.execute_update("DELETE FROM Requisition_Items WHERE requisition_id = ?", (requisition_id,))
            time.sleep(0.1)

            # Step 3: Delete ALL stock movements for this requisition
            db.execute_update("DELETE FROM Stock_Movements WHERE source_id = ?", (requisition_id,))
            time.sleep(0.1)

            # Step 4: Finally delete the requisition itself
            success = db.execute_update("DELETE FROM Requisitions WHERE id = ?", (requisition_id,))

            if success:
                logger.info(f"Successfully deleted requisition {requisition_id} and all dependencies")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to delete requisition {requisition_id}: {e}")
            return False

    def get_requesters(self) -> List[Requester]:
        """
        Get all requesters.

        Returns:
            List of requesters
        """
        try:
            return Requester.get_all()
        except Exception as e:
            logger.error(f"Failed to get requesters: {e}")
            return []

    def get_requesters_with_requisitions(self) -> List[Requester]:
        """
        Get only requesters that have created requisitions.

        Returns:
            List of requesters who have active requisitions
        """
        try:
            query = """
            SELECT DISTINCT b.* FROM Requesters b
            JOIN Requisitions r ON b.id = r.requester_id
            ORDER BY b.name
            """
            rows = db.execute_query(query)
            requesters = []
            for row in rows:
                requesters.append(Requester(**dict(row)))
            logger.info(f"Retrieved {len(requesters)} requesters with requisitions")
            return requesters
        except Exception as e:
            logger.error(f"Failed to get requesters with requisitions: {e}")
            return []

    def _get_requisition_by_id(self, requisition_id: int) -> Optional[Requisition]:
        """Get a single requisition by ID."""
        try:
            query = "SELECT * FROM Requisitions WHERE id = ?"
            rows = db.execute_query(query, (requisition_id,))
            if not rows:
                return None

            req_dict = dict(rows[0])
            # Convert dates
            if req_dict.get('date_requested'):
                req_dict['date_requested'] = date.fromisoformat(req_dict['date_requested'])
            if req_dict.get('lab_activity_date'):
                req_dict['lab_activity_date'] = date.fromisoformat(req_dict['lab_activity_date'])

            return Requisition(**req_dict)
        except Exception as e:
            logger.error(f"Failed to get requisition {requisition_id}: {e}")
            return None

    def _delete_requisition_history(self, requisition_id: int) -> None:
        """Delete all history records for a requisition."""
        try:
            query = "DELETE FROM Requisition_History WHERE requisition_id = ?"
            db.execute_update(query, (requisition_id,))
            logger.debug(f"Deleted history records for requisition {requisition_id}")
        except Exception as e:
            logger.error(f"Failed to delete requisition history for {requisition_id}: {e}")

    def _clear_requisition_items(self, requisition_id: int) -> None:
        """Remove all items from a requisition."""
        try:
            db.execute_update("DELETE FROM Requisition_Items WHERE requisition_id = ?", (requisition_id,))
        except Exception as e:
            logger.error(f"Failed to clear requisition items: {e}")
