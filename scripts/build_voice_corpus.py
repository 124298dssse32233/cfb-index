"""Build the voice training corpus from project sources.

Run: python scripts/build_voice_corpus.py [--out PATH] [--sources profile,edition,...]
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from cfb_rankings.chronicle.lora_corpus import build_corpus
from cfb_rankings.db import Database


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=Path("data/voice_corpus.jsonl"))
    p.add_argument(
        "--sources",
        default="profile,edition,mailbag,citation,design_doc",
        help="Comma-separated source kinds",
    )
    p.add_argument("--min-words", type=int, default=50)
    p.add_argument("--max-words", type=int, default=2000)
    p.add_argument("--quality-threshold", type=float, default=0.6)
    p.add_argument("--db-path", type=Path, default=Path("cfb_rankings.db"))
    p.add_argument("--profiles-dir", type=Path, default=Path("profiles"))
    p.add_argument("--design-docs-dir", type=Path, default=Path("docs/design-system"))
    p.add_argument("--editions-since", default="2025-01-01")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    db = Database(str(args.db_path)) if args.db_path.exists() else None
    if db is None:
        logging.warning("DB not found at %s — DB-backed sources will be skipped.", args.db_path)

    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    stats = build_corpus(
        out_path=args.out,
        sources=sources,
        min_words=args.min_words,
        max_words=args.max_words,
        quality_threshold=args.quality_threshold,
        db=db,
        profiles_dir=args.profiles_dir,
        design_docs_dir=args.design_docs_dir,
        editions_since=args.editions_since,
    )
    print(f"\nCorpus built: {args.out}")
    print(f"Passages: {stats.total_passages}")
    print(f"Total words: {stats.total_words}")
    print(f"Est. tokens: {stats.total_tokens_estimate}")
    print(f"By source: {stats.by_source}")
    print(f"Median words: {stats.median_words:.0f}")
    print(f"p25 / p75 words: {stats.p25_words:.0f} / {stats.p75_words:.0f}")
    print(f"Mean quality score: {stats.quality_score_mean:.2f}")


if __name__ == "__main__":
    main()
