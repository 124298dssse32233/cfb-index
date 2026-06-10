"""Migrate encoder sentiment (sentiment_v2_staging) into the production
conversation_document_targets table. FULLY REVERSIBLE + dry-run by default.

Safety design:
  * Dry-run unless --commit is passed. Dry-run prints counts + a sample.
  * Before any write, snapshots the current (VADER) values of every affected
    target row into a backup table  cdt_sentiment_backup_vader  (idempotent:
    only inserts rows not already backed up). --revert restores from it.
  * sentiment_score is set to a signed label value (+1/0/-1) so the downstream
    mean becomes net sentiment == the method used in the validated mood-impact
    analysis. Pass --score-mode confidence to use +/-pol_score instead.
  * Only updates team targets whose document is present in staging.

Run (dry-run):  .venv\\Scripts\\python.exe scripts\\migrate_sentiment_to_prod.py
Run (apply):    .venv\\Scripts\\python.exe scripts\\migrate_sentiment_to_prod.py --commit
Revert:         .venv\\Scripts\\python.exe scripts\\migrate_sentiment_to_prod.py --revert --commit
"""
import argparse
import os
import sqlite3
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "cfb_rankings.db")
MODEL_NAME = "cardiffnlp-encoder-stack"
MODEL_VERSION = "cardiffnlp-encoder-stack-v1"
BACKUP = "cdt_sentiment_backup_vader"


def score_for(label, pol_score, mode):
    if mode == "confidence":
        if label == "positive": return round(float(pol_score), 4)
        if label == "negative": return round(-float(pol_score), 4)
        return 0.0
    # default: signed label
    return {"positive": 1.0, "negative": -1.0, "neutral": 0.0}.get(label, 0.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true", help="actually write (default dry-run)")
    ap.add_argument("--revert", action="store_true", help="restore VADER values from backup table")
    ap.add_argument("--score-mode", choices=["signed", "confidence"], default="signed")
    ap.add_argument("--teams", default=None, help="optional comma slugs to limit (e.g. high-volume first)")
    args = ap.parse_args()

    db = sqlite3.connect(DB, timeout=120)
    db.execute("pragma busy_timeout=120000")
    db.execute("pragma journal_mode=WAL")

    if args.revert:
        n = db.execute(f"select count(*) from sqlite_master where type='table' and name='{BACKUP}'").fetchone()[0]
        if not n:
            print("No backup table — nothing to revert."); return
        cnt = db.execute(f"select count(*) from {BACKUP}").fetchone()[0]
        print(f"[revert] backup rows: {cnt}  commit={args.commit}")
        if args.commit:
            db.execute(f"""
                update conversation_document_targets
                   set sentiment_label=(select b.sentiment_label from {BACKUP} b where b.conversation_document_target_id=conversation_document_targets.conversation_document_target_id),
                       sentiment_score=(select b.sentiment_score from {BACKUP} b where b.conversation_document_target_id=conversation_document_targets.conversation_document_target_id),
                       emotion_primary=(select b.emotion_primary from {BACKUP} b where b.conversation_document_target_id=conversation_document_targets.conversation_document_target_id),
                       emotion_secondary=(select b.emotion_secondary from {BACKUP} b where b.conversation_document_target_id=conversation_document_targets.conversation_document_target_id),
                       sarcasm_score=(select b.sarcasm_score from {BACKUP} b where b.conversation_document_target_id=conversation_document_targets.conversation_document_target_id),
                       model_name=(select b.model_name from {BACKUP} b where b.conversation_document_target_id=conversation_document_targets.conversation_document_target_id),
                       model_version=(select b.model_version from {BACKUP} b where b.conversation_document_target_id=conversation_document_targets.conversation_document_target_id)
                 where conversation_document_target_id in (select conversation_document_target_id from {BACKUP})""")
            db.commit()
            print("[revert] restored.")
        else:
            print("[revert] dry-run — pass --commit to restore.")
        return

    # forward migration
    team_filter = ""
    params = []
    if args.teams:
        slugs = [s.strip() for s in args.teams.split(",")]
        team_filter = " and tm.slug in (%s)" % ",".join("?" * len(slugs))
        params = slugs

    rows = db.execute(f"""
        select t.conversation_document_target_id, t.sentiment_label as old_lbl,
               s.pol_label, s.pol_score, s.emo_primary, s.emo_secondary, s.sarcasm_score
        from conversation_document_targets t
        join sentiment_v2_staging s on s.conversation_document_id = t.conversation_document_id
        join teams tm on tm.team_id = t.team_id
        where t.target_type='team' and t.sentiment_label is not null {team_filter}
    """, params).fetchall()

    changed = sum(1 for r in rows if r[1] != r[2])
    print(f"[migrate] affected targets: {len(rows)}  (would change label on {changed})  score-mode={args.score_mode}  commit={args.commit}")
    # sample
    print("[migrate] sample changes (old -> new):")
    shown = 0
    for tid, old, new, ps, ep, es, sar in rows:
        if old != new:
            print(f"    target {tid}: {old} -> {new}  (emo {ep}, sarcasm {sar})")
            shown += 1
            if shown >= 8:
                break

    if not args.commit:
        print("[migrate] DRY-RUN — pass --commit to apply (will snapshot VADER values first).")
        return

    # 1) snapshot current values (idempotent)
    db.execute(f"""
        create table if not exists {BACKUP} (
          conversation_document_target_id integer primary key,
          sentiment_label text, sentiment_score real, emotion_primary text,
          emotion_secondary text, sarcasm_score real, model_name text, model_version text,
          backed_up_at text)""")
    ids = [r[0] for r in rows]
    qm = ",".join("?" * 900)
    snap = 0
    for i in range(0, len(ids), 900):
        chunk = ids[i:i+900]
        q = ",".join("?" * len(chunk))
        db.execute(f"""
            insert or ignore into {BACKUP}
            select conversation_document_target_id, sentiment_label, sentiment_score,
                   emotion_primary, emotion_secondary, sarcasm_score, model_name, model_version,
                   '{time.strftime("%Y-%m-%dT%H:%M:%S")}'
            from conversation_document_targets
            where conversation_document_target_id in ({q})""", chunk)
        snap += len(chunk)
    db.commit()
    print(f"[migrate] snapshotted {snap} rows into {BACKUP}")

    # 2) apply
    upd = [(r[2], score_for(r[2], r[3], args.score_mode), r[4], r[5], r[6],
            "local", MODEL_NAME, MODEL_VERSION, r[0]) for r in rows]
    db.executemany("""
        update conversation_document_targets
           set sentiment_label=?, sentiment_score=?, emotion_primary=?, emotion_secondary=?,
               sarcasm_score=?, model_provider=?, model_name=?, model_version=?
         where conversation_document_target_id=?""", upd)
    db.commit()
    print(f"[migrate] APPLIED encoder sentiment to {len(upd)} targets. Revert with --revert --commit.")
    db.close()


if __name__ == "__main__":
    main()
