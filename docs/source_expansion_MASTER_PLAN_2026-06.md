# CFB Source Expansion Master Plan (June 2026)

**Prepared June 10, 2026. Ground rules:** solo dev, 24/7 Windows box (RTX 3090), Python → SQLite → static Vercel site, nightly GPU window, **hard budget $0–30/mo (target spend: $0)**. Everything below maps onto the existing `SourceAdapter` / `BaseRssAdapter` framework writing to `conversation_documents`, driven by `priority_teams`. The single most important finding to internalize: **the Round-1 Reddit plan (100 QPM OAuth) is dead** — Reddit closed self-service app creation in Nov 2025 and approval for hobbyist scripts is "essentially zero" ([Responsible Builder Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy), [r/redditdev consensus](https://www.reddit.com/r/redditdev/comments/1tsv4h5/)). Unauthenticated `.json` returns 403 from our own box; `.rss` returns 200. **Our Reddit collection has silently degraded to its RSS fallback and the comment path is almost certainly broken — the 139k docs/30d figure is presumed stale until audited.** The plan below replaces Reddit-as-backbone with a four-pillar portfolio: **Reddit-RSS + Arctic Shift listings, YouTube comments, podcast transcripts, and boards/Bluesky/Threads** — all $0.

Note on team count: the 2026 FBS universe is **138 teams** (NDSU → MW and Sacramento State → MAC joined Delaware/Missouri State; Texas State → rebuilt Pac-12; UTEP/NIU/Hawaii → MW). Headers below say "134" per the brief; all seeding targets 138.

---

## 1. The 2026 CFB context that shapes collection (calendar-aware collection windows, what to collect more of WHEN)

The single January transfer-portal window (Jan 2–16, [ESPN](https://www.espn.com/college-football/story/_/id/46524004/ncaa-adopts-jan-2-16-transfer-portal-window-fbs-fcs-26)) has re-concentrated the offseason: January is now the biggest non-gameday month, April lost its portal spike, spring games are a dying signal (17+ P4 programs gutted them — [SI](https://www.si.com/fannation/college/cfb-hq/news/new-spring-game-trend-is-a-disservice-to-college-football-fans)), and July gained two new tentpoles (EA CFB 27 release July 2–9 [EA](https://news.ea.com/press-releases/press-releases-details/2026/EA-SPORTS-College-Football-27-Reveals-Cover-Athletes-Celebrating-The-Next-Generation-of-Football-Stars/default.aspx); July 4 commitment weekend [CBS](https://www.cbssports.com/college-football/news/forget-signing-day-how-the-fourth-of-july-commitment-weekend-shifted-the-landscape-and-rankings-in-2026/)).

**Mechanism:** populate the existing `calendar_pressure` table (already shipped in the chronicle migrations) with `(event_date, event_type, boost_factor, team_scope)` rows through Feb 2027, and make `tools/run_adapter.py` read it to multiply per-adapter polling cadence. All dates below are known today — this is a one-evening data-entry task, not engineering.

| Window | Volume | Driver | Collection posture |
|---|---|---|---|
| **Now–Jun 21** | MED-HIGH (recruiting verticals) | Official-visit weekends; CFP governance June meeting; EA reveal fallout | Boost recruiting-adjacent feeds (Google News per-team recruiting queries, YouTube fan channels); per-team visit weekends |
| **Jun 22–Jul 31** | MED | Recruiting dead period → speculation talk | Baseline; this is the build window — ship the adapters in §4 now, while volume is low |
| **Jul 2–9** | HIGH (casual spike) | EA CFB 27 early access → worldwide release, first PC release | Boost YouTube national + r/NCAAFBseries-adjacent talk; per-team player-ratings outrage is a sentiment goldmine |
| **Jul 4 weekend** | HIGH | Commitment-weekend tentpole | Max cadence on recruiting feeds + team subs of contending classes (A&M, Miami, ND per [ESPN](https://www.espn.com/college-football/recruiting/story/_/id/48911285/college-football-recruiting-2026-summer-intel-commits-flips-winners-visits)) |
| **Jul 7–30** | MED-HIGH rolling | Media days: Big 12 Jul 7–8, ACC Jul 15–17, SEC Jul 20–23, B1G Jul 28–30 ([Yahoo](https://sports.yahoo.com/articles/power-four-finalize-2026-college-021207468.html)) | Stagger per-conference team boosts to match each slot |
| **Aug** | MED-HIGH ramp | Fall camp, QB battles; **Week 0 Aug 29** (UNC–TCU Dublin) | Ramp to in-season cadence; Jetstream `wantedDids` must be live by late Aug |
| **Sep–Nov** | WEEKLY HEARTBEAT | Sat games → **Sun/Mon reaction is the richest sentiment harvest**; Tue CFP rankings (Nov) | In-season cadence; tiered Saturday comment pulls; losers' boards spike harder than winners' |
| **Late Oct–Nov** | HIGH rolling | Coaching carousel (34 changes last cycle); hot seats pre-staged: Norvell, Fickell, Aranda, Beamer, Riley, Belichick ([Athlon](https://athlonsports.com/college-football/college-footballs-pre-spring-rankings-top-10-coaches-on-the-hot-seat-for-2026)) | Hot-seat watchlist rows in calendar_pressure with team_scope |
| **Nov 26–28** | EXTREME | Rivalry week | Max cadence + rivalry-pair keyword sets |
| **Dec 5–6** | EXTREME | Conference championships + **Selection Sunday = biggest argument day of the year** (P4 auto-bids regardless of rank sharpen the outrage — [CBS](https://www.cbssports.com/college-football/news/college-football-playoff-12-teams-2026-season-big-ten-sec/)) | Max cadence both days |
| Dec 4 / 12 / 18–19 | HIGH | Early signing period; Army–Navy + Heisman; CFP first round on campuses | Event-keyed boosts |
| **Jan 2–16, 2027** | EXTREME | Single portal window, 12:01am Jan 2 commits; overlaps CFP semis | Max-frequency polling; portal keyword expansion |
| **Jan 25, 2027** | EXTREME | Title game, Allegiant Stadium ([ESPN](https://www.espn.com/college-football/story/_/id/48958840/2026-college-football-playoff-bowl-schedule-46-games)) | Game-day cadence + 5-day finalist portal window after |

**Two hygiene items with hard deadlines:**
1. **Realignment before July 1**: update conference fields for ~12 teams (Pac-12 = 8 members; MW backfill UTEP/NIU/Hawaii/NDSU; Sac State → MAC) or every conference-level aggregation is wrong for the season.
2. **Classifier vocabulary refresh**: seed the relevance/sentiment stack with the structural-era lexicon — "rev-share," "NIL Go," "associated entity," "cap circumvention," player "buyout," "5+11," "24-team," "CSC" — plus 2026 narrative anchors (Kiffin-LSU, Mensah case, Sorsby betting saga, Indiana repeat, Arch/CJ Carr Heisman race).

**What to collect more of, when, in one line:** recruiting verticals in June/early July, EA + media-day casual talk in July, game-reaction (Sun/Mon) Sept–Nov, carousel boards Oct–Nov, and everything at max from Dec 5 through Jan 25.

---

## 2. Source portfolio decision — the full ranked list

Verdicts: **KEEP-EXPAND** (working today, scale it) / **ADD-NOW** (build this summer) / **ADD-LATER** (in-season or gated) / **SKIP**.

| # | Source | Verdict | One-line reason | Cost | ToS status |
|---|---|---|---|---|---|
| 1 | **YouTube comments (national + per-team)** | **ADD-NOW** | Biggest unexploited fan-opinion pool: 5–15k comments/day offseason, 50–150k/day in season, at ~660 of 10,000 free daily quota units ([quota docs](https://developers.google.com/youtube/v3/determine_quota_cost)); registry rows already exist | $0 | Clean — official API; 247/On3 *YouTube channels* are permitted surface (YouTube API ToS, not their site ToS) |
| 2 | **Reddit via .rss + Arctic Shift listings** | **KEEP-EXPAND (rebuilt)** | OAuth path is dead for new apps; `.rss` works (verified 200 from our box) and Arctic Shift by-subreddit listing endpoints are alive and fresh ([Arctic Shift](https://arctic-shift.photon-reddit.com/)) — together they cover ~115 subs | $0 | Gray-but-defensible: RSS is published syndication; switch to honest UA; file the official ticket once as paper trail |
| 3 | **Per-team podcasts + local ASR** | **ADD-NOW** | Per-team by construction (Locked On 60+ college, 247Sports slate, Bleav, VOCFB, indies); discovery solved free by [Podcast Index API](https://podcastindex-org.github.io/docs-api/); 3090 runs faster-whisper at 10–30× realtime in the nightly window | $0 | Clean — open RSS is podcast-client behavior; store derived signals, don't republish transcripts |
| 4 | **Independent message boards (RSS wave)** | **ADD-NOW** | 20 verified-live feeds via 3 URL templates (XenForo `forums/-/index.rss`, Invision `{forum}.xml/`, phpBB `feed.php`) take board coverage 4 → ~24 fanbases; ToS sweeps clean on 12 big boards | $0 | Clean (published RSS); CoogFans low-frequency only (explicit anti-automation clause in [its ToS](https://www.coogfans.com/tos)) |
| 5 | **Bluesky (starter packs + CFB feed + Jetstream DIDs)** | **KEEP-EXPAND** | Works great today; +80–110 net-new live handles from 3 starter packs; the [andrewfleer CFB feed](https://bsky.app/starter-pack/redditcfb.com/3lazi46gmap2m) is a free curated firehose (~450 posts/day offseason); carries national-media layer + ~8–15 fanbases | $0 | Clean — public AppView, no auth |
| 6 | **Threads keyword-search API** | **ADD-NOW (register), build on approval** | The one genuinely new legal keyword firehose since Bluesky: server-side keyword search of public posts, free, 2,200 queries/rolling-24h ([Meta docs](https://developers.facebook.com/docs/threads/keyword-search/)) | $0 | Clean — official API, app review required |
| 7 | **Google News / campus papers / athletics / beat-writer / Substack RSS** | **KEEP-EXPAND** | Already working; the only thing wrong is 21 rows in `priority_teams` — mechanical expansion to 138 | $0 | Clean |
| 8 | **SB Nation team-blog article RSS** | **ADD-NOW (cheap)** | Every FBS-adjacent team has a blog; article RSS slots into the existing family; comments are off-limits but articles are per-team editorial signal | $0 | RSS clean; never touch Coral comments |
| 9 | **Prediction markets, Wikipedia, GDELT, SeatGeek** | **KEEP** | Working; no change | $0 | Clean |
| 10 | **Mastodon curated handles** | **ADD-NOW (1 hour)** | Near-zero yield but every account exposes `.rss`; ~1 hour of config | $0 | Clean |
| 11 | **Jetstream keyword firehose (raw)** | **ADD-LATER (in-season experiment)** | Offseason yield measured at ~0 of 8,319 posts; hashtags appear in <2% of CFB posts so keyword precision is poor — Saturday-only experiment once DID pipeline is live | $0 | Clean |
| 12 | **Twitch chat** | **ADD-LATER (Saturday burst, maybe)** | Real-CFB chat ≈ zero outside game windows; EA-game noise dominates; chat-log retention clause forces aggregate-only storage ([Twitch dev forum](https://discuss.dev.twitch.com/t/is-logging-twitch-chat-for-later-analysis-allowed/9416)) | $0 | Medium risk — aggregates only, no public raw-chat DB |
| 13 | **Discord (CFB Chat server)** | **ADD-LATER (one free pitch, build only on yes)** | Legally green via authorized bot (<100 servers = no Discord approval), but gated entirely on mod consent; ceiling ~3.5k concurrent users vs Reddit's millions | $0 | Clean **with consent**; never train on Discord text (Dev Policy §21) |
| 14 | **Reddit official Data API ticket** | **FILE ONCE, expect nothing** | Costs nothing, creates good-faith paper trail; approval odds ~zero ([r/redditdev](https://www.reddit.com/r/redditdev/comments/1ts6cuv/)) | $0 | Use the compliance-forward wording from the verification report (48h purge is real and is our strongest card) |
| 15 | **X/Twitter** | **SKIP** | Free tier dead; pay-per-use $0.005/read means $30 ≈ 200 reads/day ≈ 1.5 posts/team/day — <0.1% of corpus for 100% of budget ([pricing](https://docs.x.com/x-api/getting-started/pricing)) | n/a | Official path exists but is economically irrelevant |
| 16 | **247Sports / On3 / Rivals sites & boards** | **SKIP (permanent)** | ToS: no scraping, no AI training, no commercial — Round-1 ruling stands (their YouTube channels are the legal slice, covered in #1) | n/a | OFF LIMITS |
| 17 | **TikTok** | **SKIP** | Research API is academic/institution-only; oEmbed has no discovery/comments ([TechPolicy](https://www.techpolicy.press/the-problem-with-tiktoks-new-researcher-api-is-not-tiktok/)) | n/a | No legal hobbyist path |
| 18 | **Facebook public Groups** | **SKIP** | Groups API removed Apr 2024; Meta Content Library is institution-only ([TechCrunch](https://techcrunch.com/2024/02/05/meta-cuts-off-third-party-access-to-facebook-groups-leaving-developers-and-customers-in-disarray/)) | n/a | Dead |
| 19 | **Second-screen/watch-party apps** | **SKIP** | Category graveyard — Playback.tv dead Dec 2025, Spotify Live dead 2023 | n/a | n/a |
| 20 | **ESPN/SDS/open-web comments** | **SKIP** | ESPN removed comments ~2018; SDS has none (verified by fetch) | n/a | n/a |
| 21 | **Substack Notes, Nostr, Fizz** | **SKIP** | No official API / no CFB community / .edu-gated no-API respectively | n/a | n/a |

---

## 3. Coverage plan: 21 → 134 teams

**The thesis: no single source scales to 138 teams — the portfolio does.** Each team gets a different source mix, encoded in `priority_teams` columns, with a `collection_tier` deciding cadence. Use a `cli.py` subcommand to load seed data (never hand-edit the DB).

### New/extended `priority_teams` columns

| Column | Filled how | Scales to |
|---|---|---|
| `conference` (2026-updated) | Manual, from realignment facts above — **before July 1** | 138 |
| `collection_tier` (1/2/3) | Manual: Tier 1 = Elite Seven + narrative leaders (~22 teams: Miami, Indiana, Georgia, ND, Texas, Oregon, Ohio State, LSU, Michigan, Penn State, Alabama, USC, Ole Miss, Auburn, Texas Tech, FSU, Nebraska, UNC, Tennessee, A&M, Wisconsin, Duke — covers ~90% of June argument surface per the domain briefing); Tier 2 = rest of P4 + big G6 (~50); Tier 3 = long tail | 138 |
| `reddit_sub`, `reddit_mode` (`dedicated`/`school_flair`/`skip`), `reddit_flair_filter` | **Already done** — the census JSON in this brief + `_reddit_census/results.json` has the verified, collision-resolved pick per team. ~50 dedicated subs, ~65 school subs (filter by Sports/Athletics flair — this directly attacks the 70%-noise problem), ~20 `skip` (Kent State, CMU, EMU, ECU, etc.) | ~118 of 138 |
| `yt_official_channel_id`, `yt_fan_channel_ids` (JSON), `yt_uploads_playlist_id` | One-time: collect real URLs from Locked On directory (60+ college channels), [voiceofcfb.com/channels](https://voiceofcfb.com/channels/) (`@<Team>VOCFB`), Chat Sports, 247/On3 team channels; resolve handle→ID at zero quota via `"externalId":"UC…"` regex on channel HTML (validated on 28 channels), or `channels.list?forHandle` at 1 unit each. Uploads playlist = `UC`→`UU` swap, no call. **Never guess handles** (~60% miss rate measured) | 138 (every school has an official channel; ~80% have ≥1 fan/network channel) |
| `podcast_feed_urls` (JSON) | Discovery job: Podcast Index API query `"<team> football podcast"` per row, rank by episode recency; iTunes Search API fallback | ~138 (Locked On alone covers 60+) |
| `board_rss_url`, `board_platform` | Manual from the verified board census table (§4 build #5) | ~24 fanbases |
| `bluesky_handles` | Starter-pack harvest (~80–110 net-new live handles incl. per-team beats: Clarke/Oregon, Sauber/Penn State, Ferguson/Auburn) | National layer + 8–15 fanbases |
| `gnews_query`, `campus_paper_rss`, `athletics_rss`, `sbnation_rss` | Mechanical/manual expansion of the existing RSS families to all rows | 138 |
| `threads_keywords` (JSON) | Team name + coach name + 1–2 disambiguated nicknames; 2,200 queries/24h ÷ 138 teams ≈ 15 queries/team/day ceiling — run 2–4/team/day | 138 |

### Which sources scale where (the honest matrix)

- **All 138:** Google News RSS, YouTube (official + Locked On at minimum), podcasts, Threads keywords, SB Nation article RSS, athletics/campus RSS.
- **~118:** Reddit (50 dedicated + ~65 school-sub-with-flair; mark ~20 `reddit_skip` and route their weight to YouTube/podcasts/Google News — Reddit polling there is wasted budget).
- **~24:** independent boards (the SEC/southern fanbases that don't live on Reddit live exactly here — TigerDroppings/CougarBoard/CycloneFanatic etc., complementary by construction).
- **~8–15:** Bluesky per-team fan communities (Michigan, FSU, Auburn, LSU, Penn State, Oregon + a few).
- **Top-25-ish only:** deep comment-tree pulls, Tier-S chronicle treatment, hot-seat watchlists.

### Seed data plan
1. Load the Reddit census (this brief's JSON + `_reddit_census/results.json`) via a new `manage.py import-team-sources --csv` subcommand.
2. One supervised evening building the YouTube URL sheet (directories above), then a 138-iteration resolution script (~0–138 quota units, one-time).
3. Podcast Index discovery job writes candidates; you approve per team (LLM-assisted ranking by episode recency + title match).
4. Board/Bluesky/SBNation rows hand-entered from the census tables — ~150 rows total, one evening.

---

## 4. Build order (sequenced, with effort and expected yield)

Effort calibrated for a solo vibecoder with the adapter framework already in place. Items 0–2 are this week; 3–6 before July 31 (dead period = build window); 7–9 before Week 0 (Aug 29).

**0. Reddit pipeline health audit + honest-UA switch — 0.5 day. URGENT.**
Audit `conversation_documents` Reddit row counts and score/comment-count field completeness after 2026-05-30 (the `.json` shutoff date). Confirm `collect_reddit_comments_for_posts` is dead. Switch `RedditPublicClient` RSS path from the Chrome spoof to an honest UA (`windows:cfb-index-rss:v1.0 (by /u/<user>)`) — the spoof is the thing the RBP explicitly names as a violation. File the official Zendesk ticket once (form `14868593862164`) with the compliance-forward wording; plan as if the answer is no. *Gain: truth about current state; reduced ban risk.*

**1. `priority_teams` schema migration + census seed load — 1–2 days.**
New columns per §3, `import-team-sources` CLI subcommand, load Reddit census + conference realignment + `collection_tier`. Populate `calendar_pressure` through Feb 2027. *Gain: unlocks everything below; Google News/campus/athletics families immediately go 21 → 138 teams with zero new code.* **This is the coverage lever — everything else multiplies it.**

**2. Reddit rebuild: per-sub `.rss` sweep + Arctic Shift listing adapter — 1–2 days.**
(a) Extend the existing RSS family to poll `r/<sub>/new.rss` for all ~118 mapped subs at gentle cadence (offseason 2–4×/day; calendar-boosted in season), flair-filter school subs. (b) New `SourceAdapter` for Arctic Shift by-subreddit listing endpoints (alive, fresh, unauthenticated — and they carry scores + `num_comments` that RSS lacks); also spike the [monthly dump downloads](https://arctic-shift.photon-reddit.com/download-tool) for backfill (30 min). *Gain: restores Reddit to ~115-sub breadth with metadata; est. 2–4k docs/day in season. Dependency: #1.*

**3. YouTube adapters (`youtube_comments_nat` + `youtube_comments_team`) — 3–4 days.**
Fill the two registered-but-unbuilt adapters. Pipeline: `playlistItems.list` on UU playlists for upload detection (RSS feeds 404 from this box — do not design around them) → batched `videos.list` (50 IDs/unit) for `commentCount` triage → `commentThreads.list` (100/page) only where counts grew → `comments.list` reply expansion where `totalReplyCount > 5` → re-polls gated on commentCount delta. ~35 national channels (Tier-1/2 lists incl. Josh Pate `UCg-q_MDeWQrjizr1VPLEpYg` — 1.9K comments on one news video in 36h) + per-team channels from `yt_*` columns. Budget: ~660 units/day offseason, ~3,200 peak Saturday, vs 10,000 free. *Gain: 5–15k opinion-dense docs/day immediately — becomes our largest fan-opinion source on day one — 10× in season. Dependencies: #1 (yt columns), one evening of URL collection.*

**4. Board RSS wave (20 boards, 3 URL templates) — 1–2 days.**
Wire the verified-RSS top 20 into `BaseRssAdapter`: CanesInsight, CycloneFanatic, CougarBoard (official RSS page — best posture), SyracuseFan, HawkeyeNation, KillerFrogs, HuskerMax, StingTalk, Hardcore Husky, AllBuffs, GatorCountry, GopherHole, AUFamily, The Boneyard, BtownBanners, HornSports, CoogFans (1–2×/day max), TigerNet news feeds, SportsHawaii, Yosef's Cabin, GoMeanGreen, ZipsNation. Finish the Shaggy Bevo stub or swap to ShaggyTexas after a production-box re-test. *Gain: board coverage 4 → ~24 fanbases — and exactly the SEC/southern fanbases Reddit misses; est. 500–2k docs/day in season. No dependencies.*

**5. Bluesky expansion: starter-pack harvest + andrewfleer feed — 0.5–1 day.**
Ingest the three starter packs (/r/CFB 73, braggbobby ~95, Mandel 41) into curated handles (~80–110 net-new live, incl. beat writers); add a `getFeed` poller on the andrewfleer CFB feed (`at://did:plc:ipto52pfemju56wnsxkjcab5/app.bsky.feed.generator/aaacsiz7lqekw`, ~450 posts/day offseason). Reuses the existing AppView adapter, zero new infra. *Gain: roughly doubles Bluesky take; national-media sentiment layer complete. No dependencies.*

**6. Podcast discovery + ASR pipeline — 3–5 days (the one genuinely new subsystem).**
Discovery job (Podcast Index API, free key) populates `podcast_feed_urls`; `BaseRssAdapter` subclass ingests episode metadata + enclosure URLs; nightly faster-whisper pass (large-v3 ~10–15× realtime on the 3090) writes transcripts as `source_type='podcast_transcript'` so the sentiment stack can weight pundit-narrative separately from fan chatter. ~138 teams × ~2 eps/wk × ~1hr ≈ 38 audio-hrs/day ≈ 1.5–4 GPU-hrs/night — schedule before/after the sentiment pass. Validate ASR quality on Locked On rows we already index first. *Gain: per-team narrative coverage for ALL 138 teams incl. the 20 Reddit-dead ones; ~250–400 high-value docs/day. Dependencies: #1; GPU schedule juggling.*

**7. Threads keyword adapter — register the Meta app THIS WEEK (review takes days–weeks); build = 1–2 days on approval.**
`SourceAdapter` subclass querying `threads_keywords` per team within the 2,200/24h limit ([docs](https://developers.facebook.com/docs/threads/keyword-search/) — verify the real number post-approval; even the pessimistic 500/7d covers daily sweeps of ~70 team keywords). *Gain: the only server-side keyword search in the portfolio; est. 1–3k docs/day across 300M-MAU platform. Dependency: app approval (start the clock now).*

**8. Jetstream `wantedDids` mode — 1–2 days, deadline late August.**
Fill the registered `bluesky_firehose` stub in DID-filtered mode (server-side filtering by DID only — keyword filtering does not exist server-side), converting curated handles from nightly polling to real-time for gameday liveness. *Gain: latency, not volume. Dependency: #5 handle list.*

**9. Mastodon handles — 1 hour.** 2–3 account RSS rows (ACC Nation etc.) in the existing family. *Gain: tens of docs/month; do it because it's free.*

**10. In-season experiments (Sept+, only if capacity):** (a) one transparent pitch to CFB Chat mods (29.5k members; read-only bot, aggregate-only, privacy policy + opt-out) — build the `discord.py` adapter (1–2 days) only on a yes; (b) Twitch Saturday-burst collector on the collegefootball tag, aggregates only; (c) raw Jetstream keyword experiment on a Saturday with high-precision phrases (coach full names, `#iufb`-style tags).

**Net effect by Week 0:** from one healthy pillar (Bluesky) + one degraded one (Reddit) to **six healthy pillars covering all 138 teams**, est. offseason volume ~10–20k docs/day (vs ~5k today, mostly noise), in-season 60–170k/day — with the GPU pipeline, not any API, as the binding constraint. Total recurring cost: **$0/mo**.

---

## 5. Risk register

| Risk | Likelihood | Impact | Mitigation (wired to scrape_health/gate infra) |
|---|---|---|---|
| **Reddit kills `.rss` or blocks our IP** (it already killed `.json` ~May 30) | Medium | High — ~115-sub breadth lost | Honest UA + gentle cadence now; scrape_health per-source **row-count floor alerts** (alert if Reddit docs/day < 50% trailing-7d median); Arctic Shift listings as parallel channel; monthly dumps for backfill; YouTube/podcasts absorb the per-team load. Never re-spoof if the honest UA gets blocked — that's a reduce-dependence signal |
| **Silent degradation generally** (the Reddit lesson: we ran ~10 days degraded without noticing) | High (it already happened) | High | Generalize the lesson: scrape_health checks per adapter on (a) docs/day floor, (b) **field-completeness** (e.g. % rows with non-null score — would have caught May 30 instantly), (c) consecutive-failure gates feeding the existing automation-failure-issue path |
| **Arctic Shift disappears** (free third-party, RBP-unsanctioned) | Medium | Medium | Treat as enhancement, not dependency: `.rss` remains primary freshness channel; dump snapshots downloaded quarterly to local disk |
| **YouTube API key/project suspension or quota policy change** | Low | High — biggest single source | Strict ToS hygiene (no scraped comments, API-only); commentCount-delta gating keeps usage ~7% of quota; the zero-quota `/videos`-page scrape is upload-detection fallback only, never for comments |
| **YouTube RSS 404 is network-specific and silently "fixes" then breaks** | Low | Low | We designed around playlistItems.list; ignore RSS entirely |
| **Threads app review rejected or rate limit is 500/7d not 2,200/24h** | Medium | Low-Medium | Build is gated on approval anyway; keyword sets ranked by tier so a 500/7d budget still covers Tier 1+2 |
| **Board RSS disabled by an admin / Cloudflare expansion** (CSNbbs 403 pattern) | Medium per-board | Low each | Per-board health rows; boards are 20 independent small bets; CSNbbs stays a stretch goal |
| **ToS: Reddit content + ads** ("displaying Reddit content and running ads: No" — [Reddit](https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data)) | Certain if we ever add ads | Existential for Reddit channel | **Standing rule: site stays ad-free anywhere Reddit-derived data appears.** Document in DECISIONS.md |
| **ToS: model-training clauses** (Reddit ML clause; Discord Dev Policy §21) | Self-inflicted only | High if violated | **Hard exclusion: no Reddit or Discord text in `data/voice_corpus.jsonl` / any LoRA training.** Inference is fine. Add a source filter to `train_voice_lora.py` inputs |
| **Twitch chat-log retention clause** | Low (not built yet) | Low | If built: aggregate-only persistence, raw chat never written to `conversation_documents` |
| **User-level inference creep** (Reddit RBP zero-tolerance; general privacy) | Low | High | Aggregate at team level only, everywhere; 48h raw-text purge already implemented — keep it |
| **Bluesky list rot** (beat writers decaying monthly; platform −57% from peak) | High | Low-Medium | Quarterly re-census job: getAuthorFeed recency check on all curated handles, auto-flag dormant >60d |
| **Calendar staleness** (portal/CFP dates shift) | Medium | Medium | calendar_pressure rows carry source URLs; verify early-signing-period exact date in fall (currently "~Dec 4, reported") |

---

## 6. What we explicitly skip and why

- **X/Twitter** — $30/mo buys ~200 reads/day (~1.5 posts/team/day): the entire budget for <0.1% of corpus ([pricing](https://docs.x.com/x-api/getting-started/pricing)).
- **X gray-market resellers** (twitterapi.io, Bright Data, etc.) — unofficial scraper-backed, fails our ToS-compliant constraint.
- **247Sports / On3 / Rivals sites and boards** — ToS bans scraping, AI training, commercial use; permanent OFF LIMITS (their YouTube channels are the legal slice).
- **TikTok** — Research API is institution-only; oEmbed has no search or comments; no legal hobbyist path.
- **Facebook public Groups** — Groups API removed April 2024; Meta Content Library is academic-institution-only.
- **Second-screen/watch-party apps** — category graveyard (Playback.tv dead Dec 2025, Spotify Live dead 2023); the actual second screen is Reddit/Discord/X.
- **ESPN / Saturday Down South / On3 article comments** — removed, nonexistent, and ToS-blocked respectively.
- **SB Nation Coral comments** — no API, Vox ToS prohibits scraping, communities shrinking; we take article RSS only.
- **Substack Notes** — no official API; reverse-engineered endpoints are gray; we already have post RSS.
- **Nostr** — ~228k DAU, crypto-centric, no detectable CFB community.
- **Fizz** — where student gameday chatter actually went, but .edu-gated, campus-siloed, no API: legally untappable; worth knowing it exists.
- **Conference subreddits** — graveyard (r/MACtion: 2 subscribers); except r/Pac12, r/ACC, r/secfootball at token cadence.
- **Raw Jetstream keyword firehose (now)** — measured 0 CFB matches in 8,319 offseason posts; hashtags in <2% of CFB posts; deferred to an in-season Saturday experiment.
- **Apify or any paid scraping tier** — nothing in this plan needs it; the budget stays at $0.
- **Reddit OAuth as a planning assumption** — approval is a ghost feature; the ticket gets filed once, then we build as if denied.