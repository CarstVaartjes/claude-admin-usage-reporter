"""Thin client for the parts of Anthropic's Admin API this project needs.

Docs: https://platform.claude.com/docs/en/manage-claude/admin-api
Auth: Admin API key (starts with sk-ant-admin...) sent as the `x-api-key` header.
Only organization members with the `admin` role can create Admin API keys.
"""
from __future__ import annotations

import time
from collections.abc import Iterator
from datetime import datetime
from typing import Any

import requests

USER_AGENT = "claude-admin-usage-reporter/0.1 (+https://github.com/CarstVaartjes/claude-admin-usage-reporter)"


class AdminAPIError(RuntimeError):
    def __init__(self, status_code: int, message: str):
        super().__init__(f"Admin API request failed ({status_code}): {message}")
        self.status_code = status_code


class AdminClient:
    """Minimal, paginating wrapper around the Admin API endpoints we use.

    Only three endpoints are used:
      - GET /v1/organizations/users               (org members + role)
      - GET /v1/organizations/usage_report/messages (token usage, groupable by account_id)
      - GET /v1/organizations/cost_report            (billed cost, NOT groupable by account_id)
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.anthropic.com",
        anthropic_version: str = "2023-06-01",
        session: requests.Session | None = None,
        max_retries: int = 5,
    ):
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "x-api-key": api_key,
                "anthropic-version": anthropic_version,
                "content-type": "application/json",
                "user-agent": USER_AGENT,
            }
        )

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        params = {k: v for k, v in (params or {}).items() if v is not None}
        for attempt in range(self.max_retries):
            resp = self.session.get(url, params=params, timeout=30)
            if resp.status_code == 429:
                retry_after = float(resp.headers.get("retry-after", 2 ** attempt))
                time.sleep(min(retry_after, 30))
                continue
            if resp.status_code >= 500:
                time.sleep(min(2 ** attempt, 15))
                continue
            if resp.status_code >= 400:
                try:
                    detail = resp.json().get("error", {}).get("message", resp.text)
                except ValueError:
                    detail = resp.text
                raise AdminAPIError(resp.status_code, detail)
            return resp.json()
        raise AdminAPIError(resp.status_code, "exhausted retries")

    def list_users(self) -> list[dict[str, Any]]:
        """Return every organization member: {id, email, name, role, type, added_at}."""
        users: list[dict[str, Any]] = []
        after_id = None
        while True:
            data = self._get("/v1/organizations/users", {"limit": 100, "after_id": after_id})
            users.extend(data.get("data", []))
            if not data.get("has_more"):
                break
            after_id = data.get("last_id")
            if after_id is None:
                break
        return users

    def iter_usage_report(
        self,
        starting_at: datetime,
        ending_at: datetime | None = None,
        bucket_width: str = "1d",
        group_by: tuple[str, ...] = ("account_id", "api_key_id"),
    ) -> Iterator[dict[str, Any]]:
        """Yield individual usage result rows (already flattened out of time buckets).

        Each row is annotated with `bucket_start` / `bucket_end` for the time bucket it
        belongs to, in addition to whatever Anthropic returns (account_id, model,
        uncached_input_tokens, output_tokens, cache_read_input_tokens, cache_creation, ...).
        """
        page = None
        params_base: dict[str, Any] = {
            "starting_at": _iso(starting_at),
            "bucket_width": bucket_width,
        }
        if ending_at is not None:
            params_base["ending_at"] = _iso(ending_at)
        if group_by:
            params_base["group_by"] = list(group_by)

        while True:
            params = dict(params_base)
            if page:
                params["page"] = page
            data = self._get("/v1/organizations/usage_report/messages", params)
            for bucket in data.get("data", []):
                for row in bucket.get("results", []):
                    yield {
                        **row,
                        "bucket_start": bucket.get("starting_at"),
                        "bucket_end": bucket.get("ending_at"),
                    }
            if not data.get("has_more"):
                break
            page = data.get("next_page")
            if not page:
                break

    def iter_cost_report(
        self,
        starting_at: datetime,
        ending_at: datetime | None = None,
        bucket_width: str = "1d",
        group_by: tuple[str, ...] = ("workspace_id", "description"),
    ) -> Iterator[dict[str, Any]]:
        """Yield cost rows. NOTE: the Admin API cannot group cost by account_id/user -
        this is org/workspace-level billed cost, kept here for a sanity-check total only.
        """
        page = None
        params_base: dict[str, Any] = {
            "starting_at": _iso(starting_at),
            "bucket_width": bucket_width,
        }
        if ending_at is not None:
            params_base["ending_at"] = _iso(ending_at)
        if group_by:
            params_base["group_by"] = list(group_by)

        while True:
            params = dict(params_base)
            if page:
                params["page"] = page
            data = self._get("/v1/organizations/cost_report", params)
            for bucket in data.get("data", []):
                for row in bucket.get("results", []):
                    yield {
                        **row,
                        "bucket_start": bucket.get("starting_at"),
                        "bucket_end": bucket.get("ending_at"),
                    }
            if not data.get("has_more"):
                break
            page = data.get("next_page")
            if not page:
                break


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
