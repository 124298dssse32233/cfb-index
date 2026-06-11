Warning: True color (24-bit) support not detected. Using a terminal with true color enabled will result in a better visual experience.
Ripgrep is not available. Falling back to GrepTool.
This plan is a high-risk "fix-it-in-post" strategy that prioritizes infrastructure over data integrity. It treats accessibility as a Phase 3 "polish" item rather than a foundational constraint, risking a total UX regression during the Phase 1-2 refactors.

### Critical Risks
*   **Data Corruption:** Running "idempotent" backfills (Phase 1) against a 192-table SQLite DB *before* fixing the provenance logic (Phase 1) and registry health (Phase 0) is a recipe for duplicate-entry hell. You are pumping new data into a leaky bucket.
*   **Accessibility/UX Regression:** Delaying WCAG 2.2 and No-JS targets to Phase 3 is a failure. Any change to the 6 duplicate player modules in Phase 0-2 will likely break keyboard navigation or screen reader compatibility, requiring double work later.
*   **Unverified Claims:** The plan admits 266 unresolved claims and an empty ledger. Exposing "Receipts" (even if resolved) before the provenance gap is closed risks attributing "wins" to the wrong sources, destroying the "Fan Intelligence" brand.

### Recommendations on Open Questions
1.  **Build Path:** **Fix box path.** In a full-snapshot Vercel model, subcommands are a liability. If it isn't in the main build, it doesn't exist. Consistency beats granularity.
2.  **Backfill Order:** **Advanced Team Stats first.** PBP is a high-volume data-corruption minefield. Prove the pipeline and "Team Savant" logic on cleaner, higher-value-per-call data before drowning the DB in drives/plays.
3.  **Receipts:** **Human-in-the-loop (HITL).** Data bugs (like the Polymarket `prob_yes` failure) prove your "defensible" data is often wrong. Require manual audit for the first 100 resolutions to build a golden evaluation set.
4.  **Provenance:** **Label legacy rows.** Do NOT reconstruct `source_id`. Inferring IDs from stale names in a "fake" registry will permanently corrupt your audit trail. Mark them `legacy_unverified`.
5.  **Module Consolidation:** **Default to v2 ONLY with a "metric-parity" gate.** If v2 lacks a single field from v1, keep v1. Design ties must prioritize data density over code cleanliness.

### Final Challenge
The sequencing is backwards. You cannot "harden sources" (Phase 4) after you’ve already used them for "Metric Contracts" (Phase 2). **Move Registry Health and Provenance to the start of Phase 0.** Accessibility (Phase 3) must be moved to Phase 1. Without these, you are building a "World Class" site on a foundation of sand.
