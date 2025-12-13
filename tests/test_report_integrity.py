import unittest.mock as mock

from inventory_app.gui.reports.query_builder import ReportQueryBuilder
from inventory_app.gui.reports.report_generator import ReportGenerator
from inventory_app.database.connection import db


def test_core_report_callables_are_not_mocks():
    # Ensure core report functions are actual implementations, not mocked out
    assert not isinstance(ReportQueryBuilder.execute_report_query, mock.Mock)
    assert not isinstance(ReportQueryBuilder._build_optimized_period_columns, mock.Mock)
    assert not isinstance(ReportGenerator.generate_report, mock.Mock)
    # db.execute_query/execute_update should be real callables
    assert callable(db.execute_query)
    assert callable(db.execute_update)
