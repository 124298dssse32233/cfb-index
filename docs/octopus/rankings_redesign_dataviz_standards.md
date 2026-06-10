# Rankings Redesign — Data-Viz Standards & Chart Ledger

**Authored 2026-06-08.** The chart design language for the redesign, derived from an expert
audit (NYT Upshot / FiveThirtyEight / Baseball Savant / Bloomberg / Tufte standards) and applied
across every mockup chart. Carry these into the production build (the `charts/` module the
[engineering spec](rankings_redesign_engineering_spec.md) says is net-new — build it to this spec).

---

## The 5 cross-cutting standards (apply to EVERY chart)

1. **Every quantitative axis gets a titled scale + a "direction of good" cue.** No bare numbers, no
   scaleless bars/dots/gradients. One shared treatment: **9.5px Inter, `--color-text-muted/subtle`,
   .04em tracking, sentence case** (e.g. "Predicted win %", "Brier — lower is better →", "Percentile
   vs FBS", "RANK · 1 = best"). Never truncate an axis to dramatize a gain unless a meaningful
   **baseline is annotated**.
2. **One color system, fixed semantics.** *Identity:* **navy = model/power, coral = room/fans,
   amber = country/at-risk** (the Tri-Rank triad). *Performance/percentile:* the diverging
   **red→grey→navy** Savant track, **always with a 50th-pct tick**. *Emotion/mood:* **coral→grey→green**
   (doom→euphoria), always with a neutral midpoint. Don't mix these axes' meanings.
3. **One in-chart annotation style — every chart names its finding INSIDE the frame**, with a thin
   1px leader to the marked point, in coral. The caption above and the in-chart annotation must point
   at the **same** event. Direct-label endpoints + the hero mark; suppress redundant per-point labels.
4. **One reference-line hierarchy: reference > grid > nothing.** Reference lines (50th pct, perfect
   diagonal, 50% win, coin-flip/naive baseline, neutral mood) at **1px solid neutral and ALWAYS
   present**; gridlines hairline `--color-line`; the reference is never fainter than the data. Every
   percentile/probability/mood chart shows its mid/50 tick.
5. **De-clutter & de-conflict by rule.** Thin marks to inflection points; **halo overlapping lines**
   (white casing); when two values share one track use a **dumbbell/connector** so the *gap* is always
   visible; minimum-separation so dots/labels never occlude.

---

## Chart ledger — what each chart is, and its gold-standard reference

| Chart | Screen(s) | Form & gold-standard | Key scaffolding |
|---|---|---|---|
| **Calibration curve** | report-card (+ desktop rail) | 538 reliability plot | crisp diagonal + tolerance band, points **sized by sample**, both axes 0–100% titled, in-chart "said 70%→68%" + calibration-error figure |
| **Poll scoreboard** | report-card | **Cleveland dot plot** (Bloomberg) | real Brier axis w/ ticks, "← lower is better", position encodes value (no inverted bars) |
| **Accuracy-over-time** | report-card | NYT annotated line | naive **"favorite 72%" baseline** drawn, titled y-axis, endpoints labeled |
| **Division spectrum** | cross-bridge | bespoke dual-ruler | **FBS lane = the FBS rank scale** (#25/#50/#100 ticks), **overlap band** ("N below"), haloed bridge line, **computed** equivalents |
| **Bump chart** | desktop-board | narrated bump (NYT) | RANK axis (1=best), **halo lines**, context teams faded to ~25%, only the lead-change pair in full color, overtake annotated |
| **Fingerprint sliders** | team / mobile / compare | **Baseball Savant** | fixed **50th-pct tick** behind every bar + a "0·worse — 50=avg — elite·100" scale legend |
| **Compare overlay** | compare | **dumbbell** (Economist) | connector segment colored toward the leader, numeric gap labeled, no illegible dot letters |
| **Tri-Rank** | team / mobile / desktop | labeled-rank-axis + gap | 1→16 rank axis, three colored pips, the model↔room↔country **span shaded** ("N-rank gap"), legend names the pips |
| **Quantile dotplot** | team / mobile / desktop | frequency framing | "X / 20" + %, **legend** for the amber bubble/at-risk band ("makes it · bubble · out") |
| **Vibe sparklines** | the-room | trend spark | **shared y-domain (10–90)** so slope encodes magnitude consistently |
| **Mood gauge** | the-room | tipping-point gauge | center "Mixed" tick + the value shown (62/100) |
| **Mood-by-week** | team-detail | mood **line** (not a heat strip) | coral→green gradient stroke, **neutral midline** at 50 |
| **Rival heat / civil-war** | the-room | bar + split | heat **value shown**, single semantic color; civil-war **50% midline** + surfaced **cohesion** score |
| **Season arc** | team-detail | NYT annotated line | dots thinned to inflections, **"now #3" endpoint**, dashed **plateau guide** at #3 |

---

## Minor mop-ups still open (low priority)
- The desktop rail's **mini calibration** (`desktop-board.html calib()`) wasn't upgraded to match the
  full report-card version (it's a small rail element).
- The **Compare sim banner** (the 48/52 win bar) could take a 50% midline like the cross-bridge matchups.
- Quantile-dotplot **dot sizing** varies slightly across screens (11px team/mobile vs 4px desktop cell) —
  intentional (cell density) but could be unified.

These don't change the conclusions; everything load-bearing is rebuilt to standard.
