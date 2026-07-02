"""Tiny JSON-file cache for the aggregated report.

The raw Admin API responses can be sizeable (one row per user per model per day),
so rather than re-fetching on every dashboard page load, `refresh()` pulls fresh
data and writes the already-aggregated monthly report to disk. The FastAPI app
just reads this file. Re-run refresh (CLI command or the "Refresh" button, which
calls POST /api/refresh) to pull new data.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def save_report(path: Path, report: list[dict[str, Any]], unknown_account_ids: list[str] | None = None) -> None:
    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "unknown_account_ids": unknown_account_ids or [],
        "report": report,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def load_report(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text())
