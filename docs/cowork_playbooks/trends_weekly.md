# Google Trends Weekly Export Playbook

**Cadence**: Weekly, Monday morning (STRATEGY §7 Tier 2 / §3 `google_trends_dma`).
**Time budget**: 15 minutes.
**Source**: `google_trends_dma` — Tier C, rank-only publication.

Google Trends publishes 0–100 values that are silently rebaselined against whatever else was trending — so a score of "80 for Alabama" on week 1 and "80 for Alabama" on week 2 are not comparable numbers. We therefore publish **DMA-level regional rank only** (e.g., "Alabama is the #1 CFB query in the Atlanta DMA this week"), never the 0–100 value.

---

## DMA list (20)

One DMA per priority_teams row, chosen for geographic centrality:

| Team | DMA |
|---|---|
| Alabama | Birmingham-Tuscaloosa |
| Georgia | Atlanta |
| LSU | New Orleans |
| Tennessee | Knoxville |
| Texas | Austin |
| Ohio State | Columbus, OH |
| Michigan | Detroit |
| Penn State | Harrisburg-Lancaster |
| Oregon | Portland, OR |
| Clemson | Greenville-Spartanburg |
| Florida State | Tallahassee |
| Miami | Miami-Ft. Lauderdale |
| Texas Tech | Lubbock |
| Kansas State | Wichita-Hutchinson |
| BYU | Salt Lake City |
| Boise State | Boise |
| Memphis | Memphis |
| Tulane | New Orleans |
| Jackson State | Jackson, MS |
| Howard | Washington, DC |

---

## Extraction steps

1. Open `https://trends.google.com/trends/explore?geo=US-{state}&q={team_name}%20football` for each priority team. Cowork navigates.
2. Switch time range to "Past 7 days."
3. Scroll to "Interest by subregion." Extract:
    - The team's rank among "related queries" in that DMA (e.g., "Alabama football" ranks #3 in Birmingham-Tuscaloosa this week).
    - The top 5 related queries in the DMA.
4. Export the page as CSV if the export button is available; otherwise record the ranks in Cowork chat and Claude writes a YAML block.

---

## Row schema

```yaml
source_id:     google_trends_dma
source_tier:   C
team_id:       <from priority_teams>
dma_code:      <Google's DMA code, e.g. "US-AL-630">
dma_name:      Birmingham-Tuscaloosa
week_start:    YYYY-MM-DD (Monday)
team_rank_in_dma: 3
top_related_queries: ["alabama vs auburn", "alabama score", ...]
capture_url:   full trends URL
demographic_slice: regional_search
observed_at_utc: ISO-8601
ingestion_adapter_version: 0.1.0-manual
dedup_key:     sha1("{team_id}|{dma_code}|{week_start}")
```

---

## CSV import (if export button was used)

```
python manage.py trends-import --week=YYYY-WW --csv=path/to/export.csv
```

The CLI (TASK 6.3 follow-up) maps CSV columns to the schema above and writes into `conversation_documents` with `source_id=google_trends_dma`. Ranks flow to the `local_market` and `national_narrative` cohorts per STRATEGY §4 weights.

---

## Publication rule reminder

- Display: "Alabama is the #1 CFB search query in Birmingham this week."
- Never display: "Alabama scored 80 on Google Trends this week."
- Aggregates: Trends DMA ranks contribute to Tier C of the `local_market` cohort only. Never raw numbers.
