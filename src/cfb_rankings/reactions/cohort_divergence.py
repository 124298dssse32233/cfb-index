"""Cohort divergence extraction for Reaction Stories (Sprint 15 Phase 3).

Queries the conversation corpus for the 24h window around a trigger event,
partitions mentions by cohort signal, and returns a CohortDivergence struct
feeding the synthesizer.

Cohort definitions:
  stat_folks  — sources/text with analytics markers (efficiency, EPA, etc.)
  casual_fans — general fan corpus; default bucket
  die_hards   — program-board sources; sustained-engagement vocabulary

Offline/stub mode: when the conversation_documents table is empty or absent
(common in dev), generates plausible deterministic divergence data from the
wire entry content itself. Marked with offline=True in the returned struct.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from .data import db_conn

# Analytics markers for stat_folks cohort detection
_ANALYTICS_MARKERS: tuple[str, ...] = (
    "efficiency", "epa", "success rate", "percentile", "advanced metric",
    "ppa", "yards per play", "havoc", "finishing drives", "stuff rate",
    "line yards", "sp+", "fei", "opportunity rate", "explosiveness",
)

# Die-hard markers: program-internal language, decade-spanning context
_DIEHARDS_MARKERS: tuple[str, ...] = (
    "message board", "scout.com", "247sports", "rivals", "on3",
    "been saying this", "since 2014", "program culture", "locker room",
    "coaching staff relationships", "class of 20", "redshirt", "spring camp",
    "fall camp", "depth chart", "buyout", "nil deal",
)


@dataclass
class CohortQuote:
    text: str
    attribution: str


@dataclass
class CohortData:
    cohort: str
    stance: str
    quotes: list[CohortQuote]
    sentiment_score: float  # -1..+1
    volume_share: float     # 0..1 (sums to 1 across cohorts)


@dataclass
class CohortDivergence:
    wire_id: int
    entity_slug: str
    stat_folks: CohortData
    casual_fans: CohortData
    die_hards: CohortData
    offline: bool = False  # True when generated from stubs, not live corpus


def _classify_cohort(text: str, source_name: Optional[str]) -> str:
    """Simple heuristic classifier — returns cohort name."""
    text_lower = (text or "").lower()
    source_lower = (source_name or "").lower()

    analytics_hits = sum(1 for m in _ANALYTICS_MARKERS if m in text_lower)
    diehards_hits = sum(1 for m in _DIEHARDS_MARKERS if m in text_lower or m in source_lower)

    if analytics_hits >= 2:
        return "stat_folks"
    if diehards_hits >= 2 or source_lower in ("rivals", "247sports", "scout", "on3", "warchant"):
        return "die_hards"
    return "casual_fans"


def _simple_sentiment(text: str) -> float:
    """VADER-free fallback: count positive/negative keyword hits."""
    text_lower = text.lower()
    pos = sum(1 for w in ("good", "great", "love", "excited", "win", "huge", "best",
                          "smart", "solid", "upgrade", "steal", "nice") if w in text_lower)
    neg = sum(1 for w in ("bad", "terrible", "worry", "concern", "overhyped", "mistake",
                          "dumb", "wait and see", "risky", "overrated") if w in text_lower)
    total = pos + neg
    if total == 0:
        return 0.0
    return (pos - neg) / total


def _stub_divergence(wire_row: dict) -> CohortDivergence:
    """Generate plausible cohort divergence from wire entry data.

    Called when live corpus is unavailable. Content is derived from the
    actual wire entry so each stub is unique and editorially coherent.
    """
    action = wire_row.get("action", "")
    program_display = wire_row.get("program_display", "the program")
    why_it_matters = wire_row.get("why_it_matters", "")
    impact_label = wire_row.get("impact_label", "MINOR")
    entity_slug = wire_row.get("program_slug", "unknown")

    # Derive actor type and name from action
    is_qb = "QB" in action
    is_transfer = "transfer" in action.lower()
    actor_name_match = re.search(
        r"(?:QB|RB|WR|TE|OT|IOL|DL|LB|CB|S|EDGE|K|P|LS)\s+([A-Za-z][A-Za-z']+(?:\s+[A-Za-z][A-Za-z']+)*?)(?:\s+transfer|\s+commits|$)",
        action,
    )
    actor_name = actor_name_match.group(1) if actor_name_match else "the new addition"

    from_program_match = re.search(r"from\s+(.+?)$", action, re.IGNORECASE)
    from_program = from_program_match.group(1).strip() if from_program_match else "another program"

    pos_match = re.search(r"^(QB|RB|WR|TE|OT|IOL|DL|LB|CB|S|EDGE|K|P|LS)", action)
    position = pos_match.group(1) if pos_match else "player"

    # Build cohort stances and quotes deterministically
    if is_qb and is_transfer:
        stat_stance = f"EPA model flags {from_program} production as a limited sample — scheme fit at {program_display} is the real question"
        casual_stance = f"QB transfer = automatic excitement for {program_display} fans regardless of source"
        dh_stance = f"Board knows the depth chart, knows the staff relationship, and is already debating starting timeline"

        stat_quotes = [
            CohortQuote(
                f"Saw the {from_program} film. {actor_name}'s success rate under pressure was 38th-percentile in that scheme. Not saying it doesn't translate — saying I'd want to see him in a different context before calling it a win.",
                "CFB_Analytics (r/cfb)"
            ),
            CohortQuote(
                f"The efficiency numbers from {from_program} are real but that conference is two levels below where {program_display} is operating. Adjustment variance is the issue.",
                "EPAWatcher (Twitter)"
            ),
            CohortQuote(
                f"EPA per play at 0.18 last year — that's upper-third for the conference. Translating that to {program_display}'s schedule is the million-dollar question.",
                "AdvancedStats_CFB (Bluesky)"
            ),
        ]
        casual_quotes = [
            CohortQuote(
                f"We got a QB!! Who cares where he's from, this is exactly what we needed!",
                "Fan comment (program subreddit)"
            ),
            CohortQuote(
                f"{actor_name} to {program_display} is sending me. The staff is COOKING this portal.",
                "Fan tweet (Twitter)"
            ),
            CohortQuote(
                f"Tell me why I'm more excited about this portal class than the actual season starting lol",
                "Fan comment (r/cfb)"
            ),
        ]
        dh_quotes = [
            CohortQuote(
                f"Been tracking {actor_name} since his {from_program} spring game. Staff had eyes on him for six weeks. This isn't a panic add — it's a planned acquisition.",
                "BoardPoster (program message board)"
            ),
            CohortQuote(
                f"He fits the offense. Run-pass option heavy, mobile enough to extend plays, strong arm on the intermediate routes. This is a good get if the depth chart shakes out right.",
                "ScoutingEye247 (program forum)"
            ),
            CohortQuote(
                f"Question is whether he beats out the returning guys or if this is year-two starter material. Staff's track record here is mixed.",
                "Diehard_Fan88 (message board)"
            ),
        ]
        surprise = 52.0 if impact_label == "MAJOR" else 35.0

    elif position in ("RB",) and is_transfer:
        stat_stance = f"Contact rate and yards-after-contact metrics matter more than raw production at {from_program}"
        casual_stance = f"Running back additions always get a warm reception when the position was a visible need"
        dh_stance = f"Staff relationship and NIL timeline is the real story — the boards had wind of this two weeks ago"

        stat_quotes = [
            CohortQuote(
                f"Yards after contact at {from_program} was top-20% for the conference. That translates. The blocking scheme is different at {program_display} but I like the profile.",
                "RunningGameNerd (Twitter)"
            ),
            CohortQuote(
                f"Contact rate at 42% is solid. Fumble rate is low. This is the kind of profile that works in heavier usage — worth monitoring if {program_display} commits to the run.",
                "CFBMetrics (Bluesky)"
            ),
            CohortQuote(
                f"Opportunity rate of 0.44 with limited carries is the key number. The talent floor is higher than the {from_program} box score suggests.",
                "AnalyticsDFW (r/cfb)"
            ),
        ]
        casual_quotes = [
            CohortQuote(
                f"Running back! Yes! The backfield was hurting and now we've got fresh legs.",
                "Fan comment (program subreddit)"
            ),
            CohortQuote(
                f"Love it. We needed a real threat back there. Welcome to the family.",
                "Fan tweet"
            ),
            CohortQuote(
                f"Can't wait to see {actor_name} in the uniform. This class is fire.",
                "Fan comment (Discord)"
            ),
        ]
        dh_quotes = [
            CohortQuote(
                f"Was following this commit for three weeks. Staff locked this up quietly. Good sign about how the program communicates internally.",
                "BoardVet (message board)"
            ),
            CohortQuote(
                f"He's a grinder. Not a flashy pick but exactly the kind of back that program needs in the fourth quarter of conference games.",
                "Scout_247 (program forum)"
            ),
            CohortQuote(
                f"NIL structure here is reportedly competitive. That's how you win the portal battles for this tier of player.",
                "InsiderPost (on3)"
            ),
        ]
        surprise = 38.0 if impact_label == "MAJOR" else 28.0

    else:
        stat_stance = f"Advanced metrics suggest a developmental add — the tape will tell more than the {from_program} box score"
        casual_stance = f"Any addition to the {program_display} roster reads as a positive to the casual fan base"
        dh_stance = f"The boards have been watching this position group — this fills a real schematic need"

        stat_quotes = [
            CohortQuote(
                f"Saw the {from_program} film. Grade-ability at next level depends heavily on opponent quality adjustment.",
                "CFBFilmRoom (Twitter)"
            ),
            CohortQuote(
                f"Low sample size but the athleticism markers are there. Give him a full camp at {program_display} before judging.",
                "DraftMetrics_CFB (Bluesky)"
            ),
            CohortQuote(
                f"The numbers from {from_program} need scheme-adjustment but the physical profile is legit.",
                "AdvancedScout (r/cfb)"
            ),
        ]
        casual_quotes = [
            CohortQuote(
                f"Welcome to {program_display}! Love seeing the staff active in the portal.",
                "Fan comment (program subreddit)"
            ),
            CohortQuote(
                f"Been needing depth there all spring. Great get.",
                "Fan tweet"
            ),
            CohortQuote(
                f"The staff is working overtime in the portal. I'm here for it.",
                "Fan comment (Discord)"
            ),
        ]
        dh_quotes = [
            CohortQuote(
                f"This position group needed a body with real experience. This is exactly the fill the staff was hunting for.",
                "BoardPoster (message board)"
            ),
            CohortQuote(
                f"Watched him at {from_program} during their bowl game. Solid technique, good instincts. Low risk, decent ceiling.",
                "PositionCoachFan (rivals)"
            ),
            CohortQuote(
                f"The staff's due diligence is what made this happen. They know who they want.",
                "Diehard_Fan (message board)"
            ),
        ]
        surprise = 32.0 if impact_label == "MAJOR" else 22.0

    return CohortDivergence(
        wire_id=wire_row["id"],
        entity_slug=entity_slug,
        stat_folks=CohortData(
            cohort="stat_folks",
            stance=stat_stance,
            quotes=stat_quotes,
            sentiment_score=0.15,
            volume_share=0.28,
        ),
        casual_fans=CohortData(
            cohort="casual_fans",
            stance=casual_stance,
            quotes=casual_quotes,
            sentiment_score=0.72,
            volume_share=0.51,
        ),
        die_hards=CohortData(
            cohort="die_hards",
            stance=dh_stance,
            quotes=dh_quotes,
            sentiment_score=0.38,
            volume_share=0.21,
        ),
        offline=True,
    )


def extract_cohort_divergence(
    wire_row: dict,
    hours: int = 24,
) -> CohortDivergence:
    """Extract cohort divergence for a wire event.

    Falls back to _stub_divergence when the conversation corpus is empty.
    """
    entity_slug = wire_row.get("program_slug", "")
    window_start_dt = datetime.fromisoformat(
        wire_row["occurred_at"].replace(" ", "T")
    ) - timedelta(hours=hours // 2)
    window_end_dt = datetime.fromisoformat(
        wire_row["occurred_at"].replace(" ", "T")
    ) + timedelta(hours=hours // 2)
    window_start = window_start_dt.strftime("%Y-%m-%d %H:%M:%S")
    window_end = window_end_dt.strftime("%Y-%m-%d %H:%M:%S")

    try:
        with db_conn(read_only=True) as c:
            # Check if table exists and has rows in window
            try:
                rows = c.execute(
                    """
                    SELECT body, source_name, sentiment_score_vader
                    FROM conversation_documents
                    WHERE external_created_at_utc BETWEEN ? AND ?
                      AND (
                        LOWER(body) LIKE ? OR
                        LOWER(body) LIKE ?
                      )
                    LIMIT 500
                    """,
                    (window_start, window_end,
                     f"%{entity_slug.replace('-', ' ')}%",
                     f"%{wire_row.get('program_display', '').lower()}%"),
                ).fetchall()
            except Exception:
                return _stub_divergence(wire_row)

            if not rows:
                return _stub_divergence(wire_row)

            # Partition by cohort
            buckets: dict[str, list[dict]] = {
                "stat_folks": [], "casual_fans": [], "die_hards": []
            }
            for row in rows:
                cohort = _classify_cohort(row["body"], row["source_name"])
                buckets[cohort].append(dict(row))

            # Build CohortData per bucket
            def _build(cohort_name: str, docs: list[dict]) -> CohortData:
                sentiments = [
                    float(d["sentiment_score_vader"]) for d in docs
                    if d.get("sentiment_score_vader") is not None
                ]
                mean_sent = sum(sentiments) / len(sentiments) if sentiments else 0.0
                # Top quotes: use highest-sentiment excerpts as proxy for "most cited"
                top_docs = sorted(docs, key=lambda d: abs(float(d.get("sentiment_score_vader") or 0)), reverse=True)[:3]
                quotes = [
                    CohortQuote(
                        text=d["body"][:200].rstrip() + ("…" if len(d["body"]) > 200 else ""),
                        attribution=d.get("source_name") or "corpus",
                    )
                    for d in top_docs
                ]
                if not quotes:
                    quotes = [CohortQuote("No strong signal in the corpus window.", "corpus")]
                total = sum(len(b) for b in buckets.values()) or 1
                vol_share = len(docs) / total
                return CohortData(
                    cohort=cohort_name,
                    stance=f"{cohort_name.replace('_', ' ')} — derived from {len(docs)} corpus mentions",
                    quotes=quotes,
                    sentiment_score=round(mean_sent, 3),
                    volume_share=round(vol_share, 3),
                )

            return CohortDivergence(
                wire_id=wire_row["id"],
                entity_slug=entity_slug,
                stat_folks=_build("stat_folks", buckets["stat_folks"]),
                casual_fans=_build("casual_fans", buckets["casual_fans"]),
                die_hards=_build("die_hards", buckets["die_hards"]),
                offline=False,
            )

    except Exception:
        return _stub_divergence(wire_row)
