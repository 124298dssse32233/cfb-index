# Podcast transcription (GPU) — one-time setup (plain-language)

_Written for Kevin, 2026-06-10. Goal: turn college-football podcasts into real
fan-intel signal by transcribing recent episodes on your RTX 3090 and feeding the
transcripts through the same team/player tagging as Reddit, YouTube, and news._

## What this adds and why it's worth it

Today we ingest podcast **show-notes** (a paragraph per episode). Hosts actually
talk for 30-90 minutes — that spoken content is some of the richest, most opinion-
dense CFB conversation anywhere, and we capture none of it. This feature downloads
each recent episode's audio, transcribes it locally with **faster-whisper** on the
GPU, and stores the full transcript as a normal conversation document. From there
it flows automatically into team mood, Room cards, and player signal.

It's built to be safe for the daily trigger: it only does a small **rotated batch**
per run (default 6 episodes), stops at a **15-minute wall-clock budget**, and
**self-skips** (no error) until you install faster-whisper. It lives in the 05:00
`collect` job, while the GPU-heavy team-preview LLM runs in the 09:00 `build`
job — so the two never fight over the GPU.

## Step 1 — Install faster-whisper into the ML venv

`.venv-ml` already has CUDA-enabled PyTorch, so this is one command:

```powershell
.\.venv-ml\Scripts\python.exe -m pip install faster-whisper
```

That's the only dependency. faster-whisper bundles its own audio decoder (PyAV) and
downloads the speech model automatically on first use — you do **not** need to
install ffmpeg or download model files by hand.

## Step 2 — Validate on a couple of episodes (one command)

You need some podcast episodes in the DB first. The daily `collect` job already
ingests episode metadata; if you've run it recently you're set. Then:

```powershell
.\.venv-ml\Scripts\python.exe manage.py collect-podcast-transcripts --season 2025 --week 41 --max-episodes 2
```

Expected output (the first run also downloads the model, ~150-500 MB, one time):

```
podcast_asr: locked_on_alabama — 64210 chars (3015s audio)
podcast_asr: split_zone_duo — 71880 chars (4102s audio)
collect-podcast-transcripts season=2025 week=41: episodes=2 transcribed=2 failed=0 no_audio=0 chars=136090
```

On a 3090 with the default `small.en` model, a 60-minute episode transcribes in
roughly **1-3 minutes**. If you see `SKIPPED: faster-whisper not installed`, redo
Step 1 in the **.venv-ml** python (not `.venv`).

## Step 3 — Nothing else to wire

It's already in `scripts/collect.ps1` (the 05:00 job), right before the team-alias
tagging step, which now includes `podcast_transcript` in its sources. So once the
decoupled cadence is active and faster-whisper is installed, transcripts get
collected and team-tagged automatically every morning, and the 09:00 build folds
them into the site.

## Picking a model (speed vs. quality)

| `--model-size` | Quality | ~speed on 3090 | When to use |
|---|---|---|---|
| `tiny.en` | rough | ~30x realtime | only if you want max throughput |
| `base.en` | ok | ~20x | |
| `small.en` (default) | good | ~10-15x | the sweet spot for sentiment |
| `medium.en` | very good | ~5x | if you later want cleaner quotes |
| `large-v3` | best | ~2-3x | overkill for our use; slow |

Change it per run with `--model-size medium.en`, or edit the default in
`scripts/collect.ps1` (the `collect-podcast-transcripts` line).

## Knobs (all optional)

| Flag | Default | Meaning |
|---|---|---|
| `--max-episodes` | `6` | Rotated batch size per run (newest-then-stalest via the ledger) |
| `--budget-seconds` | `900` | Hard wall-clock cap; the rest defers to the next run |
| `--max-age-days` | `21` | Ignore episodes older than this |
| `--device` / `--compute-type` | `cuda` / `float16` | Falls back to CPU int8 automatically if CUDA can't init |
| `--show` | (all) | Limit to specific show slugs, e.g. `--show locked_on_alabama` (repeatable) |

## How coverage grows over time

Each run transcribes the newest untranscribed episodes first, so day over day you
build a rolling transcript corpus across every show in `seeds/podcast_feeds.yaml`.
Already-transcribed episodes are skipped permanently (idempotent), and a broken
audio URL gets an escalating cooldown instead of being retried every morning.

To add more shows (especially per-team pods), append entries to
`seeds/podcast_feeds.yaml` and run `python manage.py seed-feed-instances` — the
metadata adapter will start ingesting their episodes, and transcription picks them
up automatically.

## Where the data lands

- Transcript → `conversation_documents` (`content_type='podcast_transcript'`,
  `source_name='podcast_transcript'`, `source_subchannel=<show_slug>`).
- Team attribution → `tag-team-mentions --sources podcast_transcript` (already in
  the collect job).
- Player attribution → `tag-player-mentions` (already in the build job).
- The legacy `tools/transcribe_episode.py` (whisper.cpp, segment-level) is
  untouched — it remains the manual "deep-dive one episode for editorial quotes"
  path and writes to `podcast_transcript_segments`.
