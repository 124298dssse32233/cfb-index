**Adversarial Review of CFB Index Site-Quality Plan**  

---

### **Assumption Challenges & Risks**  
1. **Build Path for `/offseason/`/`/film-room/`**  
   - *Risk*: Adding these to `build-site` could violate the "build EVERY section or clobber" rule if legacy paths are not fully retired. Promoting them as subcommands risks bloating the CLI without clear value.  
   - *Recommendation*: Retain box-build parity but enforce strict manifest validation to avoid clobbering. Avoid new subcommands.  

2. **Backfill Order: Plays/Drives vs Advanced Stats**  
   - *Risk*: Front-loading heavy plays/drives may overwhelm DB/cron, delaying high-impact advanced stats. Sequencing could delay critical user value.  
   - *Recommendation*: Prioritize advanced team stats first (higher value per call), then backfill plays/drives in parallel.  

3. **Receipts Auto-Resolution**  
   - *Risk*: Automating resolution without human checks risks exposing unverified claims (e.g., Polymarket’s `prob_yes` bug). Constraints forbid new recurring costs, but human-in-the-loop may be necessary.  
   - *Recommendation*: Require human validation for claims with unresolved sources to avoid presenting unverified predictions.  

4. **Provenance Reconciliation**  
   - *Risk*: Reconstructing `source_id` from `source_name`+`source_channel` may fail due to legacy inconsistencies (e.g., duplicate channels). Labeling legacy rows without inferred IDs leaves gaps.  
   - *Recommendation*: Use existing `source_id` where possible; label legacy entries as "unresolved" rather than inferring IDs.  

5. **Player-Module Consolidation**  
   - *Risk*: Design tie constraint may lock legacy modules despite v2’s potential superiority. Duplication could regress UX (e.g., redundant "peer-comparator" modules).  
   - *Recommendation*: Default to v2 if it demonstrates clear UX/accuracy wins; otherwise, keep legacy as fallback.  

---

### **Plan-Specific Risks**  
- **Data Corruption**: Phase 1’s backfill must ensure idempotency to avoid corrupting the rolling DB artifact.  
- **UX Regression**: Hiding "Live Signal Flow" placeholders without user testing risks accessibility issues (e.g., WCAG 2.2 AA compliance in Phase 3).  
- **Cost Risk**: "Operationalize receipts resolution" may inadvertently introduce recurring costs if dependencies (e.g., Kalshi) are reactivated.  
- **Sequence Dependency**: Provenance reconstruction in Phase 1 could block Phase 2’s metric contracts if source IDs are unresolved.  

---

**Conclusion**: The plan’s sequencing and assumptions require tighter guardrails—especially around data integrity, UX continuity, and cost constraints. Prioritize lightweight, high-impact fixes first, and defer heavier operations until provenance and resolution workflows are robust.
