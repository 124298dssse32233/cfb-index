"""Quantify off-topic noise per source/subchannel — read-only (task #6).

Scores a sample of team-tagged docs with the lexical football-relevance signal
(cfb_rankings.ingest.relevance) and reports, per (source, subchannel), the share
that carry at least one football anchor. LOW share + HIGH volume = a noise
concentration and a candidate for the OFFTOPIC_SUBREDDITS blocklist (the existing
zero-false-negative lever).

Because lexical anchors miss pure-hype posts, the "football %" here is a LOWER
BOUND on true relevance — so only treat *very* low shares as off-topic signal.

    python scripts/relevance_audit.py --days 14 --sample 40000
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from cfb_rankings.ingest.relevance import score_text  # noqa: E402
try:
    from cfb_rankings.ingest.conversation import OFFTOPIC_SUBREDDITS as _BLOCKED
except Exception:  # noqa: BLE001
    _BLOCKED = ()

_DB = str(Path(__file__).resolve().parent.parent / "cfb_rankings.db")


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("db", nargs="?", default=_DB)
    p.add_argument("--days", type=int, default=14)
    p.add_argument("--sample", type=int, default=40000, help="max docs to score")
    p.add_argument("--min-vol", type=int, default=40, help="min docs to flag a subchannel")
    p.add_argument("--floor", type=float, default=25.0, help="football%% below this = noise candidate")
    a = p.parse_args(argv)
    cut = f"datetime('now','-{a.days} day')"
    c = sqlite3.connect(f"file:{Path(a.db).as_posix()}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA busy_timeout=8000")

    rows = c.execute(f"""
        select cd.source_name, coalesce(cd.source_subchannel,'') sub,
               cd.title_text, cd.body_text
          from conversation_documents cd
          join conversation_document_targets t
            on t.conversation_document_id = cd.conversation_document_id
         where t.target_type='team' and cd.collected_at_utc >= {cut}
         limit {a.sample}
    """).fetchall()
    c.close()

    # per (source, sub): [n_total, n_football]
    agg: dict[tuple, list] = {}
    src_agg: dict[str, list] = {}
    for r in rows:
        sig = score_text((r["title_text"] or "") + " " + (r["body_text"] or ""))
        k = (r["source_name"], r["sub"])
        agg.setdefault(k, [0, 0]); agg[k][0] += 1; agg[k][1] += int(sig.is_football)
        s = src_agg.setdefault(r["source_name"], [0, 0]); s[0] += 1; s[1] += int(sig.is_football)

    n = len(rows)
    overall = 100 * sum(v[1] for v in agg.values()) / n if n else 0
    print(f"\nscored {n:,} team-tagged docs (last {a.days}d)")
    print(f"overall football-anchored: {overall:.1f}%  (lower bound on true relevance)\n")

    print("-- football%% by source --")
    for s, (tot, fb) in sorted(src_agg.items(), key=lambda kv: -kv[1][0]):
        print(f"   {s:<22} {100*fb/tot:5.1f}%   ({tot:,} docs)")

    blocked = {b.lower() for b in _BLOCKED}
    cands = [(k, tot, fb) for k, (tot, fb) in agg.items()
             if tot >= a.min_vol and 100*fb/tot < a.floor and k[1].lower() not in blocked]
    cands.sort(key=lambda x: x[1], reverse=True)
    print(f"\n-- NEW NOISE CANDIDATES: subchannels ≥{a.min_vol} docs, <{a.floor:.0f}% football, "
          f"NOT already blocklisted ({len(blocked)} known) --")
    if not cands:
        print("   (none — concentrated city/campus noise is already handled by the blocklist;")
        print("    the diffuse remainder needs a per-doc classifier, not more blocklist entries)")
    for (src, sub), tot, fb in cands[:30]:
        print(f"   [{src}] {sub or '(none)':<24} {100*fb/tot:5.1f}%   ({tot:,} docs)  <- consider blocklisting")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
