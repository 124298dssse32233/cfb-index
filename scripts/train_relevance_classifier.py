"""Train + evaluate the Stage-2 relevance classifier (task #6 successor).

SetFit on a ModernBERT sentence-transformer (the officially supported combo
per SetFit v1.1.1; June-2026 research: ModernBERT is still the strongest
English classification encoder). Binary: is this post about college football?

Data: logs/relevance_gold_sample.csv (700 stratified docs across pillars)
joined with logs/relevance_gold_labels.csv (hand labels, 2026-06-10).
Split: 75/25 stratified by (pillar, label), fixed seed. Reports accuracy /
precision / recall / F1 vs the Stage-1 lexical-anchor baseline on the SAME
eval slice. Saves the model to models/relevance_setfit_v1/.

Run: .venv-cls\\Scripts\\python.exe scripts\\train_relevance_classifier.py
"""
from __future__ import annotations

import csv
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "logs"
MODEL_OUT = ROOT / "models" / "relevance_setfit_v1"
BASE_MODEL = "nomic-ai/modernbert-embed-base"
SEED = 42


def load_data() -> list[dict]:
    labels: dict[int, int] = {}
    with (LOGS / "relevance_gold_labels.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            labels[int(r["doc_id"])] = int(r["label"])

    # Kevin's dashboard labels (scripts/relevance_label_server.py -> labels.db)
    # extend the set; on shared docs the HUMAN label wins. Agreement reported.
    labels_db = ROOT / "labels.db"
    if labels_db.exists():
        import sqlite3
        con = sqlite3.connect(labels_db)
        try:
            kevin = dict(con.execute(
                "select doc_id, label from relevance_labels where label in (0,1)"))
        except sqlite3.OperationalError:
            kevin = {}
        con.close()
        if kevin:
            shared = [d for d in kevin if d in labels]
            agree = sum(1 for d in shared if kevin[d] == labels[d])
            print(f"kevin labels: {len(kevin)} ({len(shared)} shared with claude, "
                  f"agreement {agree}/{len(shared)})")
            new_docs = [d for d in kevin if d not in labels]
            labels.update({int(k): int(v) for k, v in kevin.items()})
            if new_docs:
                _append_texts_for(new_docs)

    rows: list[dict] = []
    with (LOGS / "relevance_gold_sample.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            did = int(r["doc_id"])
            if did in labels and r["text"].strip():
                rows.append({"doc_id": did, "pillar": r["pillar"],
                             "text": r["text"], "label": labels[did]})
    return rows


def _append_texts_for(doc_ids: list[int]) -> None:
    """Pull text for dashboard-labeled docs not yet in the sample CSV."""
    import re
    import sqlite3
    sample = LOGS / "relevance_gold_sample.csv"
    have: set[int] = set()
    with sample.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            have.add(int(r["doc_id"]))
    missing = [d for d in doc_ids if d not in have]
    if not missing:
        return
    con = sqlite3.connect(f"file:{ROOT / 'cfb_rankings.db'}?mode=ro", uri=True)
    q = ",".join("?" * len(missing))
    rows = con.execute(
        f"""select conversation_document_id, source_name,
                   coalesce(source_subchannel, source_channel, ''),
                   coalesce(title_text,'') || ' ' || coalesce(body_text,'')
              from conversation_documents
             where conversation_document_id in ({q})""", missing).fetchall()
    con.close()
    pillar_of = (("reddit", "reddit"), ("bluesky", "bluesky"),
                 ("youtube", "youtube"), ("locked_on_", "podcast"))
    with sample.open("a", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        for did, src, sub, txt in rows:
            pillar = next((p for prefix, p in pillar_of if src.startswith(prefix)), "other")
            clean = re.sub(r"\s+", " ", re.sub(r"http\S+", "<url>", txt or "")).strip()[:600]
            w.writerow([did, pillar, src, sub, clean, ""])
    print(f"appended {len(rows)} dashboard-labeled doc texts to the sample CSV")


def stratified_split(rows: list[dict], eval_frac: float = 0.25):
    by_stratum: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        by_stratum[(r["pillar"], r["label"])].append(r)
    rng = random.Random(SEED)
    train, ev = [], []
    for stratum in sorted(by_stratum):
        bucket = by_stratum[stratum]
        rng.shuffle(bucket)
        k = max(1, round(len(bucket) * eval_frac))
        ev.extend(bucket[:k])
        train.extend(bucket[k:])
    rng.shuffle(train)
    return train, ev


def metrics(y_true: list[int], y_pred: list[int]) -> dict:
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    acc = (tp + tn) / len(y_true)
    return {"accuracy": acc, "precision": prec, "recall": rec, "f1": f1,
            "tp": tp, "fp": fp, "fn": fn, "tn": tn}


def main() -> None:
    rows = load_data()
    train_rows, eval_rows = stratified_split(rows)
    print(f"data: {len(rows)} total -> train {len(train_rows)} / eval {len(eval_rows)}")
    print(f"train balance: {sum(r['label'] for r in train_rows)}/{len(train_rows)} relevant")

    # Stage-1 lexical baseline on the eval slice (anchor score > 0 = relevant).
    lex: dict[int, float] = {}
    key_path = LOGS / "relevance_gold_key.csv"
    if key_path.exists():
        import re as _re
        with key_path.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                raw = r["lexical_score"] or "0"
                # score_text returns a RelevanceSignal repr — is_football=True
                # is the Stage-1 verdict; bare numbers are kept as-is.
                if "is_football" in raw:
                    lex[int(r["doc_id"])] = 1.0 if "is_football=True" in raw else 0.0
                else:
                    m = _re.search(r"-?\d+(\.\d+)?", raw)
                    lex[int(r["doc_id"])] = float(m.group()) if m else 0.0
    if lex:
        y_true = [r["label"] for r in eval_rows]
        y_lex = [1 if lex.get(r["doc_id"], 0) > 0 else 0 for r in eval_rows]
        print("\nSTAGE-1 LEXICAL BASELINE (eval slice):")
        print("  ", metrics(y_true, y_lex))

    from datasets import Dataset
    from setfit import SetFitModel, Trainer, TrainingArguments

    train_ds = Dataset.from_dict({
        "text": [r["text"] for r in train_rows],
        "label": [r["label"] for r in train_rows],
    })
    eval_ds = Dataset.from_dict({
        "text": [r["text"] for r in eval_rows],
        "label": [r["label"] for r in eval_rows],
    })

    print(f"\nloading {BASE_MODEL} ...")
    model = SetFitModel.from_pretrained(BASE_MODEL)
    # ModernBERT-embed defaults to 8192-token context; our posts are <=600
    # chars (~150 tokens). Without this cap every batch pads enormously and
    # training takes ~20x longer for zero quality gain.
    model.model_body.max_seq_length = 512
    args = TrainingArguments(
        batch_size=32,
        num_epochs=1,
        num_iterations=20,   # contrastive pair sampling per example
        seed=SEED,
    )
    trainer = Trainer(model=model, args=args, train_dataset=train_ds, eval_dataset=eval_ds)
    trainer.train()

    preds = [int(p) for p in model.predict([r["text"] for r in eval_rows])]
    y_true = [r["label"] for r in eval_rows]
    m = metrics(y_true, preds)
    print("\nSETFIT + MODERNBERT (eval slice):")
    print("  ", m)

    # Per-pillar breakdown — the classifier must generalise beyond Reddit.
    print("\nper-pillar accuracy:")
    by_pillar: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for r, p in zip(eval_rows, preds):
        by_pillar[r["pillar"]].append((r["label"], p))
    for pillar in sorted(by_pillar):
        pairs = by_pillar[pillar]
        acc = sum(1 for t, p in pairs if t == p) / len(pairs)
        print(f"  {pillar:8s} n={len(pairs):3d} acc={acc:.3f}")

    # Misclassified examples for review.
    print("\nmisclassified (eval):")
    shown = 0
    for r, p in zip(eval_rows, preds):
        if p != r["label"] and shown < 12:
            print(f"  true={r['label']} pred={p} [{r['pillar']}] {r['text'][:90]}")
            shown += 1

    MODEL_OUT.parent.mkdir(exist_ok=True)
    model.save_pretrained(str(MODEL_OUT))
    print(f"\nmodel saved -> {MODEL_OUT}")


if __name__ == "__main__":
    main()
