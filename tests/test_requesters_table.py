from datetime import datetime, timedelta, timezone

from inventory_app.gui.requesters.requester_table import RequesterTable
from inventory_app.gui.requesters.requester_model import RequesterRow
from inventory_app.utils.date_utils import format_date_short


def test_requesters_table_sorts_by_created_newest_first(qtbot):
    table = RequesterTable()
    qtbot.addWidget(table)

    now = datetime.now(timezone.utc)
    rows = [
        RequesterRow(
            id=1,
            name="A",
            affiliation="X",
            group_name="G",
            created_datetime=now - timedelta(days=2),
        ),
        RequesterRow(
            id=2, name="B", affiliation="X", group_name="G", created_datetime=now
        ),
        RequesterRow(
            id=3,
            name="C",
            affiliation="X",
            group_name="G",
            created_datetime=now - timedelta(days=1),
        ),
    ]

    table.populate_table(rows)

    # After populate, default sort should be applied so newest (id=2) appears first
    first_item = table.item(0, 4)
    second_item = table.item(1, 4)
    third_item = table.item(2, 4)

    assert first_item is not None, "First row item (Created) is missing"
    assert second_item is not None, "Second row item (Created) is missing"
    assert third_item is not None, "Third row item (Created) is missing"

    first_created_text = first_item.text()
    second_created_text = second_item.text()
    third_created_text = third_item.text()

    assert format_date_short(now) in first_created_text
    assert format_date_short(now - timedelta(days=1)) in second_created_text
    assert format_date_short(now - timedelta(days=2)) in third_created_text
