#!/usr/bin/env python
"""Validate per-program Emotional-Core sidecars (docs/design-system/63 §3, §8).

Enforcement is TIERED by status:
  - todo / drafted : structure + valid enum values only (the soul may still be blank).
  - authored+      : the bespoke soul must be filled, enums valid, AND the handling rules
                     hold — the never_use guardrail is LAW, the wound carries a handling rule,
                     and the delusion has a tone (affectionate, never mocking).

Read-only. Reads profiles/emotional_core/*.yaml and the matching profiles/<slug>.md
(for the never_use list). Writes nothing.

Usage:
    python scripts/verify_emotional_cores.py [--strict] [--status authored reviewed live]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "profiles" / "emotional_core"
PROFILES = ROOT / "profiles"

STATUSES = {"todo", "drafted", "authored", "reviewed", "live"}
AUTHORED_PLUS = {"authored", "reviewed", "live"}
CORE = {"standard", "grief", "grievance", "restoration", "redemption", "disbelief",
        "spectacle", "delusion", "deprival", "contentment", "house-money", "honor"}
ARCHETYPE = {"blue-blood-living-up", "blue-blood-fallen", "riser-proving",
             "sleeping-giant", "perennial-almost", "lovable-have-not", "orphaned"}
HANDLING = {"referenceable", "never-a-punchline", "dated-grievance"}
TONE = {"earnest", "self-aware", "load-bearing", "none"}
TEXTURE = {"blood-feud", "championship", "little-brother", "killed-by-realignment", "border-war", "none"}
COACH_REL = {"savior", "legends-shadow", "forever-ours", "hot-seat-churn", "total-trust"}
# optional sub-core: splits the two over-loaded cores into finer cohorts. Only valid for these primaries.
CORE_VARIANT = {
    "restoration": {"dynasty-restoration", "perpetual-rebuild", "regime-reset", "first-ascension"},
    "grievance": {"the-snub", "the-ceiling", "the-chronic-chip"},
}

# soul text fields scanned against never_use
SOUL_TEXT = [
    ("emotional_core", "one_line"), ("self_image", "standard_gap_frame"),
    ("the_wound", "name"), ("the_wound", "detail"), ("the_dream", "text"),
    ("the_chip", "text"), ("the_delusion", "text"),
]


def _get(d, *path):
    for k in path:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def _nonempty(v) -> bool:
    return v is not None and str(v).strip() != ""


def validate(path: Path) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for one sidecar."""
    errs, warns = [], []
    try:
        d = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        return [f"YAML parse error: {e}"], []

    slug = d.get("slug") or path.stem
    status = (d.get("status") or "todo").strip()
    if status not in STATUSES:
        errs.append(f"status '{status}' not in {sorted(STATUSES)}")

    # structure present at all statuses
    for sect in ("emotional_core", "self_image", "the_wound", "the_dream",
                 "the_chip", "the_delusion", "the_grudge_texture"):
        if sect not in d:
            errs.append(f"missing section '{sect}'")

    # enum validity (only when the field is filled — todo leaves them blank)
    def check_enum(val, allowed, label):
        if _nonempty(val) and str(val).split("#")[0].strip() not in allowed:
            errs.append(f"{label}='{val}' not in {sorted(allowed)}")

    check_enum(_get(d, "emotional_core", "primary"), CORE, "emotional_core.primary")
    check_enum(_get(d, "emotional_core", "secondary"), CORE | {""}, "emotional_core.secondary")
    check_enum(_get(d, "self_image", "archetype"), ARCHETYPE, "self_image.archetype")
    check_enum(_get(d, "the_wound", "handling"), HANDLING, "the_wound.handling")
    check_enum(_get(d, "the_delusion", "tone"), TONE, "the_delusion.tone")
    check_enum(_get(d, "the_grudge_texture", "texture"), TEXTURE, "the_grudge_texture.texture")
    check_enum(_get(d, "the_coach_relationship"), COACH_REL, "the_coach_relationship")

    # core_variant: optional finer cohort; only for restoration/grievance, must match the primary's set
    cv = _get(d, "emotional_core", "core_variant")
    if _nonempty(cv):
        cvv = str(cv).split("#")[0].strip()
        prim = str(_get(d, "emotional_core", "primary") or "").split("#")[0].strip()
        allowed = CORE_VARIANT.get(prim)
        if allowed is None:
            errs.append(f"emotional_core.core_variant set but primary '{prim}' has no variants")
        elif cvv not in allowed:
            errs.append(f"emotional_core.core_variant='{cvv}' not in {sorted(allowed)} for primary={prim}")

    # the soul must be filled once authored
    if status in AUTHORED_PLUS:
        required = [
            (_get(d, "emotional_core", "primary"), "emotional_core.primary"),
            (_get(d, "emotional_core", "one_line"), "emotional_core.one_line"),
            (_get(d, "self_image", "archetype"), "self_image.archetype"),
            (_get(d, "the_coach_relationship"), "the_coach_relationship"),
            (_get(d, "register"), "register"),
        ]
        for val, label in required:
            if not _nonempty(val):
                errs.append(f"[authored] {label} must be filled")
        # a named wound needs a handling rule + freshness
        if _nonempty(_get(d, "the_wound", "name")):
            for f in ("handling", "freshness"):
                if not _nonempty(_get(d, "the_wound", f)):
                    errs.append(f"[authored] the_wound.{f} required when a wound is named")
        # a delusion with text needs a tone
        if _nonempty(_get(d, "the_delusion", "text")) and not _nonempty(_get(d, "the_delusion", "tone")):
            errs.append("[authored] the_delusion.tone required when delusion text is present")

    # never_use is LAW — scan authored soul text
    nu = d.get("never_use") or []
    soul_blob = " ".join(
        str(_get(d, *p)) for p in SOUL_TEXT if _nonempty(_get(d, *p))
    )
    if soul_blob:
        for term in nu:
            t = str(term).split(" as ")[0].split(" (")[0].strip()  # head of phrasey entries
            if len(t) < 3:
                continue
            if re.search(r"\b" + re.escape(t) + r"\b", soul_blob, re.IGNORECASE):
                errs.append(f"never_use VIOLATION: '{t}' appears in an authored field")

    # story canon (doc 64)
    if "story_canon" not in d:
        errs.append("missing section 'story_canon'")
    sc = d.get("story_canon") or {}
    MOMENT_HANDLING = {"glory", "miracle", "wound", "heartbreak"}
    if status in AUTHORED_PLUS:
        for fld in ("the_unique_thing", "the_ongoing_story"):
            if not _nonempty(sc.get(fld)):
                errs.append(f"[authored] story_canon.{fld} must be filled")
        for m in (sc.get("canonical_moments") or []):
            if isinstance(m, dict) and _nonempty(m.get("name")):
                if m.get("handling") not in MOMENT_HANDLING:
                    errs.append(f"[authored] canonical_moment '{m.get('name')}' "
                                f"handling='{m.get('handling')}' not in {sorted(MOMENT_HANDLING)}")
        if not (sc.get("sources") or []):
            warns.append("story_canon.sources empty — web-researched canon should cite verifiable sources")

    # light attribution warning: a delusion/chip line that reads as the SITE's verdict
    for sect in ("the_delusion", "the_chip"):
        txt = _get(d, sect, "text")
        if _nonempty(txt):
            low = str(txt).lower()
            attributed = any(w in low for w in ("fan", "they ", "the room", "the base", "believe", "call", "say", "'", "’", '"'))
            if not attributed and status in AUTHORED_PLUS:
                warns.append(f"{sect}.text may read as the site's verdict — attribute to the fanbase")

    return errs, warns


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="exit 1 if any errors")
    ap.add_argument("--status", nargs="*", default=None, help="only check these statuses")
    args = ap.parse_args(argv)

    files = sorted(p for p in OUT_DIR.glob("*.yaml") if not p.name.startswith("_"))
    if not files:
        print("no sidecars found (run seed_emotional_cores.py first)")
        return 0

    n_err = n_warn = n_ok = 0
    by_status: dict[str, int] = {}
    for p in files:
        d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        st = (d.get("status") or "todo").strip()
        by_status[st] = by_status.get(st, 0) + 1
        if args.status and st not in args.status:
            continue
        errs, warns = validate(p)
        if errs:
            n_err += 1
            print(f"FAIL {p.stem} [{st}]")
            for e in errs:
                print(f"     ✗ {e}")
        elif warns:
            n_warn += 1
            print(f"WARN {p.stem} [{st}]")
            for w in warns:
                print(f"     ! {w}")
        else:
            n_ok += 1

    print(f"\n{len(files)} sidecars — {n_ok} clean, {n_warn} warn, {n_err} fail")
    print("by status: " + ", ".join(f"{k}={v}" for k, v in sorted(by_status.items())))
    return 1 if (args.strict and n_err) else 0


if __name__ == "__main__":
    raise SystemExit(main())
