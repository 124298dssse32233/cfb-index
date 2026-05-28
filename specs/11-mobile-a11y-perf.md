# WS-11 — Mobile, Accessibility, Performance

**Phase:** 5 (Mar–Jun 2027)
**Owner:** Claude execution + human review
**Status:** Not blocked; can audit current state anytime

## Goal

Every page meets the "perfect" launch quality bar: Lighthouse 100/100/100/100, mobile renders at 320px, WCAG 2.1 AA accessibility, color-blind safe, keyboard-navigable, sub-100ms TTFB.

## Definition of perfect

- Every page passes Lighthouse 100/100/100/100 (Performance, Accessibility, Best Practices, SEO).
- ARIA-complete on every interactive element.
- Color-blind safe across all chart palettes (deuteranopia + protanopia + tritanopia tested).
- Keyboard-navigable across cmdk + every interactive component.
- Static SVG fallback for every chart (no JS-required chart on the site).
- Page-weight budgets enforced via CI: HTML ≤50KB, CSS ≤30KB, JS ≤30KB per page.
- TTFB <100ms for every static page (Vercel edge cache properly tuned).
- Touch targets ≥44px on every interactive element (per WCAG 2.5.5).

## Current state

- Static-site generator produces fast pages.
- Mobile rendering mostly works but not systematically tested at 320px.
- No Lighthouse CI; quality drift not enforced.
- ARIA coverage uneven across modules.
- Color-blind safety untested.
- Some charts are JS-required (no SVG fallback).

## Dependencies

- **Blocks:** Phase 5 launch
- **Blocked by:** WS-08 (chart vocab must be locked at 9 before all charts can get SVG-fallback treatment)

## Implementation approach

1. Lighthouse CI: run on every PR. Gate merges on score ≥95 per page-archetype prototype.
2. Mobile-rendering test: Playwright run at 320px / 375px / 414px on each archetype. Snapshot-test prevents regression.
3. A11y audit: axe-core integration in CI. Manual screen-reader pass on each archetype.
4. Color-blind audit: simulate D / P / T on every chart palette. Adjust where contrast fails.
5. SVG fallback: every chart-card component renders SVG server-side. JS-progressive only for interactivity.
6. Page-weight budget: build-time check; fails build if any page exceeds budget.
7. Edge cache tuning: explicit `Cache-Control` headers; ISR + on-demand revalidation patterns.
8. Keyboard nav: tab-order audit on every interactive element; visible focus indicators.

## Running gate

- Lighthouse CI green on every page-archetype.
- 320px Playwright snapshots green for 50 sampled pages.
- A11y audit green.
- Color-blind audit green.
- All charts have SVG fallback.
- Page-weight budgets enforced.

## Decisions

- None blocking

## Pointers

- VISION § 16 (Performance success metrics)
