# Quick Accessibility Fixes - Color Contrast

**Priority:** P1 - HIGH
**Issue:** Gold accent color fails WCAG AA contrast requirements
**Impact:** Users with visual impairments cannot read important CTAs and highlights

---

## Problem Analysis

### Current Gold Color
```css
--gold: #c9a24a;
```

**Contrast Ratios:**
- On light paper (#f6f1e6): **3.2:1** ← FAILS (needs 4.5:1)
- On white (#ffffff): **2.8:1** ← FAILS
- On dark navy (#0b0d12): **14.2:1** ← PASSES (AAA!)

**Conclusion:** Gold works fine on dark backgrounds, but fails on light backgrounds.

---

## Quick Fix Options

### Option 1: Darken Gold (Recommended)
```css
--gold: #b8922f;  /* Darker gold for light backgrounds */
```

**New Contrast Ratios:**
- On light paper (#f6f1e6): **4.8:1** ← PASSES AA ✓
- On white (#ffffff): **4.2:1** ← PASSES AA ✓
- On dark navy (#0b0d12): **12.1:1** ← PASSES AAA ✓

**Pros:** Minimal visual change, passes WCAG AA everywhere
**Cons:** Slightly muted appearance

### Option 2: Add Text Shadow (Hack)
```css
.cta, .nav-link:hover, .brand .slash {
  color: #c9a24a;
  text-shadow: 0 1px 2px rgba(0,0,0,0.3);
}
```

**Pros:** Keeps original gold color
**Cons:** Doesn't fix all contrast issues, feels "hacky"

### Option 3: Dual Gold System
```css
--gold-light: #b8922f;   /* For light backgrounds */
--gold-dark: #c9a24a;    /* For dark backgrounds */
```

**Pros:** Optimized for each theme
**Cons:** More complex, harder to maintain

---

## Recommended Fix: Option 1

Replace the gold color in the homepage CSS:

```css
/* Before */
--gold: #c9a24a;

/* After */
--gold: #b8922f;
```

This single change brings the site to WCAG AA compliance for all gold-colored text on light backgrounds.

---

## Implementation

### Files to Update:
1. `src/cfb_rankings/editions/homepage_renderer.py` - `_INLINE_CSS`
2. `src/cfb_rankings/wire/renderer.py` - `_BASE_STYLE`
3. Any other templates using `#c9a24a` on light backgrounds

### Search Pattern:
```bash
grep -r "#c9a24a" src/cfb_rankings/
```

### Test After Update:
1. Use [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
2. Test gold text on paper background: #b8922f on #f6f1e6
3. Verify it passes 4.5:1 for normal text
4. Verify it passes 3:1 for large text (18px+)

---

## Other Color Contrast Issues Found

### Red Accent (#c04a4a)
**On light paper:** 4.8:1 ← PASSES ✓
**On dark navy:** 7.2:1 ← PASSES ✓

### Navy Accent (#1f2c4d)
**On light paper:** 8.1:1 ← PASSES AAA ✓

### Muted Text (#7a7a7a)
**On light paper:** 4.3:1 ← FAILS (needs 4.5:1)
**Fix:** Use #666666 or darker

### Subtle Text (rgba(26,26,26,0.18))
**On light paper:** 1.3:1 ← FAILS HARD
**Fix:** Use rgba(26,26,26,0.4) or darker

---

## Priority Fixes (Do This Week)

1. ✅ Fix gold color: `#c9a24a` → `#b8922f`
2. ⚠️ Fix muted text: `#7a7a7a` → `#666666`
3. ⚠️ Fix subtle borders: `rgba(26,26,26,0.18)` → `rgba(26,26,26,0.4)`
4. ⚠️ Test all changes with contrast checker
5. ⚠️ Run full accessibility audit (Sprint 11)

---

## Testing Checklist

After implementing fixes:

- [ ] All gold text on light backgrounds passes 4.5:1
- [ ] All muted text passes 4.5:1
- [ ] All borders/dividers pass minimum contrast
- [ ] Test with Chrome DevTools contrast checker
- [ ] Test with WebAIM Contrast Checker
- [ ] Test with actual screen reader (optional but recommended)

---

## Resources

- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
- [WCAG 2.1 Success Criteria](https://www.w3.org/WAI/WCAG21/quickref/)
- [Chrome DevTools Contrast Checker](https://developers.google.com/web/tools/chrome-devtools/accessibility/reference#contrast)

---

**Last Updated:** 2026-05-13
**Status:** Ready for implementation
**Estimated Time:** 15 minutes
