# Autopilot v1 — End-to-End Audit · 2026-04-24 08:48 UTC

**13/14** checks pass.

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | source_registry §3 family coverage | ✅ PASS | 18/18 families present |
| 2 | conversation_document_targets season coverage | ✅ PASS | 2016:1 / 2022:1,738 / 2023:1,836 / 2024:4,089 / 2025:12,508 |
| 3 | conversation_document_targets player scope | ✅ PASS | 10,017 player-target rows / 1218 distinct players |
| 4 | player_week_conversation_features populated | ✅ PASS | 7,297 rows / 1212 players |
| 5 | player_advanced_metrics multi-season | ✅ PASS | 2022:20,121 / 2023:20,963 / 2024:0 / 2025:36,708 / 2026:0 |
| 6 | player_honors scoped rows | ✅ PASS | 57 rows across scopes: {'national_award': 57} |
| 7 | player_nfl_draft populated 2022-2025 | ✅ PASS | 1035 picks · 2022:262 / 2023:259 / 2024:257 / 2025:257 |
| 8 | player_draft_projection schema | ✅ PASS | 0 projection rows (table present, rows expected from per-source scrapers) |
| 9 | workflow artifact pattern | ✅ PASS | 6/6 workflows wire the DB artifact |
| 10 | publish_site.yml present | ✅ PASS | publish_site.yml present |
| 11 | cohort divergence nonzero cells | ✅ PASS | 58 (team, week) pairs with divergence_score > 0 |
| 12 | CJ Carr page renders modules | ❌ FAIL | Carr page missing: ['algorithmic-signature'] |
| 13 | methodology + freshness pages | ✅ PASS | fan-intelligence.html + freshness.html both present |
| 14 | Database retry wrapper present | ✅ PASS | db.py _with_retry wrapper present |

## Follow-ups

- Investigate: **CJ Carr page renders modules**
