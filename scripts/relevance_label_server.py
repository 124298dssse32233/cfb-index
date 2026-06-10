"""Local RELEVANCE-labeling dashboard (dependency-free, stdlib only).

Sibling of label_server.py (the sentiment dashboard) — same pattern, different
question: "is this post about college football?" One keypress per post.

Launch:  .venv\\Scripts\\python.exe scripts\\relevance_label_server.py
Then open http://127.0.0.1:8124  (it auto-opens your browser).

- READ-ONLY on cfb_rankings.db; labels go to labels.db (table relevance_labels).
- Queue is stratified across ALL source pillars INCLUDING the noisy ones —
  the filter must see noise to learn noise (unlike the sentiment dashboard,
  which deliberately queues football subs only).
- ~25% of the queue are posts Claude already labeled (data/relevance_gold/) —
  shown blind, used to measure human-AI agreement on the /stats scoreboard.
- Resumable: relaunching skips everything you've labeled.
- Keys: 1 = football · 0 = not football · s = skip.

Training merge: scripts/train_relevance_classifier.py picks these labels up
automatically (your label wins when you and Claude disagree).
"""
from __future__ import annotations

import csv
import http.server
import json
import os
import socketserver
import sqlite3
import threading
import webbrowser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DB = os.path.join(ROOT, "cfb_rankings.db")
LABELS_DB = os.path.join(ROOT, "labels.db")
GOLD_LABELS = os.path.join(ROOT, "data", "relevance_gold", "relevance_gold_labels.csv")
PORT = 8126
QUEUE_SIZE = 400
OVERLAP_SHARE = 0.25  # share of queue drawn from Claude-labeled docs (agreement check)

STRATA = [
    ("reddit",  "source_name LIKE 'reddit'",     0.40),
    ("bluesky", "source_name LIKE 'bluesky%'",   0.20),
    ("youtube", "source_name LIKE 'youtube%'",   0.15),
    ("podcast", "source_name LIKE 'locked_on_%'", 0.10),
    ("other",   "source_name NOT LIKE 'reddit' AND source_name NOT LIKE 'bluesky%' "
                "AND source_name NOT LIKE 'youtube%' AND source_name NOT LIKE 'locked_on_%'", 0.15),
]


def _claude_labels() -> dict[int, int]:
    if not os.path.exists(GOLD_LABELS):
        return {}
    with open(GOLD_LABELS, encoding="utf-8") as fh:
        return {int(r["doc_id"]): int(r["label"]) for r in csv.DictReader(fh)}


def init_labels_db() -> sqlite3.Connection:
    db = sqlite3.connect(LABELS_DB, check_same_thread=False)
    db.execute("""create table if not exists relevance_queue(
        ord integer primary key, doc_id integer unique, pillar text,
        subchannel text, txt text, claude_label integer)""")
    db.execute("""create table if not exists relevance_labels(
        doc_id integer primary key, label integer, ts text default current_timestamp)""")
    db.commit()
    return db


def build_queue(db: sqlite3.Connection) -> None:
    db.execute("delete from relevance_queue where doc_id not in "
               "(select doc_id from relevance_labels)")
    have = {r[0] for r in db.execute("select doc_id from relevance_queue")}
    done = {r[0] for r in db.execute("select doc_id from relevance_labels")}
    claude = _claude_labels()
    src = sqlite3.connect(f"file:{SRC_DB}?mode=ro", uri=True)

    rows: list[tuple] = []
    n_overlap = int(QUEUE_SIZE * OVERLAP_SHARE)
    # Overlap slice: Claude-labeled docs Kevin hasn't labeled (blind re-label).
    overlap_ids = [d for d in claude if d not in done and d not in have][:n_overlap * 3]
    if overlap_ids:
        q = ",".join("?" * len(overlap_ids))
        for r in src.execute(
            f"""select conversation_document_id, source_name,
                       coalesce(source_subchannel, source_channel, ''),
                       coalesce(title_text,'') || ' ' || coalesce(body_text,'')
                  from conversation_documents
                 where conversation_document_id in ({q})
                 limit ?""", (*overlap_ids, n_overlap)):
            rows.append((r[0], r[1], r[2], r[3][:600], claude.get(r[0])))

    fresh_target = QUEUE_SIZE - len(rows)
    for pillar, where, share in STRATA:
        want = max(1, int(fresh_target * share))
        got = src.execute(
            f"""select conversation_document_id, source_name,
                       coalesce(source_subchannel, source_channel, ''),
                       coalesce(title_text,'') || ' ' || coalesce(body_text,'')
                  from conversation_documents
                 where {where}
                   and body_text is not null and length(body_text) >= 20
                   and coalesce(is_deleted,0)=0 and coalesce(is_removed,0)=0
                 order by (conversation_document_id * 1103515245) % 4294967296
                 limit ?""", (want * 3,)).fetchall()
        kept = 0
        for r in got:
            if kept >= want:
                break
            if r[0] in done or r[0] in have or r[0] in claude:
                continue
            rows.append((r[0], pillar, r[2], r[3][:600], None))
            kept += 1

    # Interleave so overlap docs are spread out, not clumped at the start.
    rows.sort(key=lambda r: (r[0] * 2654435761) % 4294967296)
    for doc_id, pillar, sub, txt, cl in rows:
        db.execute("insert or ignore into relevance_queue "
                   "(doc_id, pillar, subchannel, txt, claude_label) values (?,?,?,?,?)",
                   (doc_id, pillar, sub, txt, cl))
    db.commit()


PAGE = """<!doctype html><html><head><meta charset="utf-8">
<title>CFB relevance labeling</title><style>
 body{font-family:system-ui,sans-serif;background:#101418;color:#e8e8e8;
      max-width:760px;margin:40px auto;padding:0 16px}
 .card{background:#1a2129;border-radius:12px;padding:24px;margin:18px 0;
       min-height:130px;font-size:17px;line-height:1.55;white-space:pre-wrap}
 .meta{color:#7d8b99;font-size:13px;margin-bottom:8px}
 button{font-size:18px;padding:14px 26px;margin:6px;border-radius:10px;
        border:0;cursor:pointer;font-weight:600}
 .yes{background:#1d7a46;color:#fff}.no{background:#8a3636;color:#fff}
 .skip{background:#39424d;color:#cfd6dd}
 #bar{color:#7d8b99;margin-top:14px;font-size:14px}
 #agree{color:#c8a34a}
 .hint{color:#5b6975;font-size:12.5px;margin-top:18px}
</style></head><body>
<h2>Is this post about college football?</h2>
<div class="meta" id="meta"></div>
<div class="card" id="txt">loading…</div>
<div>
 <button class="yes"  onclick="send(1)">🏈 Football (1)</button>
 <button class="no"   onclick="send(0)">🚫 Not football (0)</button>
 <button class="skip" onclick="send(-1)">Skip (s)</button>
</div>
<div id="bar"></div><div id="agree"></div>
<div class="hint">Count anything about the sport: games, players, coaches, recruiting,
portal, NIL, polls, gameday fandom &amp; banter with team vocabulary. Don't count: other
sports (hoops/baseball/softball), campus/city life, NFL-only talk, generic replies that
could appear in any subreddit. Keys: 1 / 0 / s.</div>
<script>
let cur=null;
function offline(){
  document.getElementById('txt').textContent=
    '⚠️ Lost contact with the labeling server. Your saved labels are safe — '+
    'relaunch it in the terminal:\\n\\n.venv\\\\Scripts\\\\python.exe scripts\\\\relevance_label_server.py\\n\\nthen refresh this page.';
}
async function next(){
  let d;
  try{ const r=await fetch('/next'); d=await r.json(); }catch(e){ offline(); return; }
  if(!d.doc_id){document.getElementById('txt').textContent='🎉 Queue empty — thank you! Relaunch to refill.';cur=null;return}
  cur=d; document.getElementById('txt').textContent=d.txt;
  document.getElementById('meta').textContent=`#${d.done+1} · ${d.pillar} · ${d.subchannel||'—'}`;
  document.getElementById('bar').textContent=`${d.done} labeled · ${d.left} left in queue`;
  if(d.agree_n>0){document.getElementById('agree').textContent=
    `agreement with Claude so far: ${d.agree_pct}% over ${d.agree_n} shared posts`;}
}
async function send(v){
  if(!cur)return;
  try{
    await fetch('/label',{method:'POST',body:JSON.stringify({doc_id:cur.doc_id,label:v})});
  }catch(e){ offline(); return; }
  next();
}
document.addEventListener('keydown',e=>{
  if(e.key==='1')send(1); else if(e.key==='0')send(0); else if(e.key==='s')send(-1);});
next();
</script></body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    db: sqlite3.Connection = None  # set in main
    lock = threading.Lock()

    def _json(self, obj) -> None:
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        if self.path == "/":
            body = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/next":
            with self.lock:
                row = self.db.execute(
                    """select q.doc_id, q.pillar, q.subchannel, q.txt
                         from relevance_queue q
                        where q.doc_id not in (select doc_id from relevance_labels)
                        order by q.ord limit 1""").fetchone()
                done = self.db.execute(
                    "select count(*) from relevance_labels where label in (0,1)").fetchone()[0]
                left = self.db.execute(
                    """select count(*) from relevance_queue
                        where doc_id not in (select doc_id from relevance_labels)""").fetchone()[0]
                ag = self.db.execute(
                    """select count(*), sum(case when l.label = q.claude_label then 1 else 0 end)
                         from relevance_labels l join relevance_queue q on q.doc_id = l.doc_id
                        where q.claude_label is not null and l.label in (0,1)""").fetchone()
            agree_n = ag[0] or 0
            agree_pct = round(100 * (ag[1] or 0) / agree_n) if agree_n else 0
            if not row:
                self._json({"doc_id": None})
                return
            self._json({"doc_id": row[0], "pillar": row[1], "subchannel": row[2],
                        "txt": row[3], "done": done, "left": left,
                        "agree_n": agree_n, "agree_pct": agree_pct})
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):  # noqa: N802
        if self.path == "/label":
            n = int(self.headers.get("Content-Length", 0))
            d = json.loads(self.rfile.read(n))
            if d.get("label") in (0, 1, -1):
                with self.lock:
                    self.db.execute(
                        "insert or replace into relevance_labels (doc_id, label) values (?,?)",
                        (int(d["doc_id"]), int(d["label"])))
                    self.db.commit()
            self._json({"ok": True})
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, *a):  # quiet
        pass


def main() -> None:
    db = init_labels_db()
    build_queue(db)
    n = db.execute("select count(*) from relevance_queue").fetchone()[0]
    Handler.db = db
    print(f"queue ready: {n} posts — http://127.0.0.1:{PORT}")
    threading.Timer(0.8, lambda: webbrowser.open(f"http://127.0.0.1:{PORT}")).start()
    with socketserver.ThreadingTCPServer(("127.0.0.1", PORT), Handler) as srv:
        srv.allow_reuse_address = True
        print("labeling server up — Ctrl+C to stop")
        srv.serve_forever()


if __name__ == "__main__":
    main()
