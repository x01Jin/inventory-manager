from datetime import datetime, timedelta, date

from inventory_app.services.validation_service import ValidationService


def make_iso(dt: datetime):
    return dt.isoformat()


def test_valid_requisition_creation_passes():
    svc = ValidationService()
    requester_id = 1
    start = datetime.now()
    end = start + timedelta(hours=2)
    requisition_data = {
        "date_requested": make_iso(start),
        "expected_return": make_iso(end),
        "lab_activity_name": "Test Activity",
        "lab_activity_date": date.today().isoformat(),
    }
    items_data = [{"item_id": 1, "quantity_requested": 2}]
    assert (
        svc.validate_requisition_creation(requester_id, requisition_data, items_data)
        is True
    )


def test_invalid_quantity_fails():
    svc = ValidationService()
    requester_id = 1
    start = datetime.now()
    end = start + timedelta(hours=1)
    requisition_data = {
        "date_requested": make_iso(start),
        "expected_return": make_iso(end),
        "lab_activity_name": "Test Activity",
        "lab_activity_date": date.today().isoformat(),
    }
    items_data = [{"item_id": 1, "quantity_requested": 0}]
    assert (
        svc.validate_requisition_creation(requester_id, requisition_data, items_data)
        is False
    )
    assert "Invalid quantity" in (svc.get_last_error() or "")


def test_exceed_max_quantity_fails():
    svc = ValidationService()
    requester_id = 1
    start = datetime.now()
    end = start + timedelta(hours=1)
    requisition_data = {
        "date_requested": make_iso(start),
        "expected_return": make_iso(end),
        "lab_activity_name": "Test Activity",
        "lab_activity_date": date.today().isoformat(),
    }
    items_data = [{"item_id": 1, "quantity_requested": svc.MAX_QUANTITY + 1}]
    assert (
        svc.validate_requisition_creation(requester_id, requisition_data, items_data)
        is False
    )
    assert "exceeds maximum" in (svc.get_last_error() or "")


def test_invalid_date_format_fails():
    svc = ValidationService()
    requester_id = 1
    requisition_data = {
        "date_requested": "not-a-date",
        "expected_return": "also-not-a-date",
        "lab_activity_name": "Test Activity",
        "lab_activity_date": "also-not-a-date",
    }
    items_data = [{"item_id": 1, "quantity_requested": 2}]
    assert (
        svc.validate_requisition_creation(requester_id, requisition_data, items_data)
        is False
    )
    assert "Invalid date_requested" in (svc.get_last_error() or "")


def test_expected_return_before_request_fails():
    svc = ValidationService()
    requester_id = 1
    start = datetime.now()
    end = start - timedelta(hours=1)
    requisition_data = {
        "date_requested": make_iso(start),
        "expected_return": make_iso(end),
        "lab_activity_name": "Test Activity",
        "lab_activity_date": date.today().isoformat(),
    }
    items_data = [{"item_id": 1, "quantity_requested": 2}]
    assert (
        svc.validate_requisition_creation(requester_id, requisition_data, items_data)
        is False
    )
    assert "Expected return must be after" in (svc.get_last_error() or "")


def test_invalid_return_data_fails():
    svc = ValidationService()
    return_data = [{"item_id": "x", "quantity_returned": -1}]
    assert svc.validate_return_data(return_data) is False
    assert svc.get_last_error() is not None
