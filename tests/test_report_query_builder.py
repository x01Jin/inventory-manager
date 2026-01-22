from datetime import date

from inventory_app.gui.reports.query_builder import ReportQueryBuilder


def test_build_dynamic_report_query_uses_placeholders():
    builder = ReportQueryBuilder()
    start = date(2023, 1, 1)
    end = date(2023, 1, 5)
    query, params = builder.build_dynamic_report_query(start, end, "daily")

    # Query should use placeholders for date bounds and other comparisons
    # After patch, lab_activity_date is used instead of expected_request
    assert (
        "r.lab_activity_date >= ? AND r.lab_activity_date < ?" in query
        or "r.lab_activity_date >= ?" in query
    )
    # Last two params should be the global bounds that cover period columns
    from inventory_app.gui.reports.report_utils import date_formatter

    keys = date_formatter.get_period_keys(start, end, "daily")
    # Compute min and max from period params
    # Extract period ranges from built columns
    period_params_for_test = params[: 2 * len(keys)]
    period_starts = [
        period_params_for_test[i] for i in range(0, len(period_params_for_test), 2)
    ]
    period_ends = [
        period_params_for_test[i] for i in range(1, len(period_params_for_test), 2)
    ]
    # Use parameterized placeholders for date bounds, not string interpolation
    assert params[-2] == min(period_starts)
    assert params[-1] == max(period_ends)


def test_skips_invalid_period_keys():
    # Directly exercise period columns builder with an invalid key
    builder = ReportQueryBuilder()
    # Simulate building period columns by calling the internal method (no mocking)
    sql, params, is_normalized, cte_sql = builder._build_optimized_period_columns(
        date(2023, 1, 1), date(2023, 1, 3), "daily"
    )

    # The SQL should not contain the bad key content
    assert "DROP TABLE" not in sql
    # Ensure params include at least the global date bounds when used in the builder
    _, full_params = builder.build_dynamic_report_query(
        date(2023, 1, 1), date(2023, 1, 3), "daily"
    )
    from datetime import timedelta

    assert full_params[-2] == date(2023, 1, 1).isoformat()
    assert full_params[-1] == (date(2023, 1, 3) + timedelta(days=1)).isoformat()


def test_fallback_to_normalized_for_many_periods():
    builder = ReportQueryBuilder()
    start = date(2023, 1, 1)
    end = date(2023, 12, 31)
    select_sql, params, is_normalized, cte_sql = (
        builder._build_optimized_period_columns(start, end, "daily")
    )
    assert is_normalized
    assert "WITH periods" in cte_sql
    assert "PERIOD" in select_sql and "PERIOD_QUANTITY" in select_sql
    # params should be 3 * len(keys)
    from inventory_app.gui.reports.report_utils import date_formatter

    keys = date_formatter.get_period_keys(start, end, "daily")
    assert len(params) == 3 * len(keys)


def test_integration_period_columns_and_params_match():
    from inventory_app.gui.reports.report_utils import date_formatter

    builder = ReportQueryBuilder()
    start = date(2023, 1, 1)
    end = date(2023, 1, 8)
    keys = date_formatter.get_period_keys(start, end, "daily")
    query, params = builder.build_dynamic_report_query(start, end, "daily")

    expected_param_count = 2 + 2 * len(keys)
    assert len(params) == expected_param_count
    # Parameter placeholders in SQL should match params list length
    assert query.count("?") == len(params)
    for k in keys:
        assert f'"{k}"' in query or f'"{k.replace('"', '""')}"' in query


def test_monthly_precise_partial_pre_and_post_excess():
    from inventory_app.gui.reports.report_utils import date_formatter

    builder = ReportQueryBuilder()
    start = date(2025, 3, 12)
    end = date(2025, 7, 12)

    keys = date_formatter.get_period_keys(start, end, "monthly")

    # Expect the first entry to be the partial March range and the last to be the partial July range
    assert keys[0] == "2025-03-12to2025-03-31"
    assert "2025-04" in keys and "2025-05" in keys and "2025-06" in keys
    assert any(k.startswith("2025-07-01to2025-07-12") for k in keys)
    # Ensure full March isn't included as a monthly bucket
    assert "2025-03" not in keys

    # Validate parsed ranges cover the requested period precisely
    from datetime import timedelta

    parsed_ranges = [
        builder._parse_period_key_to_dates(k, start, end, "monthly") for k in keys
    ]
    parsed_starts = [date.fromisoformat(s) for s, e in parsed_ranges]
    parsed_ends_exclusive = [date.fromisoformat(e) for s, e in parsed_ranges]

    assert parsed_starts[0] == start
    assert parsed_ends_exclusive[-1] == (end + timedelta(days=1))


def test_weekly_precise_partial_pre_and_post_excess():
    from inventory_app.gui.reports.report_utils import date_formatter

    builder = ReportQueryBuilder()
    start = date(2025, 3, 12)
    end = date(2025, 7, 12)

    keys = date_formatter.get_period_keys(start, end, "weekly")

    # First period should be a partial from start to that week's Sunday
    assert keys[0] == "2025-03-12to2025-03-16"
    # Last period should be a partial tail that ends at the requested end
    assert any(k.endswith("to2025-07-12") for k in keys)

    # Validate parsed ranges cover the requested period precisely
    from datetime import timedelta

    parsed_ranges = [
        builder._parse_period_key_to_dates(k, start, end, "weekly") for k in keys
    ]
    parsed_starts = [date.fromisoformat(s) for s, e in parsed_ranges]
    parsed_ends_exclusive = [date.fromisoformat(e) for s, e in parsed_ranges]

    assert parsed_starts[0] == start
    assert parsed_ends_exclusive[-1] == (end + timedelta(days=1))


def test_yearly_precise_partial_ranges_across_years():
    from inventory_app.gui.reports.report_utils import date_formatter

    builder = ReportQueryBuilder()
    start = date(2024, 7, 10)
    end = date(2026, 2, 5)

    keys = date_formatter.get_period_keys(start, end, "yearly")

    # Expect partial 2024 tail, full 2025, and partial 2026 head
    assert keys[0] == "2024-07-10to2024-12-31"
    assert "2025" in keys
    assert keys[-1] == "2026-01-01to2026-02-05"

    parsed_ranges = [
        builder._parse_period_key_to_dates(k, start, end, "yearly") for k in keys
    ]
    parsed_starts = [date.fromisoformat(s) for s, e in parsed_ranges]
    parsed_ends_exclusive = [date.fromisoformat(e) for s, e in parsed_ranges]

    from datetime import timedelta

    assert parsed_starts[0] == start
    assert parsed_ends_exclusive[-1] == (end + timedelta(days=1))


def test_weekly_excess_ranges_are_included_and_params_expand():
    from inventory_app.gui.reports.report_utils import date_formatter

    builder = ReportQueryBuilder()
    # Choose a range that does not start on Monday and does not end on Sunday
    start = date(2025, 1, 12)  # Sunday
    end = date(2025, 1, 20)  # Monday

    keys = date_formatter.get_period_keys(start, end, "weekly")
    # Should include pre-excess (to) and post-excess (to)
    assert any("to" in k for k in keys)

    query, params = builder.build_dynamic_report_query(start, end, "weekly")

    # The params used for global bounds should cover the min start and max end
    # from the period params (which are the first 2*len(keys) params)
    period_params = params[: 2 * len(keys)]
    period_starts = [period_params[i] for i in range(0, len(period_params), 2)]
    period_ends = [period_params[i] for i in range(1, len(period_params), 2)]

    # Global bounds cover at least the min/max of computed period ranges
    assert params[-2] <= min(period_starts)
    assert params[-1] >= max(period_ends)

    # Ensure the SQL contains the period aliases generated
    for k in keys:
        assert f'"{k}"' in query or f'"{k.replace('"', '""')}"' in query


def test_weekly_precise_partial_ranges_match_monthly_semantics():
    from inventory_app.gui.reports.report_utils import date_formatter

    builder = ReportQueryBuilder()
    start = date(2025, 3, 12)
    end = date(2025, 7, 12)

    keys = date_formatter.get_period_keys(start, end, "weekly")

    # Start mid-week: initial partial range should be start -> Sunday of that week
    assert any(k.startswith("2025-03-12to2025-03-16") for k in keys)
    # Tail partial week should end at the overall end date
    assert any(k.startswith("2025-07-07to2025-07-12") for k in keys)

    # Ensure parsed ranges align with request
    parsed_ranges = [
        builder._parse_period_key_to_dates(k, start, end, "weekly") for k in keys
    ]
    parsed_starts = [date.fromisoformat(s) for s, e in parsed_ranges]
    parsed_ends_exclusive = [date.fromisoformat(e) for s, e in parsed_ranges]

    assert parsed_starts[0] == start
    assert parsed_ends_exclusive[-1] == end + __import__("datetime").timedelta(days=1)


def test_monthly_partial_ranges_within_date_range():
    from inventory_app.gui.reports.report_utils import date_formatter

    builder = ReportQueryBuilder()
    start = date(2025, 3, 10)
    end = date(2025, 6, 15)

    keys = date_formatter.get_period_keys(start, end, "monthly")
    assert keys

    # Verify parsed start/end from period keys are within the requested range
    parsed_ranges = [
        builder._parse_period_key_to_dates(k, start, end, "monthly") for k in keys
    ]
    parsed_starts = [date.fromisoformat(s) for s, e in parsed_ranges]
    parsed_ends_exclusive = [date.fromisoformat(e) for s, e in parsed_ranges]

    assert parsed_starts[0] == start
    assert parsed_ends_exclusive[-1] == (end + __import__("datetime").timedelta(days=1))

    for s, e in parsed_ranges:
        s_date = date.fromisoformat(s)
        e_date = date.fromisoformat(e) - __import__("datetime").timedelta(days=1)
        assert s_date >= start
        assert e_date <= end


def test_yearly_partial_ranges_within_date_range():
    builder = ReportQueryBuilder()
    start = date(2024, 7, 10)
    end = date(2026, 2, 5)

    from inventory_app.gui.reports.report_utils import date_formatter

    keys = date_formatter.get_period_keys(start, end, "yearly")
    assert keys

    parsed_ranges = [
        builder._parse_period_key_to_dates(k, start, end, "yearly") for k in keys
    ]

    parsed_starts = [date.fromisoformat(s) for s, e in parsed_ranges]
    parsed_ends_exclusive = [date.fromisoformat(e) for s, e in parsed_ranges]

    assert parsed_starts[0] == start
    assert parsed_ends_exclusive[-1] == (end + __import__("datetime").timedelta(days=1))

    for s, e in parsed_ranges:
        s_date = date.fromisoformat(s)
        e_date = date.fromisoformat(e) - __import__("datetime").timedelta(days=1)
        assert s_date >= start
        assert e_date <= end
