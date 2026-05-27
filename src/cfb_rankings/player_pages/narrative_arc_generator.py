"""Narrative Arc LLM generator — Wave 15 / Brief §4 narrative-arc.

Three-act season story: opening / pivot / finish. Each act is ~40-60
words of grounded prose summarizing that stretch of the season.
Inputs come from the player's game log (player_game_stats joined to
games) — broken into three roughly equal slices of weeks.

Cache table: player_narrative_arc (schema added in migration
20260527_03). Re-runs are idempotent and refresh only when the input
hash changes.

Public API:
    generate_narrative_arc(db, player_id, season_year, position) -> dict | None
    fetch_narrative_arc(db, player_id, season_year)              -> dict | None
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from typing import Any

from .signature_story_generator import (
    DEFAULT_MODEL_ID, DEFAULT_OLLAMA_URL,
    _ollama_generate, _strip_artifacts, _position_phrase,
)


def _content_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:16]


def _fetch_game_log_compact(
    db, player_id: int, season_year: int,
) -> list[dict[str, Any]]:
    """One condensed row per game with the headline stat per category."""
    rows = db.query_all(
        """
        select
          pgs.week, pgs.game_id, pgs.team_id, pgs.category, pgs.stat_type,
          pgs.stat_value_num, pgs.stat_value_text,
          g.home_team_id, g.away_team_id, g.home_points, g.away_points,
          home_t.canonical_name as home_team_name,
          away_t.canonical_name as away_team_name
        from player_game_stats pgs
        left join games g on g.game_id = pgs.game_id
        left join teams home_t on home_t.team_id = g.home_team_id
        left join teams away_t on away_t.team_id = g.away_team_id
        where pgs.player_id = :pid
          and pgs.season_year = :s
          and pgs.stat_type in ('YDS','TD','INT','TOT','SACKS','PD','CAR','REC','C/ATT')
        order by pgs.week asc
        """,
        {"pid": player_id, "s": season_year},
    )
    by_game: dict[int, dict[str, Any]] = {}
    for r in rows:
        gid = int(r["game_id"]) if r.get("game_id") is not None else 0
        if gid == 0:
            continue
        bucket = by_game.setdefault(gid, {
            "game_id": gid, "week": r.get("week"),
            "team_id": r.get("team_id"),
            "home_team_id": r.get("home_team_id"),
            "away_team_id": r.get("away_team_id"),
            "home_points": r.get("home_points"),
            "away_points": r.get("away_points"),
            "home_team_name": r.get("home_team_name"),
            "away_team_name": r.get("away_team_name"),
            "stats": {},
        })
        cat = (r.get("category") or "").lower()
        stype = (r.get("stat_type") or "").upper()
        v = r.get("stat_value_num")
        if v is None:
            v = r.get("stat_value_text")
        if v is not None:
            bucket["stats"][f"{cat}.{stype}"] = v
    games = sorted(by_game.values(), key=lambda x: x.get("week") or 99)
    return games


def _summarize_act(games: list[dict[str, Any]], focus_position: str) -> str:
    """Plain-text summary of a 3-5 game stretch — fed into the LLM prompt."""
    if not games:
        return "(no games in this stretch)"
    lines: list[str] = []
    for g in games:
        wk = g.get("week")
        team = g.get("team_id")
        is_home = (team is not None and g.get("home_team_id") is not None
                   and int(team) == int(g["home_team_id"]))
        opp = g.get("away_team_name") if is_home else g.get("home_team_name")
        hp = g.get("home_points"); ap = g.get("away_points")
        loc = "vs" if is_home else "@"
        # Determine W/L from team's perspective
        result = "—"
        if hp is not None and ap is not None:
            mine = hp if is_home else ap
            theirs = ap if is_home else hp
            result = f"{'W' if mine > theirs else ('L' if mine < theirs else 'T')} {mine}-{theirs}"
        # Stats line — pick position-relevant ones
        stats = g.get("stats", {})
        s_parts: list[str] = []
        pos = (focus_position or "").upper()
        if pos == "QB":
            yd = stats.get("passing.YDS")
            td = stats.get("passing.TD")
            it = stats.get("passing.INT")
            ca = stats.get("passing.C/ATT")
            if ca: s_parts.append(f"{ca}")
            if yd is not None: s_parts.append(f"{int(yd)} yds")
            if td is not None: s_parts.append(f"{int(td)} TD")
            if it is not None: s_parts.append(f"{int(it)} INT")
        elif pos in {"RB", "TB", "FB", "HB"}:
            ca = stats.get("rushing.CAR")
            yd = stats.get("rushing.YDS")
            td = stats.get("rushing.TD")
            if ca is not None: s_parts.append(f"{int(ca)} car")
            if yd is not None: s_parts.append(f"{int(yd)} yds")
            if td is not None: s_parts.append(f"{int(td)} TD")
        elif pos in {"WR", "TE"}:
            rc = stats.get("receiving.REC")
            yd = stats.get("receiving.YDS")
            td = stats.get("receiving.TD")
            if rc is not None: s_parts.append(f"{int(rc)} rec")
            if yd is not None: s_parts.append(f"{int(yd)} yds")
            if td is not None: s_parts.append(f"{int(td)} TD")
        else:
            tk = stats.get("defensive.TOT")
            sk = stats.get("defensive.SACKS")
            pd = stats.get("defensive.PD")
            if tk is not None: s_parts.append(f"{int(tk)} tkl")
            if sk is not None: s_parts.append(f"{sk} sk")
            if pd is not None: s_parts.append(f"{int(pd)} PD")
        stat_str = " · ".join(s_parts) if s_parts else "—"
        lines.append(f"  Week {wk} {loc} {opp or '?'} ({result}): {stat_str}")
    return "\n".join(lines)


def _gather_arc_inputs(
    db, player_id: int, season_year: int, position: str,
) -> dict[str, Any] | None:
    games = _fetch_game_log_compact(db, int(player_id), int(season_year))
    if len(games) < 6:
        return None  # Too few games to write a 3-act arc

    # Player + team
    pr = db.query_all(
        "select full_name from players where player_id = :pid",
        {"pid": player_id},
    )
    if not pr:
        return None
    name = pr[0]["full_name"]
    tr = db.query_all(
        """
        select team_name, position from player_season_stats
         where player_id = :pid and season_year = :s
         order by week desc limit 1
        """,
        {"pid": player_id, "s": season_year},
    )
    team_name = tr[0]["team_name"] if tr else ""
    pos = position or (tr[0]["position"] if tr else None) or ""

    # Slice games into thirds.
    n = len(games)
    third = n // 3
    opening = games[:third]
    pivot = games[third:2*third]
    finish = games[2*third:]

    return {
        "player_name": name, "team_name": team_name,
        "position": pos, "season_year": season_year,
        "n_games": n,
        "opening_summary": _summarize_act(opening, pos),
        "pivot_summary": _summarize_act(pivot, pos),
        "finish_summary": _summarize_act(finish, pos),
    }


def _build_arc_prompt(inputs: dict[str, Any]) -> str:
    pn = inputs["player_name"]
    pos = inputs["position"]
    pos_phrase = _position_phrase(pos)
    team = inputs["team_name"] or "his program"
    return f"""Subject: {pn}. Position: {pos} ({pos_phrase}). Team: {team}. Season: {inputs['season_year']}.

You are writing a 3-act narrative arc for this {pos} player's {inputs['season_year']} season. Output ONLY structured JSON (no preamble, no commentary, no code fences) with these exact keys:

{{
  "opening": "40-60 word paragraph",
  "pivot":   "40-60 word paragraph",
  "finish":  "40-60 word paragraph"
}}

STRICT RULES:
- Position cohort: {pos_phrase}. Never refer to any other position.
- Use ONLY the game-by-game facts below. Do not invent.
- Each act is ONE paragraph of plain English, 40-60 words. No headings inside the act.
- Voice: confident, concrete, present tense. No clichés. Banned: stellar, phenomenal, generational, playmaker, gunslinger, undeniable, cementing.
- Lead each act with the structural moment (e.g. "{pn} opens the season with..."), then 1-2 specific games, then the takeaway.
- Do not mention "act 1/2/3" or "opening/pivot/finish" inside the text.

GAME LOG — OPENING ({len(inputs['opening_summary'].splitlines())} games):
{inputs['opening_summary']}

GAME LOG — PIVOT ({len(inputs['pivot_summary'].splitlines())} games):
{inputs['pivot_summary']}

GAME LOG — FINISH ({len(inputs['finish_summary'].splitlines())} games):
{inputs['finish_summary']}

Output the JSON now."""


def _parse_arc_json(raw: str) -> dict[str, str] | None:
    text = _strip_artifacts(raw)
    # Try to extract JSON block
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    out: dict[str, str] = {}
    for key in ("opening", "pivot", "finish"):
        v = data.get(key)
        if not isinstance(v, str) or len(v.strip()) < 30:
            return None
        out[key] = v.strip()
    return out


def generate_narrative_arc(
    db, player_id: int, season_year: int, position: str,
    *, model_id: str | None = None, base_url: str | None = None,
    force_refresh: bool = False,
) -> dict[str, Any] | None:
    inputs = _gather_arc_inputs(db, int(player_id), int(season_year), position or "")
    if inputs is None:
        return None
    chash = _content_hash(inputs)
    if not force_refresh:
        cached = db.query_all(
            """
            select content_hash, opening_text, pivot_text, finish_text
              from player_narrative_arc
             where player_id = :pid and season_year = :s
            """,
            {"pid": int(player_id), "s": int(season_year)},
        )
        if cached and cached[0]["content_hash"] == chash:
            return dict(cached[0])

    model = model_id or DEFAULT_MODEL_ID
    url = base_url or DEFAULT_OLLAMA_URL
    prompt = _build_arc_prompt(inputs)

    arc: dict[str, str] | None = None
    for _ in range(3):
        raw = _ollama_generate(prompt, model, url, timeout_s=90.0)
        if not raw:
            return None
        parsed = _parse_arc_json(raw)
        if parsed:
            arc = parsed
            break
    if arc is None:
        return None

    payload = {
        "player_id": int(player_id),
        "season_year": int(season_year),
        "content_hash": chash,
        "opening_text": arc["opening"],
        "pivot_text": arc["pivot"],
        "finish_text": arc["finish"],
        "model_id": f"ollama:{model}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    db.execute(
        """
        insert into player_narrative_arc
            (player_id, season_year, content_hash, opening_text,
             pivot_text, finish_text, model_id, generated_at)
        values
            (:player_id, :season_year, :content_hash, :opening_text,
             :pivot_text, :finish_text, :model_id, :generated_at)
        on conflict(player_id, season_year) do update set
            content_hash = excluded.content_hash,
            opening_text = excluded.opening_text,
            pivot_text   = excluded.pivot_text,
            finish_text  = excluded.finish_text,
            model_id     = excluded.model_id,
            generated_at = excluded.generated_at
        """,
        payload,
    )
    return payload


def fetch_narrative_arc(
    db, player_id: int | None, season_year: int | None,
) -> dict[str, Any] | None:
    if db is None or player_id is None or season_year is None:
        return None
    rows = db.query_all(
        """
        select opening_text, pivot_text, finish_text, model_id, generated_at
          from player_narrative_arc
         where player_id = :pid and season_year = :s
        """,
        {"pid": int(player_id), "s": int(season_year)},
    )
    return dict(rows[0]) if rows else None
