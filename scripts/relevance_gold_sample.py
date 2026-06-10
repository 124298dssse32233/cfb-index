"""Build the RELEVANCE gold-set sample (Stage-2 classifier, task #6 successor).

Stratified, READ-ONLY sample of recent conversation docs across source pillars
for binary labeling: is this post about college football (the sport, its teams,
players, coaches, recruiting, games) or not? Oversamples minority pillars so
the classifier generalises beyond Reddit.

Writes logs/relevance_gold_sample.csv with doc_id, source pillar, subchannel
and cleaned text. The lexical anchor score (Stage-1 signal) goes to a separate
key file so labeling stays blind, mirroring the sentiment gold-set pattern.

Run: .venv\\Scripts\\python.exe scripts\\relevance_gold_sample.py [N]
"""
from __future__ import annotations

import csv
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from cfb_rankings.ingest.relevance import score_text  # noqa: E402

DB = ROOT / "cfb_rankings.db"
LOGS = ROOT / "logs"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 700

# pillar -> (source_name LIKE pattern, share of N). Minority pillars are
# oversampled vs corpus share on purpose.
STRATA = [
    ("reddit",  "reddit",           0.40),
    ("bluesky", "bluesky%",         0.20),
    ("youtube", "youtube%",         0.15),
    ("podcast", "locked_on_%",      0.10),
    ("other",   None,               0.15),  # everything not matched above
]


def _clean(t: str | None) -> str:
    if not t:
        return ""
    t = re.sub(r"http\S+", "<url>", t)
    return re.sub(r"\s+", " ", t).strip()


def main() -> None:
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    LOGS.mkdir(exist_ok=True)

    rows_out: list[dict] = []
    for pillar, pattern, share in STRATA:
        want = max(1, int(N * share))
        if pattern is None:
            where = ("source_name NOT LIKE 'reddit' AND source_name NOT LIKE 'bluesky%' "
                     "AND source_name NOT LIKE 'youtube%' AND source_name NOT LIKE 'locked_on_%'")
            params: tuple = ()
        else:
            where = "source_name LIKE ?"
            params = (pattern,)
        # ORDER BY the dedup-ish random of the id hash keeps the sample stable
        # across reruns (no Date/random dependency, diff-friendly).
        q = f"""
            SELECT conversation_document_id AS doc_id, source_name,
                   COALESCE(source_subchannel, source_channel, '') AS subchannel,
                   title_text, body_text
              FROM conversation_documents
             WHERE {where}
               AND body_text IS NOT NULL AND LENGTH(body_text) >= 20
               AND COALESCE(is_deleted, 0) = 0 AND COALESCE(is_removed, 0) = 0
             ORDER BY (conversation_document_id * 2654435761) % 4294967296
             LIMIT ?
        """
        got = con.execute(q, (*params, want)).fetchall()
        for r in got:
            text = _clean(f"{r['title_text'] or ''} {r['body_text'] or ''}")[:600]
            rows_out.append({
                "doc_id": r["doc_id"],
                "pillar": pillar,
                "source_name": r["source_name"],
                "subchannel": r["subchannel"],
                "text": text,
            })
        print(f"  {pillar:8s} wanted={want:4d} got={len(got):4d}")

    sample_path = LOGS / "relevance_gold_sample.csv"
    with sample_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["doc_id", "pillar", "source_name",
                                           "subchannel", "text", "label"])
        w.writeheader()
        for r in rows_out:
            w.writerow({**r, "label": ""})

    key_path = LOGS / "relevance_gold_key.csv"
    with key_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["doc_id", "lexical_score"])
        for r in rows_out:
            w.writerow([r["doc_id"], score_text(r["text"]) or 0])

    print(f"wrote {len(rows_out)} rows -> {sample_path}")
    print(f"key (lexical scores) -> {key_path}")


if __name__ == "__main__":
    main()
