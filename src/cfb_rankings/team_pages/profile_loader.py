"""Profile loader: reads a ``profiles/<slug>.md`` file into a dict.

Profile format:

    ---
    <YAML frontmatter: scalar + short-list + dict fields>
    ---
    # Markdown body with section headings the loader parses into
    # {section_slug: {subsection_slug_or_field: paragraph_text}}.

The parser is intentionally permissive: unknown top-level sections become
keys in the ``sections`` dict; the frontmatter is authoritative for
structured data; and the body is the editorial long-form that can be
surfaced directly or chunked by the narrative generator.

Profiles are the *editorial infrastructure* (Iteration Log §"Deep program
profile — principles"): editing a field here should change rendered output
everywhere that field reaches. The loader intentionally keeps the schema
loose so new fields can be added without a migration.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


PROFILES_DIR = Path(__file__).resolve().parents[3] / "profiles"

PROFILED_SLUGS: set[str] = {
    p.stem.replace("_", "-")
    for p in PROFILES_DIR.glob("*.md")
    if not p.name.startswith("_")
}


@dataclass
class Profile:
    slug: str
    team_id: int | None
    program_tier: int
    voice_register: str
    tonal_template: str
    identity_phrase: str
    mantra: str
    frontmatter: dict[str, Any]
    sections: dict[str, dict[str, str]]
    source_path: Path

    # Convenience accessors -------------------------------------------------

    @property
    def accent_hex(self) -> str:
        return self.frontmatter.get("accent_hex", "#1d1d1f")

    @property
    def accent_hex_secondary(self) -> str | None:
        return self.frontmatter.get("accent_hex_secondary")

    @property
    def vocab(self) -> dict[str, str]:
        return dict(self.frontmatter.get("vocab", {}) or {})

    @property
    def mascot_voice(self) -> dict[str, str]:
        return dict(self.frontmatter.get("mascot_voice", {}) or {})

    @property
    def era_name_overrides(self) -> dict[str, str]:
        return dict(self.frontmatter.get("era_name_overrides", {}) or {})

    @property
    def never_use(self) -> list[str]:
        return list(self.frontmatter.get("never_use", []) or [])

    @property
    def always_surface(self) -> list[str]:
        return list(self.frontmatter.get("always_surface", []) or [])

    @property
    def rivalries(self) -> list[dict[str, Any]]:
        return list(self.frontmatter.get("rivalries", []) or [])

    @property
    def aspiration_ladder(self) -> list[dict[str, Any]]:
        return list(self.frontmatter.get("aspiration_ladder", []) or [])

    @property
    def stock_phrases(self) -> list[str]:
        return list(self.frontmatter.get("stock_phrases", []) or [])

    @property
    def program_name(self) -> str:
        return self.frontmatter.get("program_name", self.slug.replace("-", " ").title())

    @property
    def display_name(self) -> str:
        return self.frontmatter.get("display_name", self.program_name)

    def to_profile_json(self) -> str:
        """Full profile as JSON (for team_profiles.profile_json column)."""
        blob = {
            "frontmatter": self.frontmatter,
            "sections": self.sections,
            "slug": self.slug,
        }
        return json.dumps(blob, ensure_ascii=False, indent=2)


_FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_H1_RE = re.compile(r"^# +(.+?)\s*$", re.MULTILINE)
_H2_RE = re.compile(r"^## +(.+?)\s*$", re.MULTILINE)


def load_profile(slug: str, profiles_dir: Path | None = None) -> Profile:
    """Load ``profiles/<slug>.md`` and return a Profile dataclass.

    Raises FileNotFoundError if the file doesn't exist.
    """
    base = profiles_dir or PROFILES_DIR
    path = base / f"{slug}.md"
    if not path.exists():
        raise FileNotFoundError(f"profile not found: {path}")
    text = path.read_text(encoding="utf-8")

    front_match = _FRONT_MATTER_RE.match(text)
    if not front_match:
        raise ValueError(f"profile {path} missing YAML frontmatter")
    front_raw = front_match.group(1)
    frontmatter: dict[str, Any] = yaml.safe_load(front_raw) or {}
    body = text[front_match.end():]

    sections = _parse_sections(body)

    return Profile(
        slug=slug,
        team_id=frontmatter.get("team_id"),
        program_tier=int(frontmatter.get("program_tier", 5)),
        voice_register=frontmatter.get("voice_register", "generic"),
        tonal_template=frontmatter.get("tonal_template", "generic"),
        identity_phrase=frontmatter.get("identity_phrase", ""),
        mantra=frontmatter.get("mantra", ""),
        frontmatter=frontmatter,
        sections=sections,
        source_path=path,
    )


def _parse_sections(body: str) -> dict[str, dict[str, str]]:
    """Parse markdown body into nested {section: {subsection: content}}.

    Uses H1 for sections, H2 for subsections. Content for a subsection runs
    from the H2 line to the next H2 or H1. Content for a bare section (no
    H2s) is collected under '_body'.
    """
    out: dict[str, dict[str, str]] = {}
    # Split on H1s first
    parts = re.split(r"^# +", body, flags=re.MULTILINE)
    for part in parts:
        if not part.strip():
            continue
        lines = part.split("\n", 1)
        title = lines[0].strip()
        rest = lines[1] if len(lines) > 1 else ""
        section_slug = _slugify(title)

        subsections: dict[str, str] = {}
        sub_parts = re.split(r"^## +", rest, flags=re.MULTILINE)
        # First chunk before any H2 is the bare body
        bare = sub_parts[0].strip()
        if bare:
            subsections["_body"] = bare
        for sub in sub_parts[1:]:
            sub_lines = sub.split("\n", 1)
            sub_title = sub_lines[0].strip()
            sub_body = sub_lines[1].strip() if len(sub_lines) > 1 else ""
            subsections[_slugify(sub_title)] = sub_body
        out[section_slug] = subsections
    return out


def _slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def upsert_profile_to_db(db, profile: Profile) -> None:
    """Write the profile into team_profiles and team_voice.

    Idempotent. Overwrites the existing rows keyed on team_id / program_slug.
    """
    if profile.team_id is None:
        raise ValueError(
            f"profile '{profile.slug}' missing 'team_id' in frontmatter — "
            f"cannot upsert into team_profiles"
        )

    profile_json = profile.to_profile_json()

    db.execute(
        """
        insert into team_profiles (
            team_id, program_slug, program_tier, voice_register,
            identity_phrase, mantra, tonal_template, profile_json,
            source_path, authored_by, editorial_review_status, updated_at_utc
        ) values (
            :team_id, :slug, :tier, :register,
            :identity, :mantra, :tonal, :profile_json,
            :source_path, :authored_by, :status, current_timestamp
        )
        on conflict(team_id) do update set
            program_slug = excluded.program_slug,
            program_tier = excluded.program_tier,
            voice_register = excluded.voice_register,
            identity_phrase = excluded.identity_phrase,
            mantra = excluded.mantra,
            tonal_template = excluded.tonal_template,
            profile_json = excluded.profile_json,
            source_path = excluded.source_path,
            authored_by = excluded.authored_by,
            updated_at_utc = current_timestamp
        """,
        {
            "team_id": profile.team_id,
            "slug": profile.slug,
            "tier": profile.program_tier,
            "register": profile.voice_register,
            "identity": profile.identity_phrase,
            "mantra": profile.mantra,
            "tonal": profile.tonal_template,
            "profile_json": profile_json,
            "source_path": str(profile.source_path.relative_to(profile.source_path.parents[1])),
            "authored_by": profile.frontmatter.get("authored_by", "unknown"),
            "status": profile.frontmatter.get("editorial_review_status", "draft"),
        },
    )

    db.execute(
        """
        insert into team_voice (
            team_id, accent_hex, accent_hex_secondary, gradient_hex_pair,
            vocab_dict_json, mascot_voice_templates_json,
            era_name_overrides_json, tonal_template,
            never_use_phrases_json, always_surface_phrases_json,
            updated_at_utc
        ) values (
            :team_id, :accent, :accent2, :gradient,
            :vocab, :mascot, :eras, :tonal,
            :never_use, :always_surface, current_timestamp
        )
        on conflict(team_id) do update set
            accent_hex = excluded.accent_hex,
            accent_hex_secondary = excluded.accent_hex_secondary,
            gradient_hex_pair = excluded.gradient_hex_pair,
            vocab_dict_json = excluded.vocab_dict_json,
            mascot_voice_templates_json = excluded.mascot_voice_templates_json,
            era_name_overrides_json = excluded.era_name_overrides_json,
            tonal_template = excluded.tonal_template,
            never_use_phrases_json = excluded.never_use_phrases_json,
            always_surface_phrases_json = excluded.always_surface_phrases_json,
            updated_at_utc = current_timestamp
        """,
        {
            "team_id": profile.team_id,
            "accent": profile.accent_hex,
            "accent2": profile.accent_hex_secondary,
            "gradient": (
                f"{profile.accent_hex},{profile.accent_hex_secondary}"
                if profile.accent_hex_secondary
                else profile.accent_hex
            ),
            "vocab": json.dumps(profile.vocab, ensure_ascii=False),
            "mascot": json.dumps(profile.mascot_voice, ensure_ascii=False),
            "eras": json.dumps(profile.era_name_overrides, ensure_ascii=False),
            "tonal": profile.tonal_template,
            "never_use": json.dumps(profile.never_use, ensure_ascii=False),
            "always_surface": json.dumps(profile.always_surface, ensure_ascii=False),
        },
    )


# ---------------------------------------------------------------------------
# Sprint H — Synthesized Profiles for unprofiled FBS teams.
# Closes the audit's T31 ("two-tier reality") without authoring 100 YAMLs by
# hand. Pulls usable identity material from the database (team_brand colors +
# mascot_name, conference, school_name) and produces a Profile that lets the
# world-class renderer execute. Hand-authored YAMLs always win when present.
# ---------------------------------------------------------------------------


# Default tier ↔ register defaults. Synthesized teams land at tier 5 unless
# something in the DB pushes them higher (e.g., conference of last resort).
_CONFERENCE_TIER_HINTS: dict[str, int] = {
    "Southeastern Conference": 2,
    "SEC": 2,
    "Big Ten Conference": 2,
    "Big Ten": 2,
    "Atlantic Coast Conference": 2,
    "ACC": 2,
    "Big 12 Conference": 3,
    "Big 12": 3,
    "FBS Independents": 3,
    "American Athletic Conference": 4,
    "American Athletic": 4,
    "Mountain West Conference": 5,
    "Mountain West": 5,
    "Sun Belt Conference": 5,
    "Sun Belt": 5,
    "Mid-American Conference": 6,
    "MAC": 6,
    "Conference USA": 6,
    "C-USA": 6,
}


def _safe_color(hex_in: str | None, fallback: str) -> str:
    if not hex_in:
        return fallback
    s = str(hex_in).strip()
    if not s:
        return fallback
    if not s.startswith("#"):
        s = "#" + s
    # Reject obviously bad values
    if len(s) not in (4, 7):
        return fallback
    return s


def _fetch_synth_inputs(db, slug: str) -> dict[str, Any] | None:
    """Return the data bundle needed to synthesize a Profile.

    Returns None when no FBS team with this slug exists.
    """
    row = db.query_one(
        """
        select t.team_id, t.canonical_name, t.school_name, t.short_name,
               t.level_code, t.city, t.state, c.conference_name,
               tb.primary_color, tb.secondary_color, tb.mascot_name,
               tb.abbreviation_short
        from teams t
        left join conferences c on c.conference_id = t.current_conference_id
        left join team_brand tb on tb.team_id = t.team_id
        where t.slug = :slug
        """,
        {"slug": slug},
    )
    return dict(row) if row else None


def synthesize_profile(slug: str, db) -> Profile:
    """Build a usable Profile dataclass from database data alone.

    For programs with a hand-authored YAML, prefer load_profile(); fall here
    only for the long tail. The synthesized Profile drives the same modules
    as authored profiles, just with tier-defaulted voice + empty rituals.
    """
    inputs = _fetch_synth_inputs(db, slug)
    if inputs is None:
        raise LookupError(f"synthesize_profile: team slug not found: {slug}")

    program_name = (
        inputs.get("school_name")
        or inputs.get("canonical_name")
        or slug.replace("-", " ").title()
    )
    conference = inputs.get("conference_name") or ""
    mascot = inputs.get("mascot_name") or ""
    short_name = inputs.get("short_name") or program_name
    abbrev = inputs.get("abbreviation_short") or ""
    primary = _safe_color(inputs.get("primary_color"), "#1d1d1f")
    secondary = _safe_color(inputs.get("secondary_color"), "#8a8a8a")

    # Tier from conference, then nudge for known-tier mismatch isn't worth
    # the complexity — let the user override later with a YAML.
    tier = _CONFERENCE_TIER_HINTS.get(conference, 6)

    # Identity phrase: a plain, honest descriptor. Authored YAMLs will replace
    # this with bespoke voice; for the long tail this beats nothing.
    if conference:
        identity_phrase = (
            f"{program_name} is the {conference} program known for "
            f"{('the ' + mascot.lower()) if mascot else 'its faithful following'}."
        )
    else:
        identity_phrase = f"{program_name} is the FBS program known for its faithful following."

    selfname = (
        f"the {mascot}" if mascot and not mascot.lower().startswith("the ")
        else (mascot or f"the {short_name}")
    )

    mantra = f"Go {mascot}." if mascot else f"Go {short_name}."

    frontmatter = {
        "team_id": int(inputs["team_id"]),
        "program_name": program_name,
        "display_name": program_name,
        "program_slug": slug,
        "program_tier": tier,
        "voice_register": "plain-honest",
        "tonal_template": "plain-honest",
        "identity_phrase": identity_phrase,
        "mantra": mantra,
        "authored_by": "synthesized",
        "editorial_review_status": "synthesized",
        "model_version": "team-pages synth v1.0",
        "accent_hex": primary,
        "accent_hex_secondary": secondary,
        "gradient_hex_pair": f"{primary},{secondary}",
        "vocab": {
            "signoff": mantra,
            "greeting": f"Go {short_name}",
            "hashtags": [f"#{slug.replace('-', '').title()}", f"#Go{short_name.replace(' ', '')}"],
            "selfname": selfname,
            "stadium_short": "",
            "abbreviation": abbrev,
        },
        "rituals": [],
        "cultural_anchors": {
            "one_sentence": (
                f"{program_name} is a program whose voice hasn't been authored yet — "
                "this page renders from database signal alone until the editorial profile is filed."
            ),
            "if_team_didnt_exist_cfb_would_lose": "",
            "fan_archetype_dominant": "",
            "outsider_archetype_dominant": "",
        },
        "visual_identity_anchors": {},
        "mascot_voice": {
            "awaiting_signal": "Awaiting signal — voice not yet authored.",
            "loss_acknowledged": "Quiet today.",
            "win_celebrated": "Win in the books.",
        },
        "stock_phrases": [f"Go {short_name}", mantra],
        "never_use": [],
        "always_surface": [],
    }

    sections: dict[str, dict[str, str]] = {
        "program_history": {
            "_body": (
                f"Program profile for {program_name} has not yet been hand-authored. "
                f"This page renders the world-class chrome from database signal "
                f"({conference}, {inputs.get('city') or '?'}). The editorial body "
                "fills in when a profile YAML is filed."
            )
        },
        "fanbase_summary": {
            "_body": (
                f"Fanbase voice for {program_name} pending editorial profile. "
                "Pulse signals populate from the conversation pipeline as they arrive."
            )
        },
        "rivalry_context": {
            "_body": (
                f"Rivalry context for {program_name} pending profile authoring."
            )
        },
    }

    # Synthetic source_path points to a path that does NOT exist on disk.
    # Downstream code that branches on file existence will treat this as
    # synthesized; downstream code that just stringifies it gets a stable label.
    synth_path = PROFILES_DIR / f"_synth_{slug}.md"

    return Profile(
        slug=slug,
        team_id=int(inputs["team_id"]),
        program_tier=tier,
        voice_register="plain-honest",
        tonal_template="plain-honest",
        identity_phrase=identity_phrase,
        mantra=mantra,
        frontmatter=frontmatter,
        sections=sections,
        source_path=synth_path,
    )


def load_or_synthesize(slug: str, db, profiles_dir: Path | None = None) -> Profile:
    """Return a Profile for any FBS slug.

    Hand-authored YAML wins when present. Else falls back to synthesize_profile().
    """
    try:
        return load_profile(slug, profiles_dir=profiles_dir)
    except FileNotFoundError:
        return synthesize_profile(slug, db)


def list_real_fbs_slugs(db) -> list[str]:
    """Return the canonical list of FBS slugs (P4 + G5 + Independents).

    Used by the bulk renderer to iterate every real FBS program. Filters out
    the data-quality stragglers (e.g., "valley-city-state") that carry
    level_code='FBS' incorrectly in the source feed.
    """
    rows = db.query_all(
        """
        select t.slug
        from teams t
        join conferences c on c.conference_id = t.current_conference_id
        where t.level_code = 'FBS'
          and c.conference_name in (
              'Southeastern Conference', 'SEC',
              'Big Ten Conference', 'Big Ten',
              'Atlantic Coast Conference', 'ACC',
              'Big 12 Conference', 'Big 12',
              'American Athletic Conference', 'American Athletic',
              'Mountain West Conference', 'Mountain West',
              'Sun Belt Conference', 'Sun Belt',
              'Mid-American Conference', 'MAC',
              'Conference USA', 'C-USA',
              'FBS Independents',
              'Pac-12 Conference', 'Pac-12'
          )
        order by t.slug
        """
    )
    return [r["slug"] for r in rows]
