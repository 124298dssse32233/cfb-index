# Player ID Stability — Scoping Note

**Date:** 2026-05-21
**Status:** RESOLVED 2026-06-10 via a new **Option D — Player-ID Anchor** (see
update below). Option B (CI fail-loud gate) was already shipped; Option A/C were
NOT taken (A's URL reset + 301 map were avoidable; C's schema migration was
high-risk).

---

## UPDATE 2026-06-10 — shipped Option D (Player-ID Anchor)

The 2026-06 box migration rebuilt the DB from scratch and reassigned every
autoincrement `player_id`, breaking the live URLs (Mendoza 38276→12763, Love
48316→12194, Brown 38981→12655) exactly as drift-mode #1 predicted.

**Chosen fix — Option D (not in the original A/B/C list):** persist the canonical
`(source_name, source_player_id) → player_id` mapping to a committed CSV and
re-seed it BEFORE ingestion on a rebuild. Because `_get_or_create_player` matches
on `player_source_ids` and returns the existing id, pre-seeding the canonical ids
makes ingestion *reuse* them. Net effect: URLs stay stable across rebuilds with
**no URL-scheme change, no 404s, no 301 redirect map, and no `_player_slug` /
`reporting.py` edits** — which is why it was preferred over Option A.

- `src/cfb_rankings/player_id_anchor.py` — `export_anchor` / `seed_anchor`.
- CLI: `manage.py export-player-id-anchor` / `seed-player-id-anchor`.
- `data/player_id_anchor.csv` — 74,183-row canonical snapshot (committed).
- `publish_site.yml` runs `seed-player-id-anchor` in the seed step (after
  init-db, before CFBD ingestion). No-op on a normal restored-artifact publish;
  pins canonical ids on a from-scratch rebuild.
- 5 tests in `tests/test_player_id_anchor.py`.

**Complementary to Option B:** the fail-loud gate still blocks *accidental* empty
rebuilds; the anchor makes *intentional* rebuilds (migration / `--allow-empty`)
preserve URLs. **Refresh procedure:** run `export-player-id-anchor` and commit the
CSV after large new-player ingests (e.g. before a planned migration) so newly
created players become anchored too.

---

### Original scoping (2026-05-21) below — retained for context.
**Why this matters:** Today the production site was found broken because:
1. A `master`-branch deploy was promoted to production, but `output/` is gitignored
   so player pages 404'd across the board (fixed: promoted a `published`-branch
   deploy back to production).
2. The Heisman board on the live site links to player URLs like
   `/players/fernando-mendoza-38276.html` — the `-38276` is the SQLite
   AUTOINCREMENT `player_id`. If a future re-ingest assigns Mendoza a different
   internal id, every existing Heisman link breaks even though the page renders.

The current symptom is *just* the URL drift, not the worse "no rendered files at
all" case — that one has a separate root cause already understood (master
deploys never had the files).

---

## Current state — what the code actually does

### Schema (`research/cfb-data-schema-sqlite.sql:181`)

```sql
create table if not exists players (
  player_id integer primary key autoincrement,
  full_name text not null,
  ...
);

create table if not exists player_source_ids (
  player_source_id integer primary key autoincrement,
  player_id integer not null references players(player_id),
  source_name text not null,
  source_player_id text not null,
  unique (source_name, source_player_id)
);
```

`player_id` is autoincrement. Stable mappings to external ids (CFBD player id,
CFBD recruit id, etc.) live in `player_source_ids` with a unique constraint
on `(source_name, source_player_id)`.

### Ingest paths

**CFBD ingest — `src/cfb_rankings/ingest/cfbd.py:1042` `_get_or_create_player`**

Already does the right thing:
1. If `source_player_id` is non-empty → look up `player_source_ids` first; return
   that `player_id` if found.
2. Else (no source id) → try name-match with compatibility check; return id if
   exactly one compatible row.
3. Else → `INSERT INTO players ...` (gets a fresh autoincrement) AND
   `_upsert_player_source_ids(cfbd, source_player_id)` so the same external id
   is recoverable next run.

So CFBD-sourced players HAVE stable ids across re-ingests, provided
`player_source_ids` survives. The autoincrement only matters the first time.

**Honors ingest — `src/cfb_rankings/ingest/honors.py:169`**

Weaker: name-match only (no source-id-first lookup at the entry point), then
inserts a new players row if no name match. AFTER insert it does call
`_upsert_player_source_ids` for `cfbd_player_id` and `cfbd_recruit_id` columns
when the CSV provides them — so on a subsequent honors-only run the new row
won't be inserted again, but the **first** run on a fresh-DB scenario can
create a `players` row that later collides with a CFBD insert under a different
name spelling.

### URL construction — `src/cfb_rankings/reporting.py:20413`

```python
def _player_slug(player_id: int, full_name: str) -> str:
    return f"{slugify(full_name)}-{player_id}"
```

The URL uses the **autoincrement integer** directly. That's the only place the
internal id leaks into the public URL space, but it's used in ~5+ call sites
inside `reporting.py` (lines 6752, 6920, 7926, 8817, plus the players_dir
write at 5838).

---

## When drift actually happens

1. **DB artifact loss in CI** — workflows download the rolling
   `cfb-rankings-db` artifact via `dawidd6/action-download-artifact@v6` with
   `continue-on-error: true` + `if_no_artifact_found: warn`. If the download
   silently fails, `init-db` runs against an empty SQLite file, and the next
   ingest assigns fresh autoincrement ids starting at 1. EVERY player gets a
   new id.
2. **Honors-first on fresh DB** — if `import-player-honors` runs before any
   CFBD ingest on a fresh DB, the Heisman roster gets ids first, and a later
   CFBD ingest may attach external ids to a *different* row (name spelling
   mismatch) — creating duplicate-human entries with split ids.
3. **Manual reset** — not currently in any workflow (grep `drop table players`
   and `delete from players` → no matches), so this is hypothetical.

Drift mode #1 is the most likely one given the dawidd6 race-condition history
documented in `publish_site.yml:51-71`.

---

## Fix options, ranked

### Option A — Stabilize URL keys (recommended for MVK)

**What:** Change `_player_slug` to prefer a stable external id when one is
available; fall back to autoincrement otherwise.

```python
def _player_slug(player_id: int, full_name: str, *, stable_id: str | None = None) -> str:
    return f"{slugify(full_name)}-{stable_id or player_id}"
```

Then at every call site (5+ in reporting.py), pull `cfbd_player_id` from
`player_source_ids` via a join in the existing SELECT, or via a small helper
lookup. Players without a CFBD source id (small-school, manually-added) keep
the autoincrement form.

**Effort:** 1 full day. Most work is auditing call sites, writing the lookup
helper, and adding a redirect map so existing
`/players/<name>-<old-autoincrement>.html` URLs 301 to the new form.

**Risk:** Medium. Existing Google index entries will break briefly until the
301 redirects propagate. Bookmarks ditto.

**Acceptance:** Wipe `cfb_rankings.db`, re-ingest from scratch, regenerate
site — every CFBD-sourced player URL is identical to a known-good baseline.

### Option B — Make CI DB-artifact loss fail-loud

**What:** Change `if_no_artifact_found: warn` → `error` on the publish-site +
enrich workflows, OR add an explicit check after download that fails the
workflow if `cfb_rankings.db` is empty / has < N players.

**Effort:** 1-2 hours.

**Risk:** Low. Worst case it adds friction to a "first ever run" scenario,
which doesn't apply since the artifact has been continuously rolling for
months.

**Acceptance:** Synthetic test — temporarily change artifact name to one that
doesn't exist, confirm workflow fails fast rather than producing an
empty-DB site.

**This does NOT fix existing URL drift** — it just prevents the most common
*source* of future drift. Pair with Option A for full coverage, or use this
alone as a "stop the bleeding" patch if Option A is too costly.

### Option C — Switch to a content-derived hash id

**What:** Make `player_id` derived from a hash of stable attributes
(`hash(full_name + position + hometown + year_first_seen)`) at insert time
instead of autoincrement. Schema migration.

**Effort:** Multiple days. Touches schema, every ingest path, every join,
every existing player_id reference. Highest blast radius.

**Risk:** High. Schema migration on a 350MB+ live DB. Bug surface area is
the entire codebase.

**Recommendation:** Defer to post-season. Option A captures most of the value
at a fraction of the cost.

---

## Recommended path

1. **Now / today:** Option B (CI fail-loud on artifact loss). 1-2 hours.
   Stops the most common future regression.
2. **This week:** Option A (stable URL slug from `cfbd_player_id`). 1 day.
   Fixes the SEO/bookmark drift class for all CFBD-sourced players (~95% of
   the player corpus).
3. **Post-season (Nov 2026+):** Option C if any drift is still being
   observed.

Both A and B are reversible and surgical. Neither requires a schema migration.

---

## What ALREADY exists in our favor

- `player_source_ids` table with a unique constraint on `(source_name,
  source_player_id)` — Option A doesn't need a schema change, just to read
  this existing table.
- `_get_or_create_player` in cfbd.py already implements the
  "external-id-first, name-fallback" pattern correctly.
- `_upsert_player_source_ids` exists and is wired into both cfbd and honors
  ingests.

The infrastructure is largely there; it's the URL-construction layer that
still leaks the internal id.

---

## Open questions for the user

1. Are you OK with brief 404s on old URLs while the 301 redirect map
   propagates? (Option A introduces this.) Alternative: serve both URL forms
   for a transition period, costs ~2x disk space until cleanup.
2. Is post-season (Nov 2026+) acceptable for the schema-level Option C, or
   do you want to chase it earlier?
3. Should the Heisman board be regenerated *now* with whatever the current
   player ids are, so future ingests have a stable baseline to upsert
   against? (Cheap; ~10 min of CI time.)
