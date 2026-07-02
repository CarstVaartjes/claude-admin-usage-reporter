"""Static, overridable pricing table used to *estimate* per-user cost.

Why this exists: Anthropic's Admin API cost_report endpoint only supports
group_by=["description", "workspace_id"] - it cannot be broken down by account_id,
so there is no API that returns "$ spent by this specific user". To show a per-user
dollar figure at all, this project multiplies each user's token usage (from the
usage_report endpoint, which IS groupable by account_id) by a local price table.

This is an ESTIMATE. It will drift from your actual invoice if:
  - Anthropic changes prices (check https://claude.com/pricing) and this table is stale
  - You're on volume/enterprise pricing different from list price
  - Batch, priority tier, or other discounts/surcharges apply

Treat the token counts (from the Admin API directly) as ground truth, and the dollar
figures as directional. Override any rate via `pricing_overrides.yaml` in the repo root,
same shape as PRICING below.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# USD per million tokens, list price as of mid-2026. Verify against
# https://claude.com/pricing before relying on these for anything financial.
PRICING: dict[str, dict[str, float]] = {
    "claude-opus-4-6": {
        "input": 15.0,
        "output": 75.0,
        "cache_write_5m": 18.75,
        "cache_write_1h": 30.0,
        "cache_read": 1.5,
    },
    "claude-sonnet-4-6": {
        "input": 3.0,
        "output": 15.0,
        "cache_write_5m": 3.75,
        "cache_write_1h": 6.0,
        "cache_read": 0.3,
    },
    "claude-haiku-4-5": {
        "input": 0.8,
        "output": 4.0,
        "cache_write_5m": 1.0,
        "cache_write_1h": 1.6,
        "cache_read": 0.08,
    },
    # Fallback used for any model id not listed above (e.g. a new release).
    "_default": {
        "input": 3.0,
        "output": 15.0,
        "cache_write_5m": 3.75,
        "cache_write_1h": 6.0,
        "cache_read": 0.3,
    },
}


def load_pricing(overrides_path: Path | None = None) -> dict[str, dict[str, float]]:
    pricing = {model: dict(rates) for model, rates in PRICING.items()}
    if overrides_path and overrides_path.exists():
        with overrides_path.open() as fh:
            overrides = yaml.safe_load(fh) or {}
        for model, rates in overrides.items():
            pricing.setdefault(model, dict(pricing["_default"]))
            pricing[model].update(rates)
    return pricing


def estimate_cost_usd(usage_row: dict[str, Any], pricing: dict[str, dict[str, float]]) -> float:
    """Estimate the USD cost of a single usage_report row using `pricing`."""
    model = usage_row.get("model", "_default")
    rates = pricing.get(model, pricing["_default"])

    uncached_input = usage_row.get("uncached_input_tokens", 0) or 0
    output = usage_row.get("output_tokens", 0) or 0
    cache_read = usage_row.get("cache_read_input_tokens", 0) or 0
    cache_creation = usage_row.get("cache_creation") or {}
    cache_write_5m = cache_creation.get("ephemeral_5m_input_tokens", 0) or 0
    cache_write_1h = cache_creation.get("ephemeral_1h_input_tokens", 0) or 0

    cost = (
        uncached_input / 1_000_000 * rates["input"]
        + output / 1_000_000 * rates["output"]
        + cache_read / 1_000_000 * rates["cache_read"]
        + cache_write_5m / 1_000_000 * rates["cache_write_5m"]
        + cache_write_1h / 1_000_000 * rates["cache_write_1h"]
    )
    return cost
