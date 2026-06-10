"""Daily encoder sentiment classify -- the moat-quality consistency fix (Phase 3).

Runs the CardiffNLP encoder stack on the 3090 over docs whose targets are still
on VADER (or were collected recently), and writes encoder labels straight into
conversation_document_targets. This is what keeps the LIVE sentiment consistent
with the one-time backfill: without it, every new day's reddit/bluesky pull lands
VADER labels and the mood numbers silently drift back toward the old method.

Fuses the two existing scripts:
  * sentiment_classify_staging.py -> model load + text clean + label normalization
  * migrate_sentiment_to_prod.py  -> backup-then-UPDATE pattern (shared backup
    table, so `migrate_sentiment_to_prod.py --revert --commit` still undoes this)

Must run in the ISOLATED ML env (torch/transformers live there, NOT in .venv):
  .venv-ml\\Scripts\\python.exe scripts\\sentiment_classify_daily.py [--commit]

Dry-run by default (prints the work-list size + a sample, touches nothing).
Idempotent: deterministic argmax, skip-filter on model_version, per-chunk commits.
Reproducible: model revisions are PINNED to verified commit SHAs (see PINS).
"""
import argparse
import os
import re
import sqlite3
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "cfb_rankings.db")
LOG = os.path.join(ROOT, "logs", "sentiment_classify_daily.log")

MODEL_NAME = "cardiffnlp-encoder-stack"
MODEL_VERSION = "cardiffnlp-encoder-stack-v1"   # the skip-key + the migrator's key
BACKUP = "cdt_sentiment_backup_vader"           # shared with migrate_sentiment_to_prod.py

# Pinned commit SHAs (verified 2026-06-10 against the HF API /api/models/<repo>.sha)
# so a future re-pull can't silently swap model weights under us.
POL_MODEL = "cardiffnlp/twitter-roberta-base-sentiment-latest"
POL_REV = "3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7"
EMO_MODEL = "cardiffnlp/twitter-roberta-base-emotion-multilabel-latest"
EMO_REV = "30a56d88e47e493f08f93c786d49c526550b55b9"
IRO_MODEL = "cardiffnlp/twitter-roberta-base-irony"
IRO_REV = "3bf8f118bdf6b00c99658151ef10c9a0b9afd6bf"

CHUNK = 2000           # docs pulled + committed per loop
BATCH = 64             # GPU batch size
# Self-heal OFF by default. The encoder is deterministic and the model revisions
# are pinned, so re-scoring an already-encoded doc never changes its label -- it's
# pure wasted GPU. The model_version filter already catches every genuinely-new or
# re-tagged doc (a re-tag adds a conversation-v1/null target, which fails the
# filter). Only set --self-heal-days > 0 as a one-off after bumping a model pin,
# to force a re-score of the trailing N days at the new revision.
SELF_HEAL_DAYS = 0


def log(m):
    s = time.strftime("%H:%M:%S")
    line = f"{s}  {m}"
    print(line, flush=True)
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def clean(t):
    if not t:
        return ""
    t = re.sub(r"http\S+", "http", t)
    t = re.sub(r"@\w+", "@user", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def score_signed(label):
    # Signed label == the net-sentiment method the validated mood-impact analysis
    # and the exclude-neutral mood recalibration both rely on.
    return {"positive": 1.0, "negative": -1.0, "neutral": 0.0}.get(label, 0.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true", help="actually write (default dry-run)")
    ap.add_argument("--max-docs", type=int, default=None, help="cap docs this run (debug)")
    ap.add_argument("--self-heal-days", type=int, default=SELF_HEAL_DAYS,
                    help="re-score docs collected within N days even if already encoded")
    args = ap.parse_args()

    log(f"==== daily encoder classify START (commit={args.commit}) ====")
    db = sqlite3.connect(DB, timeout=120)
    db.execute("pragma busy_timeout=120000")
    db.execute("pragma journal_mode=WAL")
    db.execute(f"""
        create table if not exists {BACKUP} (
          conversation_document_target_id integer primary key,
          sentiment_label text, sentiment_score real, emotion_primary text,
          emotion_secondary text, sarcasm_score real, model_name text, model_version text,
          backed_up_at text)""")
    db.commit()

    # Work-list: distinct docs with usable text that have at least one target NOT
    # yet on the encoder version, OR were collected within the self-heal window.
    # New daily pulls land here automatically (their targets are VADER-labeled).
    heal = int(args.self_heal_days)
    heal_clause = (
        f"or d.collected_at_utc >= datetime('now', '-{heal} days')" if heal > 0 else ""
    )
    log(f"building work list (un-encoded targets{', self-heal '+str(heal)+'d' if heal>0 else ''})...")
    rows = db.execute(
        f"""
        select d.conversation_document_id,
               coalesce(nullif(d.body_text,''), d.title_text) as txt
        from conversation_documents d
        where coalesce(nullif(d.body_text,''), d.title_text) is not null
          and coalesce(d.body_text,'') not in ('[removed]','[deleted]')
          and exists (
            select 1 from conversation_document_targets t
            where t.conversation_document_id = d.conversation_document_id
              and (
                coalesce(t.model_version,'') <> '{MODEL_VERSION}'
                {heal_clause}
              )
          )
        order by d.collected_at_utc desc
        """
    ).fetchall()
    if args.max_docs:
        rows = rows[: args.max_docs]
    total = len(rows)
    log(f"pending docs: {total}")
    if not total:
        log("nothing to do -- all targets already on encoder version.")
        return

    if not args.commit:
        # Show the blast radius without loading models.
        tids = db.execute(
            """select count(*) from conversation_document_targets t
               where t.conversation_document_id in (%s)"""
            % ",".join(str(r[0]) for r in rows[:5000])
        ).fetchone()[0]
        log(f"DRY-RUN: would classify {total} docs and update ~{tids}+ targets "
            f"(sample over first 5000 docs). Pass --commit to apply.")
        return

    import torch
    from transformers import pipeline
    dev = 0 if torch.cuda.is_available() else -1
    log(f"torch {torch.__version__} cuda={torch.cuda.is_available()} device={'gpu' if dev==0 else 'cpu'}")

    def make(model, rev, **kw):
        return pipeline("text-classification", model=model, revision=rev, device=dev,
                        truncation=True, max_length=512, **kw)

    log("loading 3 pinned heads...")
    pol = make(POL_MODEL, POL_REV)
    emo = make(EMO_MODEL, EMO_REV, top_k=None)
    iro = make(IRO_MODEL, IRO_REV, top_k=None)

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
    updated_targets = 0
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    for i in range(0, total, CHUNK):
        chunk = rows[i:i + CHUNK]
        ids = [c[0] for c in chunk]
        texts = [clean(c[1]) for c in chunk]
        po = pol(texts, batch_size=BATCH)
        eo = emo(texts, batch_size=BATCH)
        io = iro(texts, batch_size=BATCH)

        # 1) snapshot current target values for these docs (idempotent) so the
        #    migrator's --revert can restore them.
        qm = ",".join("?" * len(ids))
        db.execute(
            f"""insert or ignore into {BACKUP}
                select conversation_document_target_id, sentiment_label, sentiment_score,
                       emotion_primary, emotion_secondary, sarcasm_score, model_name,
                       model_version, '{stamp}'
                from conversation_document_targets
                where conversation_document_id in ({qm})""",
            ids,
        )

        # 2) per-doc encoder label -> update ALL of that doc's targets (sentiment
        #    is document-level; team + player targets share it by design).
        upd = []
        for did, p, e, ir in zip(ids, po, eo, io):
            label = norm_pol(p["label"])
            ep, eps, es = emos(e)
            upd.append((label, score_signed(label), ep, es, round(float(irony(ir)), 4),
                        "local", MODEL_NAME, MODEL_VERSION, did))
        cur = db.executemany(
            """update conversation_document_targets
                  set sentiment_label=?, sentiment_score=?, emotion_primary=?,
                      emotion_secondary=?, sarcasm_score=?, model_provider=?,
                      model_name=?, model_version=?
                where conversation_document_id=?""",
            upd,
        )
        updated_targets += cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
        db.commit()

        done += len(chunk)
        rate = done / (time.time() - t0)
        eta = (total - done) / rate if rate else 0
        log(f"  {done}/{total}  ({100*done/total:.1f}%)  {rate:.0f} docs/s  "
            f"~{updated_targets} targets  ETA {eta/60:.1f} min")

    log(f"==== daily encoder classify DONE -- {done} docs, ~{updated_targets} targets "
        f"in {(time.time()-t0)/60:.1f} min ====")
    db.close()


if __name__ == "__main__":
    main()
