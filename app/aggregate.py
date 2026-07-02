"""Join usage_report rows to organization users, and roll daily buckets up to months.

The Admin API's usage_report/messages endpoint returns per-day (or finer) buckets.
There is no "1 month" bucket_width, so monthly totals are computed here from the
`bucket_start` timestamp of each row.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from app.pricing import estimate_cost_usd, load_pricing

TOKEN_FIELDS = (
    "uncached_input_tokens",
    "output_tokens",
    "cache_read_input_tokens",
    "cache_write_tokens",  # derived, not present on the raw API row
)


def _month_key(iso_timestamp: str) -> str:
    # e.g. "2026-07-01T00:00:00Z" -> "2026-07"
    return iso_timestamp[:7]


def _cache_write_tokens(row: dict[str, Any]) -> int:
    cache_creation = row.get("cache_creation") or {}
    return int(cache_creation.get("ephemeral_5m_input_tokens", 0) or 0) + int(
        cache_creation.get("ephemeral_1h_input_tokens", 0) or 0
    )


def build_monthly_report(
    users: Iterable[dict[str, Any]],
    usage_rows: Iterable[dict[str, Any]],
    pricing_overrides_path=None,
) -> list[dict[str, Any]]:
    """Return one row per (user, month): tokens by type, total tokens, estimated cost.

    Users with no usage in a given month simply don't get a row for that month -
    the frontend fills gaps with zero when rendering a full user x month grid.
    """
    users_by_id = {u["id"]: u for u in users}
    pricing = load_pricing(pricing_overrides_path)

    # key: (account_id, month) -> accumulator
    acc: dict[tuple[str, str], dict[str, Any]] = defaultdict(
        lambda: {
            "uncached_input_tokens": 0,
            "output_tokens": 0,
            "cache_read_input_tokens": 0,
            "cache_write_tokens": 0,
            "total_tokens": 0,
            "estimated_cost_usd": 0.0,
            "models": set(),
        }
    )

    unknown_account_ids: set[str] = set()

    for row in usage_rows:
        account_id = row.get("account_id")
        bucket_start = row.get("bucket_start")
        if not account_id or not bucket_start:
            continue
        if account_id not in users_by_id:
            unknown_account_ids.add(account_id)

        month = _month_key(bucket_start)
        key = (account_id, month)
        entry = acc[key]

        uncached_input = int(row.get("uncached_input_tokens", 0) or 0)
        output = int(row.get("output_tokens", 0) or 0)
        cache_read = int(row.get("cache_read_input_tokens", 0) or 0)
        cache_write = _cache_write_tokens(row)

        entry["uncached_input_tokens"] += uncached_input
        entry["output_tokens"] += output
        entry["cache_read_input_tokens"] += cache_read
        entry["cache_write_tokens"] += cache_write
        entry["total_tokens"] += uncached_input + output + cache_read + cache_write
        entry["estimated_cost_usd"] += estimate_cost_usd(row, pricing)
        if row.get("model"):
            entry["models"].add(row["model"])

    report: list[dict[str, Any]] = []
    for (account_id, month), entry in acc.items():
        user = users_by_id.get(account_id)
        report.append(
            {
                "account_id": account_id,
                "email": user.get("email") if user else None,
                "name": user.get("name") if user else None,
                "role": user.get("role") if user else "unknown",
                "month": month,
                "uncached_input_tokens": entry["uncached_input_tokens"],
                "output_tokens": entry["output_tokens"],
                "cache_read_input_tokens": entry["cache_read_input_tokens"],
                "cache_write_tokens": entry["cache_write_tokens"],
                "total_tokens": entry["total_tokens"],
                "estimated_cost_usd": round(entry["estimated_cost_usd"], 4),
                "models": sorted(entry["models"]),
            }
        )

    report.sort(key=lambda r: (r["month"], -r["total_tokens"]))
    return report


def filter_report(
    report: list[dict[str, Any]],
    role: str | None = None,
    month: str | None = None,
) -> list[dict[str, Any]]:
    rows = report
    if role:
        rows = [r for r in rows if r["role"] == role]
    if month:
        rows = [r for r in rows if r["month"] == month]
    return rows


def distinct_roles(report: list[dict[str, Any]]) -> list[str]:
    return sorted({r["role"] for r in report})


def distinct_months(report: list[dict[str, Any]]) -> list[str]:
    return sorted({r["month"] for r in report})
