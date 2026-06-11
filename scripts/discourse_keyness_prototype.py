"""Prototype of the Language Layer keyness engine (fan_lexicon_brief.md). v2.

Computes, with REAL corpus data, the inputs for the flagship mockup:
  1. Team Lexicon       — weighted log-odds (informative Dirichlet prior) vs corpus
  2. Seasons Strip      — per-season distinctive words for Michigan (2022->2026)
  3. Player Descriptors — distinctive words in +/-8 token windows around a player name
  4. Rivalry Mirror     — Michigan-fans-on-OSU vs OSU-fans-on-Michigan (windowed)
  5. Personality        — real percentile sliders from existing emotion/sarcasm fields
  6. Word of the Week   — last 7 days vs prior 28 (fan voice only)

v2 fixes (validated against v1 output):
  - fan-voice sources only (reddit/bluesky/youtube/board) — kills podcast ad-reads
    ("fanduel", "joinsubtext") and news bylines ("isaiah hole" is a Wolverines
    Wire WRITER, not fan language)
  - Stage-1 lexical relevance gate (ingest.relevance.score_text) — kills city-sub
    noise ("dispatch", "dublin", "events calendar")
  - html.unescape + URL strip — kills "nbsp", "https joinsubtext"
  - hand-curated structural alias exclusion (team_aliases only holds the school
    name) — nicknames/cities/possessives out, CULTURE stays ("blue", "autzen")
  - mirror = +/-12 token windows around rival mentions, not whole docs
  - player descriptors filter roster names (teammates) + structural aliases

Output: logs/_language_layer_proto.json  (consumed by the HTML mockup)

Run: .venv\\Scripts\\python.exe scripts\\discourse_keyness_prototype.py
"""
from __future__ import annotations

import html
import json
import math
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from cfb_rankings.ingest.relevance import score_text  # noqa: E402

DB = ROOT / "cfb_rankings.db"
OUT = ROOT / "logs" / "_language_layer_proto.json"

FOCUS_TEAMS = {293: "Michigan", 195: "Ohio State", 291: "Oregon"}
MIRROR = (293, 195)  # Michigan <-> Ohio State
PLAYER_NAME = "Bryce Underwood"
PLAYER_TEAM_ID = 293
MIN_TEAM_DOCS_FOR_PERSONALITY = 300

ALPHA0 = 500.0
Z_FLOOR = 1.96
MIN_COUNT = 10

FAN_SOURCE_SQL = ("(d.source_name like 'reddit%' or d.source_name like 'bluesky%' "
                  "or d.source_name like 'youtube%' or d.source_name like 'board%') "
                  # City subreddits are residents, not fans: r/Columbus is 18.6k
                  # of OSU's 21.6k docs and is why v2 surfaced "kroger"/"dublin".
                  "and coalesce(d.source_subchannel,'') "
                  "not in ('Columbus','Eugene','AnnArbor')")

# Structural identifiers: team name / nickname / city / possessives. These are
# trivially the "most distinctive" words and tell fans nothing. Cultural terms
# ("blue", "autzen", "harbaugh") deliberately stay IN.
STRUCTURAL: dict[int, set[str]] = {
    293: {"michigan", "michigan's", "wolverine", "wolverines", "wolverines'",
          "umich", "ann", "arbor", "ann arbor", "mich", "uofm", "u m"},
    195: {"ohio", "ohio's", "state", "state's", "ohio state", "buckeye",
          "buckeyes", "buckeyes'", "osu's", "columbus", "tosu", "thee"},
    291: {"oregon", "oregon's", "duck", "ducks", "ducks'", "eugene", "uo",
          "springfield", "portland"},
}
# rival-mention aliases for the mirror (what counts as "talking about them")
RIVAL_ALIASES: dict[int, list[str]] = {
    293: ["michigan", "wolverines", "wolverine", "umich", "scum", "ttun",
          "team up north"],
    195: ["ohio state", "buckeyes", "buckeye", "osu", "tosu", "suckeyes"],
}

JUNK = set("""
https http www com org reddit wiki comments thread threads poll view amp gt lt
nbsp x200b deleted removed url link sub subreddit post posts mod mods upvote
downvote edit tldr imo imho btw faq megathread crosspost discord
""".split())

_WORD_RE = re.compile(r"[a-z][a-z']+")
_URL_RE = re.compile(r"http\S+|www\.\S+")

STOPWORDS = set("""
a about above after again against all am an and any are aren't as at be because
been before being below between both but by can't cannot could couldn't did
didn't do does doesn't doing don't down during each few for from further had
hadn't has hasn't have haven't having he he'd he'll he's her here here's hers
herself him himself his how how's i i'd i'll i'm i've if in into is isn't it
it's its itself let's me more most mustn't my myself no nor not of off on once
only or other ought our ours ourselves out over own same shan't she she'd
she'll she's should shouldn't so some such than that that's the their theirs
them themselves then there there's these they they'd they'll they're they've
this those through to too under until up very was wasn't we we'd we'll we're
we've were weren't what what's when when's where where's which while who who's
whom why why's with won't would wouldn't you you'd you'll you're you've your
yours yourself yourselves will just also got get like one even still really
much can say said says know think going go gonna way make made want see right
yeah lol yes well thing things actually never always people year years guy
guys time game games team teams play played playing player players season
fans fan football week today day's
""".split()) | JUNK


def clean(text: str) -> str:
    return _URL_RE.sub(" ", html.unescape(text or ""))


def tokenize(text: str) -> list[str]:
    return [t for t in _WORD_RE.findall(text.lower())
            if t not in STOPWORDS and len(t) >= 3 and not t.startswith("'")]


def grams(tokens: list[str]) -> list[str]:
    out = list(tokens)
    out.extend(f"{a} {b}" for a, b in zip(tokens, tokens[1:]))
    return out


def log_odds(counts_a: Counter, n_a: int, counts_b: Counter, n_b: int,
             prior: Counter, n_prior: int,
             min_count: int = MIN_COUNT, top: int = 40) -> list[dict]:
    results = []
    for w, ca in counts_a.items():
        if ca < min_count:
            continue
        cb = counts_b.get(w, 0)
        aw = ALPHA0 * prior.get(w, 0) / max(n_prior, 1)
        if aw <= 0:
            aw = 0.01
        la = math.log((ca + aw) / (n_a + ALPHA0 - ca - aw))
        lb = math.log((cb + aw) / (n_b + ALPHA0 - cb - aw))
        delta = la - lb
        var = 1.0 / (ca + aw) + 1.0 / (cb + aw)
        z = delta / math.sqrt(var)
        if z < Z_FLOOR:
            continue
        rate_a = ca / max(n_a, 1)
        rate_b = max(cb, 0.5) / max(n_b, 1)
        ratio = rate_a / rate_b
        results.append({"term": w, "count": ca, "count_rest": cb,
                        "z": round(z, 2), "ratio": round(ratio, 1),
                        "log2_ratio": round(math.log2(ratio), 2)})
    results.sort(key=lambda r: -r["z"])
    return results[:top]


def drop_structural(res: list[dict], team_id: int, top: int) -> list[dict]:
    ex = STRUCTURAL.get(team_id, set())
    return [r for r in res
            if r["term"] not in ex
            and not any(w in ex for w in r["term"].split())][:top]


def main() -> None:
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)

    print("pass 1: streaming fan-voice corpus (relevance-gated) ...")
    focus_docs: dict[int, set[int]] = defaultdict(set)
    for did, tid in con.execute(
            "select conversation_document_id, team_id from conversation_document_targets "
            "where target_type='team' and team_id in (%s)" %
            ",".join(str(t) for t in FOCUS_TEAMS)):
        focus_docs[did].add(tid)

    global_uni: Counter = Counter()
    team_counts: dict[int, Counter] = {t: Counter() for t in FOCUS_TEAMS}
    team_tokens: dict[int, int] = {t: 0 for t in FOCUS_TEAMS}
    team_doc_n: dict[int, int] = {t: 0 for t in FOCUS_TEAMS}
    n_global = 0
    season_counts: dict[int, Counter] = defaultdict(Counter)
    season_tokens: dict[int, int] = defaultdict(int)
    n_docs = n_gated = 0

    cur = con.execute(
        "select d.conversation_document_id, "
        "coalesce(d.title_text,'') || ' ' || coalesce(d.body_text,''), "
        "substr(coalesce(d.external_created_at_utc,''),1,10) "
        f"from conversation_documents d "
        f"where coalesce(d.is_deleted,0)=0 and coalesce(d.is_removed,0)=0 "
        f"and (d.body_text is not null or d.title_text is not null) "
        f"and {FAN_SOURCE_SQL}")
    for did, text, day in cur:
        text = clean(text)
        if not score_text(text).is_football:
            n_gated += 1
            continue
        toks = tokenize(text)
        if not toks:
            continue
        gs = grams(toks)
        n_docs += 1
        n_global += len(gs)
        global_uni.update(gs)
        if did in focus_docs:
            for tid in focus_docs[did]:
                team_counts[tid].update(gs)
                team_tokens[tid] += len(gs)
                team_doc_n[tid] += 1
                if tid == 293 and len(day) == 10:
                    y, m = int(day[:4]), int(day[5:7])
                    season = y if m >= 7 else y - 1
                    season_counts[season].update(toks)
                    season_tokens[season] += len(toks)
        if n_docs % 40000 == 0:
            print(f"  {n_docs} docs kept ({n_gated} gated) vocab={len(global_uni)}")
    print(f"  done: {n_docs} kept, {n_gated} relevance-gated, "
          f"vocab {len(global_uni)}, tokens {n_global}")

    out: dict = {"corpus": {"docs": n_docs, "gated": n_gated,
                            "tokens": n_global},
                 "teams": {}}

    # ---- 1. Team Lexicons ----
    for tid, name in FOCUS_TEAMS.items():
        rest = Counter(global_uni)
        rest.subtract(team_counts[tid])
        n_rest = n_global - team_tokens[tid]
        res = log_odds(team_counts[tid], team_tokens[tid], rest, n_rest,
                       global_uni, n_global, top=150)
        res = drop_structural(res, tid, 30)
        out["teams"][name] = {"docs": team_doc_n[tid],
                              "tokens": team_tokens[tid], "lexicon": res}
        print(f"lexicon {name}: " + ", ".join(r['term'] for r in res[:14]))

    # ---- 2. Seasons strip (Michigan) ----
    mich_all: Counter = Counter()
    for c in season_counts.values():
        mich_all.update(c)
    n_mich_all = sum(season_tokens.values())
    decade = {}
    for season in sorted(season_counts):
        if season_tokens[season] < 8000:
            continue
        rest = Counter(mich_all)
        rest.subtract(season_counts[season])
        res = log_odds(season_counts[season], season_tokens[season],
                       rest, n_mich_all - season_tokens[season],
                       mich_all, n_mich_all, min_count=6, top=40)
        res = drop_structural(res, 293, 10)
        decade[season] = res
        print(f"season {season} ({season_tokens[season]} toks): "
              + ", ".join(r['term'] for r in res[:6]))
    out["decade_michigan"] = decade

    # ---- 3. Player descriptors ----
    prow = con.execute(
        "select player_id from conversation_document_targets "
        "where target_type='player' and target_label=? "
        "group by 1 order by count(*) desc limit 1", (PLAYER_NAME,)).fetchone()
    roster_names: set[str] = set()
    for (label,) in con.execute(
            "select distinct target_label from conversation_document_targets "
            "where target_type='player' and target_label is not null"):
        roster_names.update(w for w in label.lower().split() if len(w) >= 3)
    roster_names -= {PLAYER_NAME.split()[0].lower(), PLAYER_NAME.split()[-1].lower()}

    player_block = {"name": PLAYER_NAME, "docs": 0, "descriptors": [], "quotes": []}
    if prow:
        pid = prow[0]
        doc_ids = [r[0] for r in con.execute(
            "select distinct conversation_document_id from conversation_document_targets "
            "where target_type='player' and player_id=?", (pid,))]
        player_block["docs"] = len(doc_ids)
        first = PLAYER_NAME.split()[0].lower()
        last = PLAYER_NAME.split()[-1].lower()
        ex = STRUCTURAL.get(PLAYER_TEAM_ID, set()) | {first, last}
        win: Counter = Counter()
        n_win = 0
        quotes = []
        for i in range(0, len(doc_ids), 500):
            chunk = doc_ids[i:i + 500]
            q = ",".join("?" * len(chunk))
            for (text,) in con.execute(
                    f"select coalesce(title_text,'') || ' ' || coalesce(body_text,'') "
                    f"from conversation_documents d "
                    f"where conversation_document_id in ({q}) and {FAN_SOURCE_SQL}",
                    chunk):
                text = clean(text)
                raw = _WORD_RE.findall(text.lower())
                for j, t in enumerate(raw):
                    if t == last:
                        lo, hi = max(0, j - 8), j + 9
                        wtoks = [w for w in raw[lo:hi]
                                 if w not in STOPWORDS and len(w) >= 3
                                 and w not in ex and w not in roster_names]
                        win.update(wtoks)
                        n_win += len(wtoks)
                cl = re.sub(r"\s+", " ", text).strip()
                if 40 < len(cl) < 220 and last in cl.lower() and len(quotes) < 60:
                    quotes.append(cl)
        res = log_odds(win, n_win, global_uni, n_global,
                       global_uni, n_global, min_count=5, top=30)
        player_block["descriptors"] = res
        player_block["quotes"] = quotes[:14]
        print(f"player {PLAYER_NAME} ({len(doc_ids)} docs): "
              + ", ".join(r['term'] for r in res[:12]))
    out["player"] = player_block

    # ---- 4. Rivalry mirror (windowed) ----
    a_id, b_id = MIRROR

    # all-school-name tokens: windows around rival mentions pick up list-posts
    # ("Texas, Oklahoma, Michigan...") — strip every school name so what's left
    # is the actual language about the rival, not co-mentioned teams.
    school_words: set[str] = set()
    for (nm, slug) in con.execute("select school_name, slug from teams"):
        for w in (nm or "").lower().split() + (slug or "").split("-"):
            if len(w) >= 3:
                school_words.add(w)

    def rival_windows(team_id: int, rival_id: int):
        rival_terms = RIVAL_ALIASES[rival_id]
        ex = (STRUCTURAL.get(team_id, set()) | STRUCTURAL.get(rival_id, set())
              | set(w for a in rival_terms for w in a.split()) | school_words)
        cnt: Counter = Counter()
        n = 0
        quotes: list[str] = []
        pats = [re.compile(r"\b" + re.escape(a) + r"\b") for a in rival_terms]
        cur = con.execute(
            "select coalesce(d.title_text,'') || ' ' || coalesce(d.body_text,'') "
            "from conversation_documents d "
            "join conversation_document_targets t "
            "  on t.conversation_document_id = d.conversation_document_id "
            f"where t.target_type='team' and t.team_id=? "
            f"  and coalesce(d.is_deleted,0)=0 and coalesce(d.is_removed,0)=0 "
            f"  and {FAN_SOURCE_SQL}", (team_id,))
        for (text,) in cur:
            text = clean(text)
            low = text.lower()
            if not any(p.search(low) for p in pats):
                continue
            raw = _WORD_RE.findall(low)
            hit_idx = [j for j, t in enumerate(raw)
                       if any(p.fullmatch(t) for p in pats)
                       or t in ("osu", "tosu", "ttun", "scum")]
            # token-level rival hits (multiword aliases approximated by last word)
            for j, t in enumerate(raw):
                if t in ("buckeyes", "buckeye", "osu", "tosu", "suckeyes",
                         "wolverines", "wolverine", "umich", "ttun", "scum"):
                    hit_idx.append(j)
            seen: set[int] = set()
            for j in hit_idx:
                for k in range(max(0, j - 12), min(len(raw), j + 13)):
                    if k in seen:
                        continue
                    seen.add(k)
                    w = raw[k]
                    if w not in STOPWORDS and len(w) >= 3 and w not in ex:
                        cnt[w] += 1
                        n += 1
            cl = re.sub(r"\s+", " ", text).strip()
            if 40 < len(cl) < 200 and len(quotes) < 40:
                quotes.append(cl)
        return cnt, n, quotes

    print("mirror: scanning fan docs ...")
    ca, na, qa = rival_windows(a_id, b_id)
    cb, nb, qb = rival_windows(b_id, a_id)
    out["mirror"] = {
        "a": {"team": FOCUS_TEAMS[a_id], "tokens": na,
              "terms": log_odds(ca, na, cb, nb, global_uni, n_global,
                                min_count=5, top=20),
              "quotes": qa[:10]},
        "b": {"team": FOCUS_TEAMS[b_id], "tokens": nb,
              "terms": log_odds(cb, nb, ca, na, global_uni, n_global,
                                min_count=5, top=20),
              "quotes": qb[:10]},
    }
    print("mirror A: " + ", ".join(r['term'] for r in out['mirror']['a']['terms'][:10]))
    print("mirror B: " + ", ".join(r['term'] for r in out['mirror']['b']['terms'][:10]))

    # ---- 5. Personality percentiles (fan-voice sources only) ----
    rows = con.execute(f"""
        select t.team_id, tm.school_name,
               count(*) n,
               avg(t.sentiment_score) sent,
               avg(case when t.emotion_primary in ('joy','optimism') then 1.0 else 0 end) joy,
               avg(case when t.emotion_primary in ('anger','disgust') then 1.0 else 0 end) anger,
               avg(case when t.emotion_primary in ('fear','sadness','pessimism') then 1.0 else 0 end) doom,
               avg(coalesce(t.sarcasm_score,0)) sarcasm
          from conversation_document_targets t
          join teams tm on tm.team_id = t.team_id
          join conversation_documents d
            on d.conversation_document_id = t.conversation_document_id
         where t.target_type='team' and {FAN_SOURCE_SQL}
         group by 1 having n >= ?""", (MIN_TEAM_DOCS_FOR_PERSONALITY,)).fetchall()

    def pct_rank(vals, v):
        return round(100 * sum(1 for x in vals if x < v) / max(len(vals) - 1, 1))

    cols = {"sent": 3, "joy": 4, "anger": 5, "doom": 6, "sarcasm": 7}
    series = {k: [r[i] for r in rows] for k, i in cols.items()}
    personality = {}
    for r in rows:
        if r[1] in FOCUS_TEAMS.values():
            personality[r[1]] = {
                "n_mentions": r[2],
                "optimism_pct": pct_rank(series["sent"], r[3]),
                "joy_pct": pct_rank(series["joy"], r[4]),
                "anger_pct": pct_rank(series["anger"], r[5]),
                "doom_pct": pct_rank(series["doom"], r[6]),
                "sarcasm_pct": pct_rank(series["sarcasm"], r[7]),
            }
    out["personality"] = {"teams_ranked": len(rows), "focus": personality}
    print(f"personality over {len(rows)} teams")

    # ---- 6. Word of the week (fan voice, relevance-gated) ----
    today = date(2026, 6, 10)
    d7 = (today - timedelta(days=7)).isoformat()
    d35 = (today - timedelta(days=35)).isoformat()
    recent: Counter = Counter()
    base: Counter = Counter()
    n_recent = n_base = 0
    for text, day in con.execute(
            "select coalesce(d.title_text,'') || ' ' || coalesce(d.body_text,''), "
            "substr(coalesce(d.external_created_at_utc,''),1,10) "
            "from conversation_documents d "
            f"where d.external_created_at_utc >= ? and {FAN_SOURCE_SQL} "
            "and coalesce(d.is_deleted,0)=0 and coalesce(d.is_removed,0)=0", (d35,)):
        text = clean(text)
        if not score_text(text).is_football:
            continue
        gs = grams(tokenize(text))
        if day >= d7:
            recent.update(gs)
            n_recent += len(gs)
        else:
            base.update(gs)
            n_base += len(gs)
    wow = log_odds(recent, n_recent, base, n_base, global_uni, n_global,
                   min_count=8, top=15)
    out["word_of_week"] = {"recent_tokens": n_recent, "base_tokens": n_base,
                           "terms": wow}
    print("word of week: " + ", ".join(r['term'] for r in wow[:10]))

    con.close()
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
