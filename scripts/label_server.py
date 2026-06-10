"""Local sentiment-labeling dashboard (dependency-free, stdlib only).

Launch:  .venv\\Scripts\\python.exe scripts\\label_server.py
Then open http://127.0.0.1:8765  (it auto-opens your browser).

Reads a comment pool from cfb_rankings.db (READ-ONLY) and writes your labels to
a SEPARATE labels.db (your production DB is never written to). Resumable: skips
what you've already labeled. Blind by design — model guesses are hidden while you
label, then revealed on the live scoreboard so your labels stay unbiased.

Your labels power: (1) a hard accuracy score (VADER vs the new AI), and
(2) later, fine-tuning the model on CFB-specific language.
"""
import http.server
import json
import os
import random
import socketserver
import sqlite3
import threading
import webbrowser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DB = os.path.join(ROOT, "cfb_rankings.db")
LABELS_DB = os.path.join(ROOT, "labels.db")
PORT = 8123
QUEUE_SIZE = 400
TEAMS = ("michigan", "oregon", "florida-state", "penn-state", "ohio-state",
         "texas", "georgia", "alabama", "miami", "ohio-state", "nebraska", "indiana")

# Football subreddits ONLY. City/university subs (r/Eugene, r/AnnArbor, r/Columbus,
# r/PennStateUniversity, r/Tallahassee, r/statecollege, ...) are ~all off-topic local
# life, so they're excluded -> labeling time goes to real football talk. Derived from
# the corpus 2026-06-09; the deep-research pass will yield a maintained CFB-subreddit list.
FOOTBALL_SUBS = ("MichiganWolverines", "fsusports", "ducks", "CFB", "rolltide",
                 "LonghornNation", "georgiabulldogs", "LSUFootball")


def init_labels_db():
    db = sqlite3.connect(LABELS_DB)
    db.execute("""create table if not exists queue(
        ord integer primary key, doc_id integer unique, team text, txt text,
        vader text, enc text)""")
    db.execute("""create table if not exists labels(
        doc_id integer primary key, label text, sarcastic int default 0,
        offtopic int default 0, ts text)""")
    db.commit()
    return db


def build_queue(db):
    # Refresh each start: KEEP already-labeled rows (so /stats still joins + your
    # off-topic labels are preserved), DROP unlabeled rows (may be old city/campus
    # noise), then refill from FOOTBALL subreddits only.
    db.execute("delete from queue where doc_id not in (select doc_id from labels)")
    labeled = set(r[0] for r in db.execute("select doc_id from labels").fetchall())
    have = set(r[0] for r in db.execute("select doc_id from queue").fetchall())
    src = sqlite3.connect(f"file:{SRC_DB}?mode=ro", uri=True)
    subs = tuple(FOOTBALL_SUBS)
    rows = src.execute(
        """
        select t.conversation_document_id, tm.slug,
               coalesce(nullif(d.body_text,''), d.title_text) as txt,
               t.sentiment_label as vader, s.pol_label as enc
        from conversation_document_targets t
        join conversation_documents d on d.conversation_document_id = t.conversation_document_id
        join teams tm on tm.team_id = t.team_id
        left join sentiment_v2_staging s on s.conversation_document_id = t.conversation_document_id
        where t.target_type='team' and t.sentiment_label is not null
          and d.source_name='reddit' and d.source_subchannel in (%s)
          and coalesce(d.body_text,'') not in ('[removed]','[deleted]')
          and length(coalesce(nullif(d.body_text,''), d.title_text)) between 25 and 500
        """ % ",".join("?" * len(subs)),
        subs).fetchall()
    src.close()
    seen = set(); disagree = []; agree = []
    for did, slug, txt, vader, enc in rows:
        if did in seen or did in labeled or did in have:
            continue
        seen.add(did)
        (disagree if (enc and enc != vader) else agree).append((did, slug, txt, vader, enc))
    rnd = random.Random(1234)
    rnd.shuffle(disagree); rnd.shuffle(agree)
    n_dis = int(QUEUE_SIZE * 0.6)
    pool = disagree[:n_dis] + agree[:QUEUE_SIZE - n_dis]
    rnd.shuffle(pool)
    ord0 = (db.execute("select coalesce(max(ord),-1) from queue").fetchone()[0]) + 1
    for j, (did, slug, txt, vader, enc) in enumerate(pool):
        db.execute("insert or ignore into queue(ord,doc_id,team,txt,vader,enc) values(?,?,?,?,?,?)",
                   (ord0 + j, did, slug, txt, vader, enc))
    db.commit()


def next_item(db):
    row = db.execute("""
        select q.doc_id, q.team, q.txt from queue q
        left join labels l on l.doc_id = q.doc_id
        where l.doc_id is null order by q.ord limit 1""").fetchone()
    if not row:
        return None
    return {"id": row[0], "team": row[1], "text": row[2]}


def progress(db):
    total = db.execute("select count(*) from queue").fetchone()[0]
    done = db.execute("select count(*) from labels").fetchone()[0]
    return {"done": done, "total": total}


def stats(db):
    rows = db.execute("""
        select q.vader, q.enc, l.label, l.sarcastic, l.offtopic
        from labels l join queue q on q.doc_id = l.doc_id""").fetchall()
    n = len(rows)
    if n == 0:
        return {"n": 0}
    onv = [r for r in rows if not r[4]]  # exclude off-topic from accuracy
    nv = len(onv)
    v_ok = sum(1 for r in onv if (r[0] or "") == r[2])
    e_rows = [r for r in onv if r[1]]
    e_ok = sum(1 for r in e_rows if (r[1] or "") == r[2])
    sarc = sum(1 for r in rows if r[3])
    off = sum(1 for r in rows if r[4])
    return {
        "n": n, "scored": nv,
        "vader_acc": round(100 * v_ok / nv, 1) if nv else None,
        "enc_acc": round(100 * e_ok / len(e_rows), 1) if e_rows else None,
        "enc_n": len(e_rows), "sarcastic": sarc, "offtopic": off,
    }


HTML = r"""<!doctype html><html><head><meta charset=utf-8>
<title>CFB Sentiment Labeler</title>
<style>
 :root{--pos:#1d9e75;--neu:#888;--neg:#e24b4a;--bg:#15161a;--card:#222530;--ink:#f4f2ec;--mut:#9a9a97}
 *{box-sizing:border-box} body{margin:0;font-family:Inter,system-ui,Arial,sans-serif;background:var(--bg);color:var(--ink)}
 .wrap{max-width:760px;margin:0 auto;padding:24px 18px 60px}
 h1{font-size:18px;letter-spacing:.04em;color:var(--mut);font-weight:600;margin:0 0 4px}
 .bar{height:8px;background:#2c2c2a;border-radius:99px;overflow:hidden;margin:10px 0 14px}
 .guide{background:#1b1d24;border:1px solid #333;border-left:3px solid #378add;border-radius:8px;padding:10px 13px;margin:0 0 18px;font-size:12.5px;line-height:1.5;color:#c9c7c0}
 .guide b{color:var(--ink)} .guide .p{color:var(--pos)} .guide .n{color:#e8857f} .guide .u{color:var(--mut)}
 .bar>div{height:100%;background:linear-gradient(90deg,#378add,#1d9e75);width:0%}
 .team{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:#378add;font-weight:700;margin-bottom:8px}
 .card{background:var(--card);border:1px solid #333;border-radius:14px;padding:26px 24px;min-height:160px;
       font-size:21px;line-height:1.5;display:flex;align-items:center}
 .btns{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-top:18px}
 button.lab{padding:18px;border:none;border-radius:12px;font-size:17px;font-weight:700;cursor:pointer;color:#fff}
 .pos{background:var(--pos)} .neu{background:var(--neu)} .neg{background:var(--neg)}
 button.lab:hover{filter:brightness(1.12)} button.lab small{display:block;font-weight:500;opacity:.8;font-size:12px;margin-top:4px}
 .flags{display:flex;gap:10px;margin-top:14px;flex-wrap:wrap}
 .flag{padding:9px 14px;border:1px solid #444;border-radius:99px;background:#1b1d24;color:var(--mut);cursor:pointer;font-size:13px;user-select:none}
 .flag.on{background:#3a2f12;border-color:#ba7517;color:#fac775}
 .row2{display:flex;justify-content:space-between;align-items:center;margin-top:16px;color:var(--mut);font-size:13px}
 .row2 a{color:#378add;cursor:pointer}
 .score{background:#1b1d24;border:1px solid #333;border-radius:12px;padding:14px 18px;margin-top:24px;font-size:14px;line-height:1.7}
 .score b{font-size:18px}
 .done{text-align:center;padding:50px 0;font-size:20px}
 kbd{background:#333;border-radius:4px;padding:1px 6px;font-size:12px;color:#ddd}
</style></head><body><div class=wrap>
<h1>CFB SENTIMENT LABELER</h1>
<div class=bar><div id=pbar></div></div>
<div class=guide>
  Ask: <b>is this saying something GOOD or BAD about this team?</b> (the team's vibe — not the writer's mood)<br>
  <span class=p>1 Positive</span> = hype / praise / optimism &nbsp;·&nbsp; <span class=n>3 Negative</span> = criticism / doom / mockery &nbsp;·&nbsp; <b>2 Neutral</b> = just facts or no lean.<br>
  Judge the <b>meaning</b>, not the words — "oh great, another loss 🙄" is Negative (+ tap <b>Sarcastic</b>). <span class=u>Not about the team's football → Off-topic.</span><br>
  <b>Just reporting news with no opinion</b> ("QB out 3 weeks with injury") = <b>Neutral</b>, even if the news is bad — label the writer's <i>feeling</i>, not the event.<br>
  <a href="/guide" target="_blank" style="color:#378add;font-weight:600">&rarr; full rubric &amp; lots more examples</a>
</div>
<div id=main>
  <div class=team id=team></div>
  <div class=card id=comment>loading…</div>
  <div class=btns>
    <button class="lab pos" onclick="label('positive')">Positive <small>key 1</small></button>
    <button class="lab neu" onclick="label('neutral')">Neutral <small>key 2</small></button>
    <button class="lab neg" onclick="label('negative')">Negative <small>key 3</small></button>
  </div>
  <div class=flags>
    <div class=flag id=fSarc onclick="toggle('sarc')">🙄 Sarcastic <kbd>s</kbd></div>
    <div class=flag id=fOff onclick="toggle('off')">🚫 Off-topic / not about team <kbd>x</kbd></div>
  </div>
  <div class=row2><span id=prog></span><a onclick="undo()">↶ undo last (<kbd>u</kbd>)</a></div>
</div>
<div class=score id=score></div>
</div>
<script>
let cur=null, flags={sarc:false,off:false}, last=null;
async function load(){
  const r=await fetch('/api/next').then(x=>x.json());
  const p=await fetch('/api/progress').then(x=>x.json());
  document.getElementById('pbar').style.width=(p.total?100*p.done/p.total:0)+'%';
  document.getElementById('prog').textContent=p.done+' / '+p.total+' labeled';
  if(!r){document.getElementById('main').innerHTML='<div class=done>🎉 All done — every comment in the queue is labeled!<br>Tell Claude and it will score + can fine-tune the model.</div>';loadScore();return;}
  cur=r; flags={sarc:false,off:false};
  document.getElementById('team').textContent=r.team;
  document.getElementById('comment').textContent=r.text;
  document.getElementById('fSarc').classList.remove('on');
  document.getElementById('fOff').classList.remove('on');
  loadScore();
}
async function label(l){
  if(!cur)return;
  last=cur.id;
  await fetch('/api/label',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({id:cur.id,label:l,sarcastic:flags.sarc?1:0,offtopic:flags.off?1:0})});
  load();
}
function toggle(f){flags[f]=!flags[f];document.getElementById(f=='sarc'?'fSarc':'fOff').classList.toggle('on');}
async function undo(){ if(!last)return; await fetch('/api/undo',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:last})}); last=null; load(); }
async function loadScore(){
  const s=await fetch('/api/stats').then(x=>x.json());
  const el=document.getElementById('score');
  if(!s.n){el.innerHTML='Label a few and your live scoreboard appears here (it stays hidden while you decide, so your labels stay honest).';return;}
  let h='<b>Live scoreboard</b> &nbsp; ('+s.scored+' scored, '+s.offtopic+' off-topic excluded)<br>';
  if(s.vader_acc!=null) h+='Old VADER agrees with you: <b>'+s.vader_acc+'%</b><br>';
  if(s.enc_acc!=null) h+='New AI agrees with you: <b style="color:#5dcaa5">'+s.enc_acc+'%</b> &nbsp;(on '+s.enc_n+')<br>';
  h+='<span style="color:#9a9a97">You flagged '+s.sarcastic+' sarcastic.</span>';
  el.innerHTML=h;
}
document.addEventListener('keydown',e=>{
  if(e.key=='1')label('positive'); else if(e.key=='2')label('neutral'); else if(e.key=='3')label('negative');
  else if(e.key=='s')toggle('sarc'); else if(e.key=='x')toggle('off'); else if(e.key=='u')undo();
});
load();
</script></body></html>"""


GUIDE_HTML = r"""<!doctype html><html><head><meta charset=utf-8>
<title>CFB Sentiment Labeling Rubric</title>
<style>
 :root{--pos:#5dcaa5;--neg:#e8857f;--neu:#b4b2a9;--bg:#15161a;--card:#222530;--ink:#f4f2ec;--mut:#9a9a97}
 *{box-sizing:border-box} body{margin:0;font-family:Inter,system-ui,Arial,sans-serif;background:var(--bg);color:var(--ink);line-height:1.5}
 .wrap{max-width:780px;margin:0 auto;padding:26px 18px 80px}
 h1{font-size:20px;margin:0 0 4px} h2{font-size:16px;margin:26px 0 8px;padding-bottom:5px;border-bottom:1px solid #333}
 .q{background:#1b1d24;border-left:3px solid #378add;border-radius:8px;padding:12px 15px;margin:12px 0 18px;font-size:14px}
 .pos h2{color:var(--pos)} .neg h2{color:var(--neg)} .neu h2{color:var(--neu)}
 ul{margin:6px 0 14px;padding-left:0;list-style:none}
 li{padding:5px 0 5px 26px;position:relative;font-size:14px;color:#d7d5cd}
 .pos li::before{content:"\1F7E2";position:absolute;left:0} .neg li::before{content:"\1F534";position:absolute;left:0}
 .neu li::before{content:"\26AA";position:absolute;left:0} .rule li::before{content:"\26A0\FE0F";position:absolute;left:0}
 .sub{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--mut);font-weight:700;margin:12px 0 2px}
 em{color:#fac775;font-style:normal} b{color:#fff}
 table{width:100%;border-collapse:collapse;margin:8px 0 14px;font-size:13px}
 td{padding:6px 9px;border-bottom:1px solid #2c2c2a;vertical-align:top} td:first-child{color:#fff;white-space:nowrap}
 .g{color:var(--pos);text-align:center} .r{color:var(--neg);text-align:center}
 a{color:#378add}
 .flow{counter-reset:s} .flow li{padding-left:30px} .flow li::before{counter-increment:s;content:counter(s);position:absolute;left:0;width:18px;height:18px;background:#378add;color:#fff;border-radius:50%;font-size:11px;text-align:center;line-height:18px;font-weight:700}
</style></head><body><div class=wrap>
<h1>CFB Sentiment Labeling Rubric</h1>
<div class=q><b>The one question:</b> Is this comment expressing something <b>GOOD or BAD about the team shown</b>? You're labeling the team's vibe / the writer's expressed feeling — <b>not</b> the writer's general mood, and <b>not</b> how bad/good the underlying event is.</div>
<div class=sub>Decision flow</div>
<ul class=flow>
<li>About this team's <b>football</b> at all? No &rarr; <b>Off-topic</b> (flag it).</li>
<li>Any <b>feeling/opinion</b> expressed (a word with emotion or judgment)? No &rarr; <b>Neutral</b>.</li>
<li>If yes: favorable &rarr; <b>Positive</b>, unfavorable &rarr; <b>Negative</b>.</li>
<li><b>Sarcasm?</b> Judge the real meaning, then tap <b>Sarcastic</b>.</li>
<li><b>Mixed?</b> Overall lean; truly 50/50 &rarr; Neutral.</li>
</ul>

<div class=pos>
<h2>&#x1F7E2; POSITIVE &mdash; good about the team</h2>
<div class=sub>Optimism / confidence</div>
<ul class=pos><li>"This is the year we finally break through."</li><li>"Defense is going to be a problem for everybody this fall."</li><li>"Our schedule sets up perfectly for a playoff run."</li></ul>
<div class=sub>Praise</div>
<ul class=pos><li>"Coach completely changed the culture here."</li><li>"Most accurate QB we've had in a decade."</li><li>"That O-line is going to be elite."</li></ul>
<div class=sub>Hype / good news embraced</div>
<ul class=pos><li>"WE GOT THE 5-STAR!! LFG &#x1F525;"</li><li>"Portal haul is insane, GMs of the offseason."</li><li>"Spring game had me hyped &mdash; the freshmen look the part."</li></ul>
<div class=sub>Pride / defending the team</div>
<ul class=pos><li>"Four straight over them now. We own them."</li><li>"Y'all sleep on us every year and we keep proving you wrong."</li></ul>
<div class=sub>Positive slang (looks neutral/negative, means GOOD)</div>
<ul class=pos><li>"QB1 is <b>HIM</b>." (elite)</li><li>"Our secondary is <b>nasty / filthy</b> this year." (impressive)</li><li>"He's been <b>cooking</b> all spring." (dominating)</li><li>"That freshman edge is a <b>problem</b>." (a good one)</li></ul>
</div>

<div class=neg>
<h2>&#x1F534; NEGATIVE &mdash; bad about the team</h2>
<div class=sub>Pessimism / doom</div>
<ul class=neg><li>"Same old us. We'll find a way to blow it."</li><li>"Season's already over and it's August."</li></ul>
<div class=sub>Criticism</div>
<ul class=neg><li>"The OC has no creativity &mdash; same three plays every week."</li><li>"Can't tackle, can't catch, can't coach. Embarrassing."</li></ul>
<div class=sub>Frustration / anger</div>
<ul class=neg><li>"I'm so done with this program."</li><li>"How do you lose to THEM at home?? Unacceptable."</li></ul>
<div class=sub>Hot seat / mockery / bad reactions</div>
<ul class=neg><li>"Fire him tonight, buyout be damned."</li><li>"We're frauds. Always have been."</li><li>"Losing our WR to the portal is brutal, there goes the season."</li></ul>
<div class=sub>Negative slang</div>
<ul class=neg><li>"We're <b>cooked / washed / done</b>."</li><li>"Offense is <b>mid</b> at best."</li><li>"Got <b>exposed as frauds</b> again."</li><li>"We <b>fumbled the bag</b> on that hire."</li></ul>
</div>

<div class=neu>
<h2>&#x26AA; NEUTRAL &mdash; no lean (and the default when unsure)</h2>
<div class=sub>Factual news with NO opinion &mdash; even if the news is bad</div>
<ul class=neu><li>"QB ruled out Saturday with a high ankle sprain."</li><li>"Kickoff moved to 3:30 on ABC."</li><li>"He announced he's transferring." (stated flatly)</li></ul>
<div class=sub>Logistics / questions</div>
<ul class=neu><li>"Anyone have a spare ticket for the opener?"</li><li>"What channel is the game on?"</li></ul>
<div class=sub>Balanced / neutral analysis</div>
<ul class=neu><li>"Happy we won, but the run defense is still a concern." (cancels out)</li><li>"They run a lot of two-high looks under this DC."</li><li>"He's a 4-star from Texas who played both ways in HS."</li></ul>
</div>

<div class=rule>
<h2>&#x26A0;&#xFE0F; Tricky cases</h2>
<ul class=rule>
<li><b>Sarcasm</b> &mdash; judge the real meaning + tap Sarcastic: "Oh fantastic, another 3-and-out &#x1F644;" &rarr; <em>Negative</em></li>
<li><b>Factual bad/good news</b> &rarr; Neutral. "QB out 3 weeks." &rarr; <em>Neutral</em>. But "HUGE get!!" &rarr; <em>Positive</em>.</li>
<li><b>Mixed</b> &rarr; overall lean. "Defense carried us, offense looked lost &mdash; but a W is a W." &rarr; <em>lean Positive</em>.</li>
<li><b>About an opponent</b> &rarr; label toward the <b>team shown</b>. "[Michigan shown] OSU's secondary is trash, we'll torch them" &rarr; <em>Positive</em> (about Michigan).</li>
<li><b>Loaded question</b> &rarr; by implication. "Why is our OC still employed?" &rarr; <em>Negative</em>. "What time's kickoff?" &rarr; <em>Neutral</em>.</li>
<li><b>Off-topic</b> (not team football) &rarr; flag, no sentiment. "Anyone know a good plumber?" / "Selling 2 tickets, DM me."</li>
</ul>
</div>

<h2>&#x1F4D6; CFB slang cheat-sheet (what the old tool got wrong)</h2>
<table>
<tr><td>"he's <b>him</b>" / "<b>different</b>"</td><td>elite, special</td><td class=g>GOOD</td></tr>
<tr><td>"<b>nasty / filthy / sick / insane / dirty</b>"</td><td>impressive play/player</td><td class=g>GOOD</td></tr>
<tr><td>"<b>cooking</b>" / "a <b>problem</b>" / "<b>dawg</b>"</td><td>dominating / great</td><td class=g>GOOD</td></tr>
<tr><td>"<b>bag secured</b>"</td><td>got paid / recruited well</td><td class=g>GOOD</td></tr>
<tr><td>"<b>cooked / washed / done</b>"</td><td>declining / finished</td><td class=r>BAD</td></tr>
<tr><td>"<b>mid</b>"</td><td>mediocre</td><td class=r>BAD</td></tr>
<tr><td>"<b>fraud(s)</b>" / "<b>copium</b>"</td><td>overrated / delusional hope</td><td class=r>BAD</td></tr>
<tr><td>"<b>fumbled the bag</b>" / "<b>choked</b>"</td><td>botched it / blew it</td><td class=r>BAD</td></tr>
<tr><td>"<b>fire [name]</b>" / "<b>rebuild</b>"</td><td>wants coach gone / no hope</td><td class=r>BAD</td></tr>
</table>
<p style="color:var(--mut);font-size:13px">"nasty," "filthy," "sick," "insane," "dirty" are almost always <b>compliments</b> in football. The old VADER tool read them as negative &mdash; a big reason we're upgrading it.</p>
<p><a href="/">&larr; back to labeling</a></p>
</div></body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def log_message(self, *a):
        pass

    def do_GET(self):
        db = sqlite3.connect(LABELS_DB)
        try:
            if self.path == "/" or self.path.startswith("/index"):
                body = HTML.encode()
                self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            elif self.path == "/guide" or self.path.startswith("/guide"):
                body = GUIDE_HTML.encode()
                self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            elif self.path == "/api/next":
                self._json(next_item(db))
            elif self.path == "/api/progress":
                self._json(progress(db))
            elif self.path == "/api/stats":
                self._json(stats(db))
            else:
                self._json({"error": "not found"}, 404)
        finally:
            db.close()

    def do_POST(self):
        ln = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(ln) or b"{}")
        db = sqlite3.connect(LABELS_DB)
        try:
            if self.path == "/api/label":
                import datetime
                db.execute("insert or replace into labels(doc_id,label,sarcastic,offtopic,ts) values(?,?,?,?,?)",
                           (data["id"], data["label"], data.get("sarcastic", 0), data.get("offtopic", 0),
                            datetime.datetime.now().isoformat(timespec="seconds")))
                db.commit(); self._json(progress(db))
            elif self.path == "/api/undo":
                db.execute("delete from labels where doc_id=?", (data["id"],)); db.commit(); self._json({"ok": True})
            else:
                self._json({"error": "not found"}, 404)
        finally:
            db.close()


def main():
    db = init_labels_db()
    print("[labeler] building comment queue (one-time)...", flush=True)
    build_queue(db)
    p = progress(db)
    db.close()
    print(f"[labeler] queue ready: {p['total']} comments ({p['done']} already labeled)", flush=True)
    url = f"http://127.0.0.1:{PORT}"
    print(f"[labeler] open {url}  (Ctrl+C here to stop)", flush=True)
    try:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    except Exception:
        pass
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("127.0.0.1", PORT), Handler) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    main()
