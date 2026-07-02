"""FastAPI app: serves the cached report as JSON, plus a static dashboard."""
from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.aggregate import distinct_months, distinct_roles, filter_report
from app.cache import load_report
from app.config import settings
from app.refresh import run_refresh

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Claude Admin Usage Reporter", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = settings.cache_path.parent.parent / "app" / "static"


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/report")
def get_report(
    role: str | None = Query(default=None, description="Filter by organization role, e.g. 'developer'"),
    month: str | None = Query(default=None, description="Filter by month, format YYYY-MM"),
):
    cached = load_report(settings.cache_path)
    if cached is None:
        raise HTTPException(
            status_code=404,
            detail="No cached report yet. Run `python -m app.cli refresh` or POST /api/refresh first.",
        )
    rows = filter_report(cached["report"], role=role, month=month)
    return {
        "fetched_at": cached["fetched_at"],
        "unknown_account_ids": cached.get("unknown_account_ids", []),
        "roles": distinct_roles(cached["report"]),
        "months": distinct_months(cached["report"]),
        "rows": rows,
    }


@app.post("/api/refresh")
def refresh(months_back: int | None = Query(default=None, ge=1, le=36)):
    try:
        summary = run_refresh(settings, months_back=months_back)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return summary


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index():
    return FileResponse(str(STATIC_DIR / "index.html"))
