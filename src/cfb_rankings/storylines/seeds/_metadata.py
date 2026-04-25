"""Sprint 10 — the 8 active Storyline Threads.

Single source of truth for thread metadata. Chapter content lives in the
per-slug sibling modules (twelve_team_playoff_settling.py, etc.).

Voice register routing (per autonomy contract):
    - National-cross-program threads -> 'editor-desk' (synthetic house voice)
    - Program-anchored threads        -> 'profile:<slug>' (loads program profile)
    - Conference-level threads        -> 'conference:<slug>' (synthetic if no profile yet)

Started_at dates are when the thread's narrative arc began, not the
sprint date.
"""
from __future__ import annotations

THREADS: list[dict] = [
    {
        "thread_slug": "12-team-playoff-settling",
        "title": "The 12-Team Playoff Settling",
        "dek": (
            "Two cycles into the bracket. The regular season is reshaping in "
            "ways the format's architects didn't fully predict — and the "
            "discourse around it has gone exactly where it always goes."
        ),
        "accent_hex": "#c9a544",
        "status": "active",
        "started_at": "2024-08-01",
        "primary_program_slugs": [],
        "primary_conference_slug": None,
        "voice_register_source": "editor-desk",
    },
    {
        "thread_slug": "realignment-endgame",
        "title": "Realignment Endgame",
        "dek": (
            "Pac-12 dissolved. SEC and Big Ten ate the country. The ACC is "
            "the next domino. The slow-motion train of CFB's geography keeps "
            "moving, and the chapters keep landing."
        ),
        "accent_hex": "#1f5d6b",
        "status": "active",
        "started_at": "2023-08-01",
        "primary_program_slugs": [],
        "primary_conference_slug": None,
        "voice_register_source": "editor-desk",
    },
    {
        "thread_slug": "saban-to-deboer",
        "title": "The Saban-to-DeBoer Transition",
        "dek": (
            "Eighteen months into Alabama after Saban. The question is no "
            "longer whether DeBoer can win — it's what Bama becomes when the "
            "founder is gone and the standard remains."
        ),
        "accent_hex": "#9e1b32",
        "status": "active",
        "started_at": "2024-01-12",
        "primary_program_slugs": ["alabama"],
        "primary_conference_slug": "fbs-sec",
        "voice_register_source": "profile:alabama",
    },
    {
        "thread_slug": "big-ten-reasserting",
        "title": "The Big Ten Reasserting",
        "dek": (
            "After two decades of SEC primacy, the Big Ten is winning the "
            "meta. Three CFP semifinalists last year, a national title, and "
            "a recruiting map that no longer ends at the Mason-Dixon line."
        ),
        "accent_hex": "#003c7e",
        "status": "active",
        "started_at": "2024-01-08",
        "primary_program_slugs": [],
        "primary_conference_slug": "fbs-big-ten",
        "voice_register_source": "conference:fbs-big-ten",
    },
    {
        "thread_slug": "nd-usc-rivalry-recalibrating",
        "title": "ND-USC: A Rivalry Recalibrating",
        "dek": (
            "Two blue bloods, separated by realignment, a coastal divide, "
            "and a hundred and thirty years of memory. The series resumes — "
            "and the discourse about what it should be is louder than the game."
        ),
        "accent_hex": "#ae9142",
        "status": "active",
        "started_at": "2024-09-01",
        "primary_program_slugs": ["notre-dame", "southern-california"],
        "primary_conference_slug": None,
        "voice_register_source": "profile:notre-dame",
    },
    {
        "thread_slug": "coaching-carousel-2026-27",
        "title": "Coaching Carousel · 2026-27",
        "dek": (
            "The hot seats, the open jobs, the candidates that won't say "
            "they're candidates. The annual reshuffle that reshapes the "
            "sport, mapped chapter by chapter as it happens."
        ),
        "accent_hex": "#d97706",
        "status": "active",
        "started_at": "2026-09-01",
        "primary_program_slugs": [],
        "primary_conference_slug": None,
        "voice_register_source": "editor-desk",
    },
    {
        "thread_slug": "vandy-renaissance",
        "title": "The Vandy Renaissance",
        "dek": (
            "Vanderbilt isn't supposed to do this. Clark Lea, Diego Pavia, "
            "and the slow rise of the program nobody saw coming — except, "
            "apparently, the people in Nashville who never stopped watching."
        ),
        "accent_hex": "#cfae70",
        "status": "active",
        "started_at": "2024-10-01",
        "primary_program_slugs": ["vanderbilt"],
        "primary_conference_slug": "fbs-sec",
        "voice_register_source": "profile:vanderbilt",
    },
    {
        "thread_slug": "portal-era-settling",
        "title": "The Portal Era Settling",
        "dek": (
            "Four years deep into the transfer portal. The early chaos is "
            "yielding to patterns — who wins, who loses, who learned to "
            "navigate, and which programs treat the portal as a strategy "
            "rather than an emergency."
        ),
        "accent_hex": "#475569",
        "status": "active",
        "started_at": "2023-04-01",
        "primary_program_slugs": [],
        "primary_conference_slug": None,
        "voice_register_source": "editor-desk",
    },
]
