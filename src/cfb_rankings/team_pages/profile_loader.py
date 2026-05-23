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

# Try the editable-install relative path first, but fall back to CWD-relative
# if PROFILES_DIR doesn't exist or is empty (caught a CI bug where pip's
# editable install resolved __file__ to a path where parents[3] didn't reach
# the repo root).
def _resolve_profiles_dir() -> Path:
    if PROFILES_DIR.exists() and any(PROFILES_DIR.glob("*.md")):
        return PROFILES_DIR
    # Fallback 1: CWD/profiles (matches how CI / build-site is invoked)
    cwd_profiles = Path.cwd() / "profiles"
    if cwd_profiles.exists() and any(cwd_profiles.glob("*.md")):
        return cwd_profiles.resolve()
    return PROFILES_DIR


_resolved_profiles_dir = _resolve_profiles_dir()
if _resolved_profiles_dir != PROFILES_DIR:
    PROFILES_DIR = _resolved_profiles_dir

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

# Mascot-keyed voice library. Maps the lowercased mascot_name from
# team_brand to a (awaiting_signal, loss_acknowledged, win_celebrated)
# triple, so synthesized profiles get a differentiated mascot voice
# instead of all reading "Awaiting signal — voice not yet authored."
# Each entry handles plural forms (Tigers, Bulldogs) gracefully.
_MASCOT_VOICE_LIBRARY: dict[str, dict[str, str]] = {
    "tiger":     {"awaiting_signal": "The Tiger is patient.",
                  "loss_acknowledged": "Tiger waits. Tiger hunts again.",
                  "win_celebrated": "The Tiger eats tonight."},
    "tigers":    {"awaiting_signal": "The Tigers wait in the brush.",
                  "loss_acknowledged": "Quieter Tigers. Same Tigers.",
                  "win_celebrated": "The Tigers earn their dinner."},
    "bulldog":   {"awaiting_signal": "The Bulldog is patient.",
                  "loss_acknowledged": "Bulldog grunts. Bulldog comes back.",
                  "win_celebrated": "The Bulldog earns the bone."},
    "bulldogs":  {"awaiting_signal": "The Bulldogs are patient.",
                  "loss_acknowledged": "Bulldogs grunt. They come back.",
                  "win_celebrated": "Bulldogs eat tonight."},
    "wildcat":   {"awaiting_signal": "The Wildcat watches.",
                  "loss_acknowledged": "Wildcat retreats. Wildcat returns.",
                  "win_celebrated": "The Wildcat hunts."},
    "wildcats":  {"awaiting_signal": "The Wildcats are on the prowl.",
                  "loss_acknowledged": "Wildcats lick wounds.",
                  "win_celebrated": "Wildcats own the night."},
    "eagle":     {"awaiting_signal": "The Eagle circles.",
                  "loss_acknowledged": "Eagle lands. Eagle takes off again.",
                  "win_celebrated": "The Eagle soars."},
    "eagles":    {"awaiting_signal": "The Eagles circle the field.",
                  "loss_acknowledged": "Eagles land. Eagles fly tomorrow.",
                  "win_celebrated": "Eagles take flight tonight."},
    "lion":      {"awaiting_signal": "The Lion rests.",
                  "loss_acknowledged": "Lion sleeps. Lion roars again.",
                  "win_celebrated": "The Lion roars."},
    "lions":     {"awaiting_signal": "The Lions rest in the shade.",
                  "loss_acknowledged": "Lions sleep tonight.",
                  "win_celebrated": "The Lions roar."},
    "panther":   {"awaiting_signal": "The Panther is silent.",
                  "loss_acknowledged": "Panther retreats. Panther stalks again.",
                  "win_celebrated": "The Panther hunts tonight."},
    "panthers":  {"awaiting_signal": "The Panthers patrol the field.",
                  "loss_acknowledged": "Panthers regroup.",
                  "win_celebrated": "Panthers earn their kill."},
    "bear":      {"awaiting_signal": "The Bear hibernates.",
                  "loss_acknowledged": "Bear sleeps off the wound.",
                  "win_celebrated": "The Bear feeds."},
    "bears":     {"awaiting_signal": "The Bears are in the woods.",
                  "loss_acknowledged": "Bears retreat to the den.",
                  "win_celebrated": "The Bears eat tonight."},
    "knight":    {"awaiting_signal": "The Knight stands watch.",
                  "loss_acknowledged": "Knight regroups for the next campaign.",
                  "win_celebrated": "The Knight rides."},
    "knights":   {"awaiting_signal": "The Knights polish their armor.",
                  "loss_acknowledged": "Knights regroup.",
                  "win_celebrated": "Knights claim the day."},
    "cougar":    {"awaiting_signal": "The Cougar waits in the mountain.",
                  "loss_acknowledged": "Cougar retreats up the ridge.",
                  "win_celebrated": "The Cougar hunts."},
    "cougars":   {"awaiting_signal": "The Cougars survey the territory.",
                  "loss_acknowledged": "Cougars climb higher tomorrow.",
                  "win_celebrated": "Cougars own this peak."},
    "buffalo":   {"awaiting_signal": "Ralphie watches the horizon.",
                  "loss_acknowledged": "The Buffalo waits for the next run.",
                  "win_celebrated": "The Buffalo charges."},
    "buffaloes": {"awaiting_signal": "The Buffaloes graze.",
                  "loss_acknowledged": "Buffaloes regroup at the river.",
                  "win_celebrated": "Buffaloes thunder across the plain."},
    "razorback": {"awaiting_signal": "The Razorback waits.",
                  "loss_acknowledged": "Hog call quieter tonight.",
                  "win_celebrated": "WOO PIG SOOIE."},
    "razorbacks": {"awaiting_signal": "The Razorbacks wait.",
                   "loss_acknowledged": "Hog call quieter tonight.",
                   "win_celebrated": "WOO PIG SOOIE."},
    "hawkeye":   {"awaiting_signal": "The Hawkeye watches the field.",
                  "loss_acknowledged": "Hawkeye regroups.",
                  "win_celebrated": "Hawkeyes hold the line."},
    "hawkeyes":  {"awaiting_signal": "The Hawkeyes watch from above.",
                  "loss_acknowledged": "Hawkeyes regroup.",
                  "win_celebrated": "Hawkeyes own the day."},
    "duck":      {"awaiting_signal": "The Duck plots.",
                  "loss_acknowledged": "Duck regroups.",
                  "win_celebrated": "The Duck quacks."},
    "ducks":     {"awaiting_signal": "The Ducks plot the formation.",
                  "loss_acknowledged": "Ducks regroup at the pond.",
                  "win_celebrated": "Ducks fly tonight."},
    "trojan":    {"awaiting_signal": "The Trojan stands sentinel.",
                  "loss_acknowledged": "The Trojan rebuilds the wall.",
                  "win_celebrated": "The Trojan claims the day."},
    "trojans":   {"awaiting_signal": "The Trojans stand guard.",
                  "loss_acknowledged": "Trojans rebuild.",
                  "win_celebrated": "Trojans claim the day."},
    "spartan":   {"awaiting_signal": "The Spartan trains.",
                  "loss_acknowledged": "Spartan returns to the gymnasium.",
                  "win_celebrated": "The Spartan returns victorious."},
    "spartans":  {"awaiting_signal": "The Spartans drill.",
                  "loss_acknowledged": "Spartans drill harder tomorrow.",
                  "win_celebrated": "Spartans return with their shields."},
    "musketeer": {"awaiting_signal": "The Musketeer waits.",
                  "loss_acknowledged": "Musketeer regroups.",
                  "win_celebrated": "All for one, and the win is ours."},
    "rebel":     {"awaiting_signal": "The Rebel is watchful.",
                  "loss_acknowledged": "Rebel regroups.",
                  "win_celebrated": "The Rebel claims the day."},
    "rebels":    {"awaiting_signal": "The Rebels are watchful.",
                  "loss_acknowledged": "Rebels regroup.",
                  "win_celebrated": "Rebels claim the day."},
    "viking":    {"awaiting_signal": "The Viking sharpens the axe.",
                  "loss_acknowledged": "Viking sharpens for the next raid.",
                  "win_celebrated": "The Viking claims the spoils."},
    "vikings":   {"awaiting_signal": "The Vikings sharpen their axes.",
                  "loss_acknowledged": "Vikings sharpen for the next raid.",
                  "win_celebrated": "Vikings claim the spoils."},
    "pirate":    {"awaiting_signal": "The Pirate plots the route.",
                  "loss_acknowledged": "Pirate regroups at the harbor.",
                  "win_celebrated": "Pirate claims the treasure."},
    "pirates":   {"awaiting_signal": "The Pirates plot the next voyage.",
                  "loss_acknowledged": "Pirates dock for repairs.",
                  "win_celebrated": "Pirates claim the treasure."},
    "minutemen": {"awaiting_signal": "The Minutemen stand ready.",
                  "loss_acknowledged": "Minutemen return to the muster.",
                  "win_celebrated": "Minutemen hold the day."},
    "fighting irish": {"awaiting_signal": "The Leprechaun is keeping his own counsel.",
                       "loss_acknowledged": "Leprechaun stays in the green room.",
                       "win_celebrated": "The Leprechaun emerges."},
    "horned frog":   {"awaiting_signal": "SuperFrog is in stasis.",
                      "loss_acknowledged": "Riff Ram quieter tonight.",
                      "win_celebrated": "Hypnotoad approves."},
    "horned frogs":  {"awaiting_signal": "SuperFrog is in stasis.",
                      "loss_acknowledged": "Riff Ram quieter tonight.",
                      "win_celebrated": "Hypnotoad approves."},
}


def _resolve_mascot_voice(mascot_name: str) -> dict[str, str]:
    """Return a mascot-voice triple for the given mascot name.

    Tries exact mascot_name match (lowercased), then trailing-word
    match (so 'Auburn Tigers' resolves via 'tigers'), then generic
    fallback.
    """
    if not mascot_name:
        return {
            "awaiting_signal": "Awaiting signal — voice not yet authored.",
            "loss_acknowledged": "Quiet today.",
            "win_celebrated": "Win in the books.",
        }
    key = str(mascot_name).strip().lower()
    if key in _MASCOT_VOICE_LIBRARY:
        return dict(_MASCOT_VOICE_LIBRARY[key])
    # Trailing-word fallback
    parts = key.rsplit(" ", 1)
    if len(parts) > 1 and parts[-1] in _MASCOT_VOICE_LIBRARY:
        return dict(_MASCOT_VOICE_LIBRARY[parts[-1]])
    # Singular fallback (e.g. 'tigers' → 'tiger' if missing)
    if key.endswith("s") and key[:-1] in _MASCOT_VOICE_LIBRARY:
        return dict(_MASCOT_VOICE_LIBRARY[key[:-1]])
    return {
        "awaiting_signal": f"The {mascot_name} are patient.",
        "loss_acknowledged": f"The {mascot_name} regroup.",
        "win_celebrated": f"Go {mascot_name}.",
    }


# Conference-keyed voice register defaults. Synthesized teams pick up the
# regional/tonal flavor of their conference instead of all sharing
# "plain-honest". Authored YAMLs override this.
_CONFERENCE_VOICE_REGISTER: dict[str, str] = {
    "Southeastern Conference":      "sec-southern-faith",
    "SEC":                          "sec-southern-faith",
    "Big Ten Conference":           "midwest-grit-and-tradition",
    "Big Ten":                      "midwest-grit-and-tradition",
    "Atlantic Coast Conference":    "acc-coastal-academic",
    "ACC":                          "acc-coastal-academic",
    "Big 12 Conference":            "great-plains-wide-open",
    "Big 12":                       "great-plains-wide-open",
    "FBS Independents":             "independent-pragmatic",
    "American Athletic Conference": "g5-ambitious-rising",
    "American Athletic":            "g5-ambitious-rising",
    "Mountain West Conference":     "western-spare-honest",
    "Mountain West":                "western-spare-honest",
    "Sun Belt Conference":          "sunbelt-scrappy-warm",
    "Sun Belt":                     "sunbelt-scrappy-warm",
    "Mid-American Conference":      "mac-tuesday-night-faithful",
    "MAC":                          "mac-tuesday-night-faithful",
    "Conference USA":               "c-usa-overlooked-honest",
    "C-USA":                        "c-usa-overlooked-honest",
}

# Per-register identity-phrase template. Filled with program_name +
# conference. Beats the previous generic "...known for its faithful
# following." Default template still applies to unmapped conferences.
_REGISTER_IDENTITY_TEMPLATE: dict[str, str] = {
    "sec-southern-faith":
        "{program_name} is the {conf} program whose Saturdays carry the weight of an SEC Saturday.",
    "midwest-grit-and-tradition":
        "{program_name} is the {conf} program built on tradition, weather, and the long game.",
    "acc-coastal-academic":
        "{program_name} is the {conf} program balancing the classroom with a national football identity.",
    "great-plains-wide-open":
        "{program_name} is the {conf} program where the playbook opens and the field never closes.",
    "independent-pragmatic":
        "{program_name} is the program that schedules itself, on its own terms.",
    "g5-ambitious-rising":
        "{program_name} is the {conf} program building toward the next conference cycle.",
    "western-spare-honest":
        "{program_name} is the {conf} program whose climate, terrain, and roster all read mountain-time honest.",
    "sunbelt-scrappy-warm":
        "{program_name} is the {conf} program where the weather and the ambition both turn up year-round.",
    "mac-tuesday-night-faithful":
        "{program_name} is the {conf} program whose Tuesday-night cult turns midweek into a season.",
    "c-usa-overlooked-honest":
        "{program_name} is the {conf} program competing for attention against the giants of its region.",
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

    # Voice register from conference. Beats the previous all-purpose
    # "plain-honest" default by giving the synthesized 89 long-tail
    # programs regional/tonal flavor.
    voice_register = _CONFERENCE_VOICE_REGISTER.get(conference, "plain-honest")

    # Identity phrase: per-register template when available, otherwise the
    # plain-honest fallback. Authored YAMLs will replace either.
    template = _REGISTER_IDENTITY_TEMPLATE.get(voice_register)
    if template:
        identity_phrase = template.format(
            program_name=program_name,
            conf=conference,
        )
    elif conference:
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
        "voice_register": voice_register,
        "tonal_template": voice_register,
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
        "mascot_voice": _resolve_mascot_voice(mascot),
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
        voice_register=voice_register,
        tonal_template=voice_register,
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
