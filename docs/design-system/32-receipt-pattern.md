# Receipt Pattern — Citation System for AI Editorial

**Locked 2026-05-17 (v2-addendum Sprint v5-5.5)**

CFB Index's Pattern C/D AI editorial outputs are grounded in real sources (Reddit threads, beat-writer columns, podcast quotes, Wikipedia, CFBD, etc.). The Receipt Pattern surfaces those sources inline so readers can verify any claim.

This is the single biggest credibility signal AI-generated content can have in the 2026 post-AI-flood era. Without it, AI editorial reads as slop. With it, AI editorial reads as curated source synthesis.

---

## The pattern in one paragraph

Every factual or interpretive claim in Pattern C/D output carries an inline superscript citation marker. Hovering (desktop) or tapping (mobile) the marker reveals the source. A footer at the bottom of every article lists all citations with full attribution and links. The Pattern C/D system prompt is instrumented to refuse claims that can't be cited. A citation_critic role validates that markers in prose match citation entries in the structured output.

---

## Wire format (LLM output schema)

```python
from typing import TypedDict, Literal

class Citation(TypedDict):
    id: int                                          # superscript number in body_markdown
    source_kind: Literal[
        "reddit",         # Reddit thread or comment
        "beat_writer",    # Beat-writer column (Stewart Mandel, Pete Thamel, etc.)
        "podcast",        # Podcast episode (Locked On, On3, etc.)
        "wikipedia",      # Wikipedia article
        "official",       # Team/conference/NCAA official source
        "cfbd",           # CollegeFootballData.com API data
        "wire",           # CFB Index Wire entry (internal source)
        "edition",        # Prior CFB Index edition
    ]
    source_url: str | None                           # canonical URL (None for non-web sources)
    source_label: str                                # display label (e.g., "Stewart Mandel · The Athletic · May 12, 2026")
    source_date: str | None                          # ISO date for sorting
    confidence: Literal["primary", "supporting", "background"]
    # primary = the claim's foundation; supporting = corroborates; background = context

class PatternCOutput(TypedDict):
    body_markdown: str                                # prose with [N] inline markers matching citation ids
    headline: str
    dek: str | None
    citations: list[Citation]                         # REQUIRED
    confidence: Literal["high", "medium", "low"]      # REQUIRED — see 33-confidence-signaling.md
    sample_size: dict[str, int] | None                # e.g., {"reddit_mentions": 247, "beat_articles": 3}
```

**Critical constraint:** every `[N]` marker in `body_markdown` MUST have a matching entry in `citations`. The `citation_critic` enforces this.

---

## Pattern C/D system prompt extension

Add to all Pattern C and Pattern D system prompts:

```
CITATION REQUIREMENT (non-negotiable):

For every factual or interpretive claim you make, include a [N] superscript
marker in your body_markdown referring to a citation entry in your structured
output. The citation must include:
- source_kind (one of the 8 enum values)
- source_url (or null if non-web)
- source_label (display-friendly string with author + outlet + date)
- source_date (ISO format if known)
- confidence (primary, supporting, or background)

Available sources for this generation are provided in the prompt_context as
`available_sources`. Each has a stable id. Reference them by id in your
citations[] array.

If you cannot cite a source for a claim, do not make the claim. Substitute
softer language ("the discourse suggests...") or omit. Confident claims
without citations are the single biggest credibility risk for AI-generated
editorial.

Citation density target: at least 1 citation per 200 words of prose. Articles
with <1 per 400 words will be flagged by the citation_critic.
```

---

## Citation critic role

New role added to `quality_loop.py`:

```python
class CitationCritic:
    """Validates receipt pattern in Pattern C/D output.

    Checks:
    1. Every [N] marker in body_markdown has a matching citation entry
    2. Every citation entry has a real source_url OR a verifiable source_label
    3. Citation density >= 1 per 200 words (warn if <1 per 400)
    4. Citation source_kinds match available_sources from prompt_context
       (catches hallucinated sources — "Stewart Mandel said X" when Mandel
       wasn't in the available_sources list)
    5. confidence field in PatternCOutput is one of high/medium/low
    6. sample_size dict matches available_sources counts
    """

    model: Literal["haiku-4.5", "sonnet-4.6"] = "sonnet-4.6"  # Sonnet recommended for citation cross-check

    def critique(self, output: PatternCOutput, available_sources: list[Source]) -> CriticVerdict:
        issues = []

        # Extract [N] markers from body
        markers_in_body = set(re.findall(r'\[(\d+)\]', output["body_markdown"]))
        citation_ids = {str(c["id"]) for c in output["citations"]}

        missing_citations = markers_in_body - citation_ids
        orphan_citations = citation_ids - markers_in_body

        if missing_citations:
            issues.append({
                "severity": "blocker",
                "type": "missing_citation",
                "detail": f"Body has markers {missing_citations} with no matching citation entry"
            })

        if orphan_citations:
            issues.append({
                "severity": "warning",
                "type": "orphan_citation",
                "detail": f"Citations {orphan_citations} have no marker in body — remove or reference"
            })

        # Validate sources match available_sources
        available_labels = {s.label.lower() for s in available_sources}
        for c in output["citations"]:
            label_lower = c["source_label"].lower()
            # Fuzzy match — does at least one word from citation label match any available source?
            if not any(word in available_labels for word in label_lower.split() if len(word) > 3):
                issues.append({
                    "severity": "blocker",
                    "type": "hallucinated_source",
                    "detail": f"Citation '{c['source_label']}' doesn't match any available_source"
                })

        # Citation density
        word_count = len(output["body_markdown"].split())
        density = len(output["citations"]) / (word_count / 200) if word_count > 0 else 0
        if density < 0.5:
            issues.append({
                "severity": "warning",
                "type": "low_citation_density",
                "detail": f"{len(output['citations'])} citations in {word_count} words (density {density:.2f}; target >= 1.0 per 200 words)"
            })

        passed = not any(i["severity"] == "blocker" for i in issues)
        return CriticVerdict(passed=passed, issues=issues, score=...)
```

---

## prompt_context/builders.py extension

Every builder must populate `available_sources` in the prompt context:

```python
def build_daily_lead_context(date_, db) -> dict:
    """Build the prompt context for a daily lead Pattern C generation."""

    # ... existing context building ...

    # NEW: pull all sources that could feed this lead
    available_sources = []

    # Reddit threads from last 48 hours, sorted by engagement
    for row in db.execute("""
        SELECT thread_id, subreddit, title, score, num_comments, url, created_utc
        FROM conversation_documents
        WHERE source_kind = 'reddit'
          AND created_at_utc > datetime(:date, '-2 days')
          AND score >= 50
        ORDER BY score DESC LIMIT 25
    """, date=date_.isoformat()):
        available_sources.append({
            "id": f"reddit_{row['thread_id']}",
            "kind": "reddit",
            "label": f"r/{row['subreddit']} · {row['title'][:80]} · {row['num_comments']} replies",
            "url": row["url"],
            "date": row["created_utc"],
        })

    # Beat writer columns from last 7 days
    for row in db.execute("""
        SELECT entry_id, author, outlet, title, url, published_at
        FROM beat_writer_entries
        WHERE published_at > datetime(:date, '-7 days')
        ORDER BY published_at DESC LIMIT 25
    """, date=date_.isoformat()):
        available_sources.append({
            "id": f"beat_{row['entry_id']}",
            "kind": "beat_writer",
            "label": f"{row['author']} · {row['outlet']} · \"{row['title']}\"",
            "url": row["url"],
            "date": row["published_at"],
        })

    # Podcast episodes from last 14 days
    # ... similar patterns for podcast_episodes, wikipedia_pageviews, etc.

    context["available_sources"] = available_sources
    return context
```

Each Tier-1 builder (12 surfaces per `IMPLEMENTATION_PLAN.md`) gets this treatment.

---

## Render treatment

### Inline citation marker

HTML:
```html
<sup class="citation"
     data-cite-id="3"
     data-cite-label="Stewart Mandel · The Athletic · May 12, 2026"
     data-cite-url="https://theathletic.com/...">
  [3]
</sup>
```

CSS:
```css
.citation {
  font-size: 0.75em;
  font-feature-settings: "sups" 1;
  color: var(--color-amber-600);
  font-weight: var(--fw-medium);
  cursor: pointer;
  text-decoration: none;
  padding: 0 0.1em;
}

.citation:hover,
.citation:focus-visible {
  background: var(--color-amber-50);
  border-radius: var(--radius-sm);
  outline: 1px solid var(--color-amber-200);
}

/* Tooltip on desktop hover */
@media (hover: hover) and (min-width: 768px) {
  .citation:hover::after,
  .citation:focus-visible::after {
    content: attr(data-cite-label);
    position: absolute;
    background: var(--color-ink);
    color: var(--color-surface);
    padding: var(--sp-2) var(--sp-3);
    border-radius: var(--radius-md);
    font-size: 12px;
    font-feature-settings: normal;
    max-width: 32ch;
    z-index: 100;
    margin-top: 1em;
    margin-left: -0.5em;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  }
}

/* On mobile, tap-reveal via JS (no hover) */
.citation[aria-expanded="true"] + .citation-detail {
  display: block;
}
```

JS (minimal, for mobile tap-reveal):
```javascript
// Tap citation → expand inline detail below it
document.querySelectorAll('.citation').forEach(c => {
  c.addEventListener('click', e => {
    e.preventDefault();
    const expanded = c.getAttribute('aria-expanded') === 'true';
    c.setAttribute('aria-expanded', !expanded);
  });
});
```

### Footer citation list

HTML:
```html
<footer class="article-citations">
  <h3 class="citations-header">Sources</h3>
  <ol class="citations-list">
    <li id="cite-1">
      <span class="cite-num">[1]</span>
      <span class="cite-author">Stewart Mandel</span>
      <span class="cite-outlet">The Athletic</span>
      <span class="cite-title">"Texas A&M-Texas rivalry redraws SEC recruiting"</span>
      <a href="..." class="cite-link">May 12, 2026 →</a>
    </li>
    <li id="cite-2">
      <span class="cite-num">[2]</span>
      <span class="cite-author">r/CFB community</span>
      <span class="cite-outlet">Reddit</span>
      <span class="cite-title">"Sark vs Kirby: actual offer-list data"</span>
      <a href="..." class="cite-link">318 replies · May 14, 2026 →</a>
    </li>
    <!-- ... -->
  </ol>
  <p class="citations-note">
    CFB Index editorial is AI-synthesized and grounded in real sources.
    Every claim above is traceable to at least one cited source.
    <a href="/methodology/citations">How we cite →</a>
  </p>
</footer>
```

CSS:
```css
.article-citations {
  margin-top: var(--sp-12);
  padding-top: var(--sp-6);
  border-top: var(--stroke-std) solid var(--color-line);
  font-family: var(--font-ui);
  font-size: 14px;
  line-height: 1.55;
  color: var(--color-text-muted);
}

.citations-header {
  font-family: var(--font-display);
  text-transform: uppercase;
  letter-spacing: var(--tracking-label);
  font-size: 12px;
  margin-bottom: var(--sp-4);
}

.citations-list {
  list-style: none;
  padding: 0;
}

.citations-list li {
  padding: var(--sp-3) 0;
  border-bottom: var(--stroke-hair) solid var(--color-line-subtle);
}

.cite-num {
  display: inline-block;
  width: 2.5em;
  color: var(--color-amber-600);
  font-weight: var(--fw-medium);
}

.cite-author {
  font-weight: var(--fw-medium);
  color: var(--color-text);
}

.cite-outlet {
  color: var(--color-text-muted);
}

.cite-title {
  font-style: italic;
}

.cite-link {
  color: var(--color-navy-600);
  text-decoration: underline;
}

.citations-note {
  margin-top: var(--sp-6);
  font-style: italic;
  color: var(--color-text-subtle);
}
```

---

## Database schema

Migration `editorial_citations`:

```sql
CREATE TABLE IF NOT EXISTS editorial_citations (
  citation_id INTEGER PRIMARY KEY AUTOINCREMENT,
  generation_id INTEGER NOT NULL,  -- foreign key to llm_usage_log.generation_id
  marker_id INTEGER NOT NULL,      -- the [N] number in body_markdown
  source_kind TEXT NOT NULL CHECK (source_kind IN (
    'reddit', 'beat_writer', 'podcast', 'wikipedia', 'official', 'cfbd', 'wire', 'edition'
  )),
  source_url TEXT,
  source_label TEXT NOT NULL,
  source_date TEXT,
  confidence TEXT NOT NULL CHECK (confidence IN ('primary', 'supporting', 'background')),
  created_at_utc TEXT NOT NULL DEFAULT (datetime('now')),

  FOREIGN KEY (generation_id) REFERENCES llm_usage_log(generation_id)
);

CREATE INDEX IF NOT EXISTS idx_editorial_citations_generation
  ON editorial_citations(generation_id);

CREATE INDEX IF NOT EXISTS idx_editorial_citations_source_kind
  ON editorial_citations(source_kind);

CREATE INDEX IF NOT EXISTS idx_editorial_citations_date
  ON editorial_citations(source_date);
```

Used by:
- `receipts/render.py` reads citations by generation_id when rendering an article
- Citation_critic validates writes
- Future audit tooling counts citations per surface per week

---

## Implementation module

New module `src/cfb_rankings/receipts/`:

```
src/cfb_rankings/receipts/
├── __init__.py
├── persistence.py        # CRUD for editorial_citations table
├── critic.py             # CitationCritic implementation
├── render.py             # HTML rendering: inline markers + footer list
└── assets/
    └── receipts.css      # see CSS above
```

---

## Backward compatibility — FORWARD ONLY

**Policy locked:** Pattern C/D content published BEFORE the receipt pattern launches does NOT get retroactive citations.

Why: retroactively assigning sources risks misattribution (hallucinating sources we didn't actually use during the original generation). Better to be honest about the transition than to fake retroactive citations.

Visual treatment for legacy content:
```html
<aside class="legacy-pre-citation-notice">
  <p>This piece was published before our citation pattern launched on
  <time datetime="2026-05-17">May 17, 2026</time>. New CFB Index editorial
  includes inline source citations.
  <a href="/methodology/citations">Learn more →</a></p>
</aside>
```

What DOES get cleaned from legacy content: Pattern C output that was actually fall-back to seed (the "Awaiting Signal" fallback path). Those get regenerated with the new citation-enabled prompt, OR removed entirely if not regeneratable.

---

## Acceptance criteria for v5-6a.5 sprint

- 100% of NEW Pattern C/D output has citations
- citation_critic catches missing citations 95%+ of the time
- citation_critic catches hallucinated sources 90%+ of the time (validated via test fixtures with deliberately mismatched sources)
- Live site `/daily/` shows citation superscripts in editorial content
- Tap-reveal works on mobile (no hover dependency)
- Citation density average across last 4 weeks of editorial >= 1.0 per 200 words

## Kill criteria

If citation quality <80% accurate after 2 weeks of operation:
- Demote affected surfaces to Pattern B (single critic, no critique loop)
- Pause the v5-6a.5 rollout
- Diagnose: is it the prompt? the critic? the source-matching? available_sources gaps?
- Don't push forward with bad citations live — they're worse than no citations

---

## Future extensions (deferred to v6)

- Citation hover-preview with thumbnail (for visual sources)
- "Highly-cited sources this week" leaderboard (Reddit threads + columns CFB Index cites most often)
- Citation export per article (BibTeX or CSL JSON for academic use)
- Source-trust scoring (give beat writers a trust grade, weight citations)

These are post-launch. Ship the basic pattern first.

---

## Why this is the single biggest 2026 lever

Every AI-generated content site looks the same: confident prose with no sources. The signal that distinguishes "AI slop" from "AI editorial worth reading" is whether the AI shows its work.

CFB Index has a unique opportunity here because:
- It already ingests Reddit + beat writers + podcasts (the sources exist in the DB)
- It runs Pattern C/D critique loops (the architecture for source enforcement exists)
- Solo dev + AI editorial team means receipt-pattern discipline is enforceable from day one

No other CFB site does this. No major AI-content site does it well. Receipt pattern done right is a permanent moat.
