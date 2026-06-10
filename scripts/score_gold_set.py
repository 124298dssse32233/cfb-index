"""Score VADER vs the encoder stack against your hand labels.

Reads logs/gold_set_to_label.csv (after you fill 'your_label'),
logs/gold_set_key.csv (vader), and sentiment_v2_staging (encoder).
Prints accuracy for each + per-class breakdown. READ-ONLY.

Run: .venv\\Scripts\\python.exe scripts\\score_gold_set.py
"""
import csv
import os
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "cfb_rankings.db")
LOGS = os.path.join(ROOT, "logs")
LABELS = ("positive", "neutral", "negative")


def main():
    label_path = os.path.join(LOGS, "gold_set_to_label.csv")
    key_path = os.path.join(LOGS, "gold_set_key.csv")
    if not os.path.exists(label_path):
        print("No gold_set_to_label.csv — run build_gold_set.py first."); return

    gold = {}
    with open(label_path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            lbl = (row.get("your_label") or "").strip().lower()
            if lbl in LABELS:
                gold[int(row["id"])] = lbl
    if not gold:
        print("No labels filled in yet. Put positive/neutral/negative in the 'your_label' column.")
        return

    vader = {}
    with open(key_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            vader[int(row["id"])] = (row.get("vader_label") or "").strip().lower()

    db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    enc = {}
    qmarks = ",".join("?" * len(gold))
    for did, pol in db.execute(
            f"select conversation_document_id, pol_label from sentiment_v2_staging where conversation_document_id in ({qmarks})",
            tuple(gold)).fetchall():
        enc[did] = (pol or "").strip().lower()
    db.close()

    n = len(gold)
    v_correct = sum(1 for i, g in gold.items() if vader.get(i) == g)
    e_have = [i for i in gold if i in enc]
    e_correct = sum(1 for i in e_have if enc[i] == gold[i])

    print(f"=== Gold-set scoring ({n} hand-labeled comments) ===")
    print(f"VADER   accuracy: {100*v_correct/n:5.1f}%  ({v_correct}/{n})")
    if e_have:
        print(f"Encoder accuracy: {100*e_correct/len(e_have):5.1f}%  ({e_correct}/{len(e_have)})"
              + ("" if len(e_have) == n else f"   [{n-len(e_have)} not yet in staging]"))
    else:
        print("Encoder: no staging rows for these ids yet — wait for staging classify to finish.")

    # per-class recall
    print("\nper-class (gold label -> correct / total):")
    for lbl in LABELS:
        ids = [i for i, g in gold.items() if g == lbl]
        if not ids:
            continue
        vc = sum(1 for i in ids if vader.get(i) == lbl)
        ec = sum(1 for i in ids if enc.get(i) == lbl)
        print(f"  {lbl:9s} n={len(ids):3d}  VADER {vc:3d}  encoder {ec:3d}")


if __name__ == "__main__":
    main()
