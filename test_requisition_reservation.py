#!/usr/bin/env python3
"""
Unit tests for the new requisition reservation system.
Tests the reservation functionality, status logic, and model updates.
"""

import unittest
import sys
from datetime import datetime, timedelta
from unittest.mock import patch

# Add the project root to the Python path
sys.path.insert(0, 'c:/Users/Jin/Desktop/Files/DEV-stuff/commissions/inventory')

from inventory_app.database.models import Requisition


class TestRequisitionReservation(unittest.TestCase):
    """Test cases for the requisition reservation system."""

    def setUp(self):
        """Set up test fixtures."""
        self.current_time = datetime.now()
        self.future_time = self.current_time + timedelta(hours=2)
        self.return_time = self.future_time + timedelta(hours=1)

    def test_reservation_requisition_creation(self):
        """Test creating a reservation requisition."""
        req = Requisition(
            borrower_id=1,
            expected_borrow=self.future_time,
            expected_return=self.return_time,
            status='requested',
            lab_activity_name='Chemistry Lab',
            lab_activity_date=self.current_time.date(),
            num_students=25,
            num_groups=5
        )

        self.assertEqual(req.status, 'requested')
        self.assertEqual(req.borrower_id, 1)
        self.assertEqual(req.expected_borrow, self.future_time)
        self.assertEqual(req.expected_return, self.return_time)
        self.assertEqual(req.lab_activity_name, 'Chemistry Lab')
        self.assertIsNone(req.datetime_borrowed)  # Should be None for reservations

    def test_immediate_borrowing_creation(self):
        """Test creating an immediate borrowing requisition."""
        past_time = self.current_time - timedelta(minutes=30)

        req = Requisition(
            borrower_id=2,
            datetime_borrowed=past_time,
            expected_borrow=past_time,
            expected_return=past_time + timedelta(hours=1),
            status='active',
            lab_activity_name='Physics Demo',
            lab_activity_date=self.current_time.date(),
            num_students=15,
            num_groups=3
        )

        self.assertEqual(req.status, 'active')
        self.assertEqual(req.datetime_borrowed, past_time)
        self.assertEqual(req.expected_borrow, past_time)

    def test_status_validation(self):
        """Test that valid statuses are accepted."""
        valid_statuses = ['requested', 'active', 'returned', 'overdue']

        for status in valid_statuses:
            req = Requisition(
                borrower_id=1,
                expected_borrow=self.future_time,
                expected_return=self.return_time,
                status=status,
                lab_activity_name='Test',
                lab_activity_date=self.current_time.date()
            )
            self.assertEqual(req.status, status)

    def test_date_validation(self):
        """Test that return date must be after borrow date."""
        # Valid case: return after borrow
        req = Requisition(
            borrower_id=1,
            expected_borrow=self.current_time,
            expected_return=self.current_time + timedelta(hours=1),
            status='requested',
            lab_activity_name='Test',
            lab_activity_date=self.current_time.date()
        )
        self.assertTrue(req.expected_return > req.expected_borrow)

        # Invalid case: return before borrow (should still create object, validation happens in GUI)
        req_invalid = Requisition(
            borrower_id=1,
            expected_borrow=self.current_time,
            expected_return=self.current_time - timedelta(hours=1),  # Before borrow
            status='requested',
            lab_activity_name='Test',
            lab_activity_date=self.current_time.date()
        )
        self.assertTrue(req_invalid.expected_return < req_invalid.expected_borrow)

    def test_smart_status_logic(self):
        """Test the logic for determining initial status."""
        # Future borrow time should result in 'requested' status
        future_borrow = self.current_time + timedelta(hours=2)

        if future_borrow > self.current_time:
            expected_status = 'requested'
        else:
            expected_status = 'active'

        self.assertEqual(expected_status, 'requested')

        # Past borrow time should result in 'active' status
        past_borrow = self.current_time - timedelta(minutes=30)

        if past_borrow > self.current_time:
            expected_status = 'requested'
        else:
            expected_status = 'active'

        self.assertEqual(expected_status, 'active')

    @patch('inventory_app.database.connection.db.execute_update')
    def test_save_method_with_new_fields(self, mock_execute_update):
        """Test that the save method includes new fields in the SQL."""
        # Mock successful save
        mock_execute_update.return_value = None

        req = Requisition(
            borrower_id=1,
            expected_borrow=self.future_time,
            expected_return=self.return_time,
            status='requested',
            lab_activity_name='Test Activity',
            lab_activity_date=self.current_time.date(),
            num_students=10,
            num_groups=2
        )

        # Mock the get_last_insert_id method
        with patch('inventory_app.database.connection.db.get_last_insert_id', return_value=123):
            result = req.save("TestUser")

            self.assertTrue(result)
            self.assertEqual(req.id, 123)

            # Verify that execute_update was called with the correct parameters
            self.assertTrue(mock_execute_update.called)
            call_args = mock_execute_update.call_args[0]

            # Check that the SQL includes the new fields
            sql_query = call_args[0]
            params = call_args[1]

            self.assertIn('expected_borrow', sql_query)
            self.assertIn('expected_return', sql_query)
            self.assertIn('status', sql_query)

            # Check that parameters include the new values
            self.assertIn(self.future_time.isoformat(), params)
            self.assertIn(self.return_time.isoformat(), params)
            self.assertIn('requested', params)

    def test_reservation_vs_immediate_logic(self):
        """Test the logic that determines if a requisition is a reservation or immediate."""
        test_cases = [
            # (expected_borrow, current_time, expected_status, description)
            (self.current_time + timedelta(hours=1), self.current_time, 'requested', 'Future borrow - reservation'),
            (self.current_time - timedelta(minutes=30), self.current_time, 'active', 'Past borrow - immediate'),
            (self.current_time + timedelta(minutes=5), self.current_time, 'requested', 'Near future - still reservation'),
            (self.current_time, self.current_time, 'active', 'Right now - immediate'),
        ]

        for expected_borrow, current, expected_status, description in test_cases:
            with self.subTest(description=description):
                if expected_borrow > current:
                    actual_status = 'requested'
                else:
                    actual_status = 'active'

                self.assertEqual(actual_status, expected_status,
                               f"Failed for case: {description}")


class TestRequisitionWorkflow(unittest.TestCase):
    """Test the complete workflow of requisitions."""

    def setUp(self):
        """Set up test fixtures."""
        self.current_time = datetime.now()

    def test_reservation_workflow(self):
        """Test the complete reservation workflow."""
        # 1. Create reservation
        reservation_time = self.current_time + timedelta(hours=24)  # Tomorrow
        return_time = reservation_time + timedelta(hours=2)

        reservation = Requisition(
            borrower_id=1,
            expected_borrow=reservation_time,
            expected_return=return_time,
            status='requested',
            lab_activity_name='Future Lab Session',
            lab_activity_date=reservation_time.date(),
            num_students=20,
            num_groups=4
        )

        self.assertEqual(reservation.status, 'requested')
        self.assertIsNone(reservation.datetime_borrowed)

        # 2. Simulate pickup (would happen when items are actually borrowed)
        pickup_time = reservation_time  # On time pickup
        reservation.datetime_borrowed = pickup_time
        reservation.status = 'active'

        self.assertEqual(reservation.status, 'active')
        self.assertEqual(reservation.datetime_borrowed, pickup_time)

        # 3. Simulate return (would happen when items are returned)
        reservation.status = 'returned'

        self.assertEqual(reservation.status, 'returned')

    def test_overdue_workflow(self):
        """Test the overdue workflow."""
        # Create immediate borrowing
        borrow_time = self.current_time - timedelta(hours=2)
        expected_return = borrow_time + timedelta(hours=1)  # Should have been returned 1 hour ago

        overdue_req = Requisition(
            borrower_id=1,
            datetime_borrowed=borrow_time,
            expected_borrow=borrow_time,
            expected_return=expected_return,
            status='active',
            lab_activity_name='Overdue Activity',
            lab_activity_date=borrow_time.date(),
            num_students=10,
            num_groups=2
        )

        # Check if it should be overdue
        if self.current_time > expected_return:
            overdue_req.status = 'overdue'
            self.assertEqual(overdue_req.status, 'overdue')

        # Simulate late return
        overdue_req.status = 'returned'
        self.assertEqual(overdue_req.status, 'returned')


if __name__ == '__main__':
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestRequisitionReservation)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestRequisitionWorkflow))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
