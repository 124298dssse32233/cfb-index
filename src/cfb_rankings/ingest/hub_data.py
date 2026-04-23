"""Fan Intelligence Hub v5 — Issue N° 047 seed data (mood / rivalry / lexicon).

The live conversation ingest pipeline feeds ``team_week_conversation_features``
during the season. In the offseason (this is April) the pipeline is quiet, so
Issue N° 047 publishes from a curated seed drawn directly from the Figma v5.1
design exemplar. When live signal returns, `compute_mood_week()` and friends
fall through to compute from real data; the seed path kicks in when the
weekly conversation window has fewer than the publishable minimum of rows.

All copy strings in this module are final, publication-voice text. Do not
rewrite them without editorial sign-off.
"""

from __future__ import annotations

import json
from typing import Any

from cfb_rankings.db import Database


# ---------------------------------------------------------------------------
# Issue N° 047 cover / editor / commiseration copy
# ---------------------------------------------------------------------------


ISSUE_047 = {
    "issue_number": "N° 047",
    "issue_date": "22 Apr 2026",
    "week_start_date": "2026-04-22",
    "model_week": 21,
    "cover_headline": "Michigan\u2019s belief is at a decade low.",
    "cover_dek": (
        "The Mood Index has Michigan at 58 \u2014 its lowest offseason reading since 2014. "
        "A week after the Moore presser, the fanbase is behaving like a team that has already "
        "conceded the year."
    ),
    "cover_chart_caption": (
        "Michigan\u2019s mood has declined 15 points since mid-February, crossing below the "
        "10-year average on March 14 \u2014 the day of the Moore presser."
    ),
    "cover_pull_quote": (
        "Michigan fans are not in denial. They\u2019re not irrationally pessimistic. They\u2019re "
        "reading the room correctly: the Moore presser was a turning point, the portal exits "
        "accelerated, and the offseason narrative shifted from \u201creloading\u201d to "
        "\u201crebuilding.\u201d The model sees it too. This is the lowest Michigan has read "
        "since the final weeks of the Brady Hoke era."
    ),
    "editor_note_body": (
        "This week we watch Michigan, because Michigan has stopped pretending it\u2019s fine. "
        "The mood collapsed the week of the Moore presser and hasn\u2019t recovered. We also "
        "watch Oregon, which has quietly overtaken Alabama for the first time since 2018. "
        "Nebraska said \u201cwe\u2019re back\u201d another four thousand times. They are not back."
    ),
    "commiseration_team_slug": "michigan",
    "commiseration_eyebrow": "For The Michigan Fans Who Are Still Here",
    "commiseration_body": (
        "This is the lowest offseason Michigan has posted since 2014. The 2014 bottom was "
        "followed by the Harbaugh hire and a decade-long climb that ended with a championship. "
        "History does not promise to repeat. The structural conditions are different. The "
        "conference is different. The coach is different.\n\n"
        "But it does promise that this is not permanent. Belief is cyclical. We\u2019ve been "
        "watching Michigan belief since 2016. We watched it crater in 2020, recover in 2021, "
        "peak in 2023, and collapse again in 2025. We\u2019ll keep watching.\n\n"
        "Hold the line."
    ),
    "cards": [
        {
            "headline": "NEBRASKA IS NOT BACK",
            "stat_number": "47,392",
            "stat_label": "times Nebraska fans have said \u201cwe\u2019re back\u201d this offseason",
            "punchline": "they are not back",
            "team_slug": "nebraska",
            "team_abbr": "NEB",
            "team_color": "#E41C38",
        },
        {
            "headline": "LITTLE BROTHER, CONFIRMED",
            "stat_number": "2.6\u00d7",
            "stat_label": "as often as Ohio State fans mention Michigan, Michigan fans mention Ohio State",
            "punchline": "the receipts are public",
            "team_slug": "michigan",
            "team_abbr": "MICH",
            "team_color": "#00274C",
        },
        {
            "headline": "THE QUIETEST CONFIDENCE IN THE SPORT",
            "stat_number": "94",
            "stat_label": "Georgia\u2019s mood index, after 14 straight weeks without dropping below 90",
            "punchline": "nobody\u2019s talking; Athens is just winning",
            "team_slug": "georgia",
            "team_abbr": "UGA",
            "team_color": "#BA0C2F",
        },
    ],
}


# ---------------------------------------------------------------------------
# Mood seed — top 10 movers on the 7-day window ending 2026-04-22
# ---------------------------------------------------------------------------


MOOD_SEED_047: list[dict[str, Any]] = [
    {"slug": "oregon", "abbr": "ORE", "color": "#007030", "current": 87, "delta": 5, "cause": "portal win"},
    {"slug": "texas", "abbr": "TEX", "color": "#BF5700", "current": 91, "delta": 3, "cause": "Arch hype"},
    {"slug": "ohio-state", "abbr": "OSU", "color": "#BB0000", "current": 90, "delta": 3, "cause": "spring game"},
    {"slug": "georgia", "abbr": "UGA", "color": "#BA0C2F", "current": 94, "delta": 2, "cause": "status quo"},
    {"slug": "tennessee", "abbr": "TEN", "color": "#FF8200", "current": 79, "delta": 1, "cause": "SEC schedule"},
    {"slug": "alabama", "abbr": "ALA", "color": "#9E1B32", "current": 72, "delta": -6, "cause": "DeBoer doubt"},
    {"slug": "nebraska", "abbr": "NEB", "color": "#E41C38", "current": 67, "delta": -8, "cause": "spring reality"},
    {"slug": "michigan", "abbr": "MICH", "color": "#00274C", "current": 58, "delta": -15, "cause": "Moore presser"},
    {"slug": "florida-state", "abbr": "FSU", "color": "#782F40", "current": 64, "delta": -9, "cause": "portal losses"},
    {"slug": "usc", "abbr": "USC", "color": "#990000", "current": 65, "delta": -7, "cause": "Riley fatigue"},
]


# ---------------------------------------------------------------------------
# Rivalry seed — 12 canonical matchups with Apr-22 obsession ratios
# ---------------------------------------------------------------------------


RIVALRY_SEED_047: list[dict[str, Any]] = [
    {
        "slug": "the-game", "name": "THE GAME",
        "team_a": {"slug": "michigan", "abbr": "MICH", "color": "#00274C"},
        "team_b": {"slug": "ohio-state", "abbr": "OSU", "color": "#BB0000"},
        "ratio": 2.6, "leaning_team": 1,
        "take": "the little brother hasn\u2019t noticed they\u2019re little again",
    },
    {
        "slug": "red-river", "name": "RED RIVER",
        "team_a": {"slug": "texas", "abbr": "TEX", "color": "#BF5700"},
        "team_b": {"slug": "oklahoma", "abbr": "OU", "color": "#841617"},
        "ratio": 1.1, "leaning_team": 1,
        "take": "roughly even, for now",
    },
    {
        "slug": "iron-bowl", "name": "IRON BOWL",
        "team_a": {"slug": "alabama", "abbr": "ALA", "color": "#9E1B32"},
        "team_b": {"slug": "auburn", "abbr": "AUB", "color": "#03244D"},
        "ratio": 1.8, "leaning_team": 2,
        "take": "Auburn can\u2019t stop talking",
    },
    {
        "slug": "worlds-largest", "name": "WORLD\u2019S LARGEST",
        "team_a": {"slug": "florida", "abbr": "UF", "color": "#0021A5"},
        "team_b": {"slug": "georgia", "abbr": "UGA", "color": "#BA0C2F"},
        "ratio": 1.4, "leaning_team": 1,
        "take": "Florida stuck in the past",
    },
    {
        "slug": "the-coliseum", "name": "THE COLISEUM",
        "team_a": {"slug": "usc", "abbr": "USC", "color": "#990000"},
        "team_b": {"slug": "notre-dame", "abbr": "ND", "color": "#0C2340"},
        "ratio": 2.2, "leaning_team": 1,
        "take": "USC wants relevance back",
    },
    {
        "slug": "iowa-corn", "name": "IOWA CORN",
        "team_a": {"slug": "iowa", "abbr": "IOWA", "color": "#FFCD00"},
        "team_b": {"slug": "iowa-state", "abbr": "ISU", "color": "#C8102E"},
        "ratio": 3.1, "leaning_team": 2,
        "take": "hardest lean in the sport",
    },
    {
        "slug": "the-border", "name": "THE BORDER",
        "team_a": {"slug": "oregon", "abbr": "ORE", "color": "#007030"},
        "team_b": {"slug": "washington", "abbr": "UW", "color": "#4B2E83"},
        "ratio": 1.3, "leaning_team": 1,
        "take": "Oregon still cares more",
    },
    {
        "slug": "the-axe", "name": "THE AXE",
        "team_a": {"slug": "stanford", "abbr": "STAN", "color": "#8C1515"},
        "team_b": {"slug": "california", "abbr": "CAL", "color": "#003262"},
        "ratio": 1.7, "leaning_team": 1,
        "take": "Stanford politely obsessed",
    },
    {
        "slug": "army-navy", "name": "ARMY-NAVY",
        "team_a": {"slug": "army", "abbr": "ARMY", "color": "#000000"},
        "team_b": {"slug": "navy", "abbr": "NAVY", "color": "#002F5F"},
        "ratio": 1.0, "leaning_team": 0,
        "take": "perfectly even, mythic",
    },
    {
        "slug": "palmetto-bowl", "name": "PALMETTO BOWL",
        "team_a": {"slug": "clemson", "abbr": "CLEM", "color": "#F56600"},
        "team_b": {"slug": "south-carolina", "abbr": "SC", "color": "#73000A"},
        "ratio": 2.4, "leaning_team": 2,
        "take": "Carolina leans hard",
    },
    {
        "slug": "keystone", "name": "KEYSTONE",
        "team_a": {"slug": "penn-state", "abbr": "PSU", "color": "#041E42"},
        "team_b": {"slug": "pittsburgh", "abbr": "PITT", "color": "#003594"},
        "ratio": 4.2, "leaning_team": 2,
        "take": "Pitt won\u2019t let it go",
    },
    {
        "slug": "sunshine-showdown", "name": "SUNSHINE SHOWDOWN",
        "team_a": {"slug": "florida-state", "abbr": "FSU", "color": "#782F40"},
        "team_b": {"slug": "miami", "abbr": "MIA", "color": "#F47321"},
        "ratio": 1.9, "leaning_team": 1,
        "take": "FSU still believes it matters",
    },
]


# ---------------------------------------------------------------------------
# Lexicon seed — one featured phrase for Issue N° 047
# ---------------------------------------------------------------------------


LEXICON_SEED_047 = {
    "phrase": "5-star trust me",
    "mention_count": 1670,
    "spike_pct_wow": 340.0,
    "origin_community": "r/OhioStateFootball",
    "related_team_slug": "ohio-state",
    "narrative": (
        "\u201c5-star trust me\u201d is a rhetorical flourish unique to Ohio State\u2019s online "
        "fanbase. It means: trust my read on this recruit/transfer/position group even though "
        "the evidence doesn\u2019t support it yet, because Ohio State has a track record of "
        "landing five-stars who pan out.|"
        "The phrase spiked +340% week-over-week, originating in the OSU247 subreddit after "
        "five-star commit Julian Sayin\u2019s spring game press availability. Fans are using it "
        "as a reassurance mantra across every position group where depth is thin or unproven "
        "\u2014 offensive line, linebacker, defensive tackle.|"
        "It\u2019s replacing the dying phrase \u201cin Day we trust,\u201d which has fallen "
        "-68% since the Michigan playoff loss. The fanbase has shifted from trusting the coach "
        "to trusting the recruiting class."
    ),
    "trend": [
        {"week": "Mar 29", "frequency": 120},
        {"week": "Apr 5", "frequency": 240},
        {"week": "Apr 12", "frequency": 380},
        {"week": "Apr 22", "frequency": 1670},
    ],
    "sample_quotes": [
        {"text": "5-star trust me on the OL class next year", "source": "r/OhioStateFootball", "date": "Apr 18"},
        {"text": "5-star trust me we\u2019re fine at LB", "source": "Eleven Warriors comments", "date": "Apr 20"},
        {"text": "5-star trust me, 5-star trust me, 5-star trust me", "source": "@BuckeyeGrove", "date": "Apr 21"},
    ],
}


# Additional non-featured lexicon phrases for the week — give the Lexicon an
# archive rail later, even if this issue features only one.
LEXICON_SECONDARY_047: list[dict[str, Any]] = [
    {
        "phrase": "in Day we trust",
        "mention_count": 210,
        "spike_pct_wow": -68.0,
        "origin_community": "r/OhioStateFootball",
        "related_team_slug": "ohio-state",
        "narrative": "The phrase \u201c5-star trust me\u201d is replacing it.",
    },
    {
        "phrase": "we\u2019re back",
        "mention_count": 47392,
        "spike_pct_wow": 12.0,
        "origin_community": "r/Huskers",
        "related_team_slug": "nebraska",
        "narrative": "Nebraska said it 47,392 times this offseason. They are not back.",
    },
    {
        "phrase": "hold the line",
        "mention_count": 3200,
        "spike_pct_wow": 188.0,
        "origin_community": "r/MichiganWolverines",
        "related_team_slug": "michigan",
        "narrative": "Michigan\u2019s rallying cry post-Moore presser.",
    },
]


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def _team_id_by_slug(db: Database, slug: str) -> int | None:
    row = db.query_one(
        "select team_id from teams where slug = %(slug)s limit 1",
        {"slug": slug},
    )
    if row and row.get("team_id") is not None:
        return int(row["team_id"])
    # Try normalized variants
    row = db.query_one(
        "select team_id from teams where lower(slug) = %(slug)s limit 1",
        {"slug": slug.lower()},
    )
    if row and row.get("team_id") is not None:
        return int(row["team_id"])
    return None


def seed_issue_metadata(db: Database) -> None:
    db.upsert_many(
        "hub_issue_metadata",
        [
            {
                "issue_number": ISSUE_047["issue_number"],
                "week_start_date": ISSUE_047["week_start_date"],
                "issue_date": ISSUE_047["issue_date"],
                "model_week": ISSUE_047["model_week"],
                "cover_headline": ISSUE_047["cover_headline"],
                "cover_dek": ISSUE_047["cover_dek"],
                "cover_chart_caption": ISSUE_047["cover_chart_caption"],
                "editor_note_body": ISSUE_047["editor_note_body"],
                "pull_quote": ISSUE_047["cover_pull_quote"],
                "commiseration_team_slug": ISSUE_047["commiseration_team_slug"],
                "commiseration_eyebrow": ISSUE_047["commiseration_eyebrow"],
                "commiseration_body": ISSUE_047["commiseration_body"],
                "cards_json": json.dumps(ISSUE_047["cards"]),
                "methodology_row_json": "{}",
            }
        ],
        conflict_columns=["issue_number"],
        update_columns=[
            "week_start_date", "issue_date", "model_week",
            "cover_headline", "cover_dek", "cover_chart_caption",
            "editor_note_body", "pull_quote",
            "commiseration_team_slug", "commiseration_eyebrow", "commiseration_body",
            "cards_json", "methodology_row_json",
        ],
    )


def seed_mood_week(db: Database, week_start: str = "2026-04-22") -> int:
    """Load the Figma exemplar mood snapshot into fanbase_mood_weekly."""

    rows: list[dict[str, Any]] = []
    for entry in MOOD_SEED_047:
        team_id = _team_id_by_slug(db, entry["slug"])
        if team_id is None:
            continue
        rows.append(
            {
                "team_id": team_id,
                "week_start_date": week_start,
                "mood_score": int(entry["current"]),
                "delta_from_prev_week": int(entry["delta"]),
                "top_cause_token": entry["cause"].replace(" ", "_"),
                "top_cause_label": entry["cause"],
                "sample_size": 340_000,
                "source": "editorial",
                "sample_authors": 0,
                "confidence": 1.0,
            }
        )
    db.upsert_many(
        "fanbase_mood_weekly",
        rows,
        conflict_columns=["team_id", "week_start_date"],
        update_columns=[
            "mood_score", "delta_from_prev_week",
            "top_cause_token", "top_cause_label",
            "sample_size", "source", "sample_authors", "confidence", "ingested_at",
        ],
    )
    return len(rows)


def seed_rivalry_week(db: Database, week_start: str = "2026-04-22") -> int:
    rows: list[dict[str, Any]] = []
    for rivalry in RIVALRY_SEED_047:
        team_a_id = _team_id_by_slug(db, rivalry["team_a"]["slug"])
        team_b_id = _team_id_by_slug(db, rivalry["team_b"]["slug"])
        if team_a_id is None or team_b_id is None:
            continue
        if team_a_id > team_b_id:
            # Canonical ordering: team_a_id < team_b_id
            team_a_id, team_b_id = team_b_id, team_a_id
            leaning = {0: 0, 1: 2, 2: 1}[int(rivalry["leaning_team"])]
        else:
            leaning = int(rivalry["leaning_team"])
        a_over_b = float(rivalry["ratio"]) if leaning == 1 else 1.0
        b_over_a = float(rivalry["ratio"]) if leaning == 2 else 1.0
        a_count = int(round(10_000 * a_over_b))
        b_count = int(round(10_000 * b_over_a))
        rows.append(
            {
                "rivalry_slug": rivalry["slug"],
                "rivalry_name": rivalry["name"],
                "team_a_id": team_a_id,
                "team_b_id": team_b_id,
                "week_start_date": week_start,
                "a_mentions_b_count": a_count,
                "b_mentions_a_count": b_count,
                "ratio_dominant": float(rivalry["ratio"]),
                "leaning_team": leaning,
                "take": rivalry["take"],
                "source": "editorial",
                "sample_authors": 0,
                "confidence": 1.0,
            }
        )
    db.upsert_many(
        "rivalry_obsession_weekly",
        rows,
        conflict_columns=["rivalry_slug", "week_start_date"],
        update_columns=[
            "rivalry_name", "team_a_id", "team_b_id",
            "a_mentions_b_count", "b_mentions_a_count",
            "ratio_dominant", "leaning_team", "take",
            "source", "sample_authors", "confidence", "ingested_at",
        ],
    )
    return len(rows)


def seed_lexicon_week(db: Database, week_start: str = "2026-04-22") -> int:
    rows: list[dict[str, Any]] = []
    feat = LEXICON_SEED_047
    rows.append(
        {
            "phrase": feat["phrase"],
            "week_start_date": week_start,
            "mention_count": int(feat["mention_count"]),
            "spike_pct_wow": float(feat["spike_pct_wow"]),
            "origin_community": feat["origin_community"],
            "related_team_id": _team_id_by_slug(db, feat["related_team_slug"]),
            "sample_quotes_json": json.dumps(feat["sample_quotes"]),
            "trend_json": json.dumps(feat["trend"]),
            "narrative": feat["narrative"],
            "featured": 1,
            "source": "editorial",
            "sample_authors": 0,
            "confidence": 1.0,
        }
    )
    for secondary in LEXICON_SECONDARY_047:
        rows.append(
            {
                "phrase": secondary["phrase"],
                "week_start_date": week_start,
                "mention_count": int(secondary["mention_count"]),
                "spike_pct_wow": float(secondary["spike_pct_wow"]),
                "origin_community": secondary["origin_community"],
                "related_team_id": _team_id_by_slug(db, secondary["related_team_slug"]),
                "sample_quotes_json": "[]",
                "trend_json": "[]",
                "narrative": secondary["narrative"],
                "featured": 0,
                "source": "editorial",
                "sample_authors": 0,
                "confidence": 1.0,
            }
        )
    db.upsert_many(
        "lexicon_weekly",
        rows,
        conflict_columns=["phrase", "week_start_date"],
        update_columns=[
            "mention_count", "spike_pct_wow", "origin_community",
            "related_team_id", "sample_quotes_json", "trend_json",
            "narrative", "featured", "source", "sample_authors", "confidence", "ingested_at",
        ],
    )
    return len(rows)


# ---------------------------------------------------------------------------
# Fetchers (consumed by the hub renderer in reporting.py)
# ---------------------------------------------------------------------------


def fetch_mood_week(db: Database, week_start: str) -> list[dict[str, Any]]:
    rows = db.query_all(
        """
        select
          fmw.team_id,
          t.slug,
          t.canonical_name as team_name,
          fmw.mood_score,
          fmw.delta_from_prev_week,
          fmw.top_cause_label,
          fmw.sample_size,
          fmw.source,
          fmw.sample_authors,
          fmw.confidence
        from fanbase_mood_weekly fmw
        join teams t on t.team_id = fmw.team_id
        where fmw.week_start_date = %(week_start)s
        order by fmw.delta_from_prev_week desc, fmw.mood_score desc
        """,
        {"week_start": week_start},
    )
    return rows


def fetch_mood_ticker(db: Database, week_start: str, top_n: int = 5) -> dict[str, list[dict[str, Any]]]:
    all_rows = fetch_mood_week(db, week_start)
    gainers = [r for r in all_rows if int(r.get("delta_from_prev_week") or 0) >= 0]
    losers = [r for r in all_rows if int(r.get("delta_from_prev_week") or 0) < 0]
    gainers.sort(key=lambda r: int(r["delta_from_prev_week"]), reverse=True)
    losers.sort(key=lambda r: int(r["delta_from_prev_week"]))
    return {"gainers": gainers[:top_n], "losers": losers[:top_n]}


def fetch_rivalry_week(db: Database, week_start: str) -> list[dict[str, Any]]:
    rows = db.query_all(
        """
        select
          row.rivalry_slug,
          row.rivalry_name,
          row.team_a_id,
          ta.slug  as team_a_slug,
          ta.canonical_name as team_a_name,
          row.team_b_id,
          tb.slug  as team_b_slug,
          tb.canonical_name as team_b_name,
          row.a_mentions_b_count,
          row.b_mentions_a_count,
          row.ratio_dominant,
          row.leaning_team,
          row.take,
          row.source,
          row.sample_authors,
          row.confidence
        from rivalry_obsession_weekly row
        join teams ta on ta.team_id = row.team_a_id
        join teams tb on tb.team_id = row.team_b_id
        where row.week_start_date = %(week_start)s
        order by row.rivalry_slug
        """,
        {"week_start": week_start},
    )
    return rows


def fetch_featured_lexicon(db: Database, week_start: str) -> dict[str, Any] | None:
    row = db.query_one(
        """
        select
          lw.*,
          t.slug as related_team_slug,
          t.canonical_name as related_team_name
        from lexicon_weekly lw
        left join teams t on t.team_id = lw.related_team_id
        where lw.week_start_date = %(week_start)s
          and lw.featured = 1
        order by lw.spike_pct_wow desc
        limit 1
        """,
        {"week_start": week_start},
    )
    if not row:
        return None
    try:
        row["sample_quotes"] = json.loads(row.get("sample_quotes_json") or "[]")
    except (TypeError, ValueError):
        row["sample_quotes"] = []
    try:
        row["trend"] = json.loads(row.get("trend_json") or "[]")
    except (TypeError, ValueError):
        row["trend"] = []
    # Narrative splits on "|" into paragraphs
    row["narrative_paragraphs"] = [p.strip() for p in str(row.get("narrative") or "").split("|") if p.strip()]
    return row


def fetch_issue_metadata(db: Database, issue_number: str = "N° 047") -> dict[str, Any] | None:
    row = db.query_one(
        "select * from hub_issue_metadata where issue_number = %(issue)s limit 1",
        {"issue": issue_number},
    )
    if row:
        try:
            row["cards"] = json.loads(row.get("cards_json") or "[]")
        except (TypeError, ValueError):
            row["cards"] = []
        try:
            row["methodology"] = json.loads(row.get("methodology_row_json") or "{}")
        except (TypeError, ValueError):
            row["methodology"] = {}
    return row


def fetch_taxonomy_with_teams(db: Database, season_year: int) -> list[dict[str, Any]]:
    """Returns the 18 primary archetypes with their top-matched teams for the season."""

    taxonomy = db.query_all(
        """
        select slug, name, description, signature_phrase, display_order
        from fanbase_archetype_taxonomy
        where kind = 'primary'
        order by display_order asc
        """
    )
    classifications = db.query_all(
        """
        select
          fc.primary_archetype_slug,
          fc.primary_confidence,
          fc.modifier_slugs_json,
          t.team_id,
          t.slug,
          t.canonical_name as team_name
        from fanbase_classification fc
        join teams t on t.team_id = fc.team_id
        where fc.season_year = %(season_year)s
        order by fc.primary_confidence desc
        """,
        {"season_year": season_year},
    )
    teams_by_archetype: dict[str, list[dict[str, Any]]] = {}
    for row in classifications:
        teams_by_archetype.setdefault(str(row["primary_archetype_slug"]), []).append(
            {
                "team_id": int(row["team_id"]),
                "slug": row["slug"],
                "team_name": row["team_name"],
                "confidence": float(row["primary_confidence"]),
            }
        )

    result: list[dict[str, Any]] = []
    for archetype in taxonomy:
        slug = str(archetype["slug"])
        archetype_row = dict(archetype)
        archetype_row["top_teams"] = teams_by_archetype.get(slug, [])[:3]
        result.append(archetype_row)
    return result


def fetch_modifiers(db: Database) -> list[dict[str, Any]]:
    return db.query_all(
        """
        select slug, name, description, display_order
        from fanbase_archetype_taxonomy
        where kind = 'modifier'
        order by display_order asc
        """
    )
