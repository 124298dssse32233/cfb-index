# CFB Index — Unified Design System

**Status:** Draft | **Version:** 1.0 | **Last Updated:** 2026-05-13

## Executive Summary

This document defines a unified design system for CFB Index to address critical UX inconsistencies identified in the May 2026 audit. The site currently has **4+ different design languages** across sections, creating a jarring user experience.

**Current Problems:**
- Homepage: Light theme, serif typography, editorial style
- Storylines/Team Pages: Dark theme, sans-serif, modern cards
- Wire: Light theme, serif, table-based
- Daily: Light theme, serif, grid layout
- Rankings: Unknown (external CSS)

**Solution:** Adopt a **Contextual Theme System** that respects the unique character of each section while providing consistent:
- Color tokens
- Typography scale
- Spacing rhythm
- Component patterns
- Navigation behavior

---

## Design Tokens

### Color System

#### Light Theme (Editorial Sections)
**Applies to:** Homepage, Wire, Daily, Editions, Methodology

```css
:root {
  /* Base Colors */
  --bg-primary: #f6f1e6;      /* Paper - main background */
  --bg-secondary: #ece6d6;    /* Paper dim - cards/sections */
  --bg-elevated: #ffffff;     /* Pure white - raised elements */

  --fg-primary: #1a1a1a;      /* Ink - main text */
  --fg-secondary: #7a7a7a;    /* Muted - secondary text */
  --fg-tertiary: #a0a0a0;     /* Subtle - labels/metadata */

  /* Accent Colors */
  --accent-primary: #c9a24a;  /* Gold - CTAs, highlights */
  --accent-secondary: #1f2c4d; /* Navy - supplementary */
  --accent-tertiary: #c04a4a;  /* Red - alerts/errors */

  /* Borders */
  --border-default: #1a1a1a;  /* Strong borders */
  --border-subtle: rgba(26,26,26,0.18); /* Soft dividers */
}
```

#### Dark Theme (Data/Interactive Sections)
**Applies to:** Storylines, Team Pages, Rankings, Compare

```css
:root {
  /* Base Colors */
  --bg-primary: #0b0d12;      /* Deep navy - main background */
  --bg-secondary: #12151d;    /* Slightly lighter - cards */
  --bg-elevated: #1a1f2b;     /* Raised elements */

  --fg-primary: #f5f6fa;      /* Off-white - main text */
  --fg-secondary: #c6cad6;    /* Dimmed - secondary text */
  --fg-tertiary: #8a90a1;     /* Subtle - labels/metadata */

  /* Accent Colors */
  --accent-primary: #c5b358;  /* Gold - CTAs, highlights */
  --accent-secondary: #084c24; /* Green - positive indicators */
  --accent-tertiary: #c04a4a;  /* Red - negative indicators */

  /* Borders */
  --border-default: rgba(255, 255, 255, 0.10);
  --border-subtle: rgba(255, 255, 255, 0.05);
}
```

#### Per-Team Accents (Team Pages)
Injected inline as CSS custom properties:

```html
<body style="--accent-primary: #9E1B32; --accent-secondary: #FFFFFF;">
```

### Typography Scale

#### Font Families

```css
/* Editorial Sections (Light Theme) */
--font-display: 'Source Serif Pro', 'Georgia', serif;
--font-body: 'Source Serif Pro', 'Georgia', serif;
--font-ui: 'Inter', -apple-system, sans-serif;

/* Data/Interactive Sections (Dark Theme) */
--font-display: 'Inter Display', 'Inter', sans-serif;
--font-body: 'Inter', -apple-system, sans-serif;
--font-serif: 'Source Serif Pro', 'Georgia', serif; /* For editorial content */

/* Monospace */
--font-mono: 'JetBrains Mono', 'SF Mono', 'Menlo', monospace;
```

#### Type Scale (Clamp-based for responsiveness)

```css
--fs-xs: clamp(10px, 0.65vw + 8px, 11px);     /* Labels, metadata */
--fs-sm: clamp(12px, 0.72vw + 10px, 13px);    /* Secondary text */
--fs-base: clamp(14px, 0.8vw + 10px, 16px);   /* Body text */
--fs-md: clamp(16px, 0.9vw + 11px, 18px);     /* Lead text */
--fs-lg: clamp(18px, 1.2vw + 12px, 22px);     /* Subheads */
--fs-xl: clamp(22px, 1.8vw + 14px, 30px);     /* Section heads */
--fs-2xl: clamp(32px, 3.5vw + 16px, 56px);    /* Hero headlines */
--fs-3xl: clamp(48px, 5vw + 20px, 72px);      /* Display headlines */

--lh-tight: 1.12;
--lh-snug: 1.28;
--lh-normal: 1.48;
--lh-relaxed: 1.65;

--ls-tight: -0.02em;
--ls-normal: 0em;
--ls-wide: 0.04em;
--ls-label: 0.08em;
--ls-display: 0.16em; /* For UI labels */
```

### Spacing System

Based on a 4px base unit:

```css
--space-1: 4px;
--space-2: 8px;
--space-3: 12px;
--space-4: 16px;
--space-5: 20px;
--space-6: 24px;
--space-7: 32px;
--space-8: 40px;
--space-9: 56px;
--space-10: 64px;
--space-11: 80px;
--space-12: 96px;
```

### Component Patterns

#### Cards

**Light Theme Cards:**
```css
.card {
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: var(--space-6);
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
```

**Dark Theme Cards:**
```css
.card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  padding: var(--space-6);
  box-shadow: 0 4px 12px rgba(0,0,0,0.25);
}
```

#### Buttons

**Primary (CTA):**
```css
.btn-primary {
  background: var(--accent-primary);
  color: var(--fg-on-accent);
  padding: 12px 24px;
  border-radius: 6px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  font-size: var(--fs-sm);
  transition: all 180ms ease;
}

.btn-primary:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}
```

**Secondary:**
```css
.btn-secondary {
  background: transparent;
  color: var(--fg-primary);
  border: 2px solid var(--accent-primary);
  padding: 10px 22px;
  border-radius: 6px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  font-size: var(--fs-sm);
}
```

#### Navigation

**Desktop (> 860px):**
```css
.nav-link {
  margin-left: 28px;
  color: var(--fg-primary);
  font-weight: 600;
  font-size: var(--fs-sm);
  letter-spacing: 0.14em;
  text-transform: uppercase;
  transition: color 180ms ease;
}

.nav-link:hover {
  color: var(--accent-primary);
}

.nav-link.is-current {
  color: var(--accent-primary);
  border-bottom: 2px solid var(--accent-primary);
}
```

**Mobile (< 860px):**
```css
.nav-toggle {
  display: flex;
  flex-direction: column;
  gap: 5px;
  background: none;
  border: none;
  cursor: pointer;
  padding: 8px;
}

.hamburger {
  width: 24px;
  height: 2px;
  background: var(--fg-primary);
  transition: all 180ms ease;
}

.nav-links {
  display: none;
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: var(--bg-primary);
  flex-direction: column;
  padding: var(--space-4);
  border-bottom: 1px solid var(--border-default);
}

.nav-links.is-open {
  display: flex;
}

.nav-link {
  display: block;
  padding: var(--space-3) 0;
  color: var(--fg-primary);
  border-bottom: 1px solid var(--border-subtle);
}
```

---

## Migration Plan

### Phase 1: Foundation (Sprint 9.5 - Week 1)
- [x] Create shared navigation component (`src/cfb_rankings/nav.py`)
- [x] Fix mobile navigation CSS bug
- [ ] Add navigation to all templates
- [ ] Test navigation across all pages

### Phase 2: Design Tokens (Sprint 9.5 - Week 2)
- [ ] Create shared CSS token file
- [ ] Update homepage to use unified tokens
- [ ] Update Wire to use unified tokens
- [ ] Update Daily to use unified tokens
- [ ] Test responsive behavior

### Phase 3: Component Library (Sprint 10 - Week 1-2)
- [ ] Create card component with light/dark variants
- [ ] Create button component with variants
- [ ] Create table component for Wire
- [ ] Create form component for search/filters
- [ ] Document all components

### Phase 4: Section Migration (Sprint 10-11)
- [ ] Migrate Storylines to unified system
- [ ] Migrate Team Pages to unified system
- [ ] Migrate Rankings to unified system
- [ ] Migrate Compare to unified system
- [ ] Migrate remaining sections

### Phase 5: Polish & QA (Sprint 11)
- [ ] Accessibility audit (WCAG AA)
- [ ] Cross-browser testing
- [ ] Performance optimization
- [ ] Documentation finalization

---

## Accessibility Guidelines

### Color Contrast
- All text must meet WCAG AA: 4.5:1 for normal text, 3:1 for large text
- Current gold accent (#c9a24a on #f6f1e6) fails - needs adjustment
- Recommended: Use darker gold (#b8922f) or add text shadow

### Touch Targets
- Minimum 44x44px for all interactive elements
- Current navigation links: Good
- Wire table rows: Need full-row click or expandable rows

### Keyboard Navigation
- All interactive elements must be keyboard accessible
- Skip to main content link (already present on homepage)
- Focus indicators on all interactive elements

### Screen Reader Support
- ARIA labels on navigation
- Semantic HTML (nav, main, article, section)
- Alt text on all images
- Proper heading hierarchy (h1 → h2 → h3)

---

## Testing Checklist

### Navigation
- [ ] Desktop: All links work
- [ ] Mobile: Hamburger menu opens/closes
- [ ] Mobile: Menu closes on outside click
- [ ] Mobile: Menu closes on link click
- [ ] Active state highlights correctly
- [ ] Keyboard navigation works

### Visual Consistency
- [ ] Color theme consistent within sections
- [ ] Typography scale consistent
- [ ] Spacing rhythm consistent
- [ ] Component styles consistent

### Responsive Design
- [ ] Homepage: 320px - 1920px
- [ ] Wire: Table scrolls on mobile
- [ ] Team pages: Cards stack on mobile
- [ ] Rankings: Filter accessible on mobile

---

## Open Questions

1. **Should we unify all sections to one theme, or keep light/dark split?**
   - Recommendation: Keep split, but standardize tokens within each

2. **How do we handle legacy pages that can't be updated immediately?**
   - Recommendation: Create migration shim CSS that maps old classes to new tokens

3. **Should external CSS files be bundled or kept separate?**
   - Recommendation: Bundle per-section, use shared token file

4. **What's the timeline for full migration?**
   - Recommendation: Sprint 9.5 (navigation), Sprint 10 (tokens), Sprint 11 (full migration)

---

## Resources

- [Figma Design System](https://figma.com/file/cfb-index-design-system) (TODO: Create)
- [Component Storybook](https://cfb-index.dev/components) (TODO: Create)
- [Accessibility Audit Results](../accessibility/audit-2026-05.md) (TODO: Run)

**Last Updated:** 2026-05-13 by Claude (Octopus Design Workflow)
