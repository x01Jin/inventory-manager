import pytest
from inventory_app.utils.stock_parser import parse_stock_value, parse_stock_quantity


def test_numeric_values():
    assert parse_stock_quantity(3) == 3
    assert parse_stock_quantity(3.9) == 3
    assert parse_stock_quantity("4") == 4


def test_size_attached():
    info = parse_stock_value("900ml")
    assert info["quantity"] == 1
    assert info["size"] == "900ml"

    info2 = parse_stock_value("1.1 L")
    assert info2["quantity"] == 1
    assert info2["size"].lower() in ("1.1 l", "1.1l")


def test_leading_counts_and_notes():
    info = parse_stock_value("2 sets")
    assert info["quantity"] == 2
    assert info["size"] is None

    info2 = parse_stock_value("10 boxes (100pcs)")
    assert info2["quantity"] == 10
    assert info2["notes"] == "(100pcs)"

    info3 = parse_stock_value("1 set of 8 pieces")
    assert info3["quantity"] == 1
    assert info3["notes"] is not None


def test_empty_and_none():
    assert parse_stock_quantity(None) == 0
    assert parse_stock_quantity("") == 0


def test_invalid_raises():
    with pytest.raises(ValueError):
        parse_stock_value("no number here")
