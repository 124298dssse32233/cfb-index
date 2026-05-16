"""Coaching changes RSS adapter — Sprint v5-1 Day 4 Adapter 2.

Footballscoop RSS feed + 247Sports coaching-tracker scrape. Writes new
coaching events into ``coaching_changes`` and emits a parallel row into
``wire_entries`` (``actor_kind='coach'``) so the homepage Wire panel picks
them up automatically.

Public entry point:

    fetch_coaching_news(db, *, days: int = 7) -> dict[str, int]

Returns a counter dict ``{'fetched', 'matched_keyword', 'persisted',
'errors'}``. Resilient: any per-source HTTP/network/parse failure logs
and increments ``errors`` but never raises. If both feeds fail we still
return a normal counter dict.

Schema reference (``migrations.py`` ``coaching_changes`` table):
    coaching_change_id  INTEGER PK
    team_id             INTEGER NULL  (we leave NULL when slug-unresolved)
    team_slug           TEXT NOT NULL (we use 'unknown' when we cannot match)
    coach_name          TEXT NOT NULL (best-effort parse, falls back to '')
    role                TEXT NOT NULL ('head coach' default)
    change_type         TEXT NOT NULL (one of hire/exit/promotion/extension/other)
    announced_date      TEXT NOT NULL (ISO date)
    summary             TEXT NOT NULL (headline or first sentence)
    issue_number        TEXT NULL
    sources_json        TEXT default '[]'  (we stash the source URL here)
    ingested_at         TEXT default current_timestamp

Deduplication: SHA1 hash of ``(source, headline, occurred_at_iso)`` is
stashed in ``sources_json`` as ``{"dedup_key": "...", "url": "..."}`` and
also used to skip pre-existing rows via a per-call ``SELECT`` lookup.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable

log = logging.getLogger(__name__)


FOOTBALLSCOOP_RSS = "https://footballscoop.com/feed/"
TWO_FOUR_SEVEN_TRACKER = "https://247sports.com/Article/college-football-coaching-changes/"

# Headline keywords. Lowercase compare. ``contract`` + ``dismissed`` + ``named``
# + ``accepts`` extend the brief's six-keyword core to the audit-mandated list.
COACH_KEYWORDS = (
    "hired", "fired", "promoted", "resigned", "retires", "retire",
    "retiring", "extension", "contract", "dismissed", "named", "accepts",
)

# Crude mapping of keyword -> change_type. First match wins; default 'other'.
_CHANGE_TYPE_MAP: tuple[tuple[tuple[str, ...], str], ...] = (
    (("hired", "named", "accepts", "agrees"), "hire"),
    (("fired", "dismissed", "ousted", "out at", "parts ways"), "exit"),
    (("resigned", "resigns", "steps down", "retires", "retire", "retiring"), "exit"),
    (("promoted", "promotion", "elevated"), "promotion"),
    (("extension", "extended", "extends"), "extension"),
    (("contract"), "contract"),
)

from cfb_rankings.common.head_chrome import base_url

# Routes through head_chrome.base_url() so a domain swap is a one-line change.
_UA = f"CFBIndex-coaching-tracker/1.0 (+{base_url()})"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def fetch_coaching_news(db: Any, *, days: int = 7) -> dict[str, int]:
    """Pull Footballscoop RSS + 247Sports coaching tracker.

    ``db`` is a ``cfb_rankings.db.Database`` (preferred) or any object with
    a sqlite3-style ``execute`` method. Per-source failures are logged and
    counted; this function never raises.
    """
    counter = {"fetched": 0, "matched_keyword": 0, "persisted": 0, "errors": 0}

    # If the schema isn't present (fresh DB, old snapshot, etc.), bail out
    # gracefully — incrementing errors but not crashing the caller.
    if not _coaching_changes_table_exists(db):
        log.warning(
            "coaching_tracker: coaching_changes table missing; skipping run"
        )
        counter["errors"] += 1
        return counter

    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=max(1, int(days)))

    # ---- Source 1: Footballscoop RSS ---------------------------------
    try:
        rss_rows = _fetch_footballscoop(cutoff)
    except Exception as exc:  # pragma: no cover - defensive
        log.exception("coaching_tracker: footballscoop fetch failed: %s", exc)
        rss_rows = []
        counter["errors"] += 1

    counter["fetched"] += len(rss_rows)
    matched_rss = [r for r in rss_rows if _matches_keyword(r["title"])]
    counter["matched_keyword"] += len(matched_rss)

    for row in matched_rss:
        try:
            if _persist_coaching_row(db, row):
                counter["persisted"] += 1
        except Exception as exc:  # pragma: no cover - defensive
            log.exception("coaching_tracker: persist failed for %r: %s",
                          row.get("title"), exc)
            counter["errors"] += 1

    # ---- Source 2: 247Sports coaching tracker scrape -----------------
    try:
        scrape_rows = _fetch_247_tracker(cutoff)
    except Exception as exc:  # pragma: no cover - defensive
        log.exception("coaching_tracker: 247sports fetch failed: %s", exc)
        scrape_rows = []
        counter["errors"] += 1

    counter["fetched"] += len(scrape_rows)
    matched_scrape = [r for r in scrape_rows if _matches_keyword(r["title"])]
    counter["matched_keyword"] += len(matched_scrape)

    for row in matched_scrape:
        try:
            if _persist_coaching_row(db, row):
                counter["persisted"] += 1
        except Exception as exc:  # pragma: no cover - defensive
            log.exception("coaching_tracker: persist failed for %r: %s",
                          row.get("title"), exc)
            counter["errors"] += 1

    log.info(
        "coaching_tracker: fetched=%d matched_keyword=%d persisted=%d errors=%d",
        counter["fetched"], counter["matched_keyword"],
        counter["persisted"], counter["errors"],
    )
    return counter


# ---------------------------------------------------------------------------
# Source fetchers
# ---------------------------------------------------------------------------


def _fetch_footballscoop(cutoff: datetime) -> list[dict[str, Any]]:
    """Parse Footballscoop RSS via feedparser. Returns normalized rows.

    Each row carries: ``title``, ``link``, ``occurred_at`` (datetime, UTC),
    ``source``, ``summary``.
    """
    import feedparser  # local import — heavy dep, only needed at run time

    feed = feedparser.parse(FOOTBALLSCOOP_RSS)
    # feedparser surfaces transport errors via feed.bozo / feed.bozo_exception
    # but it still returns a parsed structure. We treat the entry list as
    # ground truth; an empty list is a no-op.
    out: list[dict[str, Any]] = []
    for entry in getattr(feed, "entries", []) or []:
        title = _entry_text(entry, "title")
        if not title:
            continue
        link = _entry_text(entry, "link")
        summary = _entry_text(entry, "summary") or _entry_text(entry, "description") or title
        occurred_at = _entry_published(entry) or datetime.now(tz=timezone.utc)
        if occurred_at < cutoff:
            continue
        out.append({
            "title": title,
            "link": link,
            "occurred_at": occurred_at,
            "source": "footballscoop",
            "summary": summary,
        })
    return out


def _fetch_247_tracker(cutoff: datetime) -> list[dict[str, Any]]:
    """Scrape the 247Sports coaching-changes index page.

    The 247 page is rendered server-side as a list of headlines with
    embedded links. We extract every anchor whose visible text reads like
    a coaching headline (the keyword filter happens upstream). Failure to
    load the page raises — the caller handles it.
    """
    import requests  # local import
    from bs4 import BeautifulSoup  # local import

    resp = requests.get(
        TWO_FOUR_SEVEN_TRACKER,
        timeout=20.0,
        headers={"User-Agent": _UA},
    )
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    out: list[dict[str, Any]] = []
    now = datetime.now(tz=timezone.utc)

    seen: set[str] = set()
    for anchor in soup.find_all("a"):
        text = (anchor.get_text(" ", strip=True) or "").strip()
        if not text or len(text) < 16:
            continue
        href = (anchor.get("href") or "").strip()
        if not href or href.startswith("#"):
            continue
        if href in seen:
            continue
        seen.add(href)

        # Resolve relative links to absolute.
        if href.startswith("/"):
            href = "https://247sports.com" + href

        # 247 sometimes wraps a date in the surrounding context — fall back
        # to now() and rely on the dedup key to keep things idempotent.
        out.append({
            "title": text,
            "link": href,
            "occurred_at": now,
            "source": "247sports",
            "summary": text,
        })
        if cutoff and out and out[-1]["occurred_at"] < cutoff:
            out.pop()

    return out


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def _persist_coaching_row(db: Any, row: dict[str, Any]) -> bool:
    """Write one coaching event into ``coaching_changes`` (+ wire_entries).

    Returns True if a new row was inserted, False on dedup hit.
    """
    title = (row.get("title") or "").strip()
    link = (row.get("link") or "").strip()
    occurred_at = row.get("occurred_at") or datetime.now(tz=timezone.utc)
    source = row.get("source") or "rss"
    summary = (row.get("summary") or title).strip()

    occurred_at_iso = occurred_at.date().isoformat()
    dedup_key = _make_dedup_key(source, title, occurred_at_iso)

    if _dedup_exists(db, dedup_key):
        return False

    change_type = _infer_change_type(title)
    coach_name = _infer_coach_name(title) or ""
    team_slug = _infer_team_slug(db, title) or "unknown"
    team_id = _team_id_for_slug(db, team_slug) if team_slug != "unknown" else None
    role = _infer_role(title) or "head coach"

    sources_json = json.dumps(
        [{"dedup_key": dedup_key, "url": link, "source": source}],
        ensure_ascii=False,
    )

    _exec(
        db,
        """
        insert into coaching_changes (
            team_id, team_slug, coach_name, role, change_type,
            announced_date, summary, issue_number, sources_json
        ) values (
            :team_id, :team_slug, :coach_name, :role, :change_type,
            :announced_date, :summary, :issue_number, :sources_json
        )
        """,
        {
            "team_id": team_id,
            "team_slug": team_slug,
            "coach_name": coach_name,
            "role": role,
            "change_type": change_type,
            "announced_date": occurred_at_iso,
            "summary": summary[:500],
            "issue_number": None,
            "sources_json": sources_json,
        },
    )

    # Best-effort wire emission. If wire_entries doesn't exist (fresh DB
    # missing the wire schema) we don't fail the coaching write.
    try:
        _emit_wire_entry(db, row=row, team_slug=team_slug,
                         coach_name=coach_name, change_type=change_type,
                         summary=summary, occurred_at=occurred_at)
    except Exception as exc:  # pragma: no cover - defensive
        log.warning("coaching_tracker: wire emit failed: %s", exc)

    return True


def _emit_wire_entry(
    db: Any,
    *,
    row: dict[str, Any],
    team_slug: str,
    coach_name: str,
    change_type: str,
    summary: str,
    occurred_at: datetime,
) -> None:
    """Insert a paired wire_entries row tagged ``actor_kind='coach'``.

    Uses ``insert or ignore`` so the per-day unique index
    ``idx_wire_dedupe(program_slug, action, date(occurred_at))`` swallows
    duplicates silently.
    """
    if not _wire_entries_table_exists(db):
        return

    program_display = _program_display_for_slug(db, team_slug) or team_slug.replace("-", " ").title()
    action_text = summary[:240] if summary else f"{coach_name} {change_type}".strip()
    source_url = ""
    source_name = "Footballscoop RSS" if row.get("source") == "footballscoop" else "247Sports coaching tracker"
    if isinstance(row.get("link"), str):
        source_url = row["link"]

    _exec(
        db,
        """
        insert or ignore into wire_entries
            (occurred_at, program_slug, program_display, actor_kind,
             action, why_it_matters, impact_label, impact_color,
             historical_comp, source_kind, source_url, source_name,
             related_thread_slug, fan_intel_velocity_spike)
        values
            (:occurred_at, :program_slug, :program_display, 'coach',
             :action, '', '', '',
             null, :source_kind, :source_url, :source_name,
             null, null)
        """,
        {
            "occurred_at": occurred_at.isoformat(sep=" "),
            "program_slug": None if team_slug == "unknown" else team_slug,
            "program_display": program_display,
            "action": action_text,
            "source_kind": "coaching_news",
            "source_url": source_url or None,
            "source_name": source_name,
        },
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _matches_keyword(text: str) -> bool:
    if not text:
        return False
    lower = text.lower()
    return any(kw in lower for kw in COACH_KEYWORDS)


def _make_dedup_key(source: str, headline: str, occurred_at_iso: str) -> str:
    raw = f"{source}|{headline.strip().lower()}|{occurred_at_iso}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:24]


def _infer_change_type(title: str) -> str:
    lower = (title or "").lower()
    for keywords, label in _CHANGE_TYPE_MAP:
        if isinstance(keywords, str):
            if keywords in lower:
                return label
        else:
            if any(k in lower for k in keywords):
                return label
    return "other"


def _infer_coach_name(title: str) -> str:
    """Heuristic coach-name extraction. Best effort.

    Looks for the first run of 2-4 capitalized tokens. Returns '' on miss
    rather than guessing badly — downstream callers know how to deal with
    an empty coach_name (the seed JSON tolerates non-distinct values).
    """
    if not title:
        return ""
    # Strip leading "Team: " or "BREAKING: " markers that prefix the headline.
    cleaned = re.sub(r"^[A-Z][A-Z\s\d]+:\s*", "", title.strip())
    matches = re.findall(
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})",
        cleaned,
    )
    for m in matches:
        # Skip month-day-like fragments and obvious non-names.
        if any(tok in m.lower() for tok in (
            "january", "february", "march", "april", "may", "june",
            "july", "august", "september", "october", "november", "december",
            "monday", "tuesday", "wednesday", "thursday", "friday",
            "saturday", "sunday",
        )):
            continue
        return m
    return ""


_TEAM_HINTS: tuple[tuple[str, str], ...] = (
    ("alabama", "alabama"),
    ("auburn", "auburn"),
    ("clemson", "clemson"),
    ("florida state", "florida-state"),
    ("florida", "florida"),
    ("georgia", "georgia"),
    ("lsu", "lsu"),
    ("michigan state", "michigan-state"),
    ("michigan", "michigan"),
    ("notre dame", "notre-dame"),
    ("ohio state", "ohio-state"),
    ("oklahoma state", "oklahoma-state"),
    ("oklahoma", "oklahoma"),
    ("ole miss", "ole-miss"),
    ("oregon", "oregon"),
    ("penn state", "penn-state"),
    ("tennessee", "tennessee"),
    ("texas a&m", "texas-am"),
    ("texas", "texas"),
    ("usc", "usc"),
    ("utah", "utah"),
    ("washington", "washington"),
    ("wisconsin", "wisconsin"),
)


def _infer_team_slug(db: Any, title: str) -> str:
    """Match headline against a small static program-name table.

    A future enhancement could resolve via teams.canonical_name lookup;
    for now the static hints cover the high-cardinality coaching beat.
    """
    if not title:
        return ""
    lower = title.lower()
    for needle, slug in _TEAM_HINTS:
        if needle in lower:
            return slug
    return ""


def _infer_role(title: str) -> str:
    lower = (title or "").lower()
    if "offensive coordinator" in lower or "oc " in lower or " oc," in lower:
        return "offensive coordinator"
    if "defensive coordinator" in lower or "dc " in lower or " dc," in lower:
        return "defensive coordinator"
    if "special teams" in lower:
        return "special teams coordinator"
    if "head coach" in lower:
        return "head coach"
    return ""


def _entry_text(entry: Any, attr: str) -> str:
    """Pull a string off a feedparser entry, tolerating dict-like access."""
    try:
        value = getattr(entry, attr)
    except AttributeError:
        value = None
    if value is None and isinstance(entry, dict):
        value = entry.get(attr)
    if value is None:
        return ""
    return str(value).strip()


def _entry_published(entry: Any) -> datetime | None:
    """Resolve an entry's pubdate to an aware UTC datetime, or None."""
    for attr in ("published_parsed", "updated_parsed"):
        struct = getattr(entry, attr, None)
        if struct is None and isinstance(entry, dict):
            struct = entry.get(attr)
        if struct is None:
            continue
        try:
            # struct is a time.struct_time
            return datetime(*struct[:6], tzinfo=timezone.utc)
        except Exception:
            continue
    # Try string fields
    for attr in ("published", "updated"):
        text = _entry_text(entry, attr)
        if not text:
            continue
        for fmt in (
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S %Z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%SZ",
        ):
            try:
                dt = datetime.strptime(text, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except ValueError:
                continue
    return None


# ---------------------------------------------------------------------------
# DB-tolerance helpers (work with either Database or raw sqlite3 connection)
# ---------------------------------------------------------------------------


def _exec(db: Any, sql: str, params: dict[str, Any]) -> None:
    """Run a mutating SQL statement on either Database or sqlite3.Connection."""
    if hasattr(db, "execute") and hasattr(db, "connection"):
        # cfb_rankings.db.Database — commit handled internally.
        db.execute(sql, params)
        return
    # Raw sqlite3 connection
    cur = db.execute(sql, params)
    try:
        db.commit()
    except Exception:
        pass
    return cur


def _query_one(db: Any, sql: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Fetch one row as a dict from either Database or sqlite3.Connection."""
    if hasattr(db, "query_one"):
        return db.query_one(sql, params or {})
    cur = db.execute(sql, params or {})
    row = cur.fetchone()
    if row is None:
        return None
    if hasattr(row, "keys"):
        return {k: row[k] for k in row.keys()}
    desc = [c[0] for c in cur.description or []]
    return dict(zip(desc, row))


def _coaching_changes_table_exists(db: Any) -> bool:
    try:
        row = _query_one(
            db,
            "select name from sqlite_master where type='table' and name='coaching_changes'",
        )
        return bool(row)
    except Exception:
        return False


def _wire_entries_table_exists(db: Any) -> bool:
    try:
        row = _query_one(
            db,
            "select name from sqlite_master where type='table' and name='wire_entries'",
        )
        return bool(row)
    except Exception:
        return False


def _dedup_exists(db: Any, dedup_key: str) -> bool:
    """Check coaching_changes.sources_json for a prior row with this dedup_key."""
    try:
        row = _query_one(
            db,
            "select 1 as hit from coaching_changes where sources_json like :pat limit 1",
            {"pat": f"%{dedup_key}%"},
        )
        return bool(row)
    except Exception:
        return False


def _team_id_for_slug(db: Any, slug: str) -> int | None:
    """Resolve teams.team_id for a slug. Returns None when unknown."""
    if not slug or slug == "unknown":
        return None
    try:
        row = _query_one(
            db,
            "select team_id from teams where slug = :slug limit 1",
            {"slug": slug},
        )
        if not row:
            return None
        return int(row.get("team_id")) if row.get("team_id") is not None else None
    except Exception:
        return None


def _program_display_for_slug(db: Any, slug: str) -> str:
    if not slug or slug == "unknown":
        return ""
    try:
        row = _query_one(
            db,
            """
            select coalesce(short_name, canonical_name) as display
            from teams where slug = :slug limit 1
            """,
            {"slug": slug},
        )
        return (row or {}).get("display") or ""
    except Exception:
        return ""
