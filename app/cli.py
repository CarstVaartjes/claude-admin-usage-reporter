"""Command-line entry point.

  python -m app.cli refresh --months 6   # fetch from the Admin API, cache to disk
  python -m app.cli serve --port 8000    # run the dashboard (reads the cache)
"""
from __future__ import annotations

import argparse
import json
import logging
import sys

from app.config import settings
from app.refresh import run_refresh

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="claude-admin-usage-reporter")
    sub = parser.add_subparsers(dest="command", required=True)

    refresh_p = sub.add_parser("refresh", help="Fetch usage from the Admin API and cache it")
    refresh_p.add_argument(
        "--months",
        type=int,
        default=None,
        help=(
            "How many months back to fetch (default from DEFAULT_MONTHS_BACK env, "
            f"currently {settings.default_months_back})"
        ),
    )

    serve_p = sub.add_parser("serve", help="Run the dashboard web server")
    serve_p.add_argument("--host", default="0.0.0.0")
    serve_p.add_argument("--port", type=int, default=8000)
    serve_p.add_argument("--reload", action="store_true")

    args = parser.parse_args(argv)

    if args.command == "refresh":
        summary = run_refresh(settings, months_back=args.months)
        print(json.dumps(summary, indent=2))
        return 0

    if args.command == "serve":
        import uvicorn

        uvicorn.run("app.main:app", host=args.host, port=args.port, reload=args.reload)
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
