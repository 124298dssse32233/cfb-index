"""Classify ALL comment text with the CardiffNLP encoder stack into a SEPARATE
staging table. Does NOT touch conversation_document_targets (the live VADER
data). Fully reversible: drop table sentiment_v2_staging to undo.

Resumable: skips docs already in staging. Run with the isolated env:
  .venv-ml\\Scripts\\python.exe scripts\\sentiment_classify_staging.py
Logs progress to logs/sentiment_staging.log
"""
import os
import re
import sqlite3
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "cfb_rankings.db")
LOG = os.path.join(ROOT, "logs", "sentiment_staging.log")
MODEL_VERSION = "cardiffnlp-encoder-stack-v1"
CHUNK = 2000           # docs pulled + committed per loop
BATCH = 64             # GPU batch size

POL_MODEL = "cardiffnlp/twitter-roberta-base-sentiment-latest"
EMO_MODEL = "cardiffnlp/twitter-roberta-base-emotion-multilabel-latest"
IRO_MODEL = "cardiffnlp/twitter-roberta-base-irony"


def log(m):
    s = time.strftime("%H:%M:%S")
    line = f"{s}  {m}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def clean(t):
    if not t:
        return ""
    t = re.sub(r"http\S+", "http", t)
    t = re.sub(r"@\w+", "@user", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def main():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    log(f"==== staging classify START (model={MODEL_VERSION}) ====")
    db = sqlite3.connect(DB_PATH, timeout=60)
    db.execute("pragma busy_timeout=60000")
    db.execute("pragma journal_mode=WAL")
    db.execute("""
        create table if not exists sentiment_v2_staging (
          conversation_document_id integer primary key,
          pol_label text, pol_score real,
          emo_primary text, emo_primary_score real, emo_secondary text,
          sarcasm_score real, model_version text, classified_at text
        )""")
    db.commit()

    # universe: distinct docs that (a) have a team target with a VADER label
    # (apples-to-apples vs the baseline) and (b) have usable text, not yet staged.
    log("building work list (docs with a labeled team target + text, not yet staged)...")
    pending = db.execute(
        """
        select d.conversation_document_id,
               coalesce(nullif(d.body_text,''), d.title_text) as txt
        from conversation_documents d
        where coalesce(nullif(d.body_text,''), d.title_text) is not null
          and coalesce(d.body_text,'') not in ('[removed]','[deleted]')
          and exists (
            select 1 from conversation_document_targets t
            where t.conversation_document_id = d.conversation_document_id
              and t.target_type='team' and t.sentiment_label is not null)
          and d.conversation_document_id not in (select conversation_document_id from sentiment_v2_staging)
        """
    ).fetchall()
    total = len(pending)
    log(f"pending docs: {total}")
    if not total:
        log("nothing to do — all staged."); return

    import torch
    from transformers import pipeline
    dev = 0 if torch.cuda.is_available() else -1
    log(f"torch {torch.__version__} cuda={torch.cuda.is_available()} device={'gpu' if dev==0 else 'cpu'}")

    def make(model, **kw):
        return pipeline("text-classification", model=model, device=dev,
                        truncation=True, max_length=512, **kw)

    log("loading 3 heads...")
    pol = make(POL_MODEL)
    emo = make(EMO_MODEL, top_k=None)
    iro = make(IRO_MODEL, top_k=None)

    def norm_pol(label):
        m = {"label_0": "negative", "label_1": "neutral", "label_2": "positive",
             "negative": "negative", "neutral": "neutral", "positive": "positive"}
        return m.get(str(label).lower(), str(label).lower())

    def irony(scorelist):
        d = {s["label"].lower(): s["score"] for s in scorelist}
        return d.get("irony", d.get("label_1", 0.0))

    def emos(scorelist):
        srt = sorted(scorelist, key=lambda s: -s["score"])
        p = srt[0] if srt else {"label": None, "score": 0.0}
        s2 = srt[1]["label"] if len(srt) > 1 else None
        return p["label"], round(float(p["score"]), 4), s2

    t0 = time.time()
    done = 0
    for i in range(0, total, CHUNK):
        chunk = pending[i:i + CHUNK]
        ids = [c[0] for c in chunk]
        texts = [clean(c[1]) for c in chunk]
        po = pol(texts, batch_size=BATCH)
        eo = emo(texts, batch_size=BATCH)
        io = iro(texts, batch_size=BATCH)
        rows = []
        for did, p, e, ir in zip(ids, po, eo, io):
            ep, eps, es = emos(e)
            rows.append((did, norm_pol(p["label"]), round(float(p["score"]), 4),
                         ep, eps, es, round(float(irony(ir)), 4),
                         MODEL_VERSION, time.strftime("%Y-%m-%dT%H:%M:%S")))
        db.executemany(
            """insert or replace into sentiment_v2_staging
               (conversation_document_id, pol_label, pol_score, emo_primary,
                emo_primary_score, emo_secondary, sarcasm_score, model_version, classified_at)
               values (?,?,?,?,?,?,?,?,?)""", rows)
        db.commit()
        done += len(chunk)
        rate = done / (time.time() - t0)
        eta = (total - done) / rate if rate else 0
        log(f"  {done}/{total}  ({100*done/total:.1f}%)  {rate:.0f} docs/s  ETA {eta/60:.1f} min")

    log(f"==== staging classify DONE — {done} docs in {(time.time()-t0)/60:.1f} min ====")
    db.close()


if __name__ == "__main__":
    main()
