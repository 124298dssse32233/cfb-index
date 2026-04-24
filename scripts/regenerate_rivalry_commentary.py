"""Regenerate `team_rivalry_meetings.commentary_text` via LLM.

The sprint-2 commentary (scripts/sprint2_rivalry_content.py) fills each
meeting with a templated one-liner drawn from a handful of stock
sentences. Per docs/CHRONICLE_EDITORIAL_BRIEF.md §spillover, every prior
meeting one-liner should be specific — the Beat-Writer Test applies.

This script:

  1. Loads the sprint-2 RIVALRY_FRAMES map (canonical-pair → trophy/era).
  2. For each meeting in a targeted (program_a, program_b) pair, builds a
     voice-aware prompt using BOTH programs' profile fields.
  3. Calls `claude -p` (Sonnet standard; Opus can be opted in) to produce
     ONE short line (≤25 words) anchored on the score + specific context.
  4. Validates (no banned scaffolding, contains the score, ≤45 words).
  5. Writes the new commentary to the DB; leaves the `commentary_model_id`
     set to the model used (e.g. `claude-sonnet-4-6`) so follow-up audits
     can distinguish template rows from regenerated rows.

Run:
    python scripts/regenerate_rivalry_commentary.py \
        --pair notre-dame,usc \
        --pair alabama,auburn \
        --pair michigan,ohio-state \
        --pair texas,oklahoma \
        --model auto
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Make src + repo root importable
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from cfb_rankings.team_pages.profile_loader import load_profile
from cfb_rankings.team_pages.chronicle_generator import (
    _BANNED_PHRASES, CLAUDE_MODEL_SONNET, CLAUDE_MODEL_OPUS,
)
from scripts.sprint2_rivalry_content import RIVALRY_FRAMES, PRIMARY_RIVALRIES  # type: ignore


def _canonical_pair(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a <= b else (b, a)


def build_prompt(meeting: dict, frame: dict, profile_a, profile_b) -> str:
    """Single-sentence rivalry commentary prompt — voice-aware."""
    a_never = "\n".join(f"- {s}" for s in profile_a.never_use) or "- (none)"
    b_never = "\n".join(f"- {s}" for s in profile_b.never_use) or "- (none)"
    banned_list = "\n".join(f"- {p.strip()}" for p in _BANNED_PHRASES)
    return f"""You are writing ONE sentence of commentary for a single meeting in the
{frame.get('trophy', 'rivalry')} archive. This line will display under the game's
score when a fan browses the rivalry history.

Context for the rivalry (for tone only, do not quote back):
{frame.get('era', '')}
{frame.get('register', '')}

# This meeting

Season: {meeting['season_year']}
Winner: {meeting['winner_slug']}
Score: {meeting['a_points']}-{meeting['b_points']}  (program_a={meeting['program_a_slug']}, program_b={meeting['program_b_slug']})
Margin: {meeting['margin']}
Venue: {meeting.get('venue') or 'unspecified'}

# Program A voice

program_name: {profile_a.program_name}
voice_register: {profile_a.voice_register}
stock_phrases: {profile_a.stock_phrases[:2]}
era_name_overrides: {profile_a.era_name_overrides}
never_use (avoid these even if writing about program B):
{a_never}

# Program B voice

program_name: {profile_b.program_name}
voice_register: {profile_b.voice_register}
stock_phrases: {profile_b.stock_phrases[:2]}
era_name_overrides: {profile_b.era_name_overrides}
never_use:
{b_never}

# Constraints

- ONE sentence. 14–30 words.
- Must include the score (e.g. "{meeting['a_points']}-{meeting['b_points']}") OR the year OR the margin verbatim.
- Must name ONE specific thing: a coach from the era, a venue, a play, a
  stat that actually reads off the score, or a specific cultural fact.
- Neutral editorial voice — a beat writer writing into the rivalry archive,
  not either program's fan. Do not cheerlead either side.
- NEVER use any of these phrases (case-insensitive):
{banned_list}
- Do NOT use generic phrases like "close game", "high-scoring affair",
  "instant classic", "all-time game", "will be remembered", "for the ages",
  "rivalry was built for", "shifted the sentence".

# Output

Return ONLY the single sentence, no quotes, no preamble, no JSON.
"""


def call_claude(prompt: str, model: str, timeout_s: float = 120.0) -> tuple[str, dict]:
    meta = {"model": model, "error": None, "duration_s": 0.0}
    claude_bin = shutil.which("claude")
    if not claude_bin:
        meta["error"] = "claude CLI not on PATH"
        return "", meta
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    start = time.time()
    try:
        proc = subprocess.run(
            [claude_bin, "-p", prompt, "--model", model],
            capture_output=True, text=True, timeout=timeout_s,
            encoding="utf-8", errors="replace", env=env,
        )
    except subprocess.TimeoutExpired:
        meta["error"] = "timeout"
        return "", meta
    meta["duration_s"] = round(time.time() - start, 2)
    if proc.returncode != 0:
        meta["error"] = f"exit={proc.returncode}: {(proc.stderr or '')[:200]}"
        return "", meta
    out = (proc.stdout or "").strip().strip('"').strip("'")
    # Keep the first line only (guard against multi-line model output).
    out = out.split("\n")[0].strip()
    return out, meta


_GENERIC_PHRASES = (
    "close game", "high-scoring affair", "instant classic", "all-time game",
    "will be remembered", "for the ages", "rivalry was built for",
    "shifted the sentence", "scoreboard read honest",
    "decided early enough", "second half was for record-keeping",
    "kind of game the rivalry",
)


def validate_sentence(text: str, meeting: dict) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if not text:
        reasons.append("empty output")
        return False, reasons
    low = text.lower()
    # Banned scaffolding
    for phrase in _BANNED_PHRASES:
        if phrase in low:
            reasons.append(f"banned: '{phrase.strip()}'")
            break
    for phrase in _GENERIC_PHRASES:
        if phrase in low:
            reasons.append(f"generic template phrase: '{phrase}'")
            break
    # Must mention score, margin, or year
    sc = f"{meeting['a_points']}-{meeting['b_points']}"
    alt_sc = f"{meeting['b_points']}-{meeting['a_points']}"
    has_anchor = (
        sc in text or alt_sc in text
        or str(meeting["season_year"]) in text
        or (str(abs(meeting["margin"])) in text)
    )
    if not has_anchor:
        reasons.append("no score/year/margin anchor")
    # Length check
    word_count = len(text.split())
    if word_count < 10 or word_count > 45:
        reasons.append(f"length {word_count} words outside 10–45")
    return (len(reasons) == 0), reasons


def run_pair(conn: sqlite3.Connection, a: str, b: str, *, model: str,
             workers: int = 3) -> tuple[int, int, int]:
    """Regenerate commentary for all meetings of (a, b). Returns (n_total, n_ok, n_dropped)."""
    a_slug, b_slug = _canonical_pair(a, b)
    frame = RIVALRY_FRAMES.get((a_slug, b_slug), {})
    # Load both profiles (required for voice injection).
    try:
        pa = load_profile(a_slug)
    except FileNotFoundError:
        print(f"  skip pair {a_slug}/{b_slug}: profile missing for {a_slug}")
        return 0, 0, 0
    try:
        pb = load_profile(b_slug)
    except FileNotFoundError:
        print(f"  skip pair {a_slug}/{b_slug}: profile missing for {b_slug}")
        return 0, 0, 0

    rows = conn.execute(
        """
        select team_rivalry_meeting_id, program_a_slug, program_b_slug,
               season_year, winner_slug, a_points, b_points, margin, venue
        from team_rivalry_meetings
        where program_a_slug = ? and program_b_slug = ?
          and is_complete = 1
        order by season_year
        """,
        (a_slug, b_slug),
    ).fetchall()
    meetings = [
        {
            "id": r[0], "program_a_slug": r[1], "program_b_slug": r[2],
            "season_year": int(r[3]) if r[3] else None,
            "winner_slug": r[4],
            "a_points": int(r[5]) if r[5] is not None else 0,
            "b_points": int(r[6]) if r[6] is not None else 0,
            "margin": int(r[7]) if r[7] is not None else 0,
            "venue": r[8],
        }
        for r in rows
    ]
    if not meetings:
        print(f"  pair {a_slug}/{b_slug}: no meetings")
        return 0, 0, 0

    model_sonnet = CLAUDE_MODEL_SONNET
    model_opus = CLAUDE_MODEL_OPUS

    def _worker(m: dict) -> tuple[dict, str, dict]:
        mdl = model_sonnet if model != "opus" else model_opus
        prompt = build_prompt(m, frame, pa, pb)
        text, meta = call_claude(prompt, mdl)
        return m, text, meta

    n_ok = 0
    n_dropped = 0
    n_total = len(meetings)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(_worker, m) for m in meetings]
        for fut in as_completed(futs):
            m, text, meta = fut.result()
            if meta.get("error"):
                print(f"    [{a_slug}/{b_slug} {m['season_year']}] call error: {meta['error']}")
                n_dropped += 1
                continue
            ok, reasons = validate_sentence(text, m)
            if not ok:
                # Retry once.
                prompt = build_prompt(m, frame, pa, pb)
                text2, meta2 = call_claude(prompt, meta["model"])
                ok2, reasons2 = validate_sentence(text2, m)
                if not ok2:
                    print(f"    [{a_slug}/{b_slug} {m['season_year']}] validation failed twice: "
                          f"first={reasons} retry={reasons2}")
                    n_dropped += 1
                    continue
                text = text2
            # Write the new commentary.
            conn.execute(
                """
                update team_rivalry_meetings
                set commentary_text = ?, commentary_model_id = ?
                where team_rivalry_meeting_id = ?
                """,
                (text, meta["model"], m["id"]),
            )
            n_ok += 1
            print(f"    [{a_slug}/{b_slug} {m['season_year']}] ok: {text}")
    conn.commit()
    return n_total, n_ok, n_dropped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", action="append", default=None,
                    help="Pair as 'slug1,slug2'. Repeat for multiple. Default: all Tier-1 profiled pairs.")
    ap.add_argument("--model", default="sonnet", choices=["sonnet", "opus"],
                    help="LLM for regeneration.")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--db", default="cfb_rankings.db")
    args = ap.parse_args()

    if args.pair:
        pairs = []
        for spec in args.pair:
            a, b = spec.split(",")
            pairs.append((a.strip(), b.strip()))
    else:
        pairs = []
        seen = set()
        for k, v in PRIMARY_RIVALRIES.items():
            pair = tuple(sorted([k, v]))
            if pair in seen:
                continue
            seen.add(pair)
            pairs.append(pair)

    conn = sqlite3.connect(args.db)
    conn.execute("pragma journal_mode=WAL;")
    total = ok = dropped = 0
    for (a, b) in pairs:
        print(f"\n== pair {a} / {b} ==")
        t, o, d = run_pair(conn, a, b, model=args.model, workers=args.workers)
        total += t
        ok += o
        dropped += d
    conn.close()
    print(f"\n=== done: {ok}/{total} regenerated, {dropped} dropped ===")


if __name__ == "__main__":
    main()
