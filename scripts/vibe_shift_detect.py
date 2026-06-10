"""Vibe-shift detection prototype (net-new feature from the June-2026 research).

Per the research recipe: run change-point detection on a team's MULTI-emotion
"collective affect" series (not a single polarity score). Uses `ruptures` (free,
CPU-only) Pelt with an RBF kernel over a standardized multivariate signal:
   [net_sentiment, joy, anger, fear, trust, sadness, surprise]

READ-ONLY. Run: .venv-ml\\Scripts\\python.exe scripts\\vibe_shift_detect.py [pen]
Writes logs/vibe_shifts.md
"""
import os
import sqlite3
import sys

import numpy as np
import ruptures as rpt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "cfb_rankings.db")
OUT = os.path.join(ROOT, "logs", "vibe_shifts.md")
PEN = float(sys.argv[1]) if len(sys.argv) > 1 else 12.0
MIN_MENTIONS = 5      # drop noisy low-volume days
MIN_POINTS = 50       # need enough history to detect shifts
MIN_SIZE = 7          # >=1 week between detected shifts
EMO = ["joy_share", "anger_share", "fear_share", "trust_share", "sadness_share", "surprise_share"]


def series_for(db, team_id):
    rows = db.execute(
        """
        select as_of_date, mention_count, net_sentiment_score,
               joy_share, anger_share, fear_share, trust_share, sadness_share, surprise_share
        from team_conversation_daily
        where team_id = ? and mention_count >= ?
        order by as_of_date
        """, (team_id, MIN_MENTIONS)).fetchall()
    return rows


def main():
    db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    teams = db.execute(
        """select tm.team_id, tm.slug, count(*) n
           from team_conversation_daily d join teams tm on tm.team_id=d.team_id
           where d.mention_count >= ?
           group by d.team_id having n >= ? order by n desc""",
        (MIN_MENTIONS, MIN_POINTS)).fetchall()

    lines = ["# Vibe-shift detection prototype (ruptures, multivariate affect)\n",
             f"- Signal: [net_sentiment, joy, anger, fear, trust, sadness, surprise], z-scored",
             f"- Method: ruptures KernelCPD(kernel=rbf), adaptive top-K (~1/90d, 2..5), min_size={MIN_SIZE} days",
             f"- Teams with >= {MIN_POINTS} usable days (mentions>= {MIN_MENTIONS})\n"]

    total_shifts = 0
    for team_id, slug, n in teams:
        rows = series_for(db, team_id)
        if len(rows) < MIN_POINTS:
            continue
        dates = [r[0] for r in rows]
        net = np.array([float(r[2] or 0) for r in rows])
        emo = np.array([[float(x or 0) for x in r[3:9]] for r in rows])
        sig = np.column_stack([net, emo])
        # z-score each column (guard zero-variance)
        mu = sig.mean(axis=0); sd = sig.std(axis=0); sd[sd == 0] = 1.0
        sigz = (sig - mu) / sd

        # Adaptive top-K candidate shifts (~1 per 90 days, 2..5). KernelCPD(rbf)
        # avoids penalty calibration; production would add CUSUM/BOCPD confidence.
        n_bkps = max(2, min(5, len(rows) // 90))
        algo = rpt.KernelCPD(kernel="rbf", min_size=MIN_SIZE).fit(sigz)
        bkps = [b for b in algo.predict(n_bkps=n_bkps) if 0 < b < len(rows)]

        lines.append(f"## {slug}  ({len(rows)} days, {dates[0]}..{dates[-1]})  - {len(bkps)} candidate shift(s)")
        if not bkps:
            lines.append("  (no significant vibe shift detected)\n")
            continue
        prev = 0
        seg_means = []
        for b in bkps + [len(rows)]:
            seg_means.append(net[prev:b].mean() if b > prev else 0.0)
            prev = b
        for i, b in enumerate(bkps):
            d = dates[b]
            before = seg_means[i]
            after = seg_means[i + 1]
            arrow = "UP" if after > before else "DOWN"
            # dominant emotion change around the break
            win = 7
            pre_emo = emo[max(0, b - win):b].mean(axis=0)
            post_emo = emo[b:b + win].mean(axis=0)
            demo = EMO[int(np.argmax(post_emo - pre_emo))].replace("_share", "")
            lines.append(f"  - **{d}**: net sentiment {before:+.2f} -> {after:+.2f}  ({arrow}), rising emotion: {demo}")
            total_shifts += 1
        lines.append("")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[vibe] teams analyzed: {len(teams)}; total shifts detected: {total_shifts}")
    print(f"[vibe] wrote {OUT}")
    db.close()


if __name__ == "__main__":
    main()
