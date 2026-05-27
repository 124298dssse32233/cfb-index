"""Signature Story LLM generator — Brief §4.7 (P1).

Generates a 2-3 sentence prose narrative explaining what makes a
player's season distinctive. Inputs:
  - CFB Index composite score + tier
  - Top 3 Savant bars (highest-percentile metrics + their cohort context)
  - Signature game (highest single-game volume)
  - Standing rung (e.g. R15 Heisman finalist)

Uses the local Ollama instance (mistral-nemo:12b-instruct-2407-q4_K_M
Writer per CLAUDE.md chronicle pipeline). Caches output to
`player_signature_story` keyed by player_id + season_year + content_hash.
Re-running regenerates only when inputs change.

Public API:
    generate_signature_story(db, player_id, season_year, position) -> dict | None
    fetch_signature_story(db, player_id, season_year)             -> dict | None
    DEFAULT_MODEL_ID                                              = str
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from html import escape
from typing import Any

from .box_savant import compute_savant_bars
from .composite_score import compute_cfb_index_score


DEFAULT_MODEL_ID = os.environ.get(
    "CFB_INDEX_SIGSTORY_MODEL",
    "mistral-nemo:12b-instruct-2407-q4_K_M",
)
DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")  # IPv4 — Windows binds IPv6 first by default


def _content_hash(payload: dict[str, Any]) -> str:
    """Stable hash over the structured inputs."""
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _gather_inputs(
    db, player_id: int, season_year: int, position: str,
) -> dict[str, Any] | None:
    bars = compute_savant_bars(db, player_id, season_year, position)
    if len(bars) < 3:
        return None
    score = compute_cfb_index_score(db, player_id, season_year, position)

    # Player + team. Prefer position from player_season_stats — the
    # players.position master column is sparse / sometimes wrong (e.g.
    # Dillon Gabriel listed as 'RB' in players table).
    pr = db.query_all(
        "select full_name from players where player_id = :pid",
        {"pid": player_id},
    )
    if not pr:
        return None
    full_name = pr[0]["full_name"]

    tr = db.query_all(
        """
        select team_name, position from player_season_stats
         where player_id = :pid and season_year = :s
         order by week desc limit 1
        """,
        {"pid": player_id, "s": season_year},
    )
    team_name = tr[0]["team_name"] if tr else ""
    # Trust caller's `position` first (already passed in from authoritative source);
    # fall back to player_season_stats, finally to whatever's on the players row.
    pos = position or (tr[0]["position"] if tr else None) or ""

    # Signature game = highest single-game volume in the primary metric category
    primary_cat = bars[0]["category"] if bars else "passing"
    primary_stat = "YDS"
    game_rows = db.query_all(
        f"""
        select pgs.week, pgs.stat_value_num as v, pgs.team_id,
               g.home_team_id, g.away_team_id, g.home_points, g.away_points,
               home_t.canonical_name as home_team_name,
               away_t.canonical_name as away_team_name
          from player_game_stats pgs
          left join games g on g.game_id = pgs.game_id
          left join teams home_t on home_t.team_id = g.home_team_id
          left join teams away_t on away_t.team_id = g.away_team_id
         where pgs.player_id = :pid
           and pgs.season_year = :s
           and pgs.category = :cat
           and pgs.stat_type = :stype
           and pgs.stat_value_num is not null
         order by pgs.stat_value_num desc
         limit 1
        """,
        {"pid": player_id, "s": season_year, "cat": primary_cat, "stype": primary_stat},
    )
    sig_game = None
    if game_rows:
        gr = game_rows[0]
        is_home = (gr.get("team_id") is not None
                   and gr.get("home_team_id") is not None
                   and int(gr["team_id"]) == int(gr["home_team_id"]))
        opp = gr.get("away_team_name") if is_home else gr.get("home_team_name")
        opp_loc = "vs" if is_home else "@"
        sig_game = {
            "week": gr.get("week"),
            "value": gr.get("v"),
            "opponent": opp,
            "opp_loc": opp_loc,
            "home_points": gr.get("home_points"),
            "away_points": gr.get("away_points"),
        }

    return {
        "player_name": full_name,
        "team_name": team_name,
        "position": pos,
        "season_year": season_year,
        "score": score,
        "bars": [
            {
                "label": b["label"],
                "value_fmt": b["value_fmt"],
                "percentile": round(b["percentile"], 1),
                "rank": b["rank"],
                "cohort_size": b["cohort_size"],
            }
            for b in bars[:6]
        ],
        "signature_game": sig_game,
    }


def _position_phrase(pos: str) -> str:
    """Human-readable plural for the position cohort phrase."""
    p = (pos or "").upper().strip()
    return {
        "QB": "quarterbacks",
        "RB": "running backs", "TB": "running backs", "FB": "running backs", "HB": "running backs",
        "WR": "receivers",
        "TE": "tight ends",
        "CB": "cornerbacks", "S": "safeties",
        "DB": "defensive backs",
        "LB": "linebackers", "ILB": "linebackers", "OLB": "linebackers", "MLB": "linebackers",
        "DL": "defensive linemen", "DE": "edges", "EDGE": "edges",
        "DT": "interior defensive linemen", "NT": "nose tackles",
        "OL": "offensive linemen", "OT": "offensive tackles", "OG": "offensive guards",
        "C": "centers",
        "K": "kickers", "PK": "kickers",
        "P": "punters",
    }.get(p, f"{p} players")


def _build_prompt(inputs: dict[str, Any]) -> str:
    pn = inputs["player_name"]
    team = inputs["team_name"] or "his program"
    pos = inputs["position"]
    pos_phrase = _position_phrase(pos)
    sy = inputs["season_year"]
    score = inputs.get("score") or {}
    bars = inputs.get("bars") or []

    # Pick top-3 to feed; truncate cohort size phrasing to avoid mismatch.
    bar_lines = "\n".join(
        f"  • {b['label']} = {b['value_fmt']} (percentile {int(round(b['percentile']))}, "
        f"rank {b['rank']} of {b['cohort_size']} FBS {pos_phrase})"
        for b in bars[:3]
    )

    score_line = ""
    if score and score.get("score") is not None:
        score_line = (
            f"Composite CFB Index score: {score['score']}/100 "
            f"({score.get('tier_label') or 'unrated'} tier within the cohort)."
        )

    return f"""Subject: {pn}. Position: {pos} ({pos_phrase}). Team: {team}. Season: {sy}.

You are writing the "Signature Story" prose for this {pos} player. The cohort being compared against is exclusively {pos_phrase}; do not refer to any other position. Output ONLY the body prose. 2-3 sentences, 55-85 words.

STRICT FACT RULES (violating any → output rejected):
- The position cohort is "{pos_phrase}". NEVER refer to any other position.
- Use ONLY the stats listed below. Do NOT invent stat lines, opponents, scores, or game counts.
- Do NOT mix per-game numbers with season totals. The stats below are season totals.
- Percentile phrasing: e.g. "78th-percentile" or "in the top 22% of FBS {pos_phrase}". Do not call a 60th percentile "elite".

STYLE RULES:
- Voice: confident, concrete, no hype. No clichés.
- Banned words: stellar, phenomenal, generational, playmaker, stud, dazzle, gunslinger, undeniable, cementing, cement.
- Lead with the one specific stat that defines the season. Then one supporting fact. End with the takeaway (rank/tier/cohort).
- Plain English; no em-dashes; no bracketed citations.

INPUTS (season totals, sorted best percentile first):
{bar_lines}
{score_line}

Now write the Signature Story for {pn}. Output JUST the prose paragraph, nothing else."""


_BANNED_PHRASES = (
    "stellar", "phenomenal", "generational",
    "playmaker", "stud", "dazzle",
    "gunslinger", "undeniable", "cementing", "cement",
)
_POSITION_FAMILY = {
    "QB": {"quarterbacks", "qb"},
    "RB": {"running backs", "rb", "halfback", "halfbacks", "tailback", "tailbacks"},
    "TB": {"running backs", "rb", "tailback", "tailbacks"},
    "FB": {"running backs", "fullback", "fullbacks"},
    "HB": {"running backs", "halfback", "halfbacks"},
    "WR": {"receivers", "wide receivers", "wr"},
    "TE": {"tight ends", "te"},
    "CB": {"cornerbacks", "defensive backs", "cb", "db"},
    "S":  {"safeties", "defensive backs", "db"},
    "DB": {"defensive backs", "db", "cornerbacks", "safeties"},
    "LB": {"linebackers", "lb"},
    "ILB":{"linebackers", "lb"},
    "OLB":{"linebackers", "lb"},
    "MLB":{"linebackers", "lb"},
    "DL": {"defensive linemen", "edges", "edge", "dl"},
    "DE": {"edges", "edge", "defensive ends", "dl"},
    "EDGE": {"edges", "edge", "dl"},
    "DT": {"defensive tackles", "interior defensive linemen", "dl"},
    "NT": {"nose tackles", "dl"},
    "OL": {"offensive linemen", "ol"},
    "OT": {"offensive tackles", "ol"},
    "OG": {"offensive guards", "ol"},
    "C":  {"centers", "ol"},
    "K":  {"kickers", "k"},
    "PK": {"kickers", "k"},
    "P":  {"punters", "p"},
}


def validate_story(text: str, position: str) -> tuple[bool, str | None]:
    """Return (ok, reason). False reason explains the violation."""
    lower = text.lower()
    # Banned hype/cliché words
    for w in _BANNED_PHRASES:
        if re.search(rf"\b{re.escape(w)}\b", lower):
            return (False, f"banned word: {w!r}")

    # Position cross-check: any OTHER position family name appearing in the story.
    own = _POSITION_FAMILY.get((position or "").upper(), set())
    for pos_key, names in _POSITION_FAMILY.items():
        if pos_key == (position or "").upper():
            continue
        for n in names:
            # Avoid false-positive on short tokens
            if len(n) < 3:
                continue
            if n in own:
                continue
            # Multi-word match
            if " " in n:
                if n in lower:
                    return (False, f"mentions other position cohort: {n!r}")
            else:
                # single-word: word-boundary so "edge" doesn't match "edged"
                if re.search(rf"\b{re.escape(n)}\b", lower):
                    if any(o in own for o in (n,)):
                        continue
                    return (False, f"mentions other position cohort: {n!r}")
    return (True, None)


def _strip_artifacts(text: str) -> str:
    """Remove markdown bold, thinking tags, stray quote wrappers."""
    if "<think>" in text and "</think>" in text:
        text = re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL)
    text = text.strip()
    # Strip wrapping quotes
    if (text.startswith('"') and text.endswith('"')) or (
        text.startswith("'") and text.endswith("'")
    ):
        text = text[1:-1].strip()
    # Collapse markdown bold/italic
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    # Strip leading "Signature Story:" labels
    text = re.sub(r"^(Signature Story|Story)[:\-—]\s*", "", text, flags=re.IGNORECASE)
    return text.strip()


def _ollama_generate(
    prompt: str, model_id: str, base_url: str, timeout_s: float = 60.0,
) -> str | None:
    try:
        import httpx
    except ImportError:
        return None
    body: dict[str, Any] = {
        "model": model_id,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.35,
            "top_p": 0.85,
            "repeat_penalty": 1.10,
            "num_predict": 240,
        },
        "keep_alive": "5m",
    }
    if "qwen3" in model_id.lower():
        body["think"] = False
    try:
        with httpx.Client(timeout=timeout_s) as client:
            resp = client.post(
                f"{base_url.rstrip('/')}/api/generate",
                json=body,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            return resp.json().get("response", "")
    except Exception as exc:  # noqa: BLE001
        print(f"  ollama generate failed: {type(exc).__name__}: {exc}", flush=True)
        return None


def generate_signature_story(
    db, player_id: int, season_year: int, position: str,
    *,
    model_id: str | None = None,
    base_url: str | None = None,
    force_refresh: bool = False,
) -> dict[str, Any] | None:
    """Compute and cache a signature story.

    Returns the cached/new story dict or None on failure.
    """
    inputs = _gather_inputs(db, int(player_id), int(season_year), position or "")
    if inputs is None:
        return None
    chash = _content_hash(inputs)

    # Cache hit?
    if not force_refresh:
        cached = db.query_all(
            """
            select content_hash, story_text, headline, pull_quote, model_id, n_metrics_used
              from player_signature_story
             where player_id = :pid and season_year = :s
            """,
            {"pid": int(player_id), "s": int(season_year)},
        )
        if cached and cached[0]["content_hash"] == chash:
            return dict(cached[0])

    model = model_id or DEFAULT_MODEL_ID
    url = base_url or DEFAULT_OLLAMA_URL
    prompt = _build_prompt(inputs)

    story_text: str | None = None
    last_reason = None
    for attempt in range(3):
        raw = _ollama_generate(prompt, model, url)
        if not raw:
            return None
        candidate = _strip_artifacts(raw)
        if not candidate or len(candidate) < 40:
            last_reason = "too-short"
            continue
        ok, reason = validate_story(candidate, position or "")
        if ok:
            story_text = candidate
            break
        last_reason = reason
        # Sharpen prompt on retry with explicit warning
        prompt = (
            f"PREVIOUS DRAFT WAS REJECTED. Reason: {reason}. "
            f"Do NOT repeat that error.\n\n" + _build_prompt(inputs)
        )
    if story_text is None:
        print(
            f"  signature-story rejected after 3 attempts for player={player_id}: "
            f"{last_reason}",
            flush=True,
        )
        return None

    payload = {
        "player_id": int(player_id),
        "season_year": int(season_year),
        "content_hash": chash,
        "story_text": story_text,
        "headline": None,
        "pull_quote": None,
        "model_id": f"ollama:{model}",
        "n_metrics_used": len(inputs["bars"]),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    db.execute(
        """
        insert into player_signature_story
            (player_id, season_year, content_hash, story_text, headline,
             pull_quote, model_id, n_metrics_used, generated_at)
        values
            (:player_id, :season_year, :content_hash, :story_text, :headline,
             :pull_quote, :model_id, :n_metrics_used, :generated_at)
        on conflict(player_id, season_year) do update set
            content_hash = excluded.content_hash,
            story_text = excluded.story_text,
            headline = excluded.headline,
            pull_quote = excluded.pull_quote,
            model_id = excluded.model_id,
            n_metrics_used = excluded.n_metrics_used,
            generated_at = excluded.generated_at
        """,
        payload,
    )
    return payload


def fetch_signature_story(
    db, player_id: int | None, season_year: int | None,
) -> dict[str, Any] | None:
    if db is None or player_id is None or season_year is None:
        return None
    rows = db.query_all(
        """
        select story_text, headline, pull_quote, model_id, generated_at
          from player_signature_story
         where player_id = :pid and season_year = :s
        """,
        {"pid": int(player_id), "s": int(season_year)},
    )
    return dict(rows[0]) if rows else None
