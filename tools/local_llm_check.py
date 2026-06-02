"""Smoke check for the local-LLM Tier-A path — "does my local setup actually work?"

NOT an A/B test and NOT a quality gate. It exercises the exact production path
(``local_llm.generate_local`` with the sentiment classifier's real prompt) on a
small sample of real rows and reports whether the local model is reachable,
producing parseable labels, and fast enough. Use it once after installing
Ollama to confirm the plumbing is healthy, then turn routing on and forget it.

Read-only — writes NOTHING to the database.

Run on the new box once Ollama is up:

    ollama pull qwen3:8b
    python tools/local_llm_check.py --sample 60 --local-model qwen3:8b

Needs the local server reachable (default http://localhost:11434/v1; override
with --base-url or CFB_LOCAL_LLM_BASE_URL). Does NOT need ANTHROPIC_API_KEY.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
for _p in (_REPO / "src", _REPO / ".vendor", _REPO / ".deps"):
    if _p.exists() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from cfb_rankings import local_llm  # noqa: E402
from cfb_rankings.team_pages.sentiment_classifier import (  # noqa: E402
    _SYSTEM_PROMPT,
    _build_batch_prompt,
    _parse_labels,
)

_VALID = ("positive", "neutral", "negative")


def _fetch_sample(db_path: str, sample: int) -> list[str]:
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        cur = con.cursor()
        cur.execute(
            """
            SELECT cd.body_text
            FROM conversation_document_targets cdt
            JOIN conversation_documents cd
                ON cd.conversation_document_id = cdt.conversation_document_id
            WHERE cdt.player_id IS NOT NULL
              AND cd.body_text IS NOT NULL
              AND cd.body_text != ''
            ORDER BY cdt.conversation_document_target_id
            LIMIT ?
            """,
            (int(sample),),
        )
        return [r[0] for r in cur.fetchall()]
    finally:
        con.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample", type=int, default=60, help="rows to classify (default 60)")
    ap.add_argument("--batch-size", type=int, default=30, help="docs per call (default 30)")
    ap.add_argument("--local-model", default=os.environ.get("CFB_LOCAL_LLM_MODEL", "qwen3:8b"))
    ap.add_argument("--base-url", default=os.environ.get("CFB_LOCAL_LLM_BASE_URL", "http://localhost:11434/v1"))
    ap.add_argument("--db", default=str(_REPO / "cfb_rankings.db"))
    args = ap.parse_args()

    os.environ["CFB_LOCAL_LLM_BASE_URL"] = args.base_url

    # --- preflight -------------------------------------------------------
    health = local_llm.health_check()
    if not health["ok"]:
        print(f"FAIL: local server not reachable at {health['base_url']}\n"
              f"      {health['error']}\n"
              f"      Is Ollama running? Try:  ollama serve   "
              f"(and  ollama pull {args.local_model})", file=sys.stderr)
        return 2
    models = health["models"] or []
    print(f"OK   server up at {health['base_url']}  ({len(models)} model(s) loaded)")
    if models and args.local_model not in models:
        print(f"WARN '{args.local_model}' not in {models} — pull it:  ollama pull {args.local_model}")

    if not Path(args.db).exists():
        print(f"FAIL: database not found at {args.db} (pass --db)", file=sys.stderr)
        return 2
    texts = _fetch_sample(args.db, args.sample)
    if not texts:
        print("FAIL: no player-target documents with body_text found to sample.", file=sys.stderr)
        return 2

    print(f"     classifying {len(texts)} real docs with local={args.local_model} "
          f"(temp 0, /no_think, <think> stripped)\n")

    # --- run (exactly the production local path) -------------------------
    labels: list[str | None] = []
    secs = 0.0
    bs = args.batch_size
    n_batches = -(-len(texts) // bs)
    for bi, start in enumerate(range(0, len(texts), bs), 1):
        batch = texts[start : start + bs]
        prompt = _build_batch_prompt(batch)
        t0 = time.time()
        result = local_llm.generate_local(
            prompt, system=_SYSTEM_PROMPT, model=args.local_model,
            max_tokens=256, max_retries=0, fallback_to_offline=True,
        )
        dt = time.time() - t0
        secs += dt
        if result.get("mode") == "offline-stub" or not result.get("text"):
            labels.extend([None] * len(batch))
            print(f"  batch {bi}/{n_batches}  {dt:5.1f}s  (no output — server issue?)")
            continue
        labels.extend(_parse_labels(result["text"], len(batch)))
        print(f"  batch {bi}/{n_batches}  {dt:5.1f}s")

    # --- score -----------------------------------------------------------
    valid = sum(1 for l in labels if l in _VALID)
    dist = Counter(l for l in labels if l in _VALID)
    parse_rate = 100 * valid / len(labels) if labels else 0.0

    print("\n" + "=" * 56)
    print("SMOKE CHECK RESULTS")
    print("=" * 56)
    print(f"  docs classified ......... {len(labels)}")
    print(f"  parseable labels ........ {valid}/{len(labels)}  ({parse_rate:.0f}%)")
    print(f"  label distribution ...... "
          + ", ".join(f"{k}={dist.get(k, 0)}" for k in _VALID))
    print(f"  avg latency ............. {secs/n_batches:.1f}s per {bs}-doc batch")

    print("\n  VERDICT:")
    only_one = len([k for k in _VALID if dist.get(k, 0) > 0]) <= 1
    if parse_rate >= 95 and not only_one:
        print("    ✅ Local Tier-A path is healthy — safe to enable (CFB_LOCAL_LLM=1).")
        rc = 0
    elif parse_rate >= 95 and only_one:
        print("    🔶 Parses fine but every doc got the same label — eyeball a few outputs;\n"
              "       the sample may genuinely be one-sided, or the model is collapsing.")
        rc = 0
    elif parse_rate >= 80:
        print(f"    🔶 {parse_rate:.0f}% parseable — usable (the classifier skips bad rows),\n"
              "       but try qwen3:14b or a lower temperature for cleaner output.")
        rc = 0
    else:
        print(f"    ❌ Only {parse_rate:.0f}% parseable — something's off. Check the model tag,\n"
              "       try a different model, or inspect a raw response.")
        rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
