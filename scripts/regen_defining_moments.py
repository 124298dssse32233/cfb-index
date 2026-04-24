"""Regenerate failing historical-season defining_moments cards.

Applies the Chronicle Stage-4 validation gate (proper noun + banned phrases +
comparative marker) to each defining_moment body in the 20 flagship seasons
(Alabama 2014-2025, Notre Dame 2016/2018/2020/2024, Ohio State 2014/2024,
Vanderbilt 2020/2025). For each failure:

  * Prompts Sonnet with a tight rewrite-in-place directive that preserves
    type/register/voice but fixes the comparative/proper-noun gap.
  * Retries once on validation failure.
  * Drops the card from ``defining_moments_json`` after a second failure
    (brief §Phase 3).

Per-card cost: ~1-2 Sonnet calls. Expected wall time: ~10-20 min with
``--workers 3``.
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

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from cfb_rankings.team_pages.chronicle_generator import (
    _BANNED_PHRASES, _COMPARATIVE_MARKERS_RE, _STOPWORD_CAPS,
    CLAUDE_MODEL_SONNET, CLAUDE_MODEL_OPUS,
)
from cfb_rankings.team_pages.profile_loader import load_profile


SEASONS: list[tuple[str, int]] = (
    [("alabama", y) for y in range(2014, 2026)]
    + [("notre-dame", y) for y in (2016, 2018, 2020, 2024)]
    + [("ohio-state", y) for y in (2014, 2024)]
    + [("vanderbilt", y) for y in (2020, 2025)]
)

OPUS_SEASONS = {("alabama", 2020), ("notre-dame", 2024)}


def check_card(body: str, profile) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    low = body.lower()
    program_tokens = {t.lower() for t in profile.program_name.split()} | {"the"}
    has_specific = False
    for tok in body.split():
        clean = tok.strip(".,;:!?'\"()[]·—–-").strip()
        if not clean or not clean[0].isupper():
            continue
        if clean.lower() in program_tokens:
            continue
        if clean in _STOPWORD_CAPS:
            continue
        if len(clean) < 2:
            continue
        has_specific = True
        break
    if not has_specific:
        if re.search(r"\b(19|20)\d{2}\b", body):
            has_specific = True
        elif re.search(r"\b\d+[-–]\d+\b", body):
            has_specific = True
    if not has_specific:
        reasons.append("no-proper-noun")
    for phrase in _BANNED_PHRASES:
        if phrase in low:
            reasons.append(f"banned:{phrase.strip()}")
            break
    for phrase in [p.lower() for p in (profile.never_use or [])]:
        if not phrase:
            continue
        if phrase in low:
            reasons.append(f"never_use:{phrase}")
            break
    if not _COMPARATIVE_MARKERS_RE.search(body):
        reasons.append("no-comparative")
    return (len(reasons) == 0), reasons


def build_prompt(original: str, card_type: str, register: str, profile, slug: str, year: int) -> str:
    banned = "\n".join(f"- {p.strip()}" for p in _BANNED_PHRASES)
    stock = "\n".join(f"- {s}" for s in (profile.stock_phrases or [])[:3]) or "- (none)"
    never = "\n".join(f"- {s}" for s in (profile.never_use or [])[:5]) or "- (none)"
    return f"""Rewrite ONE defining_moment body for {profile.program_name}'s {year} season.

This sits on the team page under a header like "{card_type}" (register: {register}).
Tone: archival beat-writer, not stats-engine, not cheerleading.

# Original
{original}

# Your task
Rewrite the body. KEEP every proper noun, every score, every specific name
and date from the original. Preserve the factual content exactly.

You MUST additionally:

1. Include at least ONE comparative marker from this set (pick whichever fits
   the fact, do not force it): since / like / only / longest / first time /
   last time / first since / biggest [X] since / first [X] ever / not seen
   since / most consecutive / fewest / ever / never / always / [N] years /
   decade / era / reconstruction / restoration / dynasty / wilderness /
   return / chapter / [N]th percentile / top-N / above / below / ahead of /
   behind / ranked / more than / fewer than / [N] seasons / generations.

2. Include at least one specific proper noun beyond "{profile.program_name}"
   (a player, coach, opponent, venue, date — the original already has
   these, preserve them).

3. Voice register: {profile.voice_register}
   Stock phrases you MAY lean on (don't force):
{stock}
   Never use:
{never}

# Hard constraints

- 2-4 sentences. 35-110 words.
- NO banned scaffolding phrases (case-insensitive):
{banned}
- NO "pipeline", "algorithm", "stat engine", "this card", "our model".
- Editorial, not academic. No hedging like "arguably" or "it could be said".

# Output

Return ONLY the rewritten body. No preamble, no quotes, no JSON.
"""


def call_claude(prompt: str, model: str, timeout_s: float = 180.0) -> tuple[str, dict]:
    meta: dict = {"model": model, "error": None, "duration_s": 0.0}
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
    out = (proc.stdout or "").strip()
    # Strip wrapping quotes if present.
    if out.startswith('"') and out.endswith('"'):
        out = out[1:-1].strip()
    return out, meta


def regen_one(
    original: str,
    card_type: str,
    register: str,
    profile,
    slug: str,
    year: int,
    model: str,
) -> tuple[str | None, dict]:
    prompt = build_prompt(original, card_type, register, profile, slug, year)
    text, meta = call_claude(prompt, model)
    if meta.get("error") or not text:
        return None, meta
    ok, reasons = check_card(text, profile)
    if ok:
        meta["validated"] = True
        return text, meta
    # Retry once.
    meta["first_fail_reasons"] = reasons
    text2, meta2 = call_claude(prompt, model)
    if meta2.get("error") or not text2:
        meta["retry_error"] = meta2.get("error")
        return None, meta
    ok2, reasons2 = check_card(text2, profile)
    if ok2:
        meta["validated"] = True
        meta["retry_used"] = True
        return text2, meta
    meta["retry_fail_reasons"] = reasons2
    return None, meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="cfb_rankings.db")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true",
                    help="Audit only; do not call the LLM or update the DB.")
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    cur = conn.cursor()

    profiles: dict[str, object] = {}

    def get_profile(slug: str):
        if slug not in profiles:
            profiles[slug] = load_profile(slug)
        return profiles[slug]

    jobs: list[dict] = []
    before_totals = {"pass": 0, "fail": 0}
    per_season_fails: dict[tuple[str, int], int] = {}

    for slug, year in SEASONS:
        cur.execute(
            "select defining_moments_json from team_historical_seasons "
            "where team_slug=? and season_year=?",
            (slug, year),
        )
        row = cur.fetchone()
        if not row or not row[0]:
            print(f"  MISSING: {slug}/{year}")
            continue
        dm = json.loads(row[0])
        p = get_profile(slug)
        for i, card in enumerate(dm):
            ok, reasons = check_card(card["body"], p)
            if ok:
                before_totals["pass"] += 1
                continue
            before_totals["fail"] += 1
            per_season_fails[(slug, year)] = per_season_fails.get((slug, year), 0) + 1
            jobs.append(
                {
                    "slug": slug, "year": year, "idx": i,
                    "type": card.get("type", ""),
                    "register": card.get("register", ""),
                    "body": card["body"],
                    "reasons": reasons,
                }
            )

    print(f"\nAudit: {before_totals['pass']} pass / {before_totals['fail']} fail "
          f"({len(SEASONS)} seasons, "
          f"{before_totals['pass'] + before_totals['fail']} cards)")
    if not jobs:
        print("Nothing to do.")
        return 0
    # Policy gate: per brief, >5 fails in any season signals a voice_register
    # mismatch and should stop.
    stopping = [(k, v) for k, v in per_season_fails.items() if v > 5]
    if stopping:
        print(f"STOP: {stopping} exceed 5 failures — flag to Kevin")
        return 2
    if args.dry_run:
        print("dry-run; exiting without calls.")
        return 0

    # Run jobs.
    def _runner(job: dict) -> dict:
        p = get_profile(job["slug"])
        model = (CLAUDE_MODEL_OPUS
                 if (job["slug"], job["year"]) in OPUS_SEASONS
                 else CLAUDE_MODEL_SONNET)
        new_body, meta = regen_one(
            job["body"], job["type"], job["register"], p,
            job["slug"], job["year"], model,
        )
        return {**job, "new_body": new_body, "meta": meta, "model": model}

    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(_runner, j) for j in jobs]
        for fut in as_completed(futs):
            r = fut.result()
            results.append(r)
            tag = "ok" if r.get("new_body") else "DROP"
            reasons = r["meta"].get("retry_fail_reasons") or r["meta"].get("error")
            dur = r["meta"].get("duration_s")
            print(f"  [{r['slug']}/{r['year']} #{r['idx']}] {tag} model={r['model']} dur={dur}s "
                  f"{'' if tag=='ok' else 'reason='+str(reasons)}")

    # Apply DB updates.
    updates_by_season: dict[tuple[str, int], list[dict]] = {}
    for r in results:
        updates_by_season.setdefault((r["slug"], r["year"]), []).append(r)

    n_regen = 0
    n_drop = 0
    for (slug, year), rs in updates_by_season.items():
        cur.execute(
            "select defining_moments_json from team_historical_seasons "
            "where team_slug=? and season_year=?",
            (slug, year),
        )
        dm = json.loads(cur.fetchone()[0])
        # Apply: rewrite-in-place or mark for drop.
        to_drop_idx: set[int] = set()
        for r in rs:
            i = r["idx"]
            if r.get("new_body"):
                dm[i]["body"] = r["new_body"]
                dm[i]["model_id"] = r["model"]
                n_regen += 1
            else:
                to_drop_idx.add(i)
                n_drop += 1
        dm = [c for i, c in enumerate(dm) if i not in to_drop_idx]
        cur.execute(
            "update team_historical_seasons "
            "set defining_moments_json=? where team_slug=? and season_year=?",
            (json.dumps(dm, ensure_ascii=False), slug, year),
        )
    conn.commit()
    # Post-audit.
    after_pass = 0
    after_fail = 0
    for slug, year in SEASONS:
        cur.execute(
            "select defining_moments_json from team_historical_seasons "
            "where team_slug=? and season_year=?",
            (slug, year),
        )
        row = cur.fetchone()
        if not row or not row[0]:
            continue
        dm = json.loads(row[0])
        p = get_profile(slug)
        for card in dm:
            ok, _ = check_card(card["body"], p)
            if ok:
                after_pass += 1
            else:
                after_fail += 1
    print(f"\nPost-audit: {after_pass} pass / {after_fail} fail "
          f"(regen ok={n_regen}, dropped={n_drop})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
