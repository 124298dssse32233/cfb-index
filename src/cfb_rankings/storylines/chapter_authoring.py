"""Live chapter authoring helpers for `generate-thread-chapter --auto`.

Five small responsibilities:

1. ``build_context_pack(db, slug, meta, next_n)`` — assembles the data the
   LLM needs (thread metadata + last 3 chapter teasers + voice contract +
   program profile when applicable).
2. ``build_prompt(context)`` — turns the context into the actual LLM prompt.
   Asks for a JSON-fenced chapter object the parser can ingest.
3. ``parse_llm_chapter_response(text, ...)`` — extracts the chapter dict
   from the LLM's response text. Tolerant of code-fenced JSON or raw JSON.
4. ``append_chapter_to_seed(slug, chapter)`` — splices a new chapter dict
   into the per-slug Python seed module's CHAPTERS list, preserving the
   existing formatting style.
5. ``write_draft_scaffold(slug, meta, next_n, ...)`` — fallback path used
   when no API key is set, when voice validator fails twice, or when
   response parsing fails. The scaffold ends up in
   ``seeds/_drafts/<slug>_<NN>_<ts>.py`` for human review.

Live + offline paths share ``write_draft_scaffold``; only the live + voice-
passed path mutates the canonical seed module.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SEEDS_DIR = Path(__file__).parent / "seeds"
DRAFTS_DIR = SEEDS_DIR / "_drafts"

# Map kebab thread slugs to their per-slug Python module names. The
# storylines.seeds.__init__ holds the canonical registry; we duplicate
# only the slugs we know to live-author, and fall back to a kebab→snake
# transform for anything not on the explicit list.
_SLUG_TO_MODULE: dict[str, str] = {
    "12-team-playoff-settling": "twelve_team_playoff_settling",
    "realignment-endgame": "realignment_endgame",
    "saban-to-deboer": "saban_to_deboer",
    "big-ten-reasserting": "big_ten_reasserting",
    "nd-usc-rivalry-recalibrating": "nd_usc_rivalry_recalibrating",
    "coaching-carousel-2026-27": "coaching_carousel_2026_27",
    "vandy-renaissance": "vandy_renaissance",
    "portal-era-settling": "portal_era_settling",
}


def seed_path_for_slug(slug: str) -> Path:
    module_name = _SLUG_TO_MODULE.get(slug) or slug.replace("-", "_")
    return SEEDS_DIR / f"{module_name}.py"


def canonical_byline(thread_title: str) -> str:
    """Build the exact ``From The X Department`` byline.

    Strips a leading ``The `` from thread titles that already begin with it,
    so ``"The Vandy Renaissance"`` becomes
    ``"From The Vandy Renaissance Department"`` rather than
    ``"From The The Vandy Renaissance Department"``.
    """
    title = thread_title.strip()
    if title.lower().startswith("the "):
        title = title[4:]
    return f"From The {title} Department"


# ---------------------------------------------------------------------------
# 1. Context pack
# ---------------------------------------------------------------------------

_VOICE_CONTRACT_EXCERPT = """\
VOICE CONTRACT (from CHRONICLE_EDITORIAL_BRIEF — non-negotiable):
1. Beat-Writer Test — would a sharp independent CFB blogger write this?
2. Name names every paragraph — coaches, players, dates, plays, board users, podcasters.
3. Thread to memory — connect current observation to specific historical moments.
4. One surprise per chapter.
5. Editorial prose — short sentences, concrete nouns, active voice.
6. Data shown, not explained.
7. Attribution a fan can read — "Stewart Mandel · The Athletic · Mon" / "Solid Verbal pod ep 247".

REGISTER: warm, fan-positioned, smart-but-knows-the-in-jokes. NOT The New Yorker.
The Athletic columnist + Defector mid-range + Solid Verbal in textual form.

BANNED PHRASES (any appearance fails voice validation):
analytics cohort, analytics-cohort, casual cohort, casual-cohort, die-hard cohort,
die-hard-cohort, cohort divergence, cohort split, n=, effective n, fan-intel,
discourse velocity, stat engine, our algorithm, the engine, tier-1 program,
methodology, methodologies, methodological, sample growing, summary stat,
compression of outcome, "the pattern is " (literal), every season produces,
this table, this card, this module, hot take, clown, idiot, stupid, amirite,
L take, cope, seethe, anonymous source, according to a source, we all know,
obviously, of course.

Bare "cohort" as a standard English word (e.g. "portal cohort", "freshman cohort")
is FINE — only the taxonomy compounds above are banned."""


def build_context_pack(
    db, slug: str, meta: dict, next_n: int, *, prior_chapters_to_include: int = 3,
) -> dict[str, Any]:
    """Assemble the data the LLM needs to write the next chapter.

    Pulls the most-recent ``prior_chapters_to_include`` chapters from the
    DB (newest first), trims their bodies to ~200 words for context, and
    bundles thread metadata + voice contract.
    """
    chapters = db.query_all(
        """
        select chapter_number, title, dek, body_markdown, published_at,
               referenced_sources_json, pull_quote
        from storyline_chapters
        where thread_slug = :slug
        order by chapter_number desc
        limit :lim
        """,
        {"slug": slug, "lim": prior_chapters_to_include},
    )
    prior = []
    for ch in chapters:
        body = ch.get("body_markdown") or ""
        words = body.split()
        teaser = " ".join(words[:200])
        if len(words) > 200:
            teaser += " […]"
        prior.append({
            "chapter_number": int(ch["chapter_number"]),
            "title": ch["title"],
            "dek": ch["dek"],
            "teaser": teaser,
            "pull_quote": ch.get("pull_quote"),
        })

    program_profile_excerpt: str | None = None
    voice_register_source = meta.get("voice_register_source") or "editor-desk"
    if voice_register_source.startswith("profile:"):
        slug_p = voice_register_source.split(":", 1)[1]
        program_profile_excerpt = _try_load_profile_excerpt(slug_p)

    return {
        "thread_slug": slug,
        "thread_title": meta["title"],
        "thread_dek": meta["dek"],
        "voice_register_source": voice_register_source,
        "program_profile_excerpt": program_profile_excerpt,
        "next_chapter_number": next_n,
        "prior_chapters": prior,
    }


def _try_load_profile_excerpt(program_slug: str) -> str | None:
    """Best-effort load of a program profile's voice fields. Returns None on miss."""
    try:
        from cfb_rankings.team_pages.profile_loader import load_profile
        profile = load_profile(program_slug)
        return (
            f"PROGRAM VOICE — {program_slug}:\n"
            f"  voice_register: {getattr(profile, 'voice_register', 'unknown')}\n"
            f"  identity_phrase: {getattr(profile, 'identity_phrase', 'unknown')}\n"
            f"  mantra: {getattr(profile, 'mantra', 'unknown')}\n"
        )
    except Exception:
        return None


# ---------------------------------------------------------------------------
# 2. Prompt builder
# ---------------------------------------------------------------------------

def build_prompt(context: dict[str, Any]) -> str:
    parts: list[str] = []
    parts.append(
        f"You are writing chapter {context['next_chapter_number']} of "
        f"the Storyline Thread \"{context['thread_title']}\" on the CFB "
        f"Index product."
    )
    parts.append(f"Thread dek: {context['thread_dek']}")
    parts.append(_VOICE_CONTRACT_EXCERPT)

    if context.get("program_profile_excerpt"):
        parts.append(context["program_profile_excerpt"])

    if context["prior_chapters"]:
        parts.append("\nPRIOR CHAPTERS (newest first — your chapter MUST reference at least one):")
        for ch in context["prior_chapters"]:
            parts.append(
                f"\n--- Chapter {ch['chapter_number']}: {ch['title']} ---"
                f"\n{ch['dek']}"
                f"\n{ch['teaser']}"
            )

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    parts.append(f"\nTODAY'S DATE (use this for published_at): {today}")

    byline = canonical_byline(context["thread_title"])
    parts.append(f"""\

OUTPUT FORMAT — return EXACTLY one JSON object inside a ```json``` code fence,
matching this schema. No prose before or after the fence.

```json
{{
  "chapter_number": {context['next_chapter_number']},
  "title": "<descriptive, voice-registered, no clickbait>",
  "dek": "<one sentence that sets the chapter's argument>",
  "body_markdown": "<800-1500 words of body. Paragraphs separated by blank lines. Blockquotes prefixed with '> '. Inline em via *word*, strong via **word**. Verbatim source quotes use smart quotes \\u201c\\u201d. Reference at least one prior chapter via something like 'as Chapter 2 noted'.>",
  "byline": "{byline}",
  "published_at": "{today} 09:00:00",
  "read_time_minutes": 7,
  "referenced_chapter_ids": [<list of int prior chapter_numbers you cite, must include >=1>],
  "referenced_sources": [
    {{"kind": "beat-writer", "name": "<real name>", "label": "<publication>", "url": null, "date": "YYYY-MM-DD", "quote": "<verbatim quote>"}},
    {{"kind": "podcast", "name": "<show name>", "label": "Episode <N>", "url": null, "date": "YYYY-MM-DD", "quote": "<verbatim quote>"}},
    {{"kind": "board", "name": "<username>", "label": "<board thread description>", "url": null, "date": "YYYY-MM-DD", "quote": "<verbatim quote>"}}
  ],
  "pull_quote": "<one verbatim quote from one of the cited sources>"
}}
```

REQUIREMENTS:
- 800-1500 words of body.
- Reference at least one prior chapter (referenced_chapter_ids must be non-empty if prior chapters exist).
- At least 3 source citations.
- Pull quote must be a verbatim line from one of the cited sources.
- ZERO banned phrases (the validator will catch them and reject).
- Byline must be EXACTLY: {byline}
""")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# 3. Response parser
# ---------------------------------------------------------------------------

_FENCED_JSON_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def parse_llm_chapter_response(
    text: str, *, thread_slug: str, chapter_number: int, meta: dict,
) -> dict[str, Any]:
    """Extract a chapter dict from the LLM's response.

    Tolerant of: ```json fenced blocks, ``` fenced blocks, raw JSON.
    Validates that required fields are present; raises ValueError otherwise.
    """
    if not text or not text.strip():
        raise ValueError("empty response from LLM")

    candidate: str | None = None
    fence_match = _FENCED_JSON_RE.search(text)
    if fence_match:
        candidate = fence_match.group(1)
    else:
        # No fence — try the largest balanced { ... } block.
        first = text.find("{")
        last = text.rfind("}")
        if first >= 0 and last > first:
            candidate = text[first : last + 1]
    if not candidate:
        raise ValueError("no JSON object found in LLM response")

    try:
        chapter = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in LLM response: {exc}") from exc

    # Required fields.
    required = ("chapter_number", "title", "dek", "body_markdown", "byline",
                "published_at", "referenced_sources")
    missing = [f for f in required if f not in chapter]
    if missing:
        raise ValueError(f"LLM response missing required fields: {missing}")

    # Force chapter_number to the value the caller expects (LLM may drift).
    chapter["chapter_number"] = chapter_number

    # Force byline to the canonical format (handles "The X" → no double "The").
    chapter["byline"] = canonical_byline(meta["title"])

    # Defaults.
    chapter.setdefault("read_time_minutes", 7)
    chapter.setdefault("referenced_chapter_ids", [])
    chapter.setdefault("pull_quote", None)
    return chapter


# ---------------------------------------------------------------------------
# 4. Append to seed module
# ---------------------------------------------------------------------------

def _py_str(s: str) -> str:
    """Format a string as a JSON-escaped double-quoted Python literal."""
    return json.dumps(s, ensure_ascii=False)


def _format_sources_for_seed(sources: list[dict]) -> str:
    """Produce a Python list literal matching the seed-module style."""
    if not sources:
        return "[]"
    lines = ["["]
    for s in sources:
        items: list[str] = []
        for key in ("kind", "name", "label", "url", "date", "quote"):
            if key not in s:
                continue
            v = s[key]
            if v is None:
                items.append(f'"{key}": None')
            elif isinstance(v, str):
                items.append(f'"{key}": {_py_str(v)}')
            else:
                items.append(f'"{key}": {v!r}')
        lines.append("            {" + ", ".join(items) + "},")
    lines.append("        ]")
    return "\n".join(lines)


def format_chapter_for_seed(ch: dict) -> str:
    """Format a chapter dict as a Python source block matching seeds/*.py style."""
    body = ch["body_markdown"].rstrip()
    # Paranoid escape — no body should contain `"""` but if it does, we'd
    # break the triple-quoted literal.
    if '"""' in body:
        body = body.replace('"""', '\\"\\"\\"')

    pq = ch.get("pull_quote")
    pq_repr = _py_str(pq) if pq else "None"

    sources_repr = _format_sources_for_seed(ch.get("referenced_sources") or [])
    refs_repr = repr(ch.get("referenced_chapter_ids") or [])

    return (
        "    {\n"
        f'        "chapter_number": {int(ch["chapter_number"])},\n'
        f'        "title": {_py_str(ch["title"])},\n'
        f'        "dek": {_py_str(ch["dek"])},\n'
        f'        "body_markdown": """{body}""",\n'
        f'        "byline": {_py_str(ch["byline"])},\n'
        f'        "published_at": {_py_str(ch["published_at"])},\n'
        f'        "read_time_minutes": {int(ch.get("read_time_minutes") or 7)},\n'
        f'        "referenced_chapter_ids": {refs_repr},\n'
        f'        "referenced_sources": {sources_repr},\n'
        f'        "pull_quote": {pq_repr},\n'
        "    },"
    )


_CHAPTERS_TERMINATOR_RE = re.compile(r"\n\]\s*\Z")


def append_chapter_to_seed(slug: str, chapter: dict) -> Path:
    """Append a new chapter dict to the live per-slug seed module.

    Splices the formatted block before the closing ``]`` of CHAPTERS.
    Raises if the file is not present or its terminator can't be located.
    """
    path = seed_path_for_slug(slug)
    if not path.exists():
        raise FileNotFoundError(f"seed module not found: {path}")
    text = path.read_text(encoding="utf-8").rstrip() + "\n"
    match = _CHAPTERS_TERMINATOR_RE.search(text)
    if not match:
        raise RuntimeError(f"could not locate CHAPTERS terminator in {path}")
    insertion_point = match.start() + 1  # right after the trailing newline
    new_block = format_chapter_for_seed(chapter) + "\n"
    new_text = text[:insertion_point] + new_block + text[insertion_point:]
    path.write_text(new_text, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# 5. Draft scaffold (offline / failure fallback)
# ---------------------------------------------------------------------------

def write_draft_scaffold(
    slug: str, meta: dict, next_n: int, *,
    llm_text: str | None = None, violations: list[str] | None = None,
    note: str | None = None,
) -> Path:
    """Write a draft chapter scaffold to seeds/_drafts/.

    Uses today's date in the filename + an optional note explaining why
    the live path didn't write to the canonical seed module (no API key,
    voice validator failed, parse error, etc.).
    """
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    draft_path = DRAFTS_DIR / f"{slug}_{next_n:02d}_{ts}.py"

    header_notes: list[str] = []
    if note:
        header_notes.append(f"# NOTE: {note}")
    if violations:
        header_notes.append(f"# VOICE-VALIDATOR VIOLATIONS: {violations}")

    raw_block = ""
    if llm_text:
        # Embed the raw LLM response as a comment block so the human
        # reviewer can see what the model produced.
        commented = "\n".join("# " + line for line in llm_text.splitlines())
        raw_block = (
            "\n# ----- raw LLM response (for review) -----\n"
            f"{commented}\n"
            "# ----- end raw LLM response -----\n"
        )

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    byline = canonical_byline(meta["title"])
    scaffold = (
        f'"""Draft chapter scaffold for {slug} chapter {next_n}.\n\n'
        f'Generated by `manage.py generate-thread-chapter`. The live LLM '
        f'path either had no API key, failed voice validation twice, or '
        f'produced a response that could not be parsed — see notes below.\n'
        f'"""\n'
    )
    scaffold += "\n".join(header_notes) + ("\n" if header_notes else "")
    scaffold += raw_block
    scaffold += (
        f'\nTHREAD_SLUG = "{slug}"\n\n'
        f'CHAPTERS = [\n'
        f'    {{\n'
        f'        "chapter_number": {next_n},\n'
        f'        "title": "...",\n'
        f'        "dek": "...",\n'
        f'        "body_markdown": """...""",\n'
        f'        "byline": "{byline}",\n'
        f'        "published_at": "{today}",\n'
        f'        "read_time_minutes": 6,\n'
        f'        "referenced_chapter_ids": {list(range(1, next_n))},\n'
        f'        "referenced_sources": [],\n'
        f'        "pull_quote": None,\n'
        f'    }},\n'
        f']\n'
    )
    draft_path.write_text(scaffold, encoding="utf-8")
    return draft_path
