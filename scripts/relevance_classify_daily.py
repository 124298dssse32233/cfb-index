"""Daily ML relevance scoring (Stage 2, report-only rollout).

Scores conversation docs with the SetFit+ModernBERT relevance classifier
(models/relevance_setfit_v1, trained 2026-06-10 on 700 hand labels) and writes
``relevance_ml_score`` (P(college-football-relevant), 0..1) + model version to
``conversation_documents``. Incremental: only docs not yet scored. Bounded per
run. NOTHING gates on these scores yet — this is the soak phase, mirroring the
encoder-sentiment rollout (staging first, gate later after validation).

Run nightly from build_publish.ps1 via the .venv-cls python:
    .venv-cls\\Scripts\\python.exe scripts\\relevance_classify_daily.py --commit
Without --commit it scores a sample and prints the distribution only.
"""
from __future__ import annotations

import argparse
import re
import sqlite3
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "cfb_rankings.db"
MODEL_DIR = ROOT / "models" / "relevance_setfit_v1"
MODEL_VERSION = "setfit-modernbert-v1-20260610"
BATCH = 256


def _clean(t: str) -> str:
    t = re.sub(r"http\S+", "<url>", t or "")
    return re.sub(r"\s+", " ", t).strip()[:600]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true", help="write scores to the DB")
    ap.add_argument("--max-docs", type=int, default=25000, help="cap per run")
    args = ap.parse_args()

    con = sqlite3.connect(DB, timeout=300)
    cols = {r[1] for r in con.execute("pragma table_info(conversation_documents)")}
    if "relevance_ml_score" not in cols:
        if not args.commit:
            print("columns missing (added on first --commit run)")
        else:
            con.execute("alter table conversation_documents add column relevance_ml_score real")
            con.execute("alter table conversation_documents add column relevance_ml_version text")
            con.commit()

    where = ("body_text is not null and length(body_text) >= 20 "
             "and coalesce(is_deleted,0)=0 and coalesce(is_removed,0)=0")
    if "relevance_ml_score" in cols or args.commit:
        where += " and relevance_ml_score is null"
    rows = con.execute(
        f"select conversation_document_id, coalesce(title_text,'') || ' ' || body_text"
        f"  from conversation_documents where {where} limit ?",
        (args.max_docs,),
    ).fetchall()
    if not rows:
        print("relevance-daily: nothing to score")
        return
    print(f"relevance-daily: scoring {len(rows)} docs (commit={args.commit})")

    from setfit import SetFitModel
    model = SetFitModel.from_pretrained(str(MODEL_DIR))

    t0 = time.time()
    scored: list[tuple[float, str, int]] = []
    for i in range(0, len(rows), BATCH):
        chunk = rows[i:i + BATCH]
        texts = [_clean(t) for _, t in chunk]
        probs = model.predict_proba(texts)
        for (doc_id, _), p in zip(chunk, probs):
            scored.append((float(p[1]), MODEL_VERSION, int(doc_id)))
    dt = time.time() - t0

    n_rel = sum(1 for s, _, _ in scored if s >= 0.5)
    print(f"relevance-daily: {len(scored)} scored in {dt:.0f}s "
          f"({len(scored)/max(dt,1):.0f}/s) — {n_rel} ({100*n_rel/len(scored):.0f}%) >= 0.5")

    if args.commit:
        con.executemany(
            "update conversation_documents set relevance_ml_score=?, relevance_ml_version=? "
            "where conversation_document_id=?",
            scored,
        )
        con.commit()
        print("relevance-daily: committed")


if __name__ == "__main__":
    main()
