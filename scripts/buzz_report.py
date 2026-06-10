"""buzz_report.py — the fun one. "What is the data actually saying right now?"

Read-only snapshot of the fan-intelligence corpus: who fans are talking about,
the mood of each fanbase, the most-discussed players, and what the pipeline just
heard. Pairs with the dry health/coverage reports — this is the payoff view.

    python scripts/buzz_report.py            # last 7 days
    python scripts/buzz_report.py --days 3
"""
from __future__ import annotations

import argparse
import datetime as _dt
import sqlite3
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DB = str(_REPO / "cfb_rankings.db")


def _ro(db):
    c = sqlite3.connect(f"file:{Path(db).as_posix()}?mode=ro", uri=True)
    c.execute("PRAGMA busy_timeout=8000")
    return c


def _col(c, table, candidates):
    cols = {r[1] for r in c.execute(f"PRAGMA table_info({table})").fetchall()}
    return next((x for x in candidates if x in cols), None)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("db", nargs="?", default=_DB)
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--today", default=None)
    a = p.parse_args(argv)
    today = _dt.date.fromisoformat(a.today) if a.today else _dt.date.today()
    cut = (today - _dt.timedelta(days=a.days)).isoformat()
    c = _ro(a.db)
    tlabel = _col(c, "teams", ["slug", "school", "name"]) or "team_id"
    plabel = _col(c, "players", ["full_name", "name", "display_name"]) or "player_id"

    bar = lambda n, mx, w=22: "█" * max(1, round(w * n / mx)) if mx else ""

    print(f"\n{'='*64}\n  CFB INDEX — WHAT'S BUZZING  (last {a.days}d, as of {today})\n{'='*64}")

    # 1. headline volume
    docs = c.execute("select count(*) from conversation_documents where substr(collected_at_utc,1,10) >= ?", (cut,)).fetchone()[0]
    tt = c.execute("""select count(*) from conversation_document_targets cdt
        join conversation_documents cd on cd.conversation_document_id=cdt.conversation_document_id
        where substr(cd.collected_at_utc,1,10) >= ? and cdt.target_type='team'""", (cut,)).fetchone()[0]
    print(f"\n  {docs:,} documents collected · {tt:,} team mentions tagged\n")

    # 2. buzz leaderboard
    print("  🔥 BUZZ LEADERBOARD — most-talked-about fanbases")
    rows = c.execute(f"""select t.{tlabel}, count(*) n
        from conversation_document_targets cdt
        join conversation_documents cd on cd.conversation_document_id=cdt.conversation_document_id
        join teams t on t.team_id=cdt.team_id
        where cdt.target_type='team' and substr(cd.collected_at_utc,1,10) >= ?
        group by cdt.team_id order by n desc limit 10""", (cut,)).fetchall()
    mx = rows[0][1] if rows else 1
    for i, (slug, n) in enumerate(rows, 1):
        print(f"    {i:>2}. {str(slug):<20} {n:>6,}  {bar(n, mx)}")

    # 3. mood — hype vs angst (needs sentiment + a volume floor so it's meaningful)
    mood = c.execute(f"""select t.{tlabel}, count(*) n, avg(cdt.sentiment_score) s
        from conversation_document_targets cdt
        join conversation_documents cd on cd.conversation_document_id=cdt.conversation_document_id
        join teams t on t.team_id=cdt.team_id
        where cdt.target_type='team' and cdt.sentiment_score is not null
          and substr(cd.collected_at_utc,1,10) >= ?
        group by cdt.team_id having n >= 40""", (cut,)).fetchall()
    if mood:
        mood.sort(key=lambda r: r[2], reverse=True)
        print("\n  😀 SUNNIEST fanbases (avg sentiment, ≥40 mentions)")
        for slug, n, s in mood[:5]:
            print(f"     {str(slug):<20} {s:+.3f}   ({n:,} mentions)")
        print("  😤 GRUMPIEST fanbases")
        for slug, n, s in sorted(mood, key=lambda r: r[2])[:5]:
            print(f"     {str(slug):<20} {s:+.3f}   ({n:,} mentions)")

    # 4. most-discussed players
    try:
        pl = c.execute(f"""select p.{plabel}, count(*) n
            from conversation_document_targets cdt
            join conversation_documents cd on cd.conversation_document_id=cdt.conversation_document_id
            join players p on p.player_id=cdt.player_id
            where cdt.target_type='player' and substr(cd.collected_at_utc,1,10) >= ?
            group by cdt.player_id order by n desc limit 10""", (cut,)).fetchall()
        if pl:
            print("\n  🌟 MOST-DISCUSSED PLAYERS")
            mxp = pl[0][1]
            for i, (nm, n) in enumerate(pl, 1):
                print(f"    {i:>2}. {str(nm):<24} {n:>5,}  {bar(n, mxp, 16)}")
    except sqlite3.OperationalError:
        pass

    # 5. offseason mood ring
    emo = c.execute("""select emotion_primary, count(*) n
        from conversation_document_targets cdt
        join conversation_documents cd on cd.conversation_document_id=cdt.conversation_document_id
        where cdt.emotion_primary is not null and cdt.emotion_primary <> ''
          and substr(cd.collected_at_utc,1,10) >= ?
        group by emotion_primary order by n desc limit 6""", (cut,)).fetchall()
    if emo:
        tot = sum(n for _, n in emo)
        print("\n  🎭 OFFSEASON MOOD RING")
        for e, n in emo:
            print(f"     {str(e):<14} {100*n/tot:4.1f}%")

    # 6. the AI is listening
    pod = c.execute("""select source_channel, title_text, length(body_text)
        from conversation_documents where source_name='podcast_transcript'
        order by conversation_document_id desc limit 3""").fetchall()
    if pod:
        print("\n  🎧 THE AI IS LISTENING (fresh podcast transcripts)")
        for ch, title, ln in pod:
            print(f"     [{ch}] {str(title)[:52]}  ({ln:,} chars)")

    # 7. loudest sources
    src = c.execute("""select source_name, count(*) n from conversation_documents
        where substr(collected_at_utc,1,10) >= ? group by source_name order by n desc limit 6""", (cut,)).fetchall()
    if src:
        print("\n  📡 LOUDEST SOURCES")
        for s, n in src:
            print(f"     {str(s):<22} {n:>7,}")
    print()
    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
