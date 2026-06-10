"""Product-impact check: recompute the offseason mood index from the NEW encoder
labels (staging) and diff it against the VADER-based labels, per team-week.

Apples-to-apples: BOTH sides use the same net-label method
   net_sentiment = (n_positive - n_negative) / n_total
   mood = clamp(50 + 50*net*min(1, mentions/50), 0, 100)
so the DELTA isolates the classifier change (it won't exactly equal the stored
mood_score, which uses VADER's continuous scores — noted in output).

READ-ONLY. Run with EITHER env (only needs sqlite3):
  .venv\\Scripts\\python.exe scripts\\sentiment_mood_impact.py
Writes logs/sentiment_mood_impact.md
"""
import os
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "cfb_rankings.db")
OUT = os.path.join(ROOT, "logs", "sentiment_mood_impact.md")
MIN_MENTIONS = 12  # matches MIN_MENTIONS_FOR_SIGNAL


def mood(net, n):
    v = 50 + 50 * net * min(1.0, n / 50.0)
    return max(0, min(100, round(v)))


def main():
    db = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    db.execute("pragma busy_timeout=5000")

    staged = db.execute("select count(*) from sentiment_v2_staging").fetchone()[0]
    print(f"[impact] staging rows available: {staged}")

    # offseason weeks only (these map to the published mood product)
    rows = db.execute(
        """
        select tm.slug, m.week_start_date, t.season_year, t.week,
               t.sentiment_label as vader,
               s.pol_label       as enc
        from conversation_document_targets t
        join conversation_documents d on d.conversation_document_id = t.conversation_document_id
        join teams tm on tm.team_id = t.team_id
        join offseason_week_map m on m.season_year = t.season_year and m.offseason_week = t.week
        left join sentiment_v2_staging s on s.conversation_document_id = t.conversation_document_id
        where t.target_type='team' and t.sentiment_label is not null
        """
    ).fetchall()

    # aggregate per (slug, week_start_date)
    agg = {}
    for slug, wk, sy, w, vader, enc in rows:
        key = (slug, wk)
        a = agg.setdefault(key, {"vp": 0, "vn": 0, "vt": 0, "ep": 0, "en": 0, "et": 0, "missing": 0})
        a["vt"] += 1
        if vader == "positive": a["vp"] += 1
        elif vader == "negative": a["vn"] += 1
        if enc is None:
            a["missing"] += 1
        else:
            a["et"] += 1
            if enc == "positive": a["ep"] += 1
            elif enc == "negative": a["en"] += 1

    lines = []
    lines.append("# Mood-index impact — VADER vs encoder stack (offseason weeks)\n")
    lines.append(f"- Staging rows available: **{staged}**")
    lines.append(f"- Method: net=(pos-neg)/total, mood=50+50*net*min(1,n/50). Both sides identical method; delta isolates the classifier.\n")
    lines.append("| team | week | mentions | mood (VADER) | mood (encoder) | Δ |")
    lines.append("|---|---|--:|--:|--:|--:|")

    big = []
    for (slug, wk), a in sorted(agg.items()):
        if a["vt"] < MIN_MENTIONS:
            continue
        net_v = (a["vp"] - a["vn"]) / a["vt"] if a["vt"] else 0
        mv = mood(net_v, a["vt"])
        if a["et"] >= MIN_MENTIONS:
            net_e = (a["ep"] - a["en"]) / a["et"]
            me = mood(net_e, a["et"])
            delta = me - mv
        else:
            me, delta = "n/a", None
        flag = ""
        if isinstance(delta, int) and abs(delta) >= 5:
            flag = " **"
            big.append((slug, wk, mv, me, delta))
        lines.append(f"| {slug} | {wk} | {a['vt']} | {mv} | {me} | {delta if delta is not None else 'n/a'}{flag} |")

    lines.append(f"\n## Teams/weeks whose mood shifts >=5 points: {len(big)}")
    for slug, wk, mv, me, d in sorted(big, key=lambda x: -abs(x[4])):
        lines.append(f"- **{slug} {wk}**: {mv} -> {me}  (delta {d:+d})")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[impact] wrote {OUT}")
    print(f"[impact] team-weeks compared: {sum(1 for a in agg.values() if a['vt']>=MIN_MENTIONS)}; shifts>=5pts: {len(big)}")

    db.close()


if __name__ == "__main__":
    main()
