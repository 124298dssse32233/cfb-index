# Wave 1+2 integration: 6 sprints (8/9/10/11/12/13) merged

**Open the PR by visiting:**
https://github.com/124298dssse32233/cfb-index/pull/new/integration/wave-1-2

(`gh pr create` failed because the local `gh` CLI is authenticated as `Staysette`, who can't see the repo. Git push over HTTPS used a different credential and succeeded — the branch is on GitHub.)

Paste the **Title** and **Body** below into the PR form.

---

## Title

```
Wave 1+2 integration: 6 sprints (8/9/10/11/12/13) merged
```

## Body

## Summary

Merges 6 sprint branches into one integration branch for review before fast-forward to master. All merges, conflict resolutions, and pre-existing bug fixes are documented in [output/sprint_reports/wave-12-integration.md](output/sprint_reports/wave-12-integration.md).

- **Sprint 8** (`sprint/8-pulse`): 3-line gitignore chore. Sprint 8 feature work was already on master via prior commits — confirmed via reflog and full-tree diff.
- **Sprint 9** (`sprint/9-editions`): editions framework + Homepage v4 + 4 seeded editions (3,496 lines).
- **Sprint 10** (`sprint/10-threads`): 8 storyline threads, 32 chapters, reader pages, canonical `team_pages/voice_validator.py` (13,153 lines).
- **Sprint 11** (`sprint/11-canon`): The Canon v1 — 3 lists (175 entries) (5,424 lines).
- **Sprint 12** (`sprint/12-wire`): The Wire — 110 portal entries with authored captions (3,446 lines).
- **Sprint 13** (`sprint/13-receipts`): Receipts module — 15.7k claims pipeline + 90 best-calls (4,518 lines).

### Conflicts resolved
- `cli.py` (×2 hunks): Sprint 9 `register_edition_subcommands` block + Sprint 13 receipts MERGE ZONE block.
- `team_pages/voice_validator.py` (add/add): Sprint 10's HEAD with the 20 ported editions phrases prevailed over Sprint 13's byte-identical baseline.

### Pre-existing bugs fixed inline
1. `FLOOR_AWAITING`/`FLOOR_GROWING` lifted to module-level in `team_pages/data.py` (Sprint-8 polish previously stuck in stash).
2. `editions/voice_validator.py` converted from 95-line full impl to canonical-import shim; 20 unique phrases ported to canonical.
3. `editions/cli.py:_open_db()` referenced `cfb_rankings.config.default_db_path` which never landed on master — replaced with `AppConfig.from_env()` pattern.

### Validation
- All 5 migrations apply cleanly in numerical order (09→10→11→12→13).
- Each sprint's render command succeeds: `render-homepage`, `render-storylines`, `render-canon-all` (175 entries), `render-receipts`. Sprint 12 wire output already on disk from sprint-end build.
- Voice validator sweep: 17,851 HTML files; 51,111 violations dominated by chrome false positives (Methodology nav link 17,409, Cohort Divergence card title 16,116, "this card" UI label 15,928). True editorial leakage in long tail; sweep tool needs narrower selectors as a follow-up.
- Sprint 10 voice_validator tests: 23/23 pass.

### Out-of-scope follow-ups
- Sprint 9 homepage widgets still read `editions/stub_data/*.json` instead of live tables — Sprint 9.5 wire-up.
- 1 canon validator failure: `jameis-winston::paragraph` — editorial fix.
- Add `src/cfb_rankings/storylines/seeds/_drafts/` to `.gitignore` — small commit on master.
- Stash@{1} (`sprint12-checkpoint`, mislabeled — actually Sprint 8 fan-intel WIP, 1,661 lines): Kevin's editorial review.
- Drop stash@{0} (pre-flight) post-merge.
- Sprint 8.5: pulse follow-ups (theme extraction, Lede LLM, sentiment classifier wire-up, Conference Pulse render, Player Pulse / The Room redesign).
- Wave 3: Daily / Reaction / Mailbag.

## Test plan

- [ ] Read `output/sprint_reports/wave-12-integration.md` — full per-phase log.
- [ ] Verify `python manage.py apply-migrations` is idempotent on a fresh clone.
- [ ] Run a full `python manage.py build-site` (~30 min) — confirm no new errors past the validated 12-min checkpoint.
- [ ] Spot-check rendered output: `output/site/index.html`, `output/site/storylines/index.html`, `output/site/canon/index.html`, `output/site/wire/index.html`, `output/site/receipts/index.html`.
- [ ] Sanity-check `team_pages/voice_validator.py` banlist (80 phrases; word-boundary regex; canonical for editions/canon/receipts shims).
- [ ] Inspect stash@{1} contents (`git stash show -p stash@{1}`) and decide whether to land any of it as a Sprint 8 polish commit.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
