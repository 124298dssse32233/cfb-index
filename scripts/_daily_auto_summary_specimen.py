"""Render a Daily edition with the auto-summary block wired in.

Synthetic 3-take edition + monkey-patched generate_article_summary so
the renderer exercises end-to-end without an LLM call. Output:
docs/mockups/daily_auto_summary_specimen.html

Used as visual proof for the Pattern 7 wire-up.
"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> None:
    # Monkey-patch generate_article_summary BEFORE importing the daily
    # renderer so the renderer's lazy import picks up the stub.
    import cfb_rankings.auto_summary as auto_summary

    from cfb_rankings.auto_summary import AutoSummary
    fake = AutoSummary(
        bullets=(
            "Alabama's QB-room re-stack absorbed three transfer arrivals in 72 hours.",
            "Beat-writer reporting and r/CFB film breakdown converged on faster OL drill cadence.",
            "Market hasn't priced the spring news — the cleanest unbet edge of May.",
        ),
        body_hash="specimen0123456",
    )
    original = auto_summary.generate_article_summary
    auto_summary.generate_article_summary = lambda **kw: fake

    from cfb_rankings.daily.renderer import render_daily

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_db = Path(tmpdir) / "daily.db"
        conn = sqlite3.connect(str(tmp_db))
        conn.row_factory = sqlite3.Row
        conn.execute("""
            CREATE TABLE daily_takes (
                edition_date TEXT, rank_position INTEGER, headline TEXT,
                body TEXT, cited_sources_json TEXT,
                primary_entity_slug TEXT, primary_entity_type TEXT,
                generation_model TEXT
            )
        """)
        takes = [
            (1, "Alabama spring tilts toward Underwood",
             "Bryce Underwood's comp tape leaked to 247Sports overnight and three "
             "transfers committed by sundown. The pattern under DeBoer is unmistakable: "
             "the QB room re-stacks itself the instant a real comp tape lands. The "
             "interesting question is whether anything in this picture is actually "
             "new — Tide QB recruiting has worked this way since at least 2022."),
            (2, "OL drill cadence is the real spring story",
             "Andy Staples on Locked On caught it first; r/CFB film threads "
             "corroborated within 24 hours. Alabama's offensive line is running spring "
             "drills at a cadence visibly faster than any year under Saban. Whether "
             "that translates to in-game tempo is open, but the markets haven't moved "
             "yet — which Stewart Mandel flagged as the cleanest unbet edge of spring."),
            (3, "Recruiting still #3 despite churn",
             "CFBD's class composite still has Alabama at #3 in the country, only a "
             "tenth of a point behind Georgia. The Tide finished 2025 at 13-1 with the "
             "SEC title and a CFP semifinal loss — a year that, by their standards, "
             "gets called a 'rebuilding year.' Nobody else's program operates with "
             "that calibration."),
        ]
        conn.executemany(
            "INSERT INTO daily_takes (edition_date, rank_position, headline, body, "
            "cited_sources_json, primary_entity_slug, primary_entity_type, "
            "generation_model) VALUES ('2026-05-17', ?, ?, ?, '[]', "
            "'alabama', 'team', 'specimen')",
            takes,
        )
        conn.execute("""
            CREATE TABLE daily_editions (
                edition_date TEXT PRIMARY KEY,
                status TEXT
            )
        """)
        conn.execute(
            "INSERT INTO daily_editions (edition_date, status) "
            "VALUES ('2026-05-17', 'published')"
        )
        conn.commit()

        output_dir = Path(tmpdir) / "site"
        paths = render_daily(conn, "2026-05-17", output_dir=str(output_dir))
        # The /daily/index.html is the current-edition write; we want that.
        current = output_dir / "index.html"
        if not current.exists():
            current = paths[-1]
        text = current.read_text(encoding="utf-8")
        conn.close()

        out_path = ROOT / "docs" / "mockups" / "daily_auto_summary_specimen.html"
        out_path.write_text(text, encoding="utf-8")
        print(f"wrote {out_path.relative_to(ROOT)} ({len(text):,} chars)")
        print(f"  auto-summary block present: {'auto-summary' in text}")
        print(f"  auto-summary bullets: {text.count('<li>')}")

    auto_summary.generate_article_summary = original


if __name__ == "__main__":
    main()
