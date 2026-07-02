from app.aggregate import build_monthly_report, distinct_months, distinct_roles, filter_report
from tests.fixtures import USAGE_ROWS, USERS


def test_build_monthly_report_joins_role_and_buckets_by_month():
    report = build_monthly_report(USERS, USAGE_ROWS)

    dev1_june = next(r for r in report if r["account_id"] == "user_dev1" and r["month"] == "2026-06")
    assert dev1_june["role"] == "developer"
    assert dev1_june["email"] == "dev1@example.com"
    # two June rows for dev1: (1000+500) + (2000+1000)
    assert dev1_june["uncached_input_tokens"] == 3000
    assert dev1_june["output_tokens"] == 1500
    assert dev1_june["total_tokens"] == 4500

    dev1_july = next(r for r in report if r["account_id"] == "user_dev1" and r["month"] == "2026-07")
    assert dev1_july["total_tokens"] == 700
    assert "claude-opus-4-6" in dev1_july["models"]


def test_build_monthly_report_includes_cache_tokens_in_total():
    report = build_monthly_report(USERS, USAGE_ROWS)
    dev2 = next(r for r in report if r["account_id"] == "user_dev2")
    # 100 input + 50 output + 200 cache_read + 300 cache_write = 650
    assert dev2["total_tokens"] == 650
    assert dev2["cache_read_input_tokens"] == 200
    assert dev2["cache_write_tokens"] == 300


def test_build_monthly_report_flags_unknown_users_without_crashing():
    report = build_monthly_report(USERS, USAGE_ROWS)
    ghost = next(r for r in report if r["account_id"] == "user_ghost")
    assert ghost["role"] == "unknown"
    assert ghost["email"] is None


def test_filter_report_by_role():
    report = build_monthly_report(USERS, USAGE_ROWS)
    developers = filter_report(report, role="developer")
    assert developers
    assert all(r["role"] == "developer" for r in developers)
    assert {r["account_id"] for r in developers} == {"user_dev1", "user_dev2"}


def test_filter_report_by_month():
    report = build_monthly_report(USERS, USAGE_ROWS)
    june_rows = filter_report(report, month="2026-06")
    assert all(r["month"] == "2026-06" for r in june_rows)
    assert len(june_rows) == 4  # dev1, dev2, admin1, and the "unknown" ghost user


def test_distinct_roles_and_months():
    report = build_monthly_report(USERS, USAGE_ROWS)
    assert "developer" in distinct_roles(report)
    assert "2026-06" in distinct_months(report)
    assert "2026-07" in distinct_months(report)
