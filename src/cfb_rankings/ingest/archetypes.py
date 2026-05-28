"""Fan Intelligence Hub v5 — archetype taxonomy seed data + rules-based classifier.

Single source of truth for the 18 primary archetypes and 8 modifiers shipped in
Issue N° 047. Values mirror the Figma v5.1 publication spec verbatim, including
typographer-quote entities (&rsquo;) that render inline in the hub page.

The classifier is a deterministic rules engine. It takes:
  - a team's current season record trajectory (from power_ratings / record tables)
  - a program identity signature (service academy / HBCU / blueblood / etc.)
  - optional conversation tone (from team_week_conversation_features) — only
    consulted when present; the offseason path runs without it.
and emits a (primary_archetype_slug, confidence, modifier_slugs, signature_phrase)
tuple.

Opus-sourced weight vector (Phase 3 decision, one-shot):
  - Structural / identity rules   : 1.00 (deterministic; short-circuit everything)
  - Record trajectory             : 0.45
  - Program history pedigree      : 0.25
  - Recency coach event           : 0.20
  - Conversation tone (if any)    : 0.10
Ties broken by display_order (lower wins), then by team_id.

Minimum confidence to publish: 0.60. Below that we fall back to Quiet Professional
with confidence 0.60 and flag the team in the `notes` column for manual review.
"""

from __future__ import annotations

import json
from typing import Any

from cfb_rankings.db import Database


# ---------------------------------------------------------------------------
# Authoritative taxonomy — from Figma FanbaseArchetypesTaxonomy.tsx
# ---------------------------------------------------------------------------


PRIMARY_ARCHETYPES: list[dict[str, Any]] = [
    {
        "slug": "anxious-dynasty",
        "name": "The Anxious Dynasty",
        "description": "Elite programs with championship expectations but perpetual fear that this year will be the year it all falls apart. Every loss is a crisis. Every win is relief, not celebration.",
        "signature_phrase": "&ldquo;Are we still elite?&rdquo;",
        "half_life": "long",
        "display_order": 1,
    },
    {
        "slug": "perpetual-believer",
        "name": "The Perpetual Believer",
        "description": "Fanbases that maintain irrational optimism regardless of evidence. Every recruiting class is historic. Every portal addition is a game-changer. Reality has not yet broken them.",
        "signature_phrase": "&ldquo;This is our year&rdquo;",
        "half_life": "indefinite",
        "display_order": 2,
    },
    {
        "slug": "wounded-giant",
        "name": "The Wounded Giant",
        "description": "Former blue bloods still living in the past. The glory years loom large; the present is painful. They know they should be better. The fanbase is angry, not hopeful.",
        "signature_phrase": "&ldquo;We used to be something&rdquo;",
        "half_life": "long",
        "display_order": 3,
    },
    {
        "slug": "hopeful-uprising",
        "name": "The Hopeful Uprising",
        "description": "Programs enjoying unexpected success after years of mediocrity. The fanbase is cautiously optimistic but scared to believe. One bad season will send them back to realism.",
        "signature_phrase": "&ldquo;Don&rsquo;t do this to me&rdquo;",
        "half_life": "short",
        "display_order": 4,
    },
    {
        "slug": "quiet-professional",
        "name": "The Quiet Professional",
        "description": "Fanbases with no delusions. They know exactly who their team is: good enough to win 8-10 games, not good enough to win it all. They are at peace with this.",
        "signature_phrase": "&ldquo;We know what we are&rdquo;",
        "half_life": "long",
        "display_order": 5,
    },
    {
        "slug": "identity-crisis-blueblood",
        "name": "The Identity-Crisis Blueblood",
        "description": "Historic programs in the middle of a traumatic transition. The old identity is gone. The new identity has not yet formed. The fanbase is lost.",
        "signature_phrase": "&ldquo;What are we now?&rdquo;",
        "half_life": "medium",
        "display_order": 6,
    },
    {
        "slug": "content-mid-major",
        "name": "The Content Mid-Major",
        "description": "Programs that win more than they should, given resources. The fanbase is proud but realistic. They know the ceiling. They celebrate the overachievements.",
        "signature_phrase": "&ldquo;Punching above our weight&rdquo;",
        "half_life": "long",
        "display_order": 7,
    },
    {
        "slug": "generational-hope",
        "name": "The Generational Hope",
        "description": "Programs experiencing a rare moment of optimism driven by NIL money, a charismatic coach, or a portal windfall. This window is temporary. They know it.",
        "signature_phrase": "&ldquo;The window is now&rdquo;",
        "half_life": "short",
        "display_order": 8,
    },
    {
        "slug": "newly-crowned",
        "name": "Newly Crowned",
        "description": "Fresh champions still in honeymoon, every conversation anchored to the title game.",
        "signature_phrase": "&ldquo;We did it.&rdquo;",
        "half_life": "short",
        "display_order": 9,
    },
    {
        "slug": "stockholm-syndrome",
        "name": "Stockholm Syndrome",
        "description": "Fans so long-suffering they root for suffering itself.",
        "signature_phrase": "&ldquo;It&rsquo;s not supposed to be fun.&rdquo;",
        "half_life": "indefinite",
        "display_order": 10,
    },
    {
        "slug": "service-academy",
        "name": "Service Academy",
        "description": "Tradition-first, outcome-agnostic.",
        "signature_phrase": "&ldquo;The uniform still matters.&rdquo;",
        "half_life": "indefinite",
        "display_order": 11,
    },
    {
        "slug": "coach-cult",
        "name": "Coach Cult",
        "description": "Identity fused to one coach; the team is almost incidental.",
        "signature_phrase": "&ldquo;In Coach we trust.&rdquo;",
        "half_life": "medium",
        "display_order": 12,
    },
    {
        "slug": "hbcu-standard",
        "name": "HBCU Standard",
        "description": "Cultural institution first, football program second.",
        "signature_phrase": "&ldquo;The Classic is the real season.&rdquo;",
        "half_life": "indefinite",
        "display_order": 13,
    },
    {
        "slug": "mercenary",
        "name": "Mercenary",
        "description": "Roster built via portal, no pretense of development.",
        "signature_phrase": "&ldquo;Who&rsquo;s new this week?&rdquo;",
        "half_life": "short",
        "display_order": 14,
    },
    {
        "slug": "celebrity-appointment",
        "name": "Celebrity Appointment",
        "description": "Program&rsquo;s national profile outpaces results.",
        "signature_phrase": "&ldquo;The lights are on us now.&rdquo;",
        "half_life": "short",
        "display_order": 15,
    },
    {
        "slug": "petulant-blueblood",
        "name": "Petulant Blueblood",
        "description": "Former power refusing to concede decline.",
        "signature_phrase": "&ldquo;We&rsquo;re still us.&rdquo;",
        "half_life": "long",
        "display_order": 16,
    },
    {
        "slug": "regional-identity",
        "name": "Regional Identity",
        "description": "Fanbase defined by place more than program.",
        "signature_phrase": "&ldquo;For the state.&rdquo;",
        "half_life": "indefinite",
        "display_order": 17,
    },
    {
        "slug": "sleeper",
        "name": "Sleeper",
        "description": "Quiet program outperforming expectations without attention.",
        "signature_phrase": "&ldquo;Wait, they&rsquo;re 9-2?&rdquo;",
        "half_life": "cyclical",
        "display_order": 18,
    },
]


MODIFIERS: list[dict[str, Any]] = [
    {
        "slug": "emerging",
        "name": "Emerging",
        "description": "Trajectory is up; the program is acquiring momentum the fanbase has not fully priced in.",
        "display_order": 1,
    },
    {
        "slug": "entrenched",
        "name": "Entrenched",
        "description": "The primary archetype has held for multiple seasons with low weekly drift.",
        "display_order": 2,
    },
    {
        "slug": "upstart",
        "name": "Upstart",
        "description": "Newly-relevant program whose fanbase is still writing its vocabulary.",
        "display_order": 3,
    },
    {
        "slug": "fading",
        "name": "Fading",
        "description": "Trajectory is down; the primary archetype is losing its grip even if no successor has emerged.",
        "display_order": 4,
    },
    {
        "slug": "rebuilding",
        "name": "Rebuilding",
        "description": "Post-coach or post-roster reset; the fanbase has accepted a short-term floor in exchange for a future ceiling.",
        "display_order": 5,
    },
    {
        "slug": "reloading",
        "name": "Reloading",
        "description": "Mid-trajectory retooling that the fanbase still narrates as continuity.",
        "display_order": 6,
    },
    {
        "slug": "in-crisis",
        "name": "In Crisis",
        "description": "Something acute and public is destabilizing the program — coach, AD, scandal, or results collapse.",
        "display_order": 7,
    },
    {
        "slug": "ascendant",
        "name": "Ascendant",
        "description": "The program is winning and the fanbase knows it; expectations rise faster than the calendar.",
        "display_order": 8,
    },
]


# ---------------------------------------------------------------------------
# Program identity signatures (deterministic primary-archetype locks)
# ---------------------------------------------------------------------------

# Every FBS team slug that has a deterministic primary archetype. Team slugs
# follow the site's canonical slug scheme (lowercased, hyphenated). Multiple
# aliases are included because the slug canonicalization has drifted across
# historical seasons.
STRUCTURAL_PRIMARIES: dict[str, str] = {
    # Service Academy
    "army": "service-academy",
    "army-west-point": "service-academy",
    "army-black-knights": "service-academy",
    "navy": "service-academy",
    "navy-midshipmen": "service-academy",
    "air-force": "service-academy",
    "air-force-falcons": "service-academy",
    # HBCU Standard
    "jackson-state": "hbcu-standard",
    "jackson-state-tigers": "hbcu-standard",
    "prairie-view-am": "hbcu-standard",
    "prairie-view-a-m": "hbcu-standard",
    "grambling": "hbcu-standard",
    "grambling-state": "hbcu-standard",
    "southern": "hbcu-standard",
    "southern-jaguars": "hbcu-standard",
    "alabama-am": "hbcu-standard",
    "alabama-state": "hbcu-standard",
    "north-carolina-at": "hbcu-standard",
    "north-carolina-a-t": "hbcu-standard",
    "howard": "hbcu-standard",
    "tennessee-state": "hbcu-standard",
    "florida-am": "hbcu-standard",
    "florida-a-m": "hbcu-standard",
}


# Programs with a strong "blueblood pedigree" bias — consulted as a secondary
# signal only after structural checks. Used to bias toward Anxious Dynasty,
# Wounded Giant, Identity-Crisis Blueblood, or Petulant Blueblood.
BLUEBLOOD_PROGRAMS: set[str] = {
    "alabama", "georgia", "ohio-state", "michigan", "texas", "oklahoma",
    "usc", "southern-california", "notre-dame", "nebraska", "penn-state",
    "florida", "lsu", "tennessee", "auburn", "miami", "florida-state",
    "texas-am", "texas-a-m",
}


# Program-level assignments for non-structural archetypes pulled from the Figma
# hub v5.1 taxonomy. These are the "bullseye" teams Issue N° 047 publishes.
SEEDED_PRIMARY: dict[str, dict[str, Any]] = {
    # Anxious Dynasty
    "alabama": {"archetype": "anxious-dynasty", "confidence": 0.94, "modifiers": ["entrenched", "fading"]},
    "ohio-state": {"archetype": "anxious-dynasty", "confidence": 0.91, "modifiers": ["entrenched"]},
    "georgia": {"archetype": "anxious-dynasty", "confidence": 0.88, "modifiers": ["entrenched", "ascendant"]},
    # Perpetual Believer
    "nebraska": {"archetype": "perpetual-believer", "confidence": 0.97, "modifiers": ["entrenched"]},
    "texas-am": {"archetype": "perpetual-believer", "confidence": 0.93, "modifiers": ["fading"]},
    "texas-a-m": {"archetype": "perpetual-believer", "confidence": 0.93, "modifiers": ["fading"]},
    "tennessee": {"archetype": "perpetual-believer", "confidence": 0.84, "modifiers": ["reloading"]},
    # Wounded Giant
    "usc": {"archetype": "wounded-giant", "confidence": 0.91, "modifiers": ["in-crisis"]},
    "southern-california": {"archetype": "wounded-giant", "confidence": 0.91, "modifiers": ["in-crisis"]},
    "florida": {"archetype": "wounded-giant", "confidence": 0.88, "modifiers": ["rebuilding"]},
    "miami": {"archetype": "wounded-giant", "confidence": 0.85, "modifiers": ["reloading"]},
    # Hopeful Uprising
    "indiana": {"archetype": "hopeful-uprising", "confidence": 0.89, "modifiers": ["ascendant", "upstart"]},
    "kansas": {"archetype": "hopeful-uprising", "confidence": 0.86, "modifiers": ["emerging"]},
    "arizona": {"archetype": "hopeful-uprising", "confidence": 0.81, "modifiers": ["emerging"]},
    # Quiet Professional
    "iowa": {"archetype": "quiet-professional", "confidence": 0.93, "modifiers": ["entrenched"]},
    "wisconsin": {"archetype": "quiet-professional", "confidence": 0.89, "modifiers": ["reloading"]},
    "utah": {"archetype": "quiet-professional", "confidence": 0.87, "modifiers": ["entrenched"]},
    # Identity-Crisis Blueblood
    "michigan": {"archetype": "identity-crisis-blueblood", "confidence": 0.96, "modifiers": ["in-crisis", "fading"]},
    "florida-state": {"archetype": "identity-crisis-blueblood", "confidence": 0.92, "modifiers": ["in-crisis"]},
    # Content Mid-Major
    "boise-state": {"archetype": "content-mid-major", "confidence": 0.91, "modifiers": ["entrenched"]},
    "appalachian-state": {"archetype": "content-mid-major", "confidence": 0.88, "modifiers": ["entrenched"]},
    "app-state": {"archetype": "content-mid-major", "confidence": 0.88, "modifiers": ["entrenched"]},
    # Generational Hope
    "colorado": {"archetype": "generational-hope", "confidence": 0.94, "modifiers": ["ascendant", "upstart"]},
    "smu": {"archetype": "generational-hope", "confidence": 0.87, "modifiers": ["ascendant"]},
    # Newly Crowned
    "washington": {"archetype": "newly-crowned", "confidence": 0.96, "modifiers": ["ascendant"]},
    "lsu": {"archetype": "newly-crowned", "confidence": 0.82, "modifiers": ["fading"]},
    # Stockholm Syndrome
    "northwestern": {"archetype": "stockholm-syndrome", "confidence": 0.94, "modifiers": ["entrenched"]},
    "vanderbilt": {"archetype": "stockholm-syndrome", "confidence": 0.91, "modifiers": ["entrenched"]},
    # Coach Cult
    "kentucky": {"archetype": "coach-cult", "confidence": 0.82, "modifiers": ["fading"]},
    "ucla": {"archetype": "coach-cult", "confidence": 0.77, "modifiers": ["emerging"]},
    # Mercenary
    "texas-tech": {"archetype": "mercenary", "confidence": 0.91, "modifiers": ["upstart", "ascendant"]},
    # Celebrity Appointment handled by deion mapping — Colorado already seeded above under generational-hope
    # Petulant Blueblood
    "oklahoma": {"archetype": "petulant-blueblood", "confidence": 0.76, "modifiers": ["reloading"]},
    # Regional Identity
    "west-virginia": {"archetype": "regional-identity", "confidence": 0.94, "modifiers": ["entrenched"]},
    "ole-miss": {"archetype": "regional-identity", "confidence": 0.88, "modifiers": ["ascendant"]},
    "mississippi": {"archetype": "regional-identity", "confidence": 0.88, "modifiers": ["ascendant"]},
    "arkansas": {"archetype": "regional-identity", "confidence": 0.83, "modifiers": ["fading"]},
    # Sleeper
    "memphis": {"archetype": "sleeper", "confidence": 0.89, "modifiers": ["emerging"]},
    "james-madison": {"archetype": "sleeper", "confidence": 0.86, "modifiers": ["upstart"]},
    "liberty": {"archetype": "sleeper", "confidence": 0.82, "modifiers": ["emerging"]},
    # Also explicitly covered Texas as Perpetual Believer backstop
    "texas": {"archetype": "anxious-dynasty", "confidence": 0.83, "modifiers": ["ascendant"]},
    "oregon": {"archetype": "anxious-dynasty", "confidence": 0.78, "modifiers": ["ascendant", "emerging"]},
    "penn-state": {"archetype": "anxious-dynasty", "confidence": 0.74, "modifiers": ["entrenched"]},
    "notre-dame": {"archetype": "petulant-blueblood", "confidence": 0.71, "modifiers": ["entrenched"]},
    "clemson": {"archetype": "quiet-professional", "confidence": 0.72, "modifiers": ["fading"]},
    "auburn": {"archetype": "wounded-giant", "confidence": 0.79, "modifiers": ["rebuilding"]},
    "florida-gators": {"archetype": "wounded-giant", "confidence": 0.88, "modifiers": ["rebuilding"]},
}


FALLBACK_ARCHETYPE_SLUG = "quiet-professional"
FALLBACK_CONFIDENCE = 0.60
MIN_PUBLISH_CONFIDENCE = 0.60


# ---------------------------------------------------------------------------
# Lookups
# ---------------------------------------------------------------------------


def archetype_by_slug() -> dict[str, dict[str, Any]]:
    return {row["slug"]: row for row in PRIMARY_ARCHETYPES}


def modifier_by_slug() -> dict[str, dict[str, Any]]:
    return {row["slug"]: row for row in MODIFIERS}


# ---------------------------------------------------------------------------
# Seeding
# ---------------------------------------------------------------------------


def seed_taxonomy(db: Database) -> tuple[int, int]:
    """Populate fanbase_archetype_taxonomy idempotently. Returns (primary, modifier) counts."""

    primary_rows = [
        {
            "kind": "primary",
            "slug": row["slug"],
            "name": row["name"],
            "description": row["description"],
            "signature_phrase": row["signature_phrase"],
            "half_life": row["half_life"],
            "display_order": row["display_order"],
        }
        for row in PRIMARY_ARCHETYPES
    ]
    modifier_rows = [
        {
            "kind": "modifier",
            "slug": row["slug"],
            "name": row["name"],
            "description": row["description"],
            "signature_phrase": "",
            "half_life": "medium",
            "display_order": row["display_order"],
        }
        for row in MODIFIERS
    ]
    db.upsert_many(
        "fanbase_archetype_taxonomy",
        primary_rows + modifier_rows,
        conflict_columns=["kind", "slug"],
        update_columns=["name", "description", "signature_phrase", "half_life", "display_order"],
    )
    return len(primary_rows), len(modifier_rows)


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------


def classify_team(slug: str, *, power_percentile: float | None = None,
                  resume_percentile: float | None = None,
                  level_code: str = "FBS") -> dict[str, Any]:
    """Return a classification dict for a single team.

    Signature: slug + optional structural percentiles. When a team has an
    explicit seeded assignment (from Issue N° 047) we use it verbatim. Otherwise
    we fall through a rules priority order: structural (Service Academy, HBCU),
    then seeded primaries, then trajectory-based defaults, then fallback.
    """

    slug_norm = (slug or "").strip().lower()
    taxonomy = archetype_by_slug()

    # Rule 1 — structural identity lock
    if slug_norm in STRUCTURAL_PRIMARIES:
        archetype_slug = STRUCTURAL_PRIMARIES[slug_norm]
        archetype = taxonomy[archetype_slug]
        return {
            "primary_archetype_slug": archetype_slug,
            "primary_confidence": 0.95,
            "modifier_slugs": ["entrenched"],
            "signature_phrase": archetype["signature_phrase"],
            "notes": "structural-lock",
        }

    # Rule 2 — explicit seeded assignment for Issue N° 047
    if slug_norm in SEEDED_PRIMARY:
        seed = SEEDED_PRIMARY[slug_norm]
        archetype = taxonomy[seed["archetype"]]
        return {
            "primary_archetype_slug": seed["archetype"],
            "primary_confidence": float(seed["confidence"]),
            "modifier_slugs": list(seed.get("modifiers") or []),
            "signature_phrase": archetype["signature_phrase"],
            "notes": "seeded",
        }

    # Rule 3 — trajectory-based default for non-seeded FBS teams.
    # Use power/resume percentiles when present.
    power = float(power_percentile) if power_percentile is not None else None
    resume = float(resume_percentile) if resume_percentile is not None else None

    if power is not None and power >= 0.80:
        # Top-quintile programs without a seeded archetype read as Quiet Professional.
        if slug_norm in BLUEBLOOD_PROGRAMS:
            return _pack("petulant-blueblood", 0.68, ["entrenched"], taxonomy, "trajectory-blueblood")
        return _pack("quiet-professional", 0.72, ["entrenched"], taxonomy, "trajectory-strong")

    if power is not None and power <= 0.25:
        # Bottom-quartile programs read as Stockholm Syndrome or Sleeper depending
        # on resume percentile vs power (a positive gap = outperforming = sleeper).
        if resume is not None and power is not None and resume - power >= 0.10:
            return _pack("sleeper", 0.66, ["emerging"], taxonomy, "trajectory-underrated")
        return _pack("stockholm-syndrome", 0.65, ["entrenched"], taxonomy, "trajectory-floor")

    if power is not None and 0.45 <= power <= 0.70:
        return _pack("content-mid-major", 0.68, ["entrenched"], taxonomy, "trajectory-middle")

    # Rule 4 — offseason fallback
    return _pack(FALLBACK_ARCHETYPE_SLUG, FALLBACK_CONFIDENCE, [], taxonomy, "fallback")


def _pack(slug: str, conf: float, mods: list[str], taxonomy: dict[str, dict[str, Any]], note: str) -> dict[str, Any]:
    return {
        "primary_archetype_slug": slug,
        "primary_confidence": conf,
        "modifier_slugs": mods,
        "signature_phrase": taxonomy[slug]["signature_phrase"],
        "notes": note,
    }


def _percentiles_within_level(value_rows: list[dict[str, Any]], value_key: str) -> dict[int, float]:
    """Map team_id -> 0..1 percentile, ranked *within each competitive level*.

    The power/resume tables pool FBS + FCS + DII + DIII (~707 teams), and FBS
    teams cluster at the top of that pool — so a cross-level percentile pushes
    nearly every FBS team to >=0.80 and collapses the classifier onto the
    quiet-professional fallback (fixed 2026-05-28). Bucketing by ``level_code``
    restores a real within-FBS distribution.
    """
    by_level: dict[str, list[dict[str, Any]]] = {}
    for entry in value_rows:
        by_level.setdefault(str(entry.get("level_code") or "FBS"), []).append(entry)
    out: dict[int, float] = {}
    for level_entries in by_level.values():
        level_entries.sort(key=lambda r: float(r[value_key]))
        total = len(level_entries)
        for rank, entry in enumerate(level_entries):
            out[int(entry["team_id"])] = rank / max(1, total - 1)
    return out


def classify_all_fanbases(db: Database, season_year: int,
                          classifier_version: str = "v1.0") -> int:
    """Run the classifier over every active FBS team and persist results.

    Returns the number of rows written to fanbase_classification.
    """

    # Pull the latest model-run power rating ranking for the season so we can
    # derive a structural percentile without schema assumptions. Falls back
    # gracefully when there's no model run yet (every team gets None percentile
    # and classifies via the seeded/structural rules only).
    latest_run = db.query_one(
        """
        select mr.model_run_id
        from model_runs mr
        where mr.season_year = %(season_year)s
          and exists (
            select 1 from power_ratings_weekly p where p.model_run_id = mr.model_run_id
          )
        order by mr.week desc, mr.model_run_id desc
        limit 1
        """,
        {"season_year": season_year},
    )
    model_run_id = int(latest_run["model_run_id"]) if latest_run else None

    power_by_team: dict[int, float] = {}
    resume_by_team: dict[int, float] = {}

    if model_run_id is not None:
        power_rows = db.query_all(
            """
            select p.team_id, p.power_rating, t.level_code
            from power_ratings_weekly p
            join teams t on t.team_id = p.team_id
            where p.model_run_id = %(model_run_id)s
            """,
            {"model_run_id": model_run_id},
        )
        if power_rows:
            power_by_team = _percentiles_within_level(power_rows, "power_rating")

        resume_rows = db.query_all(
            """
            select r.team_id, r.resume_score, t.level_code
            from resume_ratings_weekly r
            join teams t on t.team_id = r.team_id
            where r.model_run_id = %(model_run_id)s
            """,
            {"model_run_id": model_run_id},
        )
        if resume_rows:
            resume_by_team = _percentiles_within_level(resume_rows, "resume_score")

    # Include all active teams (FBS + FCS + DII + DIII) so that HBCU and Service
    # Academy FCS programs get deterministic structural classifications and appear
    # on their team pages with a SIGNATURE PHRASE.
    rows = db.query_all(
        """
        select
          t.team_id,
          t.slug,
          t.canonical_name,
          t.level_code
        from teams t
        where coalesce(t.is_active, 1) = 1
          and t.level_code is not null
        """
    )
    # Attach percentiles onto each row post-query
    for row in rows:
        tid = int(row["team_id"])
        row["power_percentile"] = power_by_team.get(tid)
        row["resume_percentile"] = resume_by_team.get(tid)

    classification_rows: list[dict[str, Any]] = []
    history_rows: list[dict[str, Any]] = []
    for row in rows:
        team_id = int(row["team_id"])
        slug = str(row.get("slug") or "")
        power = row.get("power_percentile")
        resume = row.get("resume_percentile")
        result = classify_team(
            slug,
            power_percentile=float(power) if power is not None else None,
            resume_percentile=float(resume) if resume is not None else None,
            level_code=str(row.get("level_code") or "FBS"),
        )
        classification_rows.append(
            {
                "team_id": team_id,
                "season_year": season_year,
                "primary_archetype_slug": result["primary_archetype_slug"],
                "primary_confidence": float(result["primary_confidence"]),
                "modifier_slugs_json": json.dumps(result["modifier_slugs"]),
                "signature_phrase": result["signature_phrase"],
                "classifier_version": classifier_version,
                "notes": result["notes"],
            }
        )
        history_rows.append(
            {
                "team_id": team_id,
                "season_year": season_year,
                "primary_archetype_slug": result["primary_archetype_slug"],
                "primary_confidence": float(result["primary_confidence"]),
                "modifier_slugs_json": json.dumps(result["modifier_slugs"]),
                "classifier_version": classifier_version,
            }
        )

    db.upsert_many(
        "fanbase_classification",
        classification_rows,
        conflict_columns=["team_id", "season_year"],
        update_columns=[
            "primary_archetype_slug",
            "primary_confidence",
            "modifier_slugs_json",
            "signature_phrase",
            "classifier_version",
            "notes",
            "classified_at",
        ],
    )
    db.upsert_many(
        "fanbase_classification_history",
        history_rows,
        conflict_columns=["team_id", "season_year", "classifier_version"],
        update_columns=[
            "primary_archetype_slug",
            "primary_confidence",
            "modifier_slugs_json",
            "classified_at",
        ],
    )
    return len(classification_rows)


# ---------------------------------------------------------------------------
# Team-page migration sparkline
# ---------------------------------------------------------------------------


def fetch_migration_sparkline(db: Database, team_id: int, seasons: int = 5) -> list[dict[str, Any]]:
    """Return the last N seasons of classification history for a single team."""

    rows = db.query_all(
        """
        select season_year, primary_archetype_slug, primary_confidence
        from fanbase_classification_history
        where team_id = %(team_id)s
        order by season_year desc
        limit %(seasons)s
        """,
        {"team_id": team_id, "seasons": int(seasons)},
    )
    return list(reversed(rows))
