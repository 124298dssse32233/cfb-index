# CFB Index — Our Data Sources, Explained

*A plain-language guide to where our data comes from and what each source is for.*
*Written for a non-engineer. Last updated 2026-06-11.*

---

## The big picture (read this first)

Most college-football sites show you the **scoreboard**: who won, who's ranked, who got recruited. We do that too — but the thing that makes us different is that we also measure **how fans feel and what fans are talking about**, team by team, and we show it with receipts.

To do that, we quietly gather public chatter and public numbers from a bunch of places every day, clean it up, and turn it into the features you see on the site (mood meters, "what this fanbase won't shut up about," buzz levels, betting-market belief, NIL value, and so on).

Three rules we never break:

1. **No fake precision.** If we don't have enough data about a team to be honest, we show a vague label ("Awaiting Signal") instead of inventing a confident-looking number.
2. **Everything is traceable.** Every single piece of data remembers exactly where it came from and when. Nothing is made up.
3. **We only use public, allowed sources.** No paywalled content, no Twitter/X, no private Discords, no scraping behind logins. Where a source's data appears on our site, that part of the site stays **ad-free** (a promise we made to keep using Reddit's public feeds respectfully).

A few quick vocabulary words you'll see below:
- **Feed / RSS** — a public "here's our latest stuff" list a website publishes for anyone to read (like a newspaper's headline ticker). Free, no login.
- **API** — an official "ask us for data" doorway a company provides (YouTube, Wikipedia, etc.).
- **Sentiment** — whether a comment sounds happy, angry, doom-y, joking, etc.
- **ASR** — "automatic speech recognition," i.e. turning podcast audio into text so we can read it.

---

## How the data flows (the daily cycle)

```
  COLLECT  ───►  PROCESS  ───►  BUILD  ───►  DEPLOY
  (5 AM)         (compute)     (make HTML)   (push live)

  pull from      score mood,   turn the      copy the
  every source   find the      numbers into  finished
  into our       phrases,      ~27,000 web   site up to
  database       rank teams    pages         the internet
```

Two automatic jobs run on your always-on PC every day: one at **5 AM** that *collects* (pulls everything in), and one at **9 AM** that *builds and deploys* (turns it into the live site). Everything below feeds into that 5 AM collect, except CFBD (the official stats), which comes in during the 9 AM build.

---

## The sources, grouped by what they're FOR

### 🗣️ Purpose 1 — What fans are SAYING (mood + the words they use)

This is the heart of the product. We read public fan conversation and measure the *feeling* and the *vocabulary* of each fanbase.

| Source | What it is, in plain terms | What we pull | What it powers on the site |
|---|---|---|---|
| **Reddit — team subs** | Each team's own subreddit (e.g. r/rolltide), read through Reddit's free public feed | Recent posts + comment threads | Mood meters, "Fanbase Voice," the words a fanbase obsesses over |
| **Reddit — r/CFB** | The big national college-football subreddit | National posts + comments | National storylines, rivalry chatter, cross-team comparisons |
| **Message boards** | Old-school independent team forums (TigerDroppings, VolNation, TideFans, etc.) | Public threads | "Die-hard" fan sentiment — an older, more hardcore voice than Reddit |
| **YouTube comments** | Comments under team channels and national CFB shows | Comment text | Another fan voice, skewed toward casual/younger viewers |
| **Bluesky** | A public Twitter-style network (the parts of "social" we're *allowed* to use) | Posts from curated CFB accounts + public CFB feeds | Media-and-fan reactions, especially national takes |
| **Podcasts** | Team and national CFB podcasts (audio turned into text on your GPU) | Transcripts of recent episodes | Adds the "talking heads" voice to discourse; quotes |

**What these become:** the mood cards, the "Fanbase Voice" personality, the **Lexicon** (slang a fanbase actually uses), the **Discourse Atlas** (which fanbases *talk alike*), **Team Eras** (how a fanbase's vocabulary changed year to year), and the real fan-quote snippets ("KWIC") on team pages. It's also tagged per-player to build "The Room on [Player]."

> **Important nuance:** raw fan text is messy — sarcasm, inside jokes, negativity that's actually affectionate. So before any of it counts, it goes through a **relevance filter** (is this even about football?) and a **sentiment model** (how does this *feel*?). That's the "process" step.

---

### 📈 Purpose 2 — How much ATTENTION a team/player is getting (buzz & volume)

This isn't about *feeling* — it's about *how loud* the conversation is. A team can be talked about a lot (high attention) whether the talk is good or bad.

| Source | What it is, in plain terms | What we pull | What it powers |
|---|---|---|---|
| **GDELT** | A free global service that counts how often each team appears in news worldwide | Daily article counts per team | News-buzz level; the "Backometer" attention metric |
| **Google News** | Google's public news feed, queried per team | Recent headlines per team | Per-team news volume + fresh storylines |
| **Campus newspapers** | Student papers (Daily Beacon, The Reveille, etc.) via their public feeds | Recent articles | The on-campus, college-age perspective |
| **Athletics sites** | Official school athletic-department news feeds | Press releases / news | Official team news, roster moves |
| **Wikipedia pageviews** | How many people looked up a team/coach/QB on Wikipedia | Daily view counts | A clean, honest "public curiosity" signal |
| **Wikipedia edits** | How much a team's Wikipedia page is being edited | Edit activity | Spikes flag big events (firings, transfers) |
| **YouTube video stats** | View counts on tracked CFB channels | Views + metadata | Attention proxy for video audiences |

**What these become:** buzz/attention metrics, "who's trending," and the freshness signals that decide which storylines surface.

---

### 🎲 Purpose 3 — What the MARKETS believe (money where the mouth is)

Fans *say* things; bettors *bet* things. Markets are a brutally honest signal of what people actually expect to happen.

| Source | What it is, in plain terms | What we pull | What it powers |
|---|---|---|---|
| **Polymarket** | A public prediction market (people bet on outcomes like "Team X wins the title") | Contract prices + volume | "Belief" signals — e.g. the market's confidence in a team, shown on player/team pages |
| **Kalshi** | A regulated US prediction market | Contract prices + volume | Same idea as Polymarket; a second market opinion |
| **SeatGeek** | Public ticket-resale prices | "Get-in" price + listing counts | Demand signal — how badly fans want to be in the building |

**What these become:** the betting-market belief chips, and the gap between what *fans hope* and what *markets expect* (a fun "delusion premium" angle).

---

### 💰 Purpose 4 — Player MONEY (NIL value)

| Source | What it is, in plain terms | What we pull | What it powers |
|---|---|---|---|
| **On3 NIL** | On3's public NIL valuation rankings (what a player's name/image/likeness is estimated to be worth) | Player valuations | The NIL value shown on player pages (e.g. Arch Manning ~$5.4M) |

---

### 🏈 Purpose 5 — The official FACTS (the scoreboard layer)

Everything above is *chatter and signals*. This is the hard, factual backbone — and it comes in during the 9 AM build, not the 5 AM collect.

| Source | What it is, in plain terms | What we pull | What it powers |
|---|---|---|---|
| **CFBD** (CollegeFootballData) | The standard public database of college-football facts (small $10/mo Patreon tier) | Games, scores, betting lines, advanced stats, recruiting classes, transfer portal, NFL Draft results, coaching records, returning production | The rankings themselves, team/player pages, recruiting footprints, draft pipelines, coaching eras — the factual spine of the whole site |
| **Coaching news** | A focused news pull about coaching moves | Recent coaching-news items | The coaching carousel / hot-seat storylines |
| **Wikipedia awards** | Public award/honor history (Heisman, all-conference, etc.) | Award winners | Player honors and accolades |

---

## What we deliberately DON'T collect (and why)

Being disciplined here is a *credibility feature*, not a limitation:

- **Twitter/X** — too expensive and against their terms. We use Bluesky instead.
- **Paywalled recruiting sites** (247/Rivals/On3 premium) — only their free, public pages.
- **Private Discords / anything behind a login** — not public, not ethical to scrape.
- **Instagram / Facebook bulk scraping** — against their terms.
- **Player personal social accounts as "fan" sentiment** — they're the *subject*, not the fan (and often minors).
- **Made-up demographic splits** (race/gender/politics) — we can't honestly infer those from public posts, so we don't pretend to.

We also publish our honest **coverage gaps** (e.g. older alumni on Facebook are hard to reach) right on the methodology page, rather than hiding them.

---

## The honest-citizen rules we follow

- **Ad-free where fan data shows.** Wherever Reddit-derived data appears, that page carries no ads — a respect-the-source promise.
- **Honest identification.** When our collector visits a public feed, it identifies itself honestly (no pretending to be a normal browser to sneak past blocks).
- **Provenance on everything.** Every row stores its source, capture time, and a link back. If a fan ever asks "where did this come from?", we can answer.
- **Privacy.** We store fan quotes pseudonymously (no real names) with a backlink, and we honor deletions.

---

## Quick reference: every active source at a glance

| Source | Purpose | Cost | How often |
|---|---|---|---|
| Reddit (team subs, r/CFB, comments) | Fan sentiment + discourse | Free | Daily |
| Message boards | Die-hard sentiment | Free | Daily |
| YouTube comments | Casual fan voice | Free | Daily |
| Bluesky (curated + feeds) | Media/fan reactions | Free | Daily |
| Podcasts (transcribed) | "Talking heads" voice | Free | Daily (time-boxed) |
| GDELT | News attention/volume | Free | Daily |
| Google News | Per-team news | Free | Daily |
| Campus newspapers | College-age view | Free | Daily |
| Athletics sites | Official team news | Free | Daily |
| Wikipedia pageviews + edits | Public curiosity | Free | Daily |
| YouTube video stats | Video attention | Free | Daily |
| Polymarket + Kalshi | Market belief | Free | Daily |
| SeatGeek | Ticket demand | Free | Daily |
| On3 NIL | Player money | Free (public) | Daily (during build) |
| CFBD | Official facts | ~$10/mo | During build |
| Coaching news / Wikipedia awards | Coaching + honors | Free | Daily/as needed |

---

*The deeper, more technical version of all this lives in `FAN_INTEL_SOURCE_STRATEGY.md` (the engineering reference). This document is the friendly translation.*
