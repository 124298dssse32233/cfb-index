# Deep Research Prompt — CFB Index Source Handle Refresh

Paste this into Claude Cowork / ChatGPT Deep Research / Perplexity Pro.
Target runtime: 90-120 min. Output format is YAML so it pastes directly
into the seed files.

---

```
ROLE
You are a college-football beat research analyst. Your job is to produce a clean,
verified YAML patch for the CFB Index pipeline. Be thorough; every handle/URL must
resolve today, not "used to work."

CONTEXT
I maintain an editorial pipeline that watches 20 priority CFB programs across
Reddit, Bluesky, YouTube, podcasts, and prediction markets. Every source I track
has to be a real, currently-working URL or handle — a 404 or stale Twitter handle
is worse than no entry because cron will keep trying it.

The 20 priority programs are:

SEC (5):            Alabama, Georgia, LSU, Tennessee, Texas
Big Ten (4):        Ohio State, Michigan, Penn State, Oregon
ACC (3):            Clemson, Florida State, Miami
Big 12 (3):         Texas Tech, Kansas State, BYU
Group of 5 (3):     Boise State, Memphis, Tulane
HBCU (2):           Jackson State, Howard

TASK
Produce a SINGLE YAML document with the structure shown under OUTPUT FORMAT.
Every entry must be confirmed real on today's date. If you cannot confirm a
handle or URL, set its value to null — do not guess. Quality over quantity.

FOR EACH of the 20 programs, return:

  1. **Bluesky beat handles** (3-5 per team) — practicing beat writers who
     cover the football team on Bluesky (*.bsky.social). Must have posted at
     least once in the past 30 days. Prefer reporters at the major local
     outlet (Atlanta Journal-Constitution for UGA, LSU Reveille for LSU, etc.).
     Exclude: fan accounts, podcasters who only repost, team's official account.

  2. **YouTube team channel ID** — the single official athletic-dept YouTube
     channel as a UC-prefixed channel_id (e.g. "UCkBImmjL0ERhgqBHPH0LkTw"), NOT
     the vanity URL. Find this by viewing source on the channel page and
     extracting the channelId from the og:url meta tag.

  3. **YouTube fan channel IDs** (2-3 per team) — unofficial channels with
     >10k subscribers that cover the team. Verify they posted in the past 30
     days. UC-prefixed IDs only.

  4. **Locked On team feed URL** — the real RSS for the Locked On [Team]
     daily podcast. Find via lockedonpodcasts.com show page. Format is usually
     https://feeds.megaphone.fm/<podcast_id> but the podcast_ids I guessed
     (lockedonalabama, lockedonbuckeyes, etc.) were wrong — find the actual ones.

  5. **Primary message board URL** — the main independent fan board (NOT
     247Sports/Rivals paywalled). Confirm the forum is publicly readable
     without a login. Tigerdroppings for LSU is a known-good example;
     VolNation, TideFans, Shaggy Bevo, 11 Warriors are other known-good.

  6. **Primary campus paper RSS** — the student newspaper's RSS feed. Many
     campus papers use SNworks (*.collegian.psu.edu/search/?f=rss pattern)
     or WordPress (*.com/feed/). Confirm the URL returns valid XML today.

  7. **Best beat-writer RSS feed** — for outlets where RSS still works. Many
     Gannett-network papers (USA Today Network) deprecated RSS in 2023-2024,
     so if the outlet is on Gannett, return null and note it as [gannett]
     in the notes field. Acceptable outlets: SBNation team sites, The Athletic
     author feeds, Dawg Nation (UGA), 247Sports free team feed, Saturday Down
     South team tag feed.

  8. **Head coach Bluesky handle** — *.bsky.social if they have one. Most
     P4 head coaches do NOT use Bluesky; return null in that case.

ADDITIONAL SECTIONS (not per-team):

  9. **Kalshi CFB contract tickers** — visit kalshi.com/markets and capture
     the real tickers (e.g. KXCFBCHAMP-26, not guesses). Specifically need:
       - 2026 National Champion
       - Each conference champion market (SEC, B1G, ACC, B12)
       - Heisman Trophy winner
       - Any open team-CFP-appearance markets (as many as exist)

 10. **Polymarket CFB market slugs** — visit polymarket.com/markets?tag=sports
     and capture real slugs (e.g. "will-ohio-state-make-the-2026-cfp"). Same
     coverage as Kalshi.

 11. **Bluesky CFB starter-pack URIs** — search bluesky for "college football"
     + "starter pack". Return up to 5 public pack URIs (at://did:plc:.../
     app.bsky.graph.starterpack/<rkey>).

 12. **TikTok creators — 30 handles** — must be currently active (posted in
     last 14 days), >50k followers, CFB focus. Break down as:
       - 15 national CFB creators
       - 10 team-aligned student-creator accounts (one per priority team
         where possible)
       - 5 HBCU-focused creators

 13. **Replacement URLs** — if any of these are now dead (404 or 403), find
     a working equivalent and return as `replacement_for: <old_source_id>`:
       - beat_alabama_tuscaloosa_news_cecil
       - beat_clemson_greenville_news
       - beat_florida-state_tallahassee_democrat
       - beat_jackson-state_clarion_ledger
       - beat_kansas-state_topeka_capital
       - beat_memphis_commercial_appeal
       - beat_michigan_detroit_free_press_um
       - beat_ohio-state_dispatch_osu
       - beat_tennessee_knoxville_sentinel_football
       - beat_texas-tech_lubbock_avalanche
       - podcast_finebaum_rss (rss.art19.com/paul-finebaum-show is dead)
       - podcast_split_zone_duo (megaphone.fm/VMP5705694282 is dead)
       - podcast_the_solid_verbal (simplecast.com/wkp4yYBk is dead)
       - podcast_the_audible (simplecast.com/k6Opj0Mx is dead)
       - All 7 locked_on_* URLs (megaphone.fm/lockedon* pattern is wrong)
       - 5 substack feeds (extra_points, max_olson, recruiting_scoops,
         swindle_stats, the_athletic_cfb)

OUTPUT FORMAT
Return exactly this YAML shape. No prose, no markdown — pure YAML
paste-ready for my seed files.

priority_teams:
  - team_slug: alabama
    bluesky_beat_handles: ["@handle1.bsky.social", "@handle2.bsky.social"]
    youtube_team_channel_id: "UC..."
    youtube_fan_channels: ["UC...", "UC..."]
    locked_on_rss: "https://..."
    message_board_primary: "https://..."
    campus_newspaper_feed: "https://..."
    beat_writer_rss: "https://..."
    head_coach_bsky: null
    notes: ""
  # ... (20 total, one per priority team)

prediction_markets:
  kalshi:
    - ticker: "KX..."
      label: "2026 National Champion"
  polymarket:
    - slug: "..."
      label: "2026 National Champion"

bluesky_starter_packs:
  - uri: "at://did:plc:.../app.bsky.graph.starterpack/..."
    name: "CFB Reporters"
    curator: "@..."

tiktok_creators:
  national:
    - handle: "@creator1"
      followers_approx: 250000
    # ... 15 total
  team_aligned:
    - handle: "@creator"
      team_slug: "alabama"
    # ... 10 total
  hbcu:
    - handle: "@creator"
      focus: "HBCU Gameday"
    # ... 5 total

replacements:
  - replacement_for: "beat_alabama_tuscaloosa_news_cecil"
    new_url: "https://..."
    new_writer_slug: "..."
    notes: "original was Gannett; replaced with SBNation"

RULES
- Verify every URL returns 200 today. For RSS feeds, the body should be
  valid XML starting with <?xml or <rss or <feed.
- For Bluesky handles, verify via https://bsky.app/profile/<handle> — the
  profile must exist AND have posted in the last 30 days.
- For YouTube channels, use the UC-prefixed channel_id from og:url. Do not
  use @handle URLs.
- Do not invent handles. Null is always better than a fake handle.
- Do not include 247Sports, Rivals, or On3 PAYWALLED feeds — only their free
  public feeds if they exist.
- HBCU section: if a program has no active beat writers on Bluesky at all,
  return an empty list + a note. Honesty beats padding.

DELIVERABLE
Paste the YAML document back to me. I will diff it against my seed files
and apply valid entries.
```

---

## After you paste the result back

Save the YAML output to `research/deep_research_refresh_<YYYY-MM-DD>.yaml`, then tell me:
> "Deep research refresh complete, file at research/deep_research_refresh_..."

I'll diff it against the current seed YAMLs and apply the verified entries:
- `priority_teams.*` → merged into `seeds/priority_teams.yaml`
- `prediction_markets.*` → replaces `seeds/prediction_market_contracts.yaml`
- `bluesky_starter_packs` → fed into `python manage.py bluesky-harvest-starterpacks`
- `tiktok_creators` → new `seeds/tiktok_creators.yaml`
- `replacements` → updates in `seeds/beat_writer_feeds.yaml` / `podcast_feeds.yaml` / `substack_feeds.yaml`

Then `python manage.py seed-priority-teams && seed-source-instances && seed-feed-instances && validate-feed-urls` and we re-run the ingest with fresh handles.
