"""Configuration loaded from environment variables (.env supported via python-dotenv)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class Settings:
    admin_api_key: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_ADMIN_KEY", ""))
    api_base_url: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_BASE_URL", "https://api.anthropic.com"))
    anthropic_version: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_VERSION", "2023-06-01"))
    default_months_back: int = field(default_factory=lambda: int(os.environ.get("DEFAULT_MONTHS_BACK", "6")))
    cache_path: Path = field(default_factory=lambda: DATA_DIR / "report_cache.json")
    pricing_overrides_path: Path = field(default_factory=lambda: BASE_DIR / "pricing_overrides.yaml")

    def require_admin_key(self) -> str:
        if not self.admin_api_key:
            raise RuntimeError(
                "ANTHROPIC_ADMIN_KEY is not set. Create an Admin API key in the Claude "
                "Console (Settings > Organization, requires the admin/owner role) and set "
                "it as an environment variable or in a .env file."
            )
        if not self.admin_api_key.startswith("sk-ant-admin"):
            raise RuntimeError(
                "ANTHROPIC_ADMIN_KEY does not look like an Admin API key (should start "
                "with 'sk-ant-admin'). A regular API key will not work against the Admin API."
            )
        return self.admin_api_key


settings = Settings()
