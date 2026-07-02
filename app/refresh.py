"""Orchestrates a full refresh: fetch users + usage from the Admin API, aggregate,
cache to disk. Used by both the CLI and the /api/refresh endpoint.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from app.admin_client import AdminClient
from app.aggregate import build_monthly_report
from app.cache import save_report
from app.config import Settings

logger = logging.getLogger(__name__)


def run_refresh(settings: Settings, months_back: int | None = None) -> dict:
    api_key = settings.require_admin_key()
    client = AdminClient(
        api_key=api_key,
        base_url=settings.api_base_url,
        anthropic_version=settings.anthropic_version,
    )

    months_back = months_back or settings.default_months_back
    now = datetime.now(timezone.utc)
    starting_at = (now - timedelta(days=31 * months_back)).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )

    logger.info("Fetching organization users...")
    users = client.list_users()
    logger.info("Fetched %d users", len(users))

    logger.info("Fetching usage report from %s onward...", starting_at.isoformat())
    usage_rows = list(
        client.iter_usage_report(
            starting_at=starting_at,
            bucket_width="1d",
            group_by=("account_id", "model"),
        )
    )
    logger.info("Fetched %d usage rows", len(usage_rows))

    report = build_monthly_report(users, usage_rows, pricing_overrides_path=settings.pricing_overrides_path)

    known_ids = {u["id"] for u in users}
    unknown_account_ids = sorted({r["account_id"] for r in usage_rows if r.get("account_id") not in known_ids})
    if unknown_account_ids:
        logger.warning(
            "%d account_id(s) in usage data have no matching user (deactivated/removed "
            "members keep their historical usage but drop out of /v1/organizations/users): %s",
            len(unknown_account_ids),
            unknown_account_ids,
        )

    save_report(settings.cache_path, report, unknown_account_ids)
    return {
        "users_count": len(users),
        "usage_rows_count": len(usage_rows),
        "report_rows_count": len(report),
        "unknown_account_ids": unknown_account_ids,
        "starting_at": starting_at.isoformat(),
    }
