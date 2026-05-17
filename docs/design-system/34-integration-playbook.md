# Integration Playbook — confidence chips + hero findings

LOCKED 2026-05-17 (Sprint v5-7.5 foundation).
References:
- [`33-confidence-signaling.md`](33-confidence-signaling.md) — what the chip means
- [`30-page-archetypes.md`](30-page-archetypes.md) — which surfaces require a hero finding
- [`docs/mockups/`](../mockups/index.html) — visual reference for every archetype
- [`src/cfb_rankings/confidence.py`](../../src/cfb_rankings/confidence.py) — the helper module
- [`src/cfb_rankings/hero_findings/`](../../src/cfb_rankings/hero_findings/) — generator + renderer

This playbook gives Window A (or Window B in a later session) a step-by-step procedure for wiring the locked primitives into an existing renderer. Each step has concrete code samples + verification commands. Follow it as written; don't improvise.

## Pre-flight

Verify your environment is on the foundation slice:

```bash
python -c "from cfb_rankings.confidence import render_confidence_chip; print('ok')"
python -c "from cfb_rankings.hero_findings import render_hero_finding_html; print('ok')"
python manage.py confidence-status   # all 5 domains should report a calibration row
```

If `confidence-status` shows FALLBACK for every domain, run:
```bash
python manage.py recompute-confidence-thresholds
```

## Pattern 1 — adding a confidence chip to a metric

The single most common integration. Use case: a renderer displays a metric (mood score, percentile, mention count) and you want the chip beside it.

### Code

```python
# In the renderer module:
from cfb_rankings.confidence import render_confidence_chip, Domain

# Where the metric is rendered:
sample_size = compute_sample_size(...)   # docs / sources / etc.
chip_html = render_confidence_chip(
    sample_size,
    Domain.FAN_INTEL,          # or HISTORICAL / MODEL / MARKET / PREDICTION
    override_label=None,       # only when an editorial override is required
)
html += f'<div class="metric">{value}{chip_html}</div>'
```

### Tests to add

```python
# in tests/test_<your_module>.py
from cfb_rankings.confidence import band_for

def test_metric_high_sample_chips_high() -> None:
    html = your_renderer(sample_size=42)
    assert 'confidence--high' in html

def test_metric_low_sample_chips_low_and_softens_label() -> None:
    html = your_renderer(sample_size=5)
    assert 'confidence--low' in html
```

### What NOT to do

* Don't add an inline `style="background: ...; color: ..."` on the chip element — use the locked CSS modifiers.
* Don't override the band via the override_label trick. The label can be softened ("Moderate" instead of "Medium confidence") but the BAND (color) is sample-derived and not negotiable.
* Don't render the chip when the sample is genuinely unknown (e.g., when the underlying table query returned NULL) — use the UNSET band's "Awaiting signal" label.

## Pattern 2 — adding a hero finding to a page archetype

For Dashboard / Profile / Article / Heisman archetypes. The hero finding is the top-of-page primitive.

### Code

```python
# In the page-renderer module:
from cfb_rankings.hero_findings import (
    generate_hub_finding, render_hero_finding_html, HeroFinding, FindingKind
)

# Generate the candidate — returns None when no data yet
finding = generate_hub_finding(db, season_year=season, week_iso=week)
if finding is None:
    # Honest empty-state — render the page without a hero finding rather
    # than fabricating data. The CSS allows for absent hero-finding;
    # the archetype's other modules carry the page.
    hero_html = ""
else:
    hero_html = render_hero_finding_html(finding)

return f'<main>{hero_html}{... rest of page ...}</main>'
```

### Fallback to hand-curated when needed

Some surfaces have hand-curated hero findings in existing tables (e.g., `hub_issue_metadata.cover_headline`). The generator returns None until the v5-7.5 DB-backed bodies ship. For now, use this pattern:

```python
finding = generate_hub_finding(db, ...)
if finding is None:
    # Fallback to existing hand-curated content
    hub_row = db.query_one(
        "SELECT cover_headline, cover_dek, cover_chart_caption "
        "FROM hub_issue_metadata ORDER BY week_start_date DESC LIMIT 1"
    )
    if hub_row:
        finding = HeroFinding(
            kind=FindingKind.COHORT_DIVERGENCE,
            number=_extract_number_from(hub_row["cover_headline"]),
            sentence=hub_row["cover_headline"],
            sample_caption=hub_row["cover_dek"][:96],
            sample_size=0,                   # unknown — chip will say "Awaiting signal"
            confidence_domain="fan_intel",
        )

hero_html = render_hero_finding_html(finding) if finding else ""
```

### Tests to add

```python
def test_hero_finding_rendered_when_data_present(populated_db):
    html = render_page(populated_db)
    assert 'class="hero-finding"' in html
    assert 'class="hero-finding__number"' in html

def test_no_hero_finding_when_data_absent(empty_db):
    html = render_page(empty_db)
    # No fabricated hero — page renders without
    assert 'class="hero-finding"' not in html
```

## Pattern 3 — adding the v5-7.5 hero pattern to a Profile (team) page

Profile archetypes have TWO hero-finding moments: the program identity at the top (always there) and the THIS-WEEK belief delta (optional, suppresses when no data). Use this pattern:

```python
from cfb_rankings.hero_findings import generate_team_finding, render_hero_finding_html

# After the program-hero block:
finding = generate_team_finding(
    db, team_id=team.team_id, season_year=season,
)
if finding is not None:
    html += render_hero_finding_html(
        finding,
        eyebrow_text=f"THIS WEEK · {team.short_name.upper()}",
    )
# When finding is None, the rest of the page (rituals, chronicle, ladder, etc.)
# carries the surface — no fabricated belief deltas.
```

## Pattern 4 — using share-card builders for OG image generation

The `viral/builders.py` module turns DB rows into render kwargs. Use this pattern when generating OG images for a page:

```python
from cfb_rankings.viral.builders import build_quote_card_input
from cfb_rankings.viral import quote_card

# For a Daily article's OG image:
kwargs = build_quote_card_input(db, edition_date=edition_date)
out = quote_card.render(
    f"output/site/assets/share/daily-{edition_date}.png",
    dark=False,                  # light variant for the og:image
    **kwargs,
)

# Also render the dark variant for iMessage / Slack share:
quote_card.render(
    f"output/site/assets/share/daily-{edition_date}-dark.png",
    dark=True,
    **kwargs,
)

# Both variants are <500KB; safe to commit to the published branch.
```

## Pattern 5 — Saturday Strip integration

For mobile-only pages — add the strip at the top of the body, BEFORE any other content:

```python
from cfb_rankings.mobile.saturday_strip import build_strip_state, render_strip_html

state = build_strip_state(db)
strip_html = render_strip_html(state)

# Mobile-only — the desktop site uses the regular site nav. The CSS
# handles the visibility:
#   @media (min-width: 768px) { .strip, .strip-off { display: none } }
return f'''
<!doctype html>
<html>
  <head>...</head>
  <body>
    {strip_html}
    <main>...</main>
  </body>
</html>
'''
```

## Feature-flagging your integration

Wrap the new behavior behind a config flag so it can be turned off if regressions appear:

```python
# In src/cfb_rankings/config.py:
class AppConfig:
    # ...
    enable_hero_findings: bool = False   # default OFF until verified
    enable_confidence_chips: bool = False
    enable_saturday_strip: bool = False
```

```python
# In the renderer:
config = AppConfig.from_env()
if config.enable_hero_findings:
    hero_html = render_hero_finding_html(...)
else:
    hero_html = ""
```

Once verified at scale, flip the default to `True` in `config.py` and remove the conditional.

## Verification checklist before merging an integration PR

Run each of these. If anything fails, the integration isn't ready.

```bash
# 1. New tests pass
python -m pytest tests/test_<your_module>.py

# 2. Existing tests still pass (no regressions)
python -m pytest tests/ -k "not voice_retry"   # skip 4 pre-existing failures

# 3. Design-system audits still clean
python scripts/design_system_audit.py

# 4. Build the site
python manage.py build-site

# 5. Verify the new chip / hero / strip renders in output
grep -c 'class="confidence' output/site/<your-page>.html
grep -c 'class="hero-finding' output/site/<your-page>.html

# 6. Run the live-site verification per the kickoff discipline rule
curl -s wonderful-margulis-8ec96b.vercel.app/<your-page>/ | \
    grep -o 'class="confidence--[^"]*"' | sort | uniq -c
```

## Common pitfalls

| Pitfall | Why it happens | Fix |
|---|---|---|
| Chip shows `--unset` everywhere | Calibration table is empty | Run `python manage.py recompute-confidence-thresholds` |
| Hero finding never renders | Generators are stubs (return None) | Use the hand-curated fallback pattern in Pattern 2 |
| Mobile site shows the desktop nav instead of the strip | Forgot the `@media` query | Verify `_mockup_shared.css` rules are inherited |
| Pillow ImportError on CI | Pillow is an optional dep | Add `pip install Pillow` to the workflow step |
| Tests pass locally but CI is red | conftest path issue | Make sure `tests/conftest.py` adds `src/` to sys.path |

## When to escalate (don't ship silently)

* The integration changes existing renderer output for >100 pages → owner review before merge
* The integration adds a new database column or table → write a migration in `migrations/` AND document the schema impact in the PR description
* The integration introduces a new external service dependency (X API, Slack, etc.) → owner credentials + secrets management need to land first

## Pattern 6 — Rituals strip on a profiled team page

**Goal**: Render the gameday-rituals horizontal strip (mockup_02_team_alabama_v2.html) just below the program-hero block on profiled team pages. Tier-aware intro copy, monogram-glyph cards, since-year, accessible (visually-hidden description for screen readers).

**When to use it**:
* Profiled team pages (slugs with a file in `profiles/*.md`)
* Anywhere a profile YAML carries a non-empty `rituals: []` list

**When NOT to use it**:
* Unprofiled programs (no profile YAML → no data → empty string returned)
* Tier-3 / sub-D1 surfaces where the rituals data is genuinely absent (no fabrication)

### The wire-up

```python
from cfb_rankings.team_pages.profile_loader import load_profile
from cfb_rankings.team_pages.rituals_module import (
    render_rituals_strip,
    render_cultural_anchors,
    render_visual_identity_chip,
)

profile = load_profile(slug)
rituals_html = render_rituals_strip(profile)           # 5-card horizontal strip
anchors_html = render_cultural_anchors(profile)        # optional sidebar
vi_chip_html = render_visual_identity_chip(profile)    # eyebrow chip

# In the page template, emit between program-hero and chronicle:
if rituals_html:
    page_html += rituals_html
if anchors_html:
    page_html += anchors_html
```

### Data contract (profile YAML frontmatter)

```yaml
rituals:
  - name: "Rammer Jammer"
    started_year: 1970
    when: "After victory"
    cultural_significance: "high"
    description: "Post-win chant…"
cultural_anchors:
  one_sentence: "Alabama is what college football looks like…"
  fan_archetype_dominant: "Process-Believer"
  outsider_archetype_dominant: "…"
  if_team_didnt_exist_cfb_would_lose: "…"
visual_identity_anchors:
  helmet_stripe_pattern: "alternating-3-stripe-crimson-white"
  signature_color_combination: "crimson-cream-houndstooth-grey"
```

### Defenses built in
* HTML-escapes user content (XSS) — ritual name/description, anchor copy
* Caps strip at 5 cards (per mockup) regardless of data length
* Drops ritual entries missing the required `name` field
* Returns "" (empty string) when no rituals — caller decides empty-state vs. omit

### Acceptance verification

```bash
# 1. Tests pass
python -m pytest tests/test_rituals_module.py -q
# Expected: 63 passed

# 2. Profile loads for all 17 currently-profiled teams
python -c "
from cfb_rankings.team_pages.profile_loader import load_profile
from cfb_rankings.team_pages.rituals_module import render_rituals_strip
for slug in ['alabama','auburn','florida','georgia','michigan',
             'notre-dame','ohio-state','oklahoma','oregon','penn-state',
             'tennessee','texas','usc','vanderbilt','washington',
             'massachusetts','uconn']:
    html = render_rituals_strip(load_profile(slug))
    assert html, f'{slug} returned empty'
    print(f'{slug}: OK')
"
```

---

## Pattern 7 — 30-second auto-summary on an article-archetype page

**Goal**: Render the locked `.auto-summary` block from `mockup_04_daily_v2.html` at the top of every article archetype (Daily, Mailbag, Reactions, Edition features). 2-3 short bullets per article; cached per (cache_key, body_hash).

**When to use it**:
* Daily editions
* Mailbag, Reactions, Wire long-form
* Any rendered article surface where 30-second readers need a TL;DR

**When NOT to use it**:
* Hub / landing pages (use a hero finding instead)
* Surfaces shorter than 200 chars (the function returns None)
* Anywhere the Rung-3 weekly ceiling is exhausted (auto-fallback to None)

### The wire-up

```python
from cfb_rankings.auto_summary import (
    generate_article_summary,
    render_auto_summary_html,
    CACHE_DDL,
)

# One-time: create cache table (idempotent)
db.execute(CACHE_DDL)

# Per-article: generate-or-cache, then render
summary = generate_article_summary(
    body_markdown=article.body_markdown,
    headline=article.title,
    dek=article.dek,
    cache_key=f"daily:{edition_date}",   # or f"mailbag:{slug}", etc.
    db=db,                                 # optional; omit = always-LLM
)
if summary:
    article_html = render_auto_summary_html(summary) + article_html
```

### Cost envelope
* ~$0.006 per LLM call (Pattern A: single-shot Sonnet, 400 max_tokens)
* Cached per (cache_key, body_hash) — same body byte-for-byte → cache hit
* 1 daily + 1 mailbag/week + ad-hoc reactions = ~$0.50/mo expected

### Defenses built in
* Returns None for bodies < 200 chars (too short to summarize)
* Returns None when LLM produces 0 parseable bullets (logged)
* Returns None when surface is Rung-3 ceiling-blocked
* HTML-escapes bullet content (XSS)
* Body excerpt truncates at 3000 chars (start 2200 + tail 700 + elision marker)
  to bound prompt tokens deterministically

### Acceptance verification

```bash
# 1. Tests pass
python -m pytest tests/test_auto_summary.py -q
# Expected: 31 passed

# 2. Live exercise against the real DB + a real article
python -c "
from cfb_rankings.db import Database
from cfb_rankings.auto_summary import generate_article_summary, CACHE_DDL
db = Database('sqlite:///../../../cfb_rankings.db')
db.execute(CACHE_DDL)  # idempotent
body = '… real daily-edition body markdown here, ≥200 chars …'
s = generate_article_summary(body, cache_key='smoke:test',
                              headline='Test', dek='', db=db)
print(s.bullets if s else 'None')
"
```

---

## Status as of 2026-05-17 (revised post-Window-B autonomous run)

Foundation slices shipped:
* `confidence.py` (37 tests) — ready to use today
* `hero_findings/` (17 tests; **all 4 generators wired** — hub uses cohort-divergence aggregator, daily reads daily_takes, heisman reads market_odds_weekly, team reads fanbase_mood_weekly) — ready to use today
* `mobile/saturday_strip.py` (9 tests) — ready to use
* `viral/` (30 tests, 5 share-card types) — renderers ready; CLI works against real DB
* `team_pages/rituals_module.py` (63 tests) — strip + cultural anchors + VI chip; data ready for all 17 profiled teams (master commit 95e7d5dd52)
* `auto_summary.py` (31 tests) — Pattern A 30-second summary; cache layer + render

Pending Window A coordination:
* Wiring chips into the existing `reporting.py` percentile + stat cell renderers
* Wiring hero-finding into `hub_page.py` / `heisman/` / `team_pages/` page entries
  (the generator bodies are now ready — only the call-site work remains)
* The bottom-nav rendering touches every existing mobile-page template
* Wiring `render_rituals_strip` into the team-pages page entry between
  program-hero and chronicle (the module is renderer-only; caller decides
  position and empty-state policy)
* Wiring `render_auto_summary_html` above the article body on Daily,
  Mailbag, Reactions, and Edition-feature renderers

See [`v5_followups.md`](../octopus/v5_followups.md) for the full punch list.
