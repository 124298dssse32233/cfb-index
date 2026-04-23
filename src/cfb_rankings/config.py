from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class AppConfig:
    database_url: str
    sportsdb_api_key: Optional[str]
    sportsdb_base_url: str
    cfbd_api_key: Optional[str]
    cfbd_base_url: str
    anthropic_api_key: Optional[str]
    apify_api_token: Optional[str]
    youtube_api_key: Optional[str]
    bluesky_public_api_base_url: str
    kalshi_api_base_url: str
    polymarket_gamma_api_base_url: str
    polymarket_clob_api_base_url: str
    request_timeout_seconds: float
    model_version: str

    @classmethod
    def from_env(cls) -> "AppConfig":
        _load_dotenv()
        return cls(
            database_url=os.getenv("DATABASE_URL", "sqlite:///./cfb_rankings.db"),
            sportsdb_api_key=os.getenv("SPORTSDB_API_KEY"),
            sportsdb_base_url=os.getenv("SPORTSDB_BASE_URL", "https://www.thesportsdb.com"),
            cfbd_api_key=os.getenv("CFBD_API_KEY"),
            cfbd_base_url=os.getenv("CFBD_BASE_URL", "https://api.collegefootballdata.com"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            apify_api_token=os.getenv("APIFY_API_TOKEN"),
            youtube_api_key=os.getenv("YOUTUBE_API_KEY"),
            bluesky_public_api_base_url=os.getenv("BLUESKY_PUBLIC_API_BASE_URL", "https://public.api.bsky.app"),
            kalshi_api_base_url=os.getenv("KALSHI_API_BASE_URL", "https://api.elections.kalshi.com/trade-api/v2"),
            polymarket_gamma_api_base_url=os.getenv("POLYMARKET_GAMMA_API_BASE_URL", "https://gamma-api.polymarket.com"),
            polymarket_clob_api_base_url=os.getenv("POLYMARKET_CLOB_API_BASE_URL", "https://clob.polymarket.com"),
            request_timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "60")),
            model_version=os.getenv("MODEL_VERSION", "power-resume-v0.1.0"),
        )


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _load_dotenv() -> None:
    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
