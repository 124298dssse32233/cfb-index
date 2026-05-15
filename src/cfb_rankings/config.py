from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from cfb_rankings.quality_loop import LoopPattern


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


# ---------------------------------------------------------------------------
# quality_loop.py feature-flag dispatch + per-surface weekly spend ceilings.
#
# Sprint v5-1 lands `quality_loop.py` with the flags dict EMPTY so no surface
# changes behavior. Subsequent sprints flip one flag at a time per the
# rollout table in DESIGN_AUDIT_2026_05_15_v5_3.md Part 5. The eight
# existing call sites that use `llm_runtime.generate_with_voice_check`
# directly stay on contract until their surface key appears here.
#
# Surface keys follow the convention `tier{N}.{surface_slug}`. Use these
# exact strings — they're the join key with WEEKLY_CEILINGS_CENTS below
# and with the telemetry written by `team_pages.llm_usage_log`.
# ---------------------------------------------------------------------------

# Empty by default. Sprint v5-2 begins populating per the rollout schedule
# in DESIGN_AUDIT_2026_05_15_v5_3.md Part 5 / IMPLEMENTATION_PLAN.md Part 5.
# Type is `dict[str, "LoopPattern"]` once quality_loop is imported by the
# caller; left as plain dict here to avoid a hard import cycle.
QUALITY_LOOP_FLAGS: dict[str, "LoopPattern"] = {}


# Per-surface weekly spend ceilings (cents). Enforced by quality_loop.py's
# Rung-3 circuit breaker. Verbatim from DESIGN_AUDIT_2026_05_15_v5_3.md
# Part 2 and IMPLEMENTATION_PLAN.md Part 6.5.
WEEKLY_CEILINGS_CENTS: dict[str, int] = {
    "tier1.edition_cover":         1000,   # $10/wk (Pattern D headroom)
    "tier1.daily_lead":             500,
    "tier1.heisman_weekly":         300,
    "tier1.mailbag":                800,
    "tier1.reaction_story":         500,
    "tier1.storyline_chapter":      400,
    "tier1.canon_top10":            200,
    "tier1.chronicle_profiled":     500,
    "tier2.team_narrative":         200,
    "tier2.pulse_state":            200,
    "tier2.chronicle_unprofiled":  1500,
    "tier3.wire":                   200,
    "tier3.canon_tail":             200,
}


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
