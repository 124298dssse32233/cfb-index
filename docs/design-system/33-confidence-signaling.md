# Confidence Signaling System

**Locked 2026-05-17 (v2-addendum Sprint v5-5.5)**

Every named metric on CFB Index carries a confidence level. The reader always knows whether to trust the number.

This is the 538-class transparency discipline applied site-wide: don't just show the number, show the dial.

---

## The three confidence levels

Three levels, no more. Simplicity is the discipline.

| Level | Visual | When to use |
|---|---|---|
| **High** | green chip `✓ high` | Sample size well above peer-week median; high-confidence model output; multi-year historical depth |
| **Medium** | amber chip `• medium` | Sample size in normal peer-week range; model "medium" confidence; partial historical depth |
| **Low** | grey chip italic `? low` | Sample size below peer-week median; model "low" confidence; thin historical record |
| **(insufficient)** | metric suppressed entirely | Below the minimum threshold — metric is not displayed; "(insufficient data)" placeholder if metric slot must exist |

---

## Calibration methodology

Thresholds are NOT arbitrary — they're calibrated against actual data distribution per domain.

### Calibration query (run quarterly)

```sql
-- fan_intel domain: per-team-week conversation_documents count
WITH per_team_week AS (
  SELECT team_id,
         strftime('%Y-%W', created_at_utc) AS week,
         COUNT(*) AS doc_count
  FROM conversation_documents cd
  JOIN conversation_document_targets cdt ON cd.document_id = cdt.document_id
  WHERE cd.created_at_utc > datetime('now', '-90 days')
  GROUP BY team_id, week
)
SELECT
  'fan_intel_per_team_week' AS metric,
  COUNT(*) AS sample_count,
  MIN(doc_count) AS min_value,
  MAX(doc_count) AS max_value,
  ROUND(AVG(doc_count), 1) AS mean_value,
  -- Quartile breakpoints (these become the threshold values)
  (SELECT doc_count FROM per_team_week ORDER BY doc_count
   LIMIT 1 OFFSET (SELECT CAST(COUNT(*) * 0.10 AS INT) FROM per_team_week)) AS p10,
  (SELECT doc_count FROM per_team_week ORDER BY doc_count
   LIMIT 1 OFFSET (SELECT CAST(COUNT(*) * 0.25 AS INT) FROM per_team_week)) AS p25,
  (SELECT doc_count FROM per_team_week ORDER BY doc_count
   LIMIT 1 OFFSET (SELECT CAST(COUNT(*) * 0.50 AS INT) FROM per_team_week)) AS p50,
  (SELECT doc_count FROM per_team_week ORDER BY doc_count
   LIMIT 1 OFFSET (SELECT CAST(COUNT(*) * 0.75 AS INT) FROM per_team_week)) AS p75,
  (SELECT doc_count FROM per_team_week ORDER BY doc_count
   LIMIT 1 OFFSET (SELECT CAST(COUNT(*) * 0.90 AS INT) FROM per_team_week)) AS p90
FROM per_team_week;
```

### Threshold mapping

Once you have the percentile breakpoints, set thresholds:

- **High confidence** = at or above p75 (top quartile of team-weeks)
- **Medium confidence** = p25 to p75 (middle 50%)
- **Low confidence** = below p25 (bottom quartile)
- **Insufficient** = below p10 (suppress metric)

Re-run the calibration query quarterly. Update the threshold values in `src/cfb_rankings/confidence.py`. Self-adjusts as data volumes change over time.

**Initial calibration values (placeholder until SQL is run):**

```python
# src/cfb_rankings/confidence.py
"""
CONFIDENCE_THRESHOLDS — values calibrated 2026-05-17.
Last re-calibration: PENDING (run the SQL in docs/design-system/33-confidence-signaling.md)
Next re-calibration due: 2026-08-17 (quarterly)

NOTE: Initial values are educated guesses. After first calibration run,
replace with actual percentile values from production data.
"""

CONFIDENCE_THRESHOLDS = {
    "fan_intel": {
        # per-team-week mention count
        "high":   {"min_mentions": 500, "min_sources": 5},
        "medium": {"min_mentions": 100, "min_sources": 3},
        "low":    {"min_mentions": 30,  "min_sources": 2},
        # below low → suppress metric
    },
    "historical": {
        # depth of historical record backing the metric
        "high":   {"min_seasons": 10, "min_games": 100},
        "medium": {"min_seasons": 5,  "min_games": 50},
        "low":    {"min_seasons": 3,  "min_games": 20},
    },
    "model": {
        # uses model's own confidence output (e.g., from heisman_rankings_weekly)
        "high":   0.80,
        "medium": 0.60,
        "low":    0.40,
    },
    "betting_market": {
        # market liquidity proxy
        "high":   {"min_volume_usd": 100_000, "min_books": 5},
        "medium": {"min_volume_usd":  20_000, "min_books": 3},
        "low":    {"min_volume_usd":   5_000, "min_books": 2},
    },
}
```

---

## Implementation module

```python
# src/cfb_rankings/confidence.py

from typing import Literal, TypedDict
from html import escape

ConfidenceLevel = Literal["high", "medium", "low", "insufficient"]


def confidence_level(domain: str, **measurements) -> ConfidenceLevel:
    """Return confidence level for a domain + measurements.

    Args:
        domain: One of "fan_intel", "historical", "model", "betting_market"
        **measurements: Domain-specific kwargs. For "fan_intel", pass
                        n_mentions= and n_sources=. For "historical", pass
                        n_seasons= and n_games=. Etc.

    Returns:
        Confidence level. Use to suppress display if "insufficient".
    """
    if domain not in CONFIDENCE_THRESHOLDS:
        raise ValueError(f"Unknown domain: {domain}")

    th = CONFIDENCE_THRESHOLDS[domain]

    if domain == "fan_intel":
        n = measurements.get("n_mentions", 0)
        s = measurements.get("n_sources", 0)
        if n >= th["high"]["min_mentions"] and s >= th["high"]["min_sources"]:
            return "high"
        if n >= th["medium"]["min_mentions"] and s >= th["medium"]["min_sources"]:
            return "medium"
        if n >= th["low"]["min_mentions"] and s >= th["low"]["min_sources"]:
            return "low"
        return "insufficient"

    if domain == "historical":
        seasons = measurements.get("n_seasons", 0)
        games = measurements.get("n_games", 0)
        if seasons >= th["high"]["min_seasons"] and games >= th["high"]["min_games"]:
            return "high"
        if seasons >= th["medium"]["min_seasons"] and games >= th["medium"]["min_games"]:
            return "medium"
        if seasons >= th["low"]["min_seasons"] and games >= th["low"]["min_games"]:
            return "low"
        return "insufficient"

    if domain == "model":
        score = measurements.get("model_confidence", 0.0)
        if score >= th["high"]: return "high"
        if score >= th["medium"]: return "medium"
        if score >= th["low"]: return "low"
        return "insufficient"

    if domain == "betting_market":
        vol = measurements.get("volume_usd", 0)
        books = measurements.get("n_books", 0)
        if vol >= th["high"]["min_volume_usd"] and books >= th["high"]["min_books"]:
            return "high"
        if vol >= th["medium"]["min_volume_usd"] and books >= th["medium"]["min_books"]:
            return "medium"
        if vol >= th["low"]["min_volume_usd"] and books >= th["low"]["min_books"]:
            return "low"
        return "insufficient"

    raise ValueError(f"Domain {domain} not handled in switch")


def confidence_chip_html(level: ConfidenceLevel, label: str | None = None) -> str:
    """Render the colored confidence chip."""
    if level == "insufficient":
        return ""  # suppress; caller should not display the metric at all

    icons = {"high": "✓", "medium": "•", "low": "?"}
    color_vars = {
        "high": "--color-green-400",
        "medium": "--color-amber-400",
        "low": "--color-gray-400",
    }
    italic = ' style="font-style: italic"' if level == "low" else ""
    display_label = escape(label) if label else level

    return (
        f'<span class="confidence-chip confidence-{level}"'
        f' aria-label="Confidence: {level}"{italic}>'
        f'{icons[level]} {display_label}'
        f'</span>'
    )


def sample_size_chip_html(domain: str, **measurements) -> str:
    """Render the inline sample-size chip for a metric.

    Example output: '<span class="sample-chip">n=247 · 5 sources · medium</span>'
    """
    level = confidence_level(domain, **measurements)
    if level == "insufficient":
        return ""

    parts = []
    if "n_mentions" in measurements:
        parts.append(f"n={measurements['n_mentions']:,}")
    if "n_sources" in measurements:
        parts.append(f"{measurements['n_sources']} sources")
    if "n_seasons" in measurements:
        parts.append(f"{measurements['n_seasons']} seasons")
    if "n_games" in measurements:
        parts.append(f"{measurements['n_games']:,} games")
    if "model_confidence" in measurements:
        parts.append(f"model {measurements['model_confidence']:.0%}")

    parts.append(level)
    return f'<span class="sample-chip sample-chip--{level}">{" · ".join(parts)}</span>'
```

---

## Render treatment

### Confidence chip CSS

```css
.confidence-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.25em;
  padding: 0.125em 0.5em;
  border-radius: var(--radius-full);
  font-family: var(--font-ui);
  font-size: 11px;
  font-weight: var(--fw-medium);
  letter-spacing: var(--tracking-label);
  text-transform: uppercase;
  white-space: nowrap;
}

.confidence-high {
  background: var(--color-green-50);
  color: var(--color-green-800);
}

.confidence-medium {
  background: var(--color-amber-50);
  color: var(--color-amber-800);
}

.confidence-low {
  background: var(--color-gray-50);
  color: var(--color-gray-600);
  font-style: italic;  /* extra "I'm tentative" signal */
}

.sample-chip {
  display: inline-block;
  font-family: var(--font-ui);
  font-size: 11px;
  color: var(--color-text-muted);
  font-variant-numeric: tabular-nums;
  padding: 0.125em 0.5em;
  background: var(--color-line-subtle);
  border-radius: var(--radius-sm);
}

.sample-chip--high { color: var(--color-green-800); background: var(--color-green-50); }
.sample-chip--medium { color: var(--color-amber-800); background: var(--color-amber-50); }
.sample-chip--low { color: var(--color-gray-600); font-style: italic; }
```

### Usage examples

In a Hub finding:
```html
<div class="hero-finding">
  <p class="finding-eyebrow">THIS WEEK IN BELIEF DIVERGENCE</p>
  <p class="finding-number">47 of 130</p>
  <p class="finding-sentence">teams diverged from model rank this week</p>
  <p class="finding-caption">
    <span class="sample-chip sample-chip--high">n=202,341 · 47 sources · high</span>
    · last 7 days
  </p>
</div>
```

In a team page mood card:
```html
<div class="mood-card">
  <p class="mood-eyebrow">FAN BELIEF</p>
  <p class="mood-score">72</p>
  <p class="mood-sample">
    <span class="sample-chip sample-chip--medium">n=247 · 5 sources · medium</span>
  </p>
</div>
```

In a Heisman card:
```html
<div class="heisman-card">
  <p class="player-name">CJ Carr · QB · Notre Dame</p>
  <p class="heisman-odds">38.4%</p>
  <p class="heisman-sample">
    <span class="sample-chip sample-chip--high">model 87% · 12 seasons · high</span>
  </p>
</div>
```

---

## When to suppress vs show "(insufficient)"

Two policies, depending on context:

### Suppress entirely (default)
For most metric displays, if confidence is "insufficient," don't render anything. Hub findings rotate to a different candidate; team Mood Card simply hides the mood number for that team; Heisman card is omitted from the visible board.

### Show "(insufficient data)" placeholder (specific contexts)
When a layout slot MUST be filled (e.g., a team page Pulse module that's always rendered), use a placeholder:

```html
<div class="mood-card mood-card--empty">
  <p class="mood-eyebrow">FAN BELIEF</p>
  <p class="mood-empty">(insufficient data — minimum 30 mentions needed)</p>
  <p class="mood-note">
    Check back as the season progresses; this team's discussion volume
    is below our reporting threshold this week.
  </p>
</div>
```

Honest about the gap. The reader appreciates the transparency more than a fake number.

---

## Migration to existing renderers

Window B Sprint v5-7.5 wires the confidence chip into every existing renderer that displays a named metric. Prioritized order:

1. Hub page (highest visibility, most metrics)
2. Heisman page (every player card)
3. Team pages — Pulse module (mood scores)
4. Team pages — Savant card (percentile bars)
5. Daily edition (hero findings)
6. Mailbag (when answers reference specific metrics)
7. All other surfaces — bulk pass via search + replace

Per-renderer change pattern:

**Before:**
```python
def render_mood_score(score: int) -> str:
    return f'<p class="mood-score">{score}</p>'
```

**After:**
```python
from cfb_rankings.confidence import sample_size_chip_html

def render_mood_score(score: int, n_mentions: int, n_sources: int) -> str:
    chip = sample_size_chip_html(
        "fan_intel",
        n_mentions=n_mentions,
        n_sources=n_sources,
    )
    if not chip:
        # insufficient data — render empty state
        return '<p class="mood-empty">(insufficient data)</p>'
    return f'<p class="mood-score">{score}</p>{chip}'
```

---

## Acceptance criteria

After Sprint v5-7.5 ships:

- Every named metric on Hub, Heisman, team pages, Daily includes a sample-size chip OR is suppressed
- `confidence_level()` function returns one of {high, medium, low, insufficient} for every domain
- Chips render in 3 distinct colors (green/amber/grey)
- `prefers-reduced-motion` users see no animation on chip state transitions
- Color-blind users can distinguish levels via icon (✓/•/?) and italic styling, not color alone
- Calibration SQL is documented and re-runnable
- Initial confidence values are placeholder; quarterly re-calibration is scheduled

---

## Color-blind safety

Confidence chips combine THREE redundant encodings:
1. **Color** (green / amber / grey)
2. **Icon** (✓ / • / ?)
3. **Italic** (low only; high and medium are upright)

This satisfies WCAG accessibility for color-blind users. Sample-size chips additionally include the level text ("medium," etc.) for screen readers.

---

## "Why we show the dial" — the public methodology

A dedicated methodology page should explain the confidence system publicly:

`/methodology/confidence`

```
HOW WE SIGNAL CONFIDENCE

CFB Index shows a confidence chip next to every metric. We do this
because no number is meaningful without context.

✓ HIGH confidence means we have substantial data backing the metric —
  for fan-belief scores, that's 500+ mentions across 5+ sources this
  week. For historical metrics, that's 10+ years of comparable data.

• MEDIUM confidence means we have normal-range data — what we typically
  see for an average team in an average week.

? LOW confidence (in italics) means we have thin data — fewer mentions
  than usual, or thinner historical record. The number is real, but
  treat it as preliminary.

When data drops below our minimum threshold, we don't show a number
at all. We'd rather say "we don't know" than guess.

We recalibrate the thresholds quarterly against the actual distribution
of data we're seeing, so "high" always means "high relative to current
typical volume."

Why this matters: in 2026 every AI-content site shows confident-sounding
prose. CFB Index shows you when to trust the confidence.
```

This page builds reader trust the way 538's methodology pages did. Link to it from every chip's `:focus-visible` tooltip.
