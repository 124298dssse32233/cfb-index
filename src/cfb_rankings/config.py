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

# Sprint v5-2 (2026-05-15) — FIRST quality_loop flag flip.
#
# `tier1.edition_cover` now routes through Pattern C (Opus 4.7 + extended
# thinking + 3-critic voice/headline/factuality loop with one revise pass)
# via `editions.cover_essay.synthesize_cover_essay`. Sync fall-through to
# `editions/seeds.py` is preserved when the loop falls back (offline,
# wall-clock timeout 90s, Rung-2 critic failures, Rung-3 weekly ceiling).
#
# Sprint v5-3 (2026-05-15) — BATCH FLIP of the next four Tier-1 surfaces.
#
# Following the v5-2 first-flag-flip pattern, the next four Tier-1
# surfaces also route through Pattern C:
#
#     * `tier1.daily_lead`         → daily.cover_essay.synthesize_daily_lead
#     * `tier1.daily_supporting`   → daily.cover_essay.synthesize_daily_supporting
#     * `tier1.heisman_weekly`     → heisman.cover_essay.synthesize_heisman_weekly
#     * `tier1.mailbag`            → mailbag.synthesizer.synthesize_mailbag_answer
#     * `tier1.reaction_story`     → reactions.synthesizer.synthesize_reaction_story
#
# Sprint v5-4 (2026-05-15) — Pattern E flag flips for cross-chapter
# continuity surfaces:
#
#     * `tier1.storyline_chapter`  → storylines.chapter_pattern_e.synthesize_storyline_chapter
#     * `tier1.chronicle_profiled` → team_pages.chronicle_pattern_e.synthesize_chronicle_card
#
# Pattern E is Pattern C plus a continuity critic + a thread-history /
# named-entity-ledger pre-pass. Chronicle Pattern E only activates for
# the PROFILED_SLUGS roster — unprofiled programs stay on the legacy
# template-only chronicle path.
#
# Each wrapper preserves the existing sync / seed / offline-stub
# fall-back when the loop falls back (offline-stub, wall-clock timeout,
# Rung-2 critic failures, Rung-3 weekly ceiling). All existing
# `generate_with_voice_check` and batch call sites stay on contract;
# the new wrappers are *additive* dispatch helpers that the new CLI
# entry points and tests reach for explicitly.
#
# Subsequent surfaces will flip per the rollout schedule in
# DESIGN_AUDIT_2026_05_15_v5_3.md Part 5 / IMPLEMENTATION_PLAN.md Part 5.
# Edition cover specifically upgrades to Pattern D (adversarial, with
# engagement critic) in Sprint v5-8 after a 4-week A/B against the
# Pattern C baseline.
#
# Type is `dict[str, "LoopPattern"]` once quality_loop is imported by the
# caller; left as plain dict here to avoid a hard import cycle. The
# import below is deferred and survives any import-time circularity by
# falling back to the raw string value, which quality_loop accepts.
_V5_3_FLAGS = (
    "tier1.edition_cover",
    "tier1.daily_lead",
    "tier1.daily_supporting",
    "tier1.heisman_weekly",
    "tier1.mailbag",
    "tier1.reaction_story",
)

# Sprint v5-4 — Pattern E (continuity-grounded) flags.
_V5_4_E_FLAGS = (
    "tier1.storyline_chapter",
    "tier1.chronicle_profiled",
)

# Sprint v5-5 (Jun 22-26 per IMPLEMENTATION_PLAN.md, brought forward
# 2026-05-16 owner request) — Canon + Pulse Pattern C flag batch:
#   tier1.canon_top10           top 10 entries of each canon list
#   tier1.canon_tail            tail entries (rank 11-N) of each canon list
#   tier1.pulse_themes_writer   Stage 2 writer that turns theme candidates
#                               into the final 1-3 themes shown on the
#                               team/conference Pulse panels
#   tier1.best_calls            Receipts "Best Calls" weekly digest
#   tier1.pulse_lede            Lede above the Pulse panel for each entity
#
# Wiring policy in this batch: the flag declarations land now. Generator
# wrappers (the actual loop_c_critic_revise dispatch) ship per-surface
# across v5-5/v5-6/v5-7 sprints — see each module's docstring for which
# surface is live and which is still pre-wrapper (flag inert).
_V5_5_FLAGS = (
    "tier1.canon_top10",
    "tier1.canon_tail",
    "tier1.best_calls",
)

# Sprint v5-5 demote (2026-05-16 22:30 UTC) — pulse_lede + pulse_themes_writer
# Pattern C produced a 100% / 71% fall-back rate respectively, exiting via
# `consecutive_critic_failures_after_escalation`. The 3-critic loop is tuned
# for long-form essay output (edition_cover convention) and rejects
# short-form (pulse_lede = 2-3 sentences) and structured-JSON
# (pulse_themes_writer) outputs. Each rejected call paid for the critic
# loop AND the sync fall-back — effectively 2× cost for no quality gain.
# Demoting to Pattern B (single critic, no revise loop). The single critic
# still validates voice but stops trying to enforce convergence on a
# pattern that doesn't fit the surface. Tier-2 narratives + Chronicle
# rank-3-5 surfaces have run on Pattern B successfully since v5-1.
_V5_5_B_FLAGS = (
    "tier1.pulse_themes_writer",
    "tier1.pulse_lede",
)


def _initial_quality_loop_flags() -> "dict[str, LoopPattern]":
    try:
        from cfb_rankings.quality_loop import LoopPattern as _LP
    except Exception:  # pragma: no cover — circular-import guardrail
        out: dict[str, str] = {k: "C_critic_revise" for k in _V5_3_FLAGS}
        out.update({k: "E_continuity" for k in _V5_4_E_FLAGS})
        out.update({k: "C_critic_revise" for k in _V5_5_FLAGS})
        out.update({k: "B_single_critic" for k in _V5_5_B_FLAGS})
        return out  # type: ignore[return-value]
    out: dict[str, "LoopPattern"] = {
        k: _LP.C_CRITIC_REVISE for k in _V5_3_FLAGS
    }
    out.update({k: _LP.E_CONTINUITY for k in _V5_4_E_FLAGS})
    out.update({k: _LP.C_CRITIC_REVISE for k in _V5_5_FLAGS})
    out.update({k: _LP.B_SINGLE_CRITIC for k in _V5_5_B_FLAGS})
    return out


QUALITY_LOOP_FLAGS: dict[str, "LoopPattern"] = _initial_quality_loop_flags()


# Per-surface weekly spend ceilings (cents). Enforced by quality_loop.py's
# Rung-3 circuit breaker. Verbatim from DESIGN_AUDIT_2026_05_15_v5_3.md
# Part 2 and IMPLEMENTATION_PLAN.md Part 6.5.
WEEKLY_CEILINGS_CENTS: dict[str, int] = {
    "tier1.edition_cover":         1000,   # $10/wk (Pattern D headroom)
    "tier1.daily_lead":             500,
    "tier1.daily_supporting":       500,   # supporting takes 2 + 3 of The Daily
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
    # Sprint v5-5 additions (2026-05-16) — Canon + Pulse Pattern C. The
    # tier1.canon_top10 ceiling above is the v5-3 pre-allocation;
    # tier1.canon_tail / pulse_themes_writer / best_calls / pulse_lede
    # are new and get conservative $2-3/wk caps. The auto-disable rolling
    # 24h aggregate (DAILY_AGGREGATE_CEILINGS_USD below) is the primary
    # cost guardrail for these — weekly is a secondary backstop.
    "tier1.canon_tail":             300,
    "tier1.pulse_themes_writer":    300,
    "tier1.best_calls":             200,
    "tier1.pulse_lede":             200,
}


# ---------------------------------------------------------------------------
# Sprint v5-3 owner Interrupt 2 (2026-05-15) — per-surface CostMeter
# ceilings + 24-hour rolling aggregate auto-disable.
#
# Two guardrails layered on top of the existing weekly ceilings:
#
# 1. PER_RUN_CEILINGS_USD — hard ceiling for a single workflow invocation.
#    Trips ``llm_runtime.CostMeter.record()`` (which raises
#    ``CostCeilingExceeded``) and aborts that run immediately. Defense
#    against a single runaway loop racking up a multi-dollar bill in one
#    invocation.
#
# 2. DAILY_AGGREGATE_CEILINGS_USD — sum of cost over the last 24 hours
#    across ALL runs. When breached, the surface's Pattern C flag is
#    auto-disabled and the surface degrades to ``SURFACE_DEGRADE_PATTERN``
#    until human re-enable via ``manage.py quality-loop-reenable``.
#    Defense against bursty news cycles where Reactions could fire many
#    times in a day.
#
# Together they form a defense-in-depth around the
# console.anthropic.com $100/mo outer cap — the per-run ceiling catches
# runaway within seconds, the 24hr aggregate catches it within hours.
# ---------------------------------------------------------------------------

# Per-run cost ceiling (single workflow invocation) in USD.
# Trips CostMeter.record() and aborts the run immediately.
PER_RUN_CEILINGS_USD: dict[str, float] = {
    "tier1.edition_cover":       5.00,
    "tier1.daily_lead":          3.00,
    "tier1.daily_supporting":    3.00,
    "tier1.heisman_weekly":      2.00,
    "tier1.mailbag":             1.00,
    "tier1.reaction_story":      0.50,
    "tier1.storyline_chapter":   2.00,
    "tier1.chronicle_profiled":  0.50,
    # Sprint v5-5 additions:
    # Canon top-10 + tail run nightly in batch over ~300 entries total;
    # cap per-run high enough to allow the full list refresh in one shot.
    # Pulse themes/lede fire per-entity (17 profiled teams + conferences),
    # each cheap individually. Best calls is one weekly digest call.
    "tier1.canon_top10":         3.00,
    "tier1.canon_tail":          5.00,
    "tier1.pulse_themes_writer": 2.00,
    "tier1.best_calls":          1.00,
    "tier1.pulse_lede":          1.00,
}

# Per-24hr rolling aggregate ceiling (USD). When a surface's last-24h
# spend exceeds this, auto-disable Pattern C and degrade to Pattern B/A
# until human re-enables.
DAILY_AGGREGATE_CEILINGS_USD: dict[str, float] = {
    "tier1.edition_cover":       10.00,
    "tier1.daily_lead":          15.00,
    "tier1.daily_supporting":    15.00,
    "tier1.heisman_weekly":       5.00,
    "tier1.mailbag":             20.00,
    "tier1.reaction_story":      15.00,
    "tier1.storyline_chapter":   10.00,
    "tier1.chronicle_profiled":  25.00,  # 595 cards/wk worst case
    # Sprint v5-5 additions: rolling 24h aggregates. Auto-disable Pattern C
    # if exceeded, surface degrades to SURFACE_DEGRADE_PATTERN until manual
    # quality-loop-reenable. Sized 5-10× weekly to allow bursty days
    # (e.g. a canon list full refresh nightly).
    "tier1.canon_top10":          5.00,
    "tier1.canon_tail":          10.00,
    "tier1.pulse_themes_writer":  8.00,
    "tier1.best_calls":           5.00,
    "tier1.pulse_lede":           5.00,
}


def _surface_degrade_pattern_map() -> "dict[str, LoopPattern]":
    """Build the degrade-pattern map. Deferred to avoid a hard import
    cycle with ``cfb_rankings.quality_loop``; falls back to string values
    that ``circuit_state.get_active_pattern`` accepts."""
    try:
        from cfb_rankings.quality_loop import LoopPattern as _LP
    except Exception:  # pragma: no cover — circular-import guardrail
        return {
            "tier1.edition_cover":       "A_single_shot",
            "tier1.daily_lead":          "A_single_shot",
            "tier1.daily_supporting":    "A_single_shot",
            "tier1.heisman_weekly":      "A_single_shot",
            "tier1.mailbag":             "A_single_shot",
            "tier1.reaction_story":      "A_single_shot",
            "tier1.storyline_chapter":   "B_single_critic",
            "tier1.chronicle_profiled":  "B_single_critic",
            # Sprint v5-5 additions — Canon/Pulse/Best Calls degrade to
            # Pattern A on auto-disable, same as the other tier1
            # editorial surfaces. Loses the critic loop but preserves
            # the underlying Opus/Sonnet output.
            "tier1.canon_top10":         "A_single_shot",
            "tier1.canon_tail":          "A_single_shot",
            "tier1.pulse_themes_writer": "A_single_shot",
            "tier1.best_calls":          "A_single_shot",
            "tier1.pulse_lede":          "A_single_shot",
        }  # type: ignore[return-value]
    # Most degrade to Pattern A (single shot) — preserves output but
    # drops the 3-critic loop. Storyline/Chronicle profiled degrade to
    # Pattern B (single critic) because continuity is core to their value.
    return {
        "tier1.edition_cover":       _LP.A_SINGLE_SHOT,
        "tier1.daily_lead":          _LP.A_SINGLE_SHOT,
        "tier1.daily_supporting":    _LP.A_SINGLE_SHOT,
        "tier1.heisman_weekly":      _LP.A_SINGLE_SHOT,
        "tier1.mailbag":             _LP.A_SINGLE_SHOT,
        "tier1.reaction_story":      _LP.A_SINGLE_SHOT,
        "tier1.storyline_chapter":   _LP.B_SINGLE_CRITIC,
        "tier1.chronicle_profiled":  _LP.B_SINGLE_CRITIC,
        "tier1.canon_top10":         _LP.A_SINGLE_SHOT,
        "tier1.canon_tail":          _LP.A_SINGLE_SHOT,
        "tier1.pulse_themes_writer": _LP.A_SINGLE_SHOT,
        "tier1.best_calls":          _LP.A_SINGLE_SHOT,
        "tier1.pulse_lede":          _LP.A_SINGLE_SHOT,
    }


SURFACE_DEGRADE_PATTERN: "dict[str, LoopPattern]" = _surface_degrade_pattern_map()


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
