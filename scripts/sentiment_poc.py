"""Sentiment POC: CardiffNLP encoder stack vs the stored VADER labels.

READ-ONLY on the DB (opens read-only; writes only to logs/). Run with the
ISOLATED env:  .venv-ml\\Scripts\\python.exe scripts\\sentiment_poc.py [N]

What it does:
  1. Pulls a stratified sample of real high-volume-team comments (text + the
     VADER label already stored in conversation_document_targets).
  2. Runs three free CardiffNLP RoBERTa heads:
        polarity : cardiffnlp/twitter-roberta-base-sentiment-latest
        emotion  : cardiffnlp/twitter-roberta-base-emotion-multilabel-latest
        irony    : cardiffnlp/twitter-roberta-base-irony   (sarcasm prob)
  3. Compares new polarity vs VADER, surfaces the disagreements (esp. where the
     irony head flags sarcasm — the classic VADER failure), measures throughput.
  4. Writes logs/sentiment_poc_report.md + logs/sentiment_poc_detail.csv
"""
import csv
import os
import re
import sqlite3
import sys
import time

N = int(sys.argv[1]) if len(sys.argv) > 1 else 450
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cfb_rankings.db")
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
TEAMS = ("michigan", "oregon", "florida-state", "penn-state", "ohio-state")

POL_MODEL = "cardiffnlp/twitter-roberta-base-sentiment-latest"
EMO_MODEL = "cardiffnlp/twitter-roberta-base-emotion-multilabel-latest"
IRO_MODEL = "cardiffnlp/twitter-roberta-base-irony"

JUNK = {"[removed]", "[deleted]", "", None}


def clean(t):
    if not t:
        return ""
    t = re.sub(r"http\S+", "http", t)
    t = re.sub(r"@\w+", "@user", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def pull_sample(n):
    """Stratified by stored VADER label so disagreements surface across classes."""
    uri = f"file:{DB_PATH}?mode=ro"
    db = sqlite3.connect(uri, uri=True)
    db.execute("pragma busy_timeout=5000")
    rows = []
    per_label = max(1, n // 3)
    for lbl in ("positive", "neutral", "negative"):
        q = db.execute(
            """
            select d.conversation_document_id, tm.slug, d.source_name,
                   coalesce(nullif(d.body_text,''), d.title_text) as txt,
                   t.sentiment_label
            from conversation_document_targets t
            join conversation_documents d on d.conversation_document_id = t.conversation_document_id
            join teams tm on tm.team_id = t.team_id
            where t.target_type='team' and t.sentiment_label = ?
              and tm.slug in (%s)
              and coalesce(nullif(d.body_text,''), d.title_text) is not null
              and coalesce(d.body_text,'') not in ('[removed]','[deleted]')
              and length(coalesce(nullif(d.body_text,''), d.title_text)) between 15 and 1200
            order by d.conversation_document_id
            limit ?
            """ % (",".join("?" * len(TEAMS))),
            (lbl, *TEAMS, per_label),
        ).fetchall()
        rows.extend(q)
    db.close()
    out = []
    for doc_id, slug, src, txt, vader in rows:
        c = clean(txt)
        if c and c.lower() not in JUNK:
            out.append({"doc_id": doc_id, "slug": slug, "src": src, "text": c, "vader": vader})
    return out


def main():
    print(f"[poc] sampling up to {N} docs from {TEAMS} ...", flush=True)
    sample = pull_sample(N)
    print(f"[poc] pulled {len(sample)} usable docs", flush=True)
    if not sample:
        print("[poc] NO SAMPLE — abort"); return

    import torch
    from transformers import pipeline

    use_gpu = torch.cuda.is_available()
    device = 0 if use_gpu else -1
    print(f"[poc] torch {torch.__version__}  cuda={use_gpu}  device={'gpu' if use_gpu else 'cpu'}", flush=True)

    def make(model, **kw):
        try:
            return pipeline("text-classification", model=model, device=device,
                            truncation=True, max_length=512, **kw)
        except Exception as e:
            print(f"[poc] GPU load failed for {model} ({e}); retrying on CPU", flush=True)
            return pipeline("text-classification", model=model, device=-1,
                            truncation=True, max_length=512, **kw)

    print("[poc] loading polarity head ...", flush=True)
    pol = make(POL_MODEL)
    print("[poc] loading emotion head ...", flush=True)
    emo = make(EMO_MODEL, top_k=None)   # multi-label -> all scores
    print("[poc] loading irony head ...", flush=True)
    iro = make(IRO_MODEL, top_k=None)

    texts = [r["text"] for r in sample]

    def norm_pol(label):
        m = {"label_0": "negative", "label_1": "neutral", "label_2": "positive",
             "negative": "negative", "neutral": "neutral", "positive": "positive"}
        return m.get(str(label).lower(), str(label).lower())

    t0 = time.time()
    pol_out = pol(texts, batch_size=32)
    emo_out = emo(texts, batch_size=32)
    iro_out = iro(texts, batch_size=32)
    dt = time.time() - t0
    rate = len(texts) / dt if dt else 0
    print(f"[poc] classified {len(texts)} docs x3 heads in {dt:.1f}s  ({rate:.1f} docs/s)", flush=True)

    def top_irony(scorelist):
        d = {s["label"].lower(): s["score"] for s in scorelist}
        # irony head: labels 'irony'/'non_irony' or LABEL_1/LABEL_0
        return d.get("irony", d.get("label_1", 0.0))

    def top_emos(scorelist, k=2):
        srt = sorted(scorelist, key=lambda s: -s["score"])
        return [(s["label"], round(s["score"], 3)) for s in srt[:k]]

    rows = []
    agree = 0
    flips = {"pos->neg": 0, "neg->pos": 0, "to_neutral": 0, "from_neutral": 0}
    sarcastic = 0
    for r, p, e, i in zip(sample, pol_out, emo_out, iro_out):
        new_pol = norm_pol(p["label"])
        sar = top_irony(i)
        emos = top_emos(e)
        if new_pol == r["vader"]:
            agree += 1
        else:
            if r["vader"] == "positive" and new_pol == "negative":
                flips["pos->neg"] += 1
            elif r["vader"] == "negative" and new_pol == "positive":
                flips["neg->pos"] += 1
            elif new_pol == "neutral":
                flips["to_neutral"] += 1
            elif r["vader"] == "neutral":
                flips["from_neutral"] += 1
        if sar >= 0.5:
            sarcastic += 1
        rows.append({**r, "new_pol": new_pol, "pol_conf": round(p["score"], 3),
                     "sarcasm": round(sar, 3), "emo1": emos[0][0] if emos else "",
                     "emo1_p": emos[0][1] if emos else 0, "emo2": emos[1][0] if len(emos) > 1 else "",
                     "agree": new_pol == r["vader"]})

    n = len(rows)
    agree_pct = 100 * agree / n if n else 0

    # detail CSV
    os.makedirs(LOG_DIR, exist_ok=True)
    csv_path = os.path.join(LOG_DIR, "sentiment_poc_detail.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["doc_id", "slug", "src", "vader", "new_pol", "pol_conf",
                    "sarcasm", "emo1", "emo1_p", "emo2", "agree", "text"])
        for r in rows:
            w.writerow([r["doc_id"], r["slug"], r["src"], r["vader"], r["new_pol"],
                        r["pol_conf"], r["sarcasm"], r["emo1"], r["emo1_p"], r["emo2"],
                        r["agree"], r["text"][:300]])

    # most interesting disagreements: VADER said positive but sarcasm high, or any flip with high confidence
    disagreements = [r for r in rows if not r["agree"]]
    spicy = sorted(disagreements, key=lambda r: (r["sarcasm"], r["pol_conf"]), reverse=True)[:25]

    md = []
    md.append("# Sentiment POC — CardiffNLP encoder stack vs stored VADER\n")
    md.append(f"- Sample: **{n}** real comments from {', '.join(TEAMS)}")
    md.append(f"- Throughput: **{rate:.1f} docs/sec** ({'GPU' if use_gpu else 'CPU'}) across 3 heads → ~{rate*3600/1000:.1f}k docs/hr/head-equivalent")
    md.append(f"- Polarity agreement with VADER: **{agree_pct:.1f}%** ({agree}/{n})")
    md.append(f"- Disagreements: **{len(disagreements)}** — pos→neg {flips['pos->neg']}, neg→pos {flips['neg->pos']}, →neutral {flips['to_neutral']}, neutral→ {flips['from_neutral']}")
    md.append(f"- Flagged sarcastic (irony≥0.5): **{sarcastic}** ({100*sarcastic/n:.1f}%)\n")
    md.append("## Most telling disagreements (sorted by sarcasm, then confidence)\n")
    md.append("| team | VADER | new | conf | sarcasm | emotion | comment |")
    md.append("|---|---|---|--:|--:|---|---|")
    for r in spicy:
        txt = r["text"][:140].replace("|", "\\|").replace("\n", " ")
        md.append(f"| {r['slug']} | {r['vader']} | **{r['new_pol']}** | {r['pol_conf']} | {r['sarcasm']} | {r['emo1']} | {txt} |")
    md_path = os.path.join(LOG_DIR, "sentiment_poc_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print(f"\n[poc] DONE")
    print(f"[poc] agreement {agree_pct:.1f}%  | sarcastic {sarcastic} ({100*sarcastic/n:.1f}%)  | flips {flips}")
    print(f"[poc] report: {md_path}")
    print(f"[poc] detail: {csv_path}")


if __name__ == "__main__":
    main()
