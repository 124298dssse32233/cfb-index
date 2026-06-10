"""Re-measure on CLEAN (football-subreddit-only) data — the earlier mood-impact
was contaminated by ~72% city/campus off-topic noise.

Reports, restricted to football subreddits:
  * real football-comment coverage per team
  * offseason team-weeks that clear the >=12 gate on FOOTBALL data (true coverage)
  * VADER vs encoder mood on clean data (net excl-neutral) + spread
READ-ONLY.  Run: .venv\\Scripts\\python.exe scripts\\sentiment_clean_impact.py
"""
import os, sqlite3, statistics as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db = sqlite3.connect(f"file:{os.path.join(ROOT,'cfb_rankings.db')}?mode=ro", uri=True)
FOOTBALL = ("MichiganWolverines", "fsusports", "ducks", "CFB", "rolltide",
            "LonghornNation", "georgiabulldogs", "LSUFootball")
MIN = 12
ph = ",".join("?" * len(FOOTBALL))


def mood(net, n):
    return max(0, min(100, round(50 + 50 * net * min(1.0, n / 50.0))))


print("=== football-only corpus size ===")
tot = db.execute(f"""select count(*) from conversation_document_targets t
  join conversation_documents d on d.conversation_document_id=t.conversation_document_id
  where t.target_type='team' and t.sentiment_label is not null and d.source_subchannel in ({ph})""", FOOTBALL).fetchone()[0]
print(f"  football team-target rows: {tot}")

print("\n=== football comments per team (top 20) ===")
for slug, c in db.execute(f"""select tm.slug, count(*) c
  from conversation_document_targets t
  join conversation_documents d on d.conversation_document_id=t.conversation_document_id
  join teams tm on tm.team_id=t.team_id
  where t.target_type='team' and t.sentiment_label is not null and d.source_subchannel in ({ph})
  group by t.team_id order by c desc limit 20""", FOOTBALL).fetchall():
    print(f"  {slug:16s} {c}")

print("\n=== offseason team-weeks clearing >=12 on FOOTBALL data (true mood coverage) ===")
rows = db.execute(f"""
  select tm.slug, m.week_start_date,
         t.sentiment_label as vader, s.pol_label as enc
  from conversation_document_targets t
  join conversation_documents d on d.conversation_document_id=t.conversation_document_id
  join teams tm on tm.team_id=t.team_id
  join offseason_week_map m on m.season_year=t.season_year and m.offseason_week=t.week
  left join sentiment_v2_staging s on s.conversation_document_id=t.conversation_document_id
  where t.target_type='team' and t.sentiment_label is not null and d.source_subchannel in ({ph})
""", FOOTBALL).fetchall()
agg = {}
for slug, wk, vader, enc in rows:
    a = agg.setdefault((slug, wk), {"vp":0,"vn":0,"vt":0,"ep":0,"en":0,"et":0})
    a["vt"]+=1; a["vp"]+= vader=="positive"; a["vn"]+= vader=="negative"
    if enc: a["et"]+=1; a["ep"]+= enc=="positive"; a["en"]+= enc=="negative"
qualifying = [(k,a) for k,a in agg.items() if a["vt"]>=MIN]
print(f"  offseason football team-weeks with >=12: {len(qualifying)}  (distinct teams: {len({k[0] for k,_ in qualifying})})")
mv, me = [], []
print("  team-week | n | mood VADER | mood encoder(excl-neu)")
for (slug,wk),a in sorted(qualifying, key=lambda x:-x[1]['vt'])[:25]:
    netv=(a["vp"]-a["vn"])/a["vt"]; Mv=mood(netv,a["vt"]); mv.append(Mv)
    pol=a["ep"]+a["en"]
    if a["et"]>=MIN and pol:
        nete=(a["ep"]-a["en"])/pol; Me=mood(nete,a["et"]); me.append(Me)
    else: Me="n/a"
    print(f"  {slug:14s} {wk} | {a['vt']:<4} | {Mv:<3} | {Me}")
if mv: print(f"\n  VADER mood spread: mean={st.mean(mv):.1f} stdev={st.pstdev(mv):.1f}")
if me: print(f"  encoder(excl-neu) spread: mean={st.mean(me):.1f} stdev={st.pstdev(me):.1f}")
db.close()
