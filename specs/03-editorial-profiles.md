# WS-03 — Editorial Profiles Scale to 119

**Phase:** 2–3 (Aug 2026–Mar 2027)
**Owner:** Claude execution + human review
**Status:** Blocked on D-011 (profile expansion ratios)

## Goal

Expand editorial profiles from current 17 hand-authored to ~40 by Aug 23 (top-25 P4 + top-15 G5) and 119 full coverage by mid-2027. Voice quality preserved at scale via LLM-draft + human-review pipeline + voice_validator enforcement.

## Definition of perfect

- Three profile tiers defined: `editorial_full` (hand-authored, current 17), `editorial_assisted` (LLM-drafted, hand-reviewed for voice, ~25 new), `minimal` (frontmatter only, no body, the remaining ~80).
- Every team has at minimum a `minimal` profile with: primary_subreddit, accent_hex, mantra, identity_phrase, never_use list.
- `editorial_full` and `editorial_assisted` profiles pass voice_validator + chronicle_banlist at merge time.
- Profile YAML frontmatter consistency CI check: archetype in profile matches WS-02 classifier output (or has explicit `archetype_override` with reason).
- `profile_tier` column in `team_coverage` table reflects which tier each team is in.

## Current state

- 17 hand-authored profiles in `profiles/*.md` with rich frontmatter (program_tier, voice_register, identity_phrase, mantra, vocab dict, mascot_voice, era_name_overrides, never_use list, always_surface, rivalries, aspiration_ladder, stock_phrases).
- 102 FBS teams have zero profile.
- No CI enforcement on profile-classifier consistency.

## Dependencies

- **Blocks:** WS-07 (era pages need profile depth for top-25), WS-12 (voice consistency at scale)
- **Blocked by:** D-011 (ratios), WS-02 (archetype output for consistency check), Voice LoRA training (WS-12)

## Implementation approach

1. Lock D-011 — recommend 17 full + 25 assisted + 77 minimal.
2. Generate minimal-tier YAML for all 102 missing teams: primary_subreddit (from team_aliases + Reddit `/about.json` verification), accent_hex (from existing visual_assets), mantra + identity_phrase + never_use (LLM-drafted, single-pass review).
3. Build LLM-draft pipeline using Mistral Small 24B or Qwen3-30B-A3B (Tier 1 model per VISION § 11). Each draft passes voice_validator before commit.
4. Hand-review queue for the 25 editorial_assisted profiles. ~2 hours of human review per profile.
5. CI check: profile frontmatter archetype matches WS-02 classifier output OR has `archetype_override: <slug>` + `archetype_override_reason: <text>`.
6. Voice LoRA training (WS-12 dependency) applies to editorial_assisted output for tone consistency.

## Running gate

- 119 teams have a profile file. CI enforces non-empty primary_subreddit + accent_hex + mantra + identity_phrase + never_use minimums.
- Every profile in `editorial_full` and `editorial_assisted` tier passes voice_validator.
- No profile-classifier archetype mismatch without explicit override.

## Decisions

- D-011 — Profile expansion targets — OPEN

## Pointers

- `src/cfb_rankings/team_pages/profile_loader.py` (loader + Profile dataclass)
- `profiles/*.md` (current 17)
- VISION § 2 (bespoke-to-CFB voice criteria), § 11 (LLM stack)
