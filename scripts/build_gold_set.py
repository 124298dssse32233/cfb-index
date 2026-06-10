"""Build a CFB-specific gold-set labeling file (the rigor step the research said
is non-optional before any production swap).

Produces a BLIND labeling sheet (no model guesses shown, to avoid biasing you)
plus a separate key file. After you label, scripts/score_gold_set.py will join
your labels with VADER and the encoder (from sentiment_v2_staging) and print
accuracy for each.

READ-ONLY on the DB. Run: .venv\\Scripts\\python.exe scripts\\build_gold_set.py [N]
Writes logs/gold_set_to_label.csv  (you fill the 'your_label' column)
       logs/gold_set_key.csv        (doc ids + vader label; keep separate)
"""
import csv
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "cfb_rankings.db")
LOGS = os.path.join(ROOT, "logs")
N = int(sys.argv[1]) if len(sys.argv) > 1 else 150
TEAMS = ("michigan", "oregon", "florida-state", "penn-state", "ohio-state", "texas")


def clean(t):
    if not t:
        return ""
    t = re.sub(r"http\S+", "http", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def main():
    db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    per_label = max(1, N // 3)
    picked = []
    for lbl in ("positive", "neutral", "negative"):
        # spread across teams; sample deterministically (every k-th) for a spread
        rows = db.execute(
            """
            select d.conversation_document_id, tm.slug,
                   coalesce(nullif(d.body_text,''), d.title_text) as txt,
                   t.sentiment_label
            from conversation_document_targets t
            join conversation_documents d on d.conversation_document_id = t.conversation_document_id
            join teams tm on tm.team_id = t.team_id
            where t.target_type='team' and t.sentiment_label = ?
              and tm.slug in (%s)
              and coalesce(d.body_text,'') not in ('[removed]','[deleted]')
              and length(coalesce(nullif(d.body_text,''), d.title_text)) between 25 and 600
            order by d.conversation_document_id
            """ % ",".join("?" * len(TEAMS)),
            (lbl, *TEAMS)).fetchall()
        # even spread across the result set
        if rows:
            step = max(1, len(rows) // per_label)
            picked.extend(rows[::step][:per_label])
    db.close()

    # de-dup by doc id, keep order
    seen = set()
    final = []
    for did, slug, txt, vader in picked:
        if did in seen:
            continue
        seen.add(did)
        c = clean(txt)
        if c:
            final.append((did, slug, c, vader))

    os.makedirs(LOGS, exist_ok=True)
    label_path = os.path.join(LOGS, "gold_set_to_label.csv")
    key_path = os.path.join(LOGS, "gold_set_key.csv")
    with open(label_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["id", "team", "comment", "your_label"])  # your_label: positive / neutral / negative
        for did, slug, c, vader in final:
            w.writerow([did, slug, c, ""])
    with open(key_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "vader_label"])
        for did, slug, c, vader in final:
            w.writerow([did, vader])

    print(f"[gold] wrote {len(final)} comments to label -> {label_path}")
    print(f"[gold] key (vader labels) -> {key_path}")
    print("[gold] Fill the 'your_label' column (positive/neutral/negative), then run score_gold_set.py")


if __name__ == "__main__":
    main()
