from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import json
from typing import Any
from zoneinfo import ZoneInfo

from cfb_rankings.conversation_utils import (
    attention_score,
    extract_keywords,
    is_probably_cfb_reddit_post,
    normalize_lookup_text,
    sample_quality_score,
    score_sentiment,
)
from cfb_rankings.db import Database
from cfb_rankings.storage import Repository


ET_ZONE = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class WatchlistTeam:
    team_id: int
    team_name: str
    aliases: list[str]


def collect_reddit_watchlist(
    repository: Repository,
    db: Database,
    client: Any,
    season: int,
    week: int,
    team_names: list[str] | None = None,
    limit_teams: int = 25,
    subreddit: str | None = "CFB",
    audience_bucket: str = "national",
    search_limit: int = 15,
    require_cfb_context: bool = True,
    after: int | None = None,
    before: int | None = None,
    provider_name: str = "reddit",
    replace_existing: bool = True,
) -> dict[str, int]:
    repository.seed_team_aliases(season)
    watchlist = _build_watchlist(repository, db, season=season, week=week, team_names=team_names or [], limit_teams=limit_teams)
    if not watchlist:
        raise RuntimeError(f"No watchlist teams available for season {season} week {week}.")

    run_id = _create_collection_run(
        db=db,
        source_name="reddit",
        collection_scope="team-watchlist",
        target_label=f"{season} week {week}",
        season=season,
        week=week,
        raw_config={
            "source": "reddit",
            "provider": provider_name,
            "subreddit": subreddit,
            "audience_bucket": audience_bucket,
            "search_limit": search_limit,
            "watchlist_team_count": len(watchlist),
            "require_cfb_context": require_cfb_context,
            "after": after,
            "before": before,
            "replace_existing": replace_existing,
        },
    )

    document_rows_by_source_id: dict[str, dict[str, Any]] = {}
    target_rows: dict[tuple[str, str, str], dict[str, Any]] = {}
    try:
        if replace_existing:
            _delete_existing_reddit_query_match_targets(
                db=db,
                season=season,
                week=week,
                audience_bucket=audience_bucket,
                subreddit=subreddit,
                team_ids=[team.team_id for team in watchlist],
            )
        for team in watchlist:
            aliases = _preferred_aliases(team.aliases, team.team_name)
            if not aliases:
                continue
            for alias in aliases:
                query = _reddit_query(alias=alias, subreddit=subreddit)
                for post in client.search_posts(query=query, subreddit=subreddit, limit=search_limit, after=after, before=before):
                    source_document_id = str(post.get("name") or post.get("id") or "").strip()
                    if not source_document_id:
                        continue
                    if not _reddit_post_relevant(post, aliases):
                        continue
                    if require_cfb_context and not is_probably_cfb_reddit_post(
                        title=str(post.get("title") or ""),
                        body=str(post.get("selftext") or ""),
                        subreddit=str(post.get("subreddit") or subreddit or ""),
                        source_prior=False,
                    ):
                        continue
                    document_rows_by_source_id[source_document_id] = _normalize_reddit_post(
                        post=post,
                        collection_run_id=run_id,
                    )
                    sentiment = score_sentiment(_document_text(post))
                    target_key = f"team:{team.team_id}"
                    target_rows[(source_document_id, target_key, audience_bucket)] = {
                        "source_document_id": source_document_id,
                        "season_year": season,
                        "week": week,
                        "game_id": None,
                        "team_id": team.team_id,
                        "player_id": None,
                        "target_type": "team",
                        "target_key": target_key,
                        "target_label": team.team_name,
                        "affiliation_team_id": None,
                        "audience_bucket": audience_bucket,
                        "mention_role": "query-match",
                        "sentiment_label": sentiment["sentiment_label"],
                        "sentiment_score": sentiment["sentiment_score"],
                        "emotion_primary": sentiment["emotion_primary"],
                        "emotion_secondary": sentiment["emotion_secondary"],
                        "sarcasm_score": sentiment["sarcasm_score"],
                        "toxicity_score": sentiment["toxicity_score"],
                        "confidence_score": sentiment["confidence_score"],
                        "model_provider": "local",
                        "model_name": "vader+lexicon",
                        "model_version": "conversation-v1",
                        "is_primary_target": 1,
                        "notes": f"reddit:{subreddit or 'sitewide'};provider={provider_name}",
                    }

        document_rows = list(document_rows_by_source_id.values())
        if document_rows:
            db.upsert_many(
                "conversation_documents",
                document_rows,
                conflict_columns=["source_name", "source_document_id"],
                update_columns=[
                    "collection_run_id",
                    "source_parent_document_id",
                    "source_author_id",
                    "source_author_name",
                    "source_channel",
                    "source_subchannel",
                    "source_url",
                    "content_type",
                    "language_code",
                    "title_text",
                    "body_text",
                    "external_created_at_utc",
                    "like_count",
                    "reply_count",
                    "repost_count",
                    "view_count",
                    "is_deleted",
                    "is_removed",
                    "raw_payload_json",
                    "raw_text_purged_at_utc",
                    "raw_payload_purged_at_utc",
                    "raw_retention_policy",
                ],
            )

        document_id_lookup = _conversation_document_id_lookup(
            db=db,
            source_name="reddit",
            source_document_ids=[row["source_document_id"] for row in document_rows],
        )
        resolved_target_rows: list[dict[str, Any]] = []
        for row in target_rows.values():
            conversation_document_id = document_id_lookup.get(row["source_document_id"])
            if conversation_document_id is None:
                continue
            resolved_target_rows.append(
                {
                    "conversation_document_id": conversation_document_id,
                    "season_year": row["season_year"],
                    "week": row["week"],
                    "game_id": row["game_id"],
                    "team_id": row["team_id"],
                    "player_id": row["player_id"],
                    "target_type": row["target_type"],
                    "target_key": row["target_key"],
                    "target_label": row["target_label"],
                    "affiliation_team_id": row["affiliation_team_id"],
                    "audience_bucket": row["audience_bucket"],
                    "mention_role": row["mention_role"],
                    "sentiment_label": row["sentiment_label"],
                    "sentiment_score": row["sentiment_score"],
                    "emotion_primary": row["emotion_primary"],
                    "emotion_secondary": row["emotion_secondary"],
                    "sarcasm_score": row["sarcasm_score"],
                    "toxicity_score": row["toxicity_score"],
                    "confidence_score": row["confidence_score"],
                    "model_provider": row["model_provider"],
                    "model_name": row["model_name"],
                    "model_version": row["model_version"],
                    "is_primary_target": row["is_primary_target"],
                    "notes": row["notes"],
                }
            )
        if resolved_target_rows:
            db.upsert_many(
                "conversation_document_targets",
                resolved_target_rows,
                conflict_columns=["conversation_document_id", "target_key", "audience_bucket", "mention_role"],
                update_columns=[
                    "season_year",
                    "week",
                    "game_id",
                    "team_id",
                    "player_id",
                    "target_type",
                    "target_label",
                    "affiliation_team_id",
                    "sentiment_label",
                    "sentiment_score",
                    "emotion_primary",
                    "emotion_secondary",
                    "sarcasm_score",
                    "toxicity_score",
                    "confidence_score",
                    "model_provider",
                    "model_name",
                    "model_version",
                    "is_primary_target",
                    "notes",
                ],
            )

        _finish_collection_run(
            db=db,
            run_id=run_id,
            status="completed",
            item_count=len(document_rows),
            notes=f"targets={len(resolved_target_rows)}",
        )
        return {
            "watchlist_team_count": len(watchlist),
            "document_count": len(document_rows),
            "target_count": len(resolved_target_rows),
        }
    except Exception as exc:
        _finish_collection_run(
            db=db,
            run_id=run_id,
            status="failed",
            item_count=0,
            notes=str(exc),
        )
        raise


_REDDIT_RSS_UA = "windows:cfb-index-rss:v1.0 (by /u/cfbindex)"
_ATOM_NS = "{http://www.w3.org/2005/Atom}"


def _reddit_rss_feed_url(subreddit: str, mode: str | None, flair_filter: str | None, limit: int) -> str:
    """new.rss for dedicated subs; flair-filtered search.rss for school subs.

    School (university) subs carry mostly non-football chatter, so we pull only
    posts whose flair is football/sports — this is what stops the 70%-noise the
    old city/university-sub collection produced.
    """
    from urllib.parse import quote

    sub = subreddit.strip().lstrip("/")
    if sub.lower().startswith("r/"):
        sub = sub[2:]
    if (mode or "") == "school_flair" and (flair_filter or "").strip():
        flairs = [f.strip() for f in flair_filter.split(",") if f.strip()]
        q = " OR ".join(f'flair:"{fl}"' for fl in flairs)
        return (f"https://www.reddit.com/r/{sub}/search.rss?q={quote(q)}"
                f"&restrict_sr=on&sort=new&limit={limit}")
    return f"https://www.reddit.com/r/{sub}/new.rss?limit={limit}"


def _reddit_rss_fetch(url: str, timeout: float = 20.0) -> bytes:
    """Honest, RBP-compliant fetch. NEVER spoof a browser UA (the Responsible
    Builder Policy names spoofing as a violation); a 403 means back off."""
    from urllib.request import Request, urlopen

    req = Request(url, headers={"User-Agent": _REDDIT_RSS_UA,
                                "Accept": "application/atom+xml, application/xml, */*"})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _reddit_rss_entry_to_post(entry: Any, subreddit: str) -> dict[str, Any] | None:
    """Map one Atom <entry> to a reddit-post dict shaped for _normalize_reddit_post."""
    import re as _re
    from html import unescape
    from urllib.parse import urlparse

    def _txt(tag: str) -> str:
        el = entry.find(f"{_ATOM_NS}{tag}")
        return (el.text or "").strip() if (el is not None and el.text) else ""

    href = ""
    link = entry.find(f"{_ATOM_NS}link")
    if link is not None:
        href = link.get("href") or ""
    # base36 post id from the permalink (/r/<sub>/comments/<id>/...) or the <id> tag
    post_id = ""
    m = _re.search(r"/comments/([a-z0-9]+)/", href)
    if m:
        post_id = m.group(1)
    else:
        m2 = _re.search(r"t3_([a-z0-9]+)", _txt("id"))
        post_id = m2.group(1) if m2 else ""
    if not post_id:
        return None
    author = ""
    an = entry.find(f"{_ATOM_NS}author/{_ATOM_NS}name")
    if an is not None and an.text:
        author = an.text.strip()
        if author.startswith("/u/"):
            author = author[3:]
    flair = ""
    cat = entry.find(f"{_ATOM_NS}category")
    if cat is not None:
        flair = cat.get("label") or cat.get("term") or ""
    content = ""
    ce = entry.find(f"{_ATOM_NS}content")
    if ce is not None and ce.text:
        content = _re.sub(r"<[^>]+>", " ", unescape(ce.text))
        content = _re.sub(r"\s+", " ", content).strip()
    created_utc = None
    created_iso = _txt("published") or _txt("updated")
    if created_iso:
        try:
            created_utc = datetime.fromisoformat(created_iso.replace("Z", "+00:00")).timestamp()
        except ValueError:
            created_utc = None
    return {
        "name": f"t3_{post_id}",
        "id": post_id,
        "author": author,
        "author_fullname": "",
        "subreddit": subreddit,
        "permalink": urlparse(href).path if href else "",
        "created_utc": created_utc,
        "title": _txt("title"),
        "selftext": content,
        "ups": None,            # RSS lacks score/comments; nightly encoder +
        "num_comments": None,   # the Arctic Shift listing adapter enrich later
        "link_flair_text": flair,
        "view_count": None,
        "removed_by_category": None,
    }


def collect_reddit_team_subs_rss(
    db: Database,
    repository: Repository,
    season: int,
    week: int,
    *,
    limit: int = 50,
    only_team_ids: list[int] | None = None,
    audience_bucket: str = "fan",
) -> dict[str, int]:
    """Collect each priority team's FOOTBALL subreddit via the .rss path.

    Replaces the dead text-search watchlist for per-team Reddit. Reads
    priority_teams.(reddit_team_sub, reddit_mode, reddit_flair_filter); skips
    rows with reddit_mode='skip' or no sub. Writes conversation_documents +
    a team target per post (sentiment via the existing VADER scorer; the nightly
    encoder upgrades it). Writes a per-team scrape_health beacon so a silently
    broken feed is visible. Idempotent (upsert on source_name+source_document_id).
    """
    import xml.etree.ElementTree as ET

    teams = db.query_all(
        """
        select pt.team_id, t.slug, t.canonical_name,
               pt.reddit_team_sub as sub, pt.reddit_mode as mode,
               pt.reddit_flair_filter as flair
        from priority_teams pt
        join teams t on t.team_id = pt.team_id
        where coalesce(pt.reddit_team_sub, '') <> ''
          and coalesce(pt.reddit_mode, '') <> 'skip'
        order by pt.collection_tier, pt.rank_priority
        """
    )
    if only_team_ids:
        keep = set(only_team_ids)
        teams = [t for t in teams if int(t["team_id"]) in keep]
    if not teams:
        return {"teams": 0, "documents": 0, "targets": 0, "feeds_failed": 0}

    run_id = _create_collection_run(
        db=db, source_name="reddit", collection_scope="team-subreddit-rss",
        target_label=f"{len(teams)} team subs", season=season, week=week,
        raw_config={"provider": "reddit-rss", "limit": limit, "teams": len(teams)},
    )
    import time as _time
    total_docs = total_targets = feeds_failed = 0
    try:
        for _i, tm in enumerate(teams):
            # Gentle pacing: 138 rapid reddit.com .rss fetches in a burst can trip
            # reddit's per-IP rate limit. ~0.4s between feeds keeps the full sweep
            # under a minute of added wall time while staying polite.
            if _i:
                _time.sleep(0.4)
            slug = str(tm["slug"])
            sub = str(tm["sub"])
            url = _reddit_rss_feed_url(sub, tm.get("mode"), tm.get("flair"), limit)
            health_src = f"reddit_rss_{slug}"
            started = _utcnow_iso_z()
            try:
                raw = _reddit_rss_fetch(url)
                entries = ET.fromstring(raw).findall(f".//{_ATOM_NS}entry")
            except Exception as exc:  # noqa: BLE001 — one dead feed must not stop the sweep
                feeds_failed += 1
                _write_reddit_rss_health(db, health_src, 0, "error", f"{type(exc).__name__}: {exc}", started)
                continue

            doc_rows: dict[str, dict[str, Any]] = {}
            tgt_rows: list[dict[str, Any]] = []
            for entry in entries:
                post = _reddit_rss_entry_to_post(entry, sub)
                if not post:
                    continue
                sdid = post["name"]
                doc_rows[sdid] = _normalize_reddit_post(post=post, collection_run_id=run_id)
                sentiment = score_sentiment(_document_text(post))
                tgt_rows.append({
                    "source_document_id": sdid,
                    "team_id": int(tm["team_id"]),
                    "target_label": str(tm["canonical_name"]),
                    "sentiment": sentiment,
                })

            docs = list(doc_rows.values())
            if docs:
                db.upsert_many(
                    "conversation_documents", docs,
                    conflict_columns=["source_name", "source_document_id"],
                    update_columns=[
                        "collection_run_id", "source_parent_document_id", "source_author_id",
                        "source_author_name", "source_channel", "source_subchannel", "source_url",
                        "content_type", "language_code", "title_text", "body_text",
                        "external_created_at_utc", "like_count", "reply_count", "repost_count",
                        "view_count", "is_deleted", "is_removed", "raw_payload_json",
                        "raw_text_purged_at_utc", "raw_payload_purged_at_utc", "raw_retention_policy",
                    ],
                )
            id_lookup = _conversation_document_id_lookup(
                db=db, source_name="reddit",
                source_document_ids=[r["source_document_id"] for r in docs],
            )
            resolved = []
            for tr in tgt_rows:
                cdid = id_lookup.get(tr["source_document_id"])
                if cdid is None:
                    continue
                s = tr["sentiment"]
                resolved.append({
                    "conversation_document_id": cdid,
                    "season_year": season, "week": week, "game_id": None,
                    "team_id": tr["team_id"], "player_id": None,
                    "target_type": "team", "target_key": f"team:{tr['team_id']}",
                    "target_label": tr["target_label"], "affiliation_team_id": tr["team_id"],
                    "audience_bucket": audience_bucket, "mention_role": "team-sub",
                    "sentiment_label": s["sentiment_label"], "sentiment_score": s["sentiment_score"],
                    "emotion_primary": s["emotion_primary"], "emotion_secondary": s["emotion_secondary"],
                    "sarcasm_score": s["sarcasm_score"], "toxicity_score": s["toxicity_score"],
                    "confidence_score": s["confidence_score"],
                    "model_provider": "local", "model_name": "vader+lexicon",
                    "model_version": "conversation-v1", "is_primary_target": 1,
                    "notes": f"reddit-rss:{sub};mode={tm.get('mode') or 'dedicated'}",
                })
            if resolved:
                db.upsert_many(
                    "conversation_document_targets", resolved,
                    conflict_columns=["conversation_document_id", "target_key", "audience_bucket", "mention_role"],
                    update_columns=[
                        "season_year", "week", "game_id", "team_id", "player_id", "target_type",
                        "target_label", "affiliation_team_id", "sentiment_label", "sentiment_score",
                        "emotion_primary", "emotion_secondary", "sarcasm_score", "toxicity_score",
                        "confidence_score", "model_provider", "model_name", "model_version",
                        "is_primary_target", "notes",
                    ],
                )
            total_docs += len(docs)
            total_targets += len(resolved)
            _write_reddit_rss_health(db, health_src, len(docs),
                                     "ok" if docs else "empty", None, started)

        _finish_collection_run(
            db=db, run_id=run_id, status="completed", item_count=total_docs,
            notes=f"teams={len(teams)} targets={total_targets} feeds_failed={feeds_failed}",
        )
    except Exception as exc:
        _finish_collection_run(db=db, run_id=run_id, status="failed", item_count=total_docs, notes=str(exc))
        raise
    return {"teams": len(teams), "documents": total_docs,
            "targets": total_targets, "feeds_failed": feeds_failed}


def _parse_rfc822_or_iso(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    try:  # Atom ISO
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        pass
    try:  # RSS 2.0 RFC-822
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(value)
        if dt is not None:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        pass
    return None


def collect_team_boards_rss(
    db: Database,
    repository: Repository,
    season: int,
    week: int,
    board_seed: list[dict[str, str]],
    *,
    only_team_slugs: list[str] | None = None,
) -> dict[str, int]:
    """Collect independent team message boards via their public RSS (Build #4).

    Each board maps to one team (board_seed: [{team_slug, board_name,
    board_rss_url}]), so every post is tagged to that team directly (fan bucket).
    Captures the SEC/southern + G5 fanbases that live on boards, not Reddit.
    Handles RSS 2.0 (<item>) and Atom (<entry>). Per-board scrape_health beacon.
    """
    import re as _re
    import xml.etree.ElementTree as ET
    from html import unescape
    from urllib.request import Request, urlopen

    slug_to_team = {
        r["slug"]: int(r["team_id"])
        for r in db.query_all(
            "select t.team_id, t.slug from teams t "
            "where t.level_code='FBS' or lower(coalesce(t.cfbd_classification,''))='fbs'"
        )
    }
    seeds = board_seed
    if only_team_slugs:
        keep = set(only_team_slugs)
        seeds = [s for s in seeds if s["team_slug"] in keep]

    run_id = _create_collection_run(
        db=db, source_name="board", collection_scope="team-board-rss",
        target_label=f"{len(seeds)} boards", season=season, week=week,
        raw_config={"boards": len(seeds)},
    )
    total_docs = total_targets = boards_failed = 0
    atom = "{http://www.w3.org/2005/Atom}"
    dc = "{http://purl.org/dc/elements/1.1/}"
    try:
        for s in seeds:
            slug = s["team_slug"]
            team_id = slug_to_team.get(slug)
            board = s["board_name"]
            started = _utcnow_iso_z()
            health_src = f"board_{board.lower()}"
            if team_id is None:
                boards_failed += 1
                _write_reddit_rss_health(db, health_src, 0, "error", f"unknown team_slug {slug}", started)
                continue
            try:
                req = Request(s["board_rss_url"], headers={
                    "User-Agent": _REDDIT_RSS_UA,
                    "Accept": "application/rss+xml, application/atom+xml, application/xml, */*"})
                with urlopen(req, timeout=20) as resp:
                    raw = resp.read()
                root = ET.fromstring(raw)
                items = root.findall(".//item") or root.findall(f".//{atom}entry")
            except Exception as exc:  # noqa: BLE001
                boards_failed += 1
                _write_reddit_rss_health(db, health_src, 0, "error", f"{type(exc).__name__}: {exc}", started)
                continue

            doc_rows: dict[str, dict[str, Any]] = {}
            text_by_id: dict[str, str] = {}
            for it in items:
                def _f(tag: str) -> str:
                    # NB: a leaf Element is falsy in ElementTree (bool = has
                    # children), so never use `find(a) or find(b)` — check None.
                    el = it.find(tag)
                    if el is None:
                        el = it.find(f"{atom}{tag}")
                    return (el.text or "").strip() if (el is not None and el.text) else ""
                title = _f("title")
                link = _f("link")
                if not link:
                    le = it.find(f"{atom}link")
                    if le is not None:
                        link = le.get("href") or ""
                guid = _f("guid") or link
                if not guid:
                    continue
                desc = _f("description") or _f("summary") or _f("content")
                body = _re.sub(r"<[^>]+>", " ", unescape(desc))
                body = _re.sub(r"\s+", " ", body).strip()
                author = _f(f"{dc}creator") or _f("author")
                if not author:
                    ae = it.find(f"{atom}author/{atom}name")
                    author = (ae.text or "").strip() if (ae is not None and ae.text) else ""
                created = _parse_rfc822_or_iso(_f("pubDate") or _f("published") or _f("updated"))
                sdid = f"{board}:{guid}"[:300]
                doc_rows[sdid] = {
                    "collection_run_id": run_id, "source_name": "board",
                    "source_document_id": sdid, "source_parent_document_id": None,
                    "source_author_id": "", "source_author_name": author,
                    "source_channel": "board", "source_subchannel": board,
                    "source_url": link or None, "content_type": "post", "language_code": "en",
                    "title_text": title, "body_text": body or title,
                    "external_created_at_utc": created,
                    "like_count": 0, "reply_count": 0, "repost_count": 0, "view_count": None,
                    "is_deleted": 0, "is_removed": 0,
                    "raw_payload_json": json.dumps({"board": board, "guid": guid}, ensure_ascii=True),
                    "raw_text_purged_at_utc": None, "raw_payload_purged_at_utc": None,
                    "raw_retention_policy": "board_rss_derived_only",
                }
                text_by_id[sdid] = (title + " " + (body or "")).strip()

            docs = list(doc_rows.values())
            if docs:
                db.upsert_many(
                    "conversation_documents", docs,
                    conflict_columns=["source_name", "source_document_id"],
                    update_columns=[
                        "collection_run_id", "source_parent_document_id", "source_author_id",
                        "source_author_name", "source_channel", "source_subchannel", "source_url",
                        "content_type", "language_code", "title_text", "body_text",
                        "external_created_at_utc", "like_count", "reply_count", "repost_count",
                        "view_count", "is_deleted", "is_removed", "raw_payload_json",
                        "raw_text_purged_at_utc", "raw_payload_purged_at_utc", "raw_retention_policy",
                    ],
                )
                id_lookup = _conversation_document_id_lookup(
                    db=db, source_name="board",
                    source_document_ids=[d["source_document_id"] for d in docs])
                targets = []
                for sdid, cdid in id_lookup.items():
                    sent = score_sentiment(text_by_id.get(sdid, ""))
                    targets.append({
                        "conversation_document_id": cdid,
                        "season_year": season, "week": week, "game_id": None,
                        "team_id": team_id, "player_id": None,
                        "target_type": "team", "target_key": f"team:{team_id}",
                        "target_label": "", "affiliation_team_id": team_id,
                        "audience_bucket": "fan", "mention_role": "board",
                        "sentiment_label": sent["sentiment_label"], "sentiment_score": sent["sentiment_score"],
                        "emotion_primary": sent["emotion_primary"], "emotion_secondary": sent["emotion_secondary"],
                        "sarcasm_score": sent["sarcasm_score"], "toxicity_score": sent["toxicity_score"],
                        "confidence_score": sent["confidence_score"],
                        "model_provider": "local", "model_name": "vader+lexicon",
                        "model_version": "conversation-v1", "is_primary_target": 1,
                        "notes": f"board:{board}",
                    })
                if targets:
                    db.upsert_many(
                        "conversation_document_targets", targets,
                        conflict_columns=["conversation_document_id", "target_key", "audience_bucket", "mention_role"],
                        update_columns=[
                            "season_year", "week", "game_id", "team_id", "player_id", "target_type",
                            "target_label", "affiliation_team_id", "sentiment_label", "sentiment_score",
                            "emotion_primary", "emotion_secondary", "sarcasm_score", "toxicity_score",
                            "confidence_score", "model_provider", "model_name", "model_version",
                            "is_primary_target", "notes",
                        ],
                    )
                    total_targets += len(targets)
            total_docs += len(docs)
            _write_reddit_rss_health(db, health_src, len(docs), "ok" if docs else "empty", None, started)

        _finish_collection_run(db=db, run_id=run_id, status="completed", item_count=total_docs,
                               notes=f"boards={len(seeds)} targets={total_targets} failed={boards_failed}")
    except Exception as exc:
        _finish_collection_run(db=db, run_id=run_id, status="failed", item_count=total_docs, notes=str(exc))
        raise
    return {"boards": len(seeds), "documents": total_docs, "targets": total_targets, "boards_failed": boards_failed}


def _write_reddit_rss_health(db: Database, source_id: str, rows: int,
                             status: str, err: str | None, started: str) -> None:
    db.execute(
        """
        insert into scrape_health (source_id, run_date, rows_inserted, status,
            error_message, run_started_at_utc, run_finished_at_utc, adapter_version)
        values (:sid, :rd, :rows, :status, :err, :st, :ft, :ver)
        on conflict (source_id, run_date) do update set
            rows_inserted=excluded.rows_inserted, status=excluded.status,
            error_message=excluded.error_message, run_started_at_utc=excluded.run_started_at_utc,
            run_finished_at_utc=excluded.run_finished_at_utc, adapter_version=excluded.adapter_version
        """,
        {"sid": source_id, "rd": started[:10], "rows": rows, "status": status,
         "err": err, "st": started, "ft": _utcnow_iso_z(), "ver": "reddit-rss-1.0"},
    )


def _utcnow_iso_z() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def collect_reddit_subreddit_listing(
    repository: Repository,
    db: Database,
    client: Any,
    season: int,
    week: int,
    target_team_name: str,
    subreddit: str,
    audience_bucket: str = "fan",
    listing: str = "new",
    limit: int = 25,
    require_cfb_context: bool = True,
    after: int | None = None,
    before: int | None = None,
    provider_name: str = "reddit",
    replace_existing: bool = True,
) -> dict[str, int | str]:
    repository.seed_team_aliases(season)
    team_id = repository.match_team_by_name(target_team_name)
    if team_id is None:
        raise RuntimeError(f"Could not resolve team name for subreddit listing: {target_team_name}")

    team_row = db.query_one(
        """
        select canonical_name
        from teams
        where team_id = %(team_id)s
        """,
        {"team_id": team_id},
    )
    if team_row is None:
        raise RuntimeError(f"Could not load team row for subreddit listing: {target_team_name}")

    canonical_team_name = str(team_row["canonical_name"])
    subreddit_name = subreddit.strip()
    if not subreddit_name:
        raise RuntimeError("Subreddit listing collection requires a non-empty subreddit name.")

    run_id = _create_collection_run(
        db=db,
        source_name="reddit",
        collection_scope="team-subreddit",
        target_label=f"{canonical_team_name} from r/{subreddit_name}",
        season=season,
        week=week,
        raw_config={
            "source": "reddit",
            "provider": provider_name,
            "subreddit": subreddit_name,
            "audience_bucket": audience_bucket,
            "listing": listing,
            "limit": limit,
            "target_team": canonical_team_name,
            "require_cfb_context": require_cfb_context,
            "after": after,
            "before": before,
            "replace_existing": replace_existing,
        },
    )

    document_rows_by_source_id: dict[str, dict[str, Any]] = {}
    target_rows: dict[tuple[str, str, str], dict[str, Any]] = {}
    skipped_non_cfb = 0
    try:
        if replace_existing:
            _delete_existing_reddit_source_prior_targets(
                db=db,
                season=season,
                week=week,
                audience_bucket=audience_bucket,
                subreddit=subreddit_name,
                team_id=team_id,
            )
        for post in client.list_subreddit(subreddit=subreddit_name, listing=listing, limit=limit, after=after, before=before):
            source_document_id = str(post.get("name") or post.get("id") or "").strip()
            if not source_document_id:
                continue
            if require_cfb_context and not is_probably_cfb_reddit_post(
                title=str(post.get("title") or ""),
                body=str(post.get("selftext") or ""),
                subreddit=str(post.get("subreddit") or subreddit_name),
                source_prior=True,
            ):
                skipped_non_cfb += 1
                continue
            document_text = _document_text(post)

            document_rows_by_source_id[source_document_id] = _normalize_reddit_post(
                post=post,
                collection_run_id=run_id,
            )
            sentiment = score_sentiment(document_text)
            target_key = f"team:{team_id}"
            target_rows[(source_document_id, target_key, audience_bucket)] = {
                "source_document_id": source_document_id,
                "season_year": season,
                "week": week,
                "game_id": None,
                "team_id": team_id,
                "player_id": None,
                "target_type": "team",
                "target_key": target_key,
                "target_label": canonical_team_name,
                "affiliation_team_id": team_id if audience_bucket == "fan" else None,
                "audience_bucket": audience_bucket,
                "mention_role": "source-prior",
                "sentiment_label": sentiment["sentiment_label"],
                "sentiment_score": sentiment["sentiment_score"],
                "emotion_primary": sentiment["emotion_primary"],
                "emotion_secondary": sentiment["emotion_secondary"],
                "sarcasm_score": sentiment["sarcasm_score"],
                "toxicity_score": sentiment["toxicity_score"],
                "confidence_score": sentiment["confidence_score"],
                "model_provider": "local",
                "model_name": "vader+lexicon",
                "model_version": "conversation-v1",
                "is_primary_target": 1,
                "notes": f"reddit:{subreddit_name};listing={listing};source_prior=team_subreddit;provider={provider_name}",
            }

        document_rows = list(document_rows_by_source_id.values())
        if document_rows:
            db.upsert_many(
                "conversation_documents",
                document_rows,
                conflict_columns=["source_name", "source_document_id"],
                update_columns=[
                    "collection_run_id",
                    "source_parent_document_id",
                    "source_author_id",
                    "source_author_name",
                    "source_channel",
                    "source_subchannel",
                    "source_url",
                    "content_type",
                    "language_code",
                    "title_text",
                    "body_text",
                    "external_created_at_utc",
                    "like_count",
                    "reply_count",
                    "repost_count",
                    "view_count",
                    "is_deleted",
                    "is_removed",
                    "raw_payload_json",
                    "raw_text_purged_at_utc",
                    "raw_payload_purged_at_utc",
                    "raw_retention_policy",
                ],
            )

        document_id_lookup = _conversation_document_id_lookup(
            db=db,
            source_name="reddit",
            source_document_ids=[row["source_document_id"] for row in document_rows],
        )
        resolved_target_rows: list[dict[str, Any]] = []
        for row in target_rows.values():
            conversation_document_id = document_id_lookup.get(row["source_document_id"])
            if conversation_document_id is None:
                continue
            resolved_target_rows.append(
                {
                    "conversation_document_id": conversation_document_id,
                    "season_year": row["season_year"],
                    "week": row["week"],
                    "game_id": row["game_id"],
                    "team_id": row["team_id"],
                    "player_id": row["player_id"],
                    "target_type": row["target_type"],
                    "target_key": row["target_key"],
                    "target_label": row["target_label"],
                    "affiliation_team_id": row["affiliation_team_id"],
                    "audience_bucket": row["audience_bucket"],
                    "mention_role": row["mention_role"],
                    "sentiment_label": row["sentiment_label"],
                    "sentiment_score": row["sentiment_score"],
                    "emotion_primary": row["emotion_primary"],
                    "emotion_secondary": row["emotion_secondary"],
                    "sarcasm_score": row["sarcasm_score"],
                    "toxicity_score": row["toxicity_score"],
                    "confidence_score": row["confidence_score"],
                    "model_provider": row["model_provider"],
                    "model_name": row["model_name"],
                    "model_version": row["model_version"],
                    "is_primary_target": row["is_primary_target"],
                    "notes": row["notes"],
                }
            )
        if resolved_target_rows:
            db.upsert_many(
                "conversation_document_targets",
                resolved_target_rows,
                conflict_columns=["conversation_document_id", "target_key", "audience_bucket", "mention_role"],
                update_columns=[
                    "season_year",
                    "week",
                    "game_id",
                    "team_id",
                    "player_id",
                    "target_type",
                    "target_label",
                    "affiliation_team_id",
                    "sentiment_label",
                    "sentiment_score",
                    "emotion_primary",
                    "emotion_secondary",
                    "sarcasm_score",
                    "toxicity_score",
                    "confidence_score",
                    "model_provider",
                    "model_name",
                    "model_version",
                    "is_primary_target",
                    "notes",
                ],
            )

        _finish_collection_run(
            db=db,
            run_id=run_id,
            status="completed",
            item_count=len(document_rows),
            notes=f"targets={len(resolved_target_rows)};skipped_non_cfb={skipped_non_cfb}",
        )
        return {
            "team_name": canonical_team_name,
            "subreddit": subreddit_name,
            "document_count": len(document_rows),
            "target_count": len(resolved_target_rows),
            "skipped_non_cfb": skipped_non_cfb,
        }
    except Exception as exc:
        _finish_collection_run(
            db=db,
            run_id=run_id,
            status="failed",
            item_count=0,
            notes=str(exc),
        )
        raise


def collect_reddit_comments_for_posts(
    db: Database,
    client: Any,
    season: int,
    week: int,
    source_name: str = "reddit",
    provider_name: str = "arctic_shift",
    subreddits: list[str] | None = None,
    limit_posts: int = 100,
    comments_per_post: int = 100,
    min_post_comments: int = 5,
    min_post_score: int = 0,
    replace_existing: bool = True,
) -> dict[str, int]:
    """Collect comments under already-targeted Reddit posts.

    Single-team threads inherit the parent post target. Multi-team threads only
    target comments with direct team-alias or author-flair evidence, which keeps
    generic replies from becoming false directional fanbase signal.
    """

    if not hasattr(client, "list_post_comments"):
        raise RuntimeError(f"Client {client.__class__.__name__} does not support Reddit comment collection.")

    subreddit_filter = sorted({sub.strip() for sub in subreddits or [] if sub.strip()})
    run_id = _create_collection_run(
        db=db,
        source_name=source_name,
        collection_scope="reddit-comment-thread",
        target_label=f"{season} week {week} comments",
        season=season,
        week=week,
        raw_config={
            "source": source_name,
            "provider": provider_name,
            "subreddits": subreddit_filter,
            "limit_posts": limit_posts,
            "comments_per_post": comments_per_post,
            "min_post_comments": min_post_comments,
            "min_post_score": min_post_score,
            "replace_existing": replace_existing,
        },
    )

    try:
        if replace_existing:
            _delete_existing_reddit_comment_thread_targets(
                db=db,
                season=season,
                week=week,
                source_name=source_name,
                subreddits=subreddit_filter,
            )

        parent_posts = _candidate_posts_for_comment_collection(
            db=db,
            season=season,
            week=week,
            source_name=source_name,
            subreddits=subreddit_filter,
            limit_posts=limit_posts,
            min_post_comments=min_post_comments,
            min_post_score=min_post_score,
        )
        document_rows_by_source_id: dict[str, dict[str, Any]] = {}
        target_rows: dict[tuple[str, str, str], dict[str, Any]] = {}
        skipped_empty = 0
        skipped_no_target = 0
        parent_team_ids = {
            int(target["team_id"])
            for parent in parent_posts
            for target in parent["targets"]
            if target.get("team_id") is not None
        }
        aliases_by_team = _load_comment_target_aliases(db, season=season, team_ids=parent_team_ids)

        for parent in parent_posts:
            post_id = _reddit_base36_id(str(parent["source_document_id"]))
            if not post_id:
                continue
            parent_targets = parent["targets"]
            for comment in client.list_post_comments(post_id=post_id, limit=comments_per_post):
                source_document_id = str(comment.get("name") or comment.get("id") or "").strip()
                if not source_document_id:
                    continue
                body_text = str(comment.get("body") or "").strip()
                if not body_text or _is_deleted_reddit_text(body_text):
                    skipped_empty += 1
                    continue
                document_rows_by_source_id[source_document_id] = _normalize_reddit_comment(
                    comment=comment,
                    collection_run_id=run_id,
                    source_name=source_name,
                    parent_source_document_id=str(parent["source_document_id"]),
                    parent_post_id=post_id,
                )
                sentiment = score_sentiment(body_text)
                resolved_targets = _comment_targets_for_parent(
                    comment=comment,
                    parent_targets=parent_targets,
                    aliases_by_team=aliases_by_team,
                )
                if not resolved_targets:
                    skipped_no_target += 1
                    continue
                for target, attribution_reason in resolved_targets:
                    target_key = str(target["target_key"])
                    audience_bucket = str(target["audience_bucket"])
                    target_rows[(source_document_id, target_key, audience_bucket)] = {
                        "source_document_id": source_document_id,
                        "season_year": season,
                        "week": week,
                        "game_id": target.get("game_id"),
                        "team_id": target.get("team_id"),
                        "player_id": target.get("player_id"),
                        "target_type": target.get("target_type") or "team",
                        "target_key": target_key,
                        "target_label": target.get("target_label"),
                        "affiliation_team_id": target.get("affiliation_team_id"),
                        "audience_bucket": audience_bucket,
                        "mention_role": "comment-thread",
                        "sentiment_label": sentiment["sentiment_label"],
                        "sentiment_score": sentiment["sentiment_score"],
                        "emotion_primary": sentiment["emotion_primary"],
                        "emotion_secondary": sentiment["emotion_secondary"],
                        "sarcasm_score": sentiment["sarcasm_score"],
                        "toxicity_score": sentiment["toxicity_score"],
                        "confidence_score": sentiment["confidence_score"],
                        "model_provider": "local",
                        "model_name": "vader+lexicon",
                        "model_version": "conversation-v1",
                        "is_primary_target": 0,
                        "notes": (
                            f"reddit:{comment.get('subreddit') or parent.get('source_subchannel')};"
                            f"comment_thread={parent['source_document_id']};provider={provider_name};"
                            f"attribution={attribution_reason}"
                        ),
                    }

        document_rows = list(document_rows_by_source_id.values())
        if document_rows:
            db.upsert_many(
                "conversation_documents",
                document_rows,
                conflict_columns=["source_name", "source_document_id"],
                update_columns=[
                    "collection_run_id",
                    "source_parent_document_id",
                    "source_author_id",
                    "source_author_name",
                    "source_channel",
                    "source_subchannel",
                    "source_url",
                    "content_type",
                    "language_code",
                    "title_text",
                    "body_text",
                    "external_created_at_utc",
                    "like_count",
                    "reply_count",
                    "repost_count",
                    "view_count",
                    "is_deleted",
                    "is_removed",
                    "raw_payload_json",
                    "raw_text_purged_at_utc",
                    "raw_payload_purged_at_utc",
                    "raw_retention_policy",
                ],
            )

        document_id_lookup = _conversation_document_id_lookup(
            db=db,
            source_name=source_name,
            source_document_ids=[row["source_document_id"] for row in document_rows],
        )
        resolved_target_rows: list[dict[str, Any]] = []
        for row in target_rows.values():
            conversation_document_id = document_id_lookup.get(row["source_document_id"])
            if conversation_document_id is None:
                continue
            resolved_target_rows.append(
                {
                    "conversation_document_id": conversation_document_id,
                    "season_year": row["season_year"],
                    "week": row["week"],
                    "game_id": row["game_id"],
                    "team_id": row["team_id"],
                    "player_id": row["player_id"],
                    "target_type": row["target_type"],
                    "target_key": row["target_key"],
                    "target_label": row["target_label"],
                    "affiliation_team_id": row["affiliation_team_id"],
                    "audience_bucket": row["audience_bucket"],
                    "mention_role": row["mention_role"],
                    "sentiment_label": row["sentiment_label"],
                    "sentiment_score": row["sentiment_score"],
                    "emotion_primary": row["emotion_primary"],
                    "emotion_secondary": row["emotion_secondary"],
                    "sarcasm_score": row["sarcasm_score"],
                    "toxicity_score": row["toxicity_score"],
                    "confidence_score": row["confidence_score"],
                    "model_provider": row["model_provider"],
                    "model_name": row["model_name"],
                    "model_version": row["model_version"],
                    "is_primary_target": row["is_primary_target"],
                    "notes": row["notes"],
                }
            )
        if resolved_target_rows:
            db.upsert_many(
                "conversation_document_targets",
                resolved_target_rows,
                conflict_columns=["conversation_document_id", "target_key", "audience_bucket", "mention_role"],
                update_columns=[
                    "season_year",
                    "week",
                    "game_id",
                    "team_id",
                    "player_id",
                    "target_type",
                    "target_label",
                    "affiliation_team_id",
                    "sentiment_label",
                    "sentiment_score",
                    "emotion_primary",
                    "emotion_secondary",
                    "sarcasm_score",
                    "toxicity_score",
                    "confidence_score",
                    "model_provider",
                    "model_name",
                    "model_version",
                    "is_primary_target",
                    "notes",
                ],
            )

        _finish_collection_run(
            db=db,
            run_id=run_id,
            status="completed",
            item_count=len(document_rows),
            notes=(
                f"posts={len(parent_posts)};targets={len(resolved_target_rows)};"
                f"skipped_empty={skipped_empty};skipped_no_target={skipped_no_target}"
            ),
        )
        return {
            "post_count": len(parent_posts),
            "document_count": len(document_rows),
            "target_count": len(resolved_target_rows),
            "skipped_empty": skipped_empty,
            "skipped_no_target": skipped_no_target,
        }
    except Exception as exc:
        _finish_collection_run(
            db=db,
            run_id=run_id,
            status="failed",
            item_count=0,
            notes=str(exc),
        )
        raise


def purge_reddit_raw_content(
    db: Database,
    source_name: str = "reddit",
    provider_name: str | None = None,
    older_than_days: int = 2,
    cutoff_utc: str | None = None,
    dry_run: bool = False,
    require_weekly_features: bool = True,
) -> dict[str, int | str | bool]:
    cutoff = cutoff_utc or (datetime.now(UTC) - timedelta(days=older_than_days)).strftime("%Y-%m-%d %H:%M:%S")
    candidate_rows = _raw_content_purge_candidates(
        db=db,
        source_name=source_name,
        provider_name=provider_name,
        cutoff_utc=cutoff,
        require_weekly_features=require_weekly_features,
    )
    candidate_ids = [int(row["conversation_document_id"]) for row in candidate_rows]
    if not dry_run:
        for chunk in _chunks(candidate_ids, 400):
            placeholders = ", ".join(f":doc_{index}" for index in range(len(chunk)))
            params = {f"doc_{index}": doc_id for index, doc_id in enumerate(chunk)}
            db.execute(
                f"""
                update conversation_documents
                set title_text = '',
                    body_text = '',
                    source_author_id = '',
                    source_author_name = '',
                    raw_payload_json = null,
                    raw_text_purged_at_utc = current_timestamp,
                    raw_payload_purged_at_utc = current_timestamp,
                    raw_retention_policy = coalesce(raw_retention_policy, 'reddit_48h_after_feature_build')
                where conversation_document_id in ({placeholders})
                """,
                params,
            )
    db.execute(
        """
        insert into conversation_raw_retention_audit (
          source_name,
          provider_name,
          cutoff_utc,
          documents_examined,
          documents_purged,
          dry_run,
          notes
        )
        values (
          %(source_name)s,
          %(provider_name)s,
          %(cutoff_utc)s,
          %(documents_examined)s,
          %(documents_purged)s,
          %(dry_run)s,
          %(notes)s
        )
        """,
        {
            "source_name": source_name,
            "provider_name": provider_name,
            "cutoff_utc": cutoff,
            "documents_examined": len(candidate_rows),
            "documents_purged": 0 if dry_run else len(candidate_ids),
            "dry_run": 1 if dry_run else 0,
            "notes": "require_weekly_features=1" if require_weekly_features else "require_weekly_features=0",
        },
    )
    return {
        "cutoff_utc": cutoff,
        "documents_examined": len(candidate_rows),
        "documents_purged": 0 if dry_run else len(candidate_ids),
        "dry_run": dry_run,
    }


# Off-topic source blocklist (RELEVANCE FIX 2026-06-09, see task #6 + deep-research
# wf_c9853ea4-434). Hand-labeling showed ~74% of team-tagged Reddit comments were
# off-topic; the noise is structurally concentrated in CITY and UNIVERSITY subreddits
# (local/campus life: "the Chipotle closed", "got my Kroger delivery") that get tagged
# to a team only via city/school name. Football subreddits are mostly on-topic. We use a
# BLOCKLIST (not an allowlist) so this can NEVER drop genuine football talk -- the
# research's key requirement (zero false-negative risk). Expand as new city/campus subs
# appear; the durable follow-up is a SetFit relevance classifier on the off-topic labels.
OFFTOPIC_SUBREDDITS = (
    "Eugene", "AnnArbor", "PennStateUniversity", "Columbus", "Tallahassee",
    "statecollege", "Knoxville", "Austin", "Athens", "batonrouge", "tuscaloosa",
)


def build_conversation_features(
    db: Database,
    season: int,
    week: int,
    source_name: str = "reddit",
    pregame_days: int = 7,
    postgame_hours: int = 48,
) -> dict[str, int]:
    _blocklist_sql = ", ".join("'" + s.replace("'", "''") + "'" for s in OFFTOPIC_SUBREDDITS)
    rows = db.query_all(
        f"""
        select
          cdt.team_id,
          cdt.conversation_document_id,
          cdt.audience_bucket,
          cd.source_name,
          cd.source_subchannel,
          coalesce(cd.source_author_id, cd.source_author_name, cd.source_document_id) as author_key,
          cd.source_url,
          cd.title_text,
          cd.body_text,
          cd.external_created_at_utc,
          cdt.sentiment_label,
          cdt.sentiment_score,
          cdt.emotion_primary,
          cdt.emotion_secondary,
          cdt.sarcasm_score,
          cdt.confidence_score
        from conversation_document_targets cdt
        join conversation_documents cd on cd.conversation_document_id = cdt.conversation_document_id
        where cdt.season_year = %(season)s
          and cdt.week = %(week)s
          and cdt.target_type = 'team'
          and cd.source_name = %(source_name)s
          and coalesce(cd.source_subchannel, '') not in ({_blocklist_sql})
        """,
        {"season": season, "week": week, "source_name": source_name},
    )
    if not rows:
        return {"daily_rows": 0, "weekly_rows": 0, "rival_mention_rows": 0, "game_rows": 0, "storyline_rows": 0}

    db.execute(
        """
        delete from team_conversation_daily
        where season_year = %(season)s
          and week = %(week)s
          and source_name = %(source_name)s
        """,
        {"season": season, "week": week, "source_name": source_name},
    )
    db.execute(
        """
        delete from team_week_conversation_features
        where season_year = %(season)s
          and week = %(week)s
          and source_name = %(source_name)s
        """,
        {"season": season, "week": week, "source_name": source_name},
    )
    db.execute(
        """
        delete from team_game_conversation_features
        where season_year = %(season)s
          and week = %(week)s
          and source_name = %(source_name)s
        """,
        {"season": season, "week": week, "source_name": source_name},
    )
    db.execute(
        """
        delete from conversation_storylines
        where season_year = %(season)s
          and week = %(week)s
          and source_name = %(source_name)s
        """,
        {"season": season, "week": week, "source_name": source_name},
    )
    db.execute(
        """
        delete from team_week_rival_mentions
        where season_year = %(season)s
          and week = %(week)s
          and source_name = %(source_name)s
        """,
        {"season": season, "week": week, "source_name": source_name},
    )

    parsed_rows = [_parsed_conversation_row(row) for row in rows]

    daily_rows = _build_daily_rows(parsed_rows, season=season, week=week)
    if daily_rows:
        db.upsert_many(
            "team_conversation_daily",
            daily_rows,
            conflict_columns=["team_id", "as_of_date", "source_name", "audience_bucket"],
            update_columns=[column for column in daily_rows[0].keys() if column not in {"team_id", "as_of_date", "source_name", "audience_bucket"}],
        )

    weekly_rows, weekly_storyline_rows = _build_weekly_rows(parsed_rows, season=season, week=week, source_name=source_name)
    if weekly_rows:
        db.upsert_many(
            "team_week_conversation_features",
            weekly_rows,
            conflict_columns=["season_year", "week", "team_id", "source_name", "audience_bucket"],
            update_columns=[column for column in weekly_rows[0].keys() if column not in {"season_year", "week", "team_id", "source_name", "audience_bucket"}],
        )

    rival_rows = _build_rival_mention_rows(db, parsed_rows, season=season, week=week, source_name=source_name)
    if rival_rows:
        db.upsert_many(
            "team_week_rival_mentions",
            rival_rows,
            conflict_columns=["team_id", "rival_team_id", "season_year", "week", "source_name", "audience_bucket"],
            update_columns=[
                column
                for column in rival_rows[0].keys()
                if column not in {"team_id", "rival_team_id", "season_year", "week", "source_name", "audience_bucket"}
            ],
        )

    game_rows, game_storyline_rows = _build_game_rows(
        db=db,
        rows=parsed_rows,
        season=season,
        week=week,
        source_name=source_name,
        pregame_days=pregame_days,
        postgame_hours=postgame_hours,
    )
    if game_rows:
        db.upsert_many(
            "team_game_conversation_features",
            game_rows,
            conflict_columns=["game_id", "team_id", "source_name", "audience_bucket", "window_label"],
            update_columns=[column for column in game_rows[0].keys() if column not in {"game_id", "team_id", "source_name", "audience_bucket", "window_label"}],
        )

    storyline_rows = weekly_storyline_rows + game_storyline_rows
    if storyline_rows:
        db.upsert_many(
            "conversation_storylines",
            storyline_rows,
            conflict_columns=["season_year", "week", "game_id", "team_id", "source_name", "audience_bucket", "window_label", "storyline_rank"],
            update_columns=[column for column in storyline_rows[0].keys() if column not in {"season_year", "week", "game_id", "team_id", "source_name", "audience_bucket", "window_label", "storyline_rank"}],
        )

    return {
        "daily_rows": len(daily_rows),
        "weekly_rows": len(weekly_rows),
        "rival_mention_rows": len(rival_rows),
        "game_rows": len(game_rows),
        "storyline_rows": len(storyline_rows),
    }


def build_phrase_mentions_weekly(
    db: Database,
    season: int,
    week: int,
    source_name: str = "reddit",
    phrases: list[str] | None = None,
) -> dict[str, int]:
    """Populate tracked phrase counts for the lexicon spike compute path."""

    tracked_phrases = phrases or _load_tracked_lexicon_phrases(db, season)
    if not tracked_phrases:
        return {"phrase_rows": 0}

    db.execute(
        """
        delete from phrase_mentions_weekly
        where season_year = %(season)s
          and week = %(week)s
          and source_name = %(source_name)s
        """,
        {"season": season, "week": week, "source_name": source_name},
    )

    rows = db.query_all(
        """
        select
          cdt.conversation_document_id,
          cdt.audience_bucket,
          cd.title_text,
          cd.body_text,
          cd.source_url
        from conversation_document_targets cdt
        join conversation_documents cd on cd.conversation_document_id = cdt.conversation_document_id
        where cdt.season_year = %(season)s
          and cdt.week = %(week)s
          and cdt.target_type = 'team'
          and cd.source_name = %(source_name)s
        """,
        {"season": season, "week": week, "source_name": source_name},
    )
    if not rows:
        return {"phrase_rows": 0}

    normalized_phrases = [
        (phrase, normalize_lookup_text(phrase))
        for phrase in tracked_phrases
        if normalize_lookup_text(phrase)
    ]
    doc_sets: dict[tuple[str, str], set[int]] = defaultdict(set)
    mention_counts: dict[tuple[str, str], int] = defaultdict(int)
    sample_quotes: dict[tuple[str, str], list[str]] = defaultdict(list)
    seen_targets: set[tuple[str, str, int]] = set()

    for row in rows:
        document_id = int(row["conversation_document_id"])
        audience_bucket = str(row.get("audience_bucket") or "unknown")
        raw_text = " ".join(part for part in [str(row.get("title_text") or ""), str(row.get("body_text") or "")] if part.strip())
        normalized_text = f" {normalize_lookup_text(raw_text)} "
        if not normalized_text.strip():
            continue
        for phrase, normalized_phrase in normalized_phrases:
            if f" {normalized_phrase} " not in normalized_text:
                continue
            target_key = (phrase, audience_bucket)
            dedupe_key = (phrase, audience_bucket, document_id)
            if dedupe_key in seen_targets:
                continue
            seen_targets.add(dedupe_key)
            doc_sets[target_key].add(document_id)
            mention_counts[target_key] += max(1, normalized_text.count(f" {normalized_phrase} "))
            if len(sample_quotes[target_key]) < 3:
                sample_quotes[target_key].append(_sample_quote(raw_text))

    output_rows: list[dict[str, Any]] = []
    for (phrase, audience_bucket), docs in doc_sets.items():
        output_rows.append(
            {
                "phrase": phrase,
                "season_year": season,
                "week": week,
                "mention_count": int(mention_counts[(phrase, audience_bucket)]),
                "document_count": len(docs),
                "source_name": source_name,
                "audience_bucket": audience_bucket,
                "sample_quotes_json": json.dumps(sample_quotes[(phrase, audience_bucket)], ensure_ascii=True),
            }
        )
    if output_rows:
        db.upsert_many(
            "phrase_mentions_weekly",
            output_rows,
            conflict_columns=["phrase", "season_year", "week", "source_name", "audience_bucket"],
            update_columns=["mention_count", "document_count", "sample_quotes_json", "ingested_at"],
        )
    return {"phrase_rows": len(output_rows)}


def _load_tracked_lexicon_phrases(db: Database, season: int) -> list[str]:
    rows = db.query_all(
        """
        select distinct lw.phrase
        from lexicon_weekly lw
        join offseason_week_map owm on owm.week_start_date = lw.week_start_date
        where owm.season_year = %(season)s
        order by lw.phrase
        """,
        {"season": season},
    )
    return [str(row["phrase"]) for row in rows if str(row.get("phrase") or "").strip()]


def _sample_quote(text: str) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= 220:
        return cleaned
    return f"{cleaned[:217].rstrip()}..."


def _build_watchlist(
    repository: Repository,
    db: Database,
    season: int,
    week: int,
    team_names: list[str],
    limit_teams: int,
) -> list[WatchlistTeam]:
    if team_names:
        team_ids: list[int] = []
        for team_name in team_names:
            team_id = repository.match_team_by_name(team_name)
            if team_id is None:
                raise RuntimeError(f"Could not resolve team name for watchlist: {team_name}")
            team_ids.append(team_id)
    else:
        rows = db.query_all(
            """
            with latest_model_run as (
              select mr.model_run_id
              from model_runs mr
              where mr.season_year = %(season)s
                and exists (
                  select 1
                  from power_ratings_weekly pr
                  where pr.model_run_id = mr.model_run_id
                )
              order by mr.week desc, mr.model_run_id desc
              limit 1
            ),
            latest_team_power as (
              select pr.model_run_id, pr.team_id, pr.power_rating
              from power_ratings_weekly pr
              join (
                select model_run_id, team_id, max(week) as max_week
                from power_ratings_weekly
                group by model_run_id, team_id
              ) latest
                on latest.model_run_id = pr.model_run_id
               and latest.team_id = pr.team_id
               and latest.max_week = pr.week
            ),
            week_teams as (
              select home_team_id as team_id
              from games
              where season_year = %(season)s
                and week = %(week)s
              union
              select away_team_id as team_id
              from games
              where season_year = %(season)s
                and week = %(week)s
            )
            select t.team_id, t.canonical_name, coalesce(pr.power_rating, -999.0) as power_rating
            from week_teams wt
            join teams t on t.team_id = wt.team_id
            left join latest_model_run lmr on 1 = 1
            left join latest_team_power pr
              on pr.model_run_id = lmr.model_run_id
             and pr.team_id = t.team_id
            order by pr.power_rating desc, t.canonical_name
            limit %(limit)s
            """,
            {"season": season, "week": week, "limit": limit_teams},
        )
        if not rows:
            rows = db.query_all(
                """
                with latest_model_run as (
                  select mr.model_run_id
                  from model_runs mr
                  where mr.season_year = %(season)s
                    and exists (
                      select 1
                      from power_ratings_weekly pr
                      where pr.model_run_id = mr.model_run_id
                    )
                  order by mr.week desc, mr.model_run_id desc
                  limit 1
                ),
                latest_team_power as (
                  select pr.model_run_id, pr.team_id, pr.power_rating
                  from power_ratings_weekly pr
                  join (
                    select model_run_id, team_id, max(week) as max_week
                    from power_ratings_weekly
                    group by model_run_id, team_id
                  ) latest
                    on latest.model_run_id = pr.model_run_id
                   and latest.team_id = pr.team_id
                   and latest.max_week = pr.week
                )
                select t.team_id, t.canonical_name, pr.power_rating
                from latest_team_power pr
                join latest_model_run lmr on lmr.model_run_id = pr.model_run_id
                join teams t on t.team_id = pr.team_id
                order by pr.power_rating desc, t.canonical_name
                limit %(limit)s
                """,
                {"season": season, "limit": limit_teams},
            )
        team_ids = [int(row["team_id"]) for row in rows]

    watchlist: list[WatchlistTeam] = []
    for team_id in team_ids:
        team_row = db.query_one(
            """
            select canonical_name
            from teams
            where team_id = %(team_id)s
            """,
            {"team_id": team_id},
        )
        if team_row is None:
            continue
        aliases = repository.team_aliases_for_season(season_year=season, team_id=team_id)
        watchlist.append(
            WatchlistTeam(
                team_id=team_id,
                team_name=str(team_row["canonical_name"]),
                aliases=aliases,
            )
        )
    return watchlist


def _preferred_aliases(aliases: list[str], team_name: str) -> list[str]:
    preferred: list[str] = []
    seen: set[str] = set()
    for alias in [team_name] + aliases:
        normalized = normalize_lookup_text(alias)
        if not normalized or normalized in seen:
            continue
        if " " not in normalized and len(normalized) < 6 and normalized != normalize_lookup_text(team_name):
            continue
        seen.add(normalized)
        preferred.append(alias)
        if len(preferred) >= 3:
            break
    return preferred


def _reddit_query(alias: str, subreddit: str | None) -> str:
    cleaned = alias.strip()
    if subreddit:
        return f"\"{cleaned}\""
    return f"\"{cleaned}\" football"


def _reddit_post_relevant(post: dict[str, Any], aliases: list[str]) -> bool:
    text = normalize_lookup_text(_document_text(post))
    if not text:
        return False
    padded_text = f" {text} "
    for alias in aliases:
        normalized = normalize_lookup_text(alias)
        if not normalized:
            continue
        if f" {normalized} " in padded_text:
            return True
    return False


def _document_text(post: dict[str, Any]) -> str:
    title = str(post.get("title") or "").strip()
    body = str(post.get("selftext") or "").strip()
    return " ".join(part for part in [title, body] if part)


def _normalize_reddit_post(post: dict[str, Any], collection_run_id: int) -> dict[str, Any]:
    created_at = _timestamp_to_iso(post.get("created_utc"))
    permalink = str(post.get("permalink") or "").strip()
    return {
        "collection_run_id": collection_run_id,
        "source_name": "reddit",
        "source_document_id": str(post.get("name") or post.get("id") or ""),
        "source_parent_document_id": None,
        "source_author_id": str(post.get("author_fullname") or ""),
        "source_author_name": str(post.get("author") or ""),
        "source_channel": "reddit",
        "source_subchannel": str(post.get("subreddit") or ""),
        "source_url": f"https://www.reddit.com{permalink}" if permalink else None,
        "content_type": "post",
        "language_code": "en",
        "title_text": str(post.get("title") or ""),
        "body_text": str(post.get("selftext") or ""),
        "external_created_at_utc": created_at,
        "like_count": int(post.get("ups") or 0),
        "reply_count": int(post.get("num_comments") or 0),
        "repost_count": 0,
        "view_count": int(post.get("view_count") or 0) if post.get("view_count") else None,
        "is_deleted": 1 if str(post.get("removed_by_category") or "") in {"deleted"} else 0,
        "is_removed": 1 if post.get("removed_by_category") else 0,
        "raw_payload_json": json.dumps(post, ensure_ascii=True),
        "raw_text_purged_at_utc": None,
        "raw_payload_purged_at_utc": None,
        "raw_retention_policy": "reddit_48h_after_feature_build",
    }


def _normalize_reddit_comment(
    comment: dict[str, Any],
    collection_run_id: int,
    source_name: str,
    parent_source_document_id: str,
    parent_post_id: str,
) -> dict[str, Any]:
    created_at = _timestamp_to_iso(comment.get("created_utc"))
    permalink = str(comment.get("permalink") or "").strip()
    if not permalink:
        comment_id = _reddit_base36_id(str(comment.get("name") or comment.get("id") or ""))
        subreddit = str(comment.get("subreddit") or "").strip()
        if subreddit and parent_post_id and comment_id:
            permalink = f"/r/{subreddit}/comments/{parent_post_id}/_/{comment_id}/"
    return {
        "collection_run_id": collection_run_id,
        "source_name": source_name,
        "source_document_id": str(comment.get("name") or comment.get("id") or ""),
        "source_parent_document_id": parent_source_document_id,
        "source_author_id": str(comment.get("author_fullname") or ""),
        "source_author_name": str(comment.get("author") or ""),
        "source_channel": "reddit",
        "source_subchannel": str(comment.get("subreddit") or ""),
        "source_url": f"https://www.reddit.com{permalink}" if permalink else None,
        "content_type": "comment",
        "language_code": "en",
        "title_text": "",
        "body_text": str(comment.get("body") or ""),
        "external_created_at_utc": created_at,
        "like_count": int(comment.get("ups") or 0),
        "reply_count": 0,
        "repost_count": 0,
        "view_count": None,
        "is_deleted": 1 if _is_deleted_reddit_text(str(comment.get("body") or "")) else 0,
        "is_removed": 1 if comment.get("removed_by_category") else 0,
        "raw_payload_json": json.dumps(comment, ensure_ascii=True),
        "raw_text_purged_at_utc": None,
        "raw_payload_purged_at_utc": None,
        "raw_retention_policy": "reddit_48h_after_feature_build",
    }


def _create_collection_run(
    db: Database,
    source_name: str,
    collection_scope: str,
    target_label: str,
    season: int,
    week: int,
    raw_config: dict[str, Any],
) -> int:
    row = db.query_one(
        """
        insert into conversation_collection_runs (
          source_name,
          collection_scope,
          target_label,
          season_year,
          week,
          status,
          raw_config_json
        )
        values (
          %(source_name)s,
          %(collection_scope)s,
          %(target_label)s,
          %(season)s,
          %(week)s,
          'running',
          %(raw_config_json)s
        )
        returning conversation_collection_run_id
        """,
        {
            "source_name": source_name,
            "collection_scope": collection_scope,
            "target_label": target_label,
            "season": season,
            "week": week,
            "raw_config_json": json.dumps(raw_config, ensure_ascii=True),
        },
    )
    if row is None:
        raise RuntimeError("Failed to create conversation collection run")
    return int(row["conversation_collection_run_id"])


def _finish_collection_run(
    db: Database,
    run_id: int,
    status: str,
    item_count: int,
    notes: str,
) -> None:
    db.execute(
        """
        update conversation_collection_runs
        set status = %(status)s,
            item_count = %(item_count)s,
            notes = %(notes)s,
            finished_at_utc = CURRENT_TIMESTAMP
        where conversation_collection_run_id = %(run_id)s
        """,
        {"run_id": run_id, "status": status, "item_count": item_count, "notes": notes},
    )


def _delete_existing_reddit_query_match_targets(
    db: Database,
    season: int,
    week: int,
    audience_bucket: str,
    subreddit: str | None,
    team_ids: list[int],
) -> None:
    if not team_ids:
        return
    placeholders = ", ".join(f":team_id_{index}" for index in range(len(team_ids)))
    params: dict[str, Any] = {
        "season": season,
        "week": week,
        "audience_bucket": audience_bucket,
    }
    params.update({f"team_id_{index}": team_id for index, team_id in enumerate(team_ids)})

    subreddit_filter = ""
    if subreddit:
        params["subreddit"] = subreddit
        subreddit_filter = "and coalesce(cd.source_subchannel, '') = :subreddit"

    db.execute(
        f"""
        delete from conversation_document_targets
        where conversation_document_target_id in (
          select cdt.conversation_document_target_id
          from conversation_document_targets cdt
          join conversation_documents cd on cd.conversation_document_id = cdt.conversation_document_id
          where cdt.season_year = :season
            and cdt.week = :week
            and cdt.audience_bucket = :audience_bucket
            and cdt.mention_role = 'query-match'
            and cdt.team_id in ({placeholders})
            and cd.source_name = 'reddit'
            {subreddit_filter}
        )
        """,
        params,
    )


def _delete_existing_reddit_source_prior_targets(
    db: Database,
    season: int,
    week: int,
    audience_bucket: str,
    subreddit: str,
    team_id: int,
) -> None:
    db.execute(
        """
        delete from conversation_document_targets
        where conversation_document_target_id in (
          select cdt.conversation_document_target_id
          from conversation_document_targets cdt
          join conversation_documents cd on cd.conversation_document_id = cdt.conversation_document_id
          where cdt.season_year = %(season)s
            and cdt.week = %(week)s
            and cdt.audience_bucket = %(audience_bucket)s
            and cdt.mention_role = 'source-prior'
            and cdt.team_id = %(team_id)s
            and cd.source_name = 'reddit'
            and coalesce(cd.source_subchannel, '') = %(subreddit)s
        )
        """,
        {
            "season": season,
            "week": week,
            "audience_bucket": audience_bucket,
            "team_id": team_id,
            "subreddit": subreddit,
        },
    )


def _delete_existing_reddit_comment_thread_targets(
    db: Database,
    season: int,
    week: int,
    source_name: str,
    subreddits: list[str],
) -> None:
    params: dict[str, Any] = {
        "season": season,
        "week": week,
        "source_name": source_name,
    }
    subreddit_filter = ""
    if subreddits:
        placeholders = ", ".join(f":subreddit_{index}" for index in range(len(subreddits)))
        params.update({f"subreddit_{index}": subreddit for index, subreddit in enumerate(subreddits)})
        subreddit_filter = f"and coalesce(cd.source_subchannel, '') in ({placeholders})"
    db.execute(
        f"""
        delete from conversation_document_targets
        where conversation_document_target_id in (
          select cdt.conversation_document_target_id
          from conversation_document_targets cdt
          join conversation_documents cd on cd.conversation_document_id = cdt.conversation_document_id
          where cdt.season_year = :season
            and cdt.week = :week
            and cdt.mention_role = 'comment-thread'
            and cd.source_name = :source_name
            {subreddit_filter}
        )
        """,
        params,
    )


def _conversation_document_id_lookup(
    db: Database,
    source_name: str,
    source_document_ids: list[str],
) -> dict[str, int]:
    if not source_document_ids:
        return {}
    placeholders = ", ".join(f":doc_id_{index}" for index in range(len(source_document_ids)))
    params = {"source_name": source_name}
    params.update({f"doc_id_{index}": value for index, value in enumerate(source_document_ids)})
    rows = db.query_all(
        f"""
        select conversation_document_id, source_document_id
        from conversation_documents
        where source_name = :source_name
          and source_document_id in ({placeholders})
        """,
        params,
    )
    return {str(row["source_document_id"]): int(row["conversation_document_id"]) for row in rows}


def _candidate_posts_for_comment_collection(
    db: Database,
    season: int,
    week: int,
    source_name: str,
    subreddits: list[str],
    limit_posts: int,
    min_post_comments: int,
    min_post_score: int,
    parent_mention_roles: tuple[str, ...] = ("query-match", "source-prior", "team-sub"),
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "season": season,
        "week": week,
        "source_name": source_name,
        "min_post_comments": min_post_comments,
        "min_post_score": min_post_score,
        "limit_posts": limit_posts,
    }
    # Which post mention_roles are eligible to be comment PARENTS. In-season this
    # is the watchlist/listing-sourced posts ('query-match'/'source-prior'); in
    # offseason the per-team .rss sweep tags posts 'team-sub', so include it or
    # no offseason post is ever eligible and comment collection silently yields 0.
    role_placeholders = ", ".join(f":role_{i}" for i in range(len(parent_mention_roles)))
    params.update({f"role_{i}": r for i, r in enumerate(parent_mention_roles)})
    subreddit_filter = ""
    if subreddits:
        placeholders = ", ".join(f":subreddit_{index}" for index in range(len(subreddits)))
        params.update({f"subreddit_{index}": subreddit for index, subreddit in enumerate(subreddits)})
        subreddit_filter = f"and coalesce(cd.source_subchannel, '') in ({placeholders})"
    rows = db.query_all(
        f"""
        with candidate_posts as (
          select
            cd.conversation_document_id,
            cd.source_document_id,
            cd.source_subchannel,
            cd.source_url,
            coalesce(cd.like_count, 0) as like_count,
            coalesce(cd.reply_count, 0) as reply_count,
            cd.external_created_at_utc
          from conversation_documents cd
          where cd.source_name = :source_name
            and cd.content_type = 'post'
            and coalesce(cd.reply_count, 0) >= :min_post_comments
            and coalesce(cd.like_count, 0) >= :min_post_score
            {subreddit_filter}
            and exists (
              select 1
              from conversation_document_targets cdt_exists
              where cdt_exists.conversation_document_id = cd.conversation_document_id
                and cdt_exists.season_year = :season
                and cdt_exists.week = :week
                and cdt_exists.target_type = 'team'
                and cdt_exists.mention_role in ({role_placeholders})
            )
          order by coalesce(cd.reply_count, 0) desc, coalesce(cd.like_count, 0) desc, cd.external_created_at_utc desc
          limit :limit_posts
        )
        select
          cd.conversation_document_id,
          cd.source_document_id,
          cd.source_subchannel,
          cd.source_url,
          coalesce(cd.like_count, 0) as like_count,
          coalesce(cd.reply_count, 0) as reply_count,
          cdt.game_id,
          cdt.team_id,
          cdt.player_id,
          cdt.target_type,
          cdt.target_key,
          cdt.target_label,
          cdt.affiliation_team_id,
          cdt.audience_bucket
        from candidate_posts cd
        join conversation_document_targets cdt
          on cdt.conversation_document_id = cd.conversation_document_id
        where cdt.season_year = :season
          and cdt.week = :week
          and cdt.target_type = 'team'
          and cdt.mention_role in ({role_placeholders})
        order by coalesce(cd.reply_count, 0) desc, coalesce(cd.like_count, 0) desc, cd.external_created_at_utc desc
        """,
        params,
    )
    grouped: dict[int, dict[str, Any]] = {}
    for row in rows:
        document_id = int(row["conversation_document_id"])
        entry = grouped.setdefault(
            document_id,
            {
                "conversation_document_id": document_id,
                "source_document_id": str(row["source_document_id"]),
                "source_subchannel": str(row.get("source_subchannel") or ""),
                "source_url": row.get("source_url"),
                "reply_count": int(row.get("reply_count") or 0),
                "like_count": int(row.get("like_count") or 0),
                "targets": [],
            },
        )
        entry["targets"].append(
            {
                "game_id": row.get("game_id"),
                "team_id": row.get("team_id"),
                "player_id": row.get("player_id"),
                "target_type": row.get("target_type"),
                "target_key": row.get("target_key"),
                "target_label": row.get("target_label"),
                "affiliation_team_id": row.get("affiliation_team_id"),
                "audience_bucket": row.get("audience_bucket"),
            }
        )
    return list(grouped.values())


def _load_comment_target_aliases(db: Database, season: int, team_ids: set[int]) -> dict[int, set[str]]:
    if not team_ids:
        return {}
    team_id_list = sorted(team_ids)
    placeholders = ", ".join(f":team_{idx}" for idx, _ in enumerate(team_id_list))
    params: dict[str, Any] = {f"team_{idx}": team_id for idx, team_id in enumerate(team_id_list)}
    params["season"] = season
    rows = db.query_all(
        f"""
        select team_id, canonical_name, slug
        from teams
        where team_id in ({placeholders})
        """,
        params,
    )
    aliases: dict[int, set[str]] = defaultdict(set)
    for row in rows:
        team_id = int(row["team_id"])
        for raw in (row.get("canonical_name"), str(row.get("slug") or "").replace("-", " ")):
            normalized = normalize_lookup_text(str(raw or ""))
            if len(normalized) >= 4:
                aliases[team_id].add(normalized)

    alias_rows = db.query_all(
        f"""
        select team_id, alias_normalized
        from team_aliases
        where is_active = 1
          and (season_year is null or season_year = %(season)s)
          and team_id in ({placeholders})
        """,
        params,
    )
    for row in alias_rows:
        normalized = normalize_lookup_text(str(row.get("alias_normalized") or ""))
        if len(normalized) >= 4:
            aliases[int(row["team_id"])].add(normalized)
    return aliases


def _comment_targets_for_parent(
    comment: dict[str, Any],
    parent_targets: list[dict[str, Any]],
    aliases_by_team: dict[int, set[str]],
) -> list[tuple[dict[str, Any], str]]:
    unique_targets: dict[int, dict[str, Any]] = {}
    for target in parent_targets:
        if target.get("team_id") is None:
            continue
        unique_targets.setdefault(int(target["team_id"]), target)
    if len(unique_targets) == 1:
        return [(next(iter(unique_targets.values())), "single_parent_target")]

    comment_text = f" {normalize_lookup_text(str(comment.get('body') or ''))} "
    flair_text = _comment_author_flair_text(comment)
    matched: list[tuple[dict[str, Any], str]] = []
    for team_id, target in unique_targets.items():
        aliases = aliases_by_team.get(team_id) or set()
        if _text_matches_alias(comment_text, aliases):
            matched.append((target, "comment_alias_match"))
            continue
        if flair_text and _text_matches_alias(flair_text, aliases):
            matched.append((target, "author_flair_match"))
    return matched


def _comment_author_flair_text(comment: dict[str, Any]) -> str:
    raw = comment.get("_raw") if isinstance(comment.get("_raw"), dict) else {}
    parts = [
        str(comment.get("author_flair_text") or ""),
        str(comment.get("author_flair_css_class") or ""),
        str(raw.get("author_flair_text") or ""),
        str(raw.get("author_flair_css_class") or ""),
    ]
    richtext = raw.get("author_flair_richtext")
    if isinstance(richtext, list):
        for item in richtext:
            if isinstance(item, dict):
                parts.append(str(item.get("t") or item.get("a") or ""))
    normalized = " ".join(normalize_lookup_text(part) for part in parts if str(part).strip())
    return f" {normalized} " if normalized.strip() else ""


def _text_matches_alias(text: str, aliases: set[str]) -> bool:
    return any(f" {alias} " in text for alias in aliases)


def _raw_content_purge_candidates(
    db: Database,
    source_name: str,
    provider_name: str | None,
    cutoff_utc: str,
    require_weekly_features: bool,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "source_name": source_name,
        "cutoff_utc": cutoff_utc,
    }
    provider_filter = ""
    if provider_name:
        params["provider_name"] = provider_name
        provider_filter = """
          and (
            case
              when ccr.raw_config_json is not null and json_valid(ccr.raw_config_json)
              then json_extract(ccr.raw_config_json, '$.provider')
              else null
            end
          ) = :provider_name
        """
    feature_filter = ""
    if require_weekly_features:
        feature_filter = """
          and not exists (
            select 1
            from conversation_document_targets cdt_missing
            where cdt_missing.conversation_document_id = cd.conversation_document_id
              and cdt_missing.target_type = 'team'
              and not exists (
                select 1
                from team_week_conversation_features twcf
                where twcf.season_year = cdt_missing.season_year
                  and twcf.week = cdt_missing.week
                  and twcf.team_id = cdt_missing.team_id
                  and twcf.source_name = cd.source_name
                  and twcf.audience_bucket = cdt_missing.audience_bucket
              )
          )
        """
    return db.query_all(
        f"""
        select cd.conversation_document_id
        from conversation_documents cd
        left join conversation_collection_runs ccr
          on ccr.conversation_collection_run_id = cd.collection_run_id
        where cd.source_name = :source_name
          and cd.source_channel = 'reddit'
          and cd.content_type in ('post', 'comment')
          and coalesce(cd.collected_at_utc, '') <= :cutoff_utc
          and cd.raw_text_purged_at_utc is null
          and (
            coalesce(cd.title_text, '') <> ''
            or coalesce(cd.body_text, '') <> ''
            or cd.raw_payload_json is not null
            or coalesce(cd.source_author_id, '') <> ''
            or coalesce(cd.source_author_name, '') <> ''
          )
          and exists (
            select 1
            from conversation_document_targets cdt
            where cdt.conversation_document_id = cd.conversation_document_id
          )
          {provider_filter}
          {feature_filter}
        order by cd.conversation_document_id
        """,
        params,
    )


def _reddit_base36_id(value: str) -> str:
    text = value.strip()
    if text.startswith("t3_") or text.startswith("t1_"):
        return text[3:]
    return text


def _is_deleted_reddit_text(value: str) -> bool:
    return value.strip().lower() in {"[deleted]", "[removed]", "deleted", "removed"}


def _chunks(values: list[int], size: int) -> list[list[int]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def _parsed_conversation_row(row: dict[str, Any]) -> dict[str, Any]:
    parsed = dict(row)
    parsed["team_id"] = int(parsed["team_id"])
    parsed["timestamp"] = _parse_datetime(str(parsed.get("external_created_at_utc") or ""))
    parsed["document_text"] = " ".join(
        part.strip()
        for part in [str(parsed.get("title_text") or ""), str(parsed.get("body_text") or "")]
        if str(part).strip()
    )
    return parsed


def date_et(timestamp: datetime | str | None) -> str:
    """Return the America/New_York calendar date for a UTC timestamp."""

    if timestamp is None:
        return ""
    parsed = timestamp if isinstance(timestamp, datetime) else _parse_datetime(str(timestamp))
    if parsed is None:
        return ""
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(ET_ZONE).date().isoformat()


def _load_rival_pairs(db: Database, season: int, week: int) -> dict[int, set[int]]:
    pairs = db.query_all(
        """
        select row.team_a_id, row.team_b_id
        from rivalry_obsession_weekly row
        join offseason_week_map owm on owm.week_start_date = row.week_start_date
        where owm.season_year = %(season)s
          and owm.offseason_week = %(week)s
        """,
        {"season": season, "week": week},
    )
    rivals_by_team: dict[int, set[int]] = defaultdict(set)
    for pair in pairs:
        team_a_id = int(pair["team_a_id"])
        team_b_id = int(pair["team_b_id"])
        rivals_by_team[team_a_id].add(team_b_id)
        rivals_by_team[team_b_id].add(team_a_id)
    return rivals_by_team


def _load_rival_aliases(db: Database, season: int, team_ids: set[int]) -> dict[int, set[str]]:
    if not team_ids:
        return {}
    team_id_list = sorted(team_ids)
    placeholders = ", ".join(f":team_{idx}" for idx, _ in enumerate(team_id_list))
    params: dict[str, Any] = {f"team_{idx}": team_id for idx, team_id in enumerate(team_id_list)}
    params["season"] = season
    teams = db.query_all(
        f"""
        select team_id, slug, canonical_name
        from teams
        where team_id in ({placeholders})
        """,
        params,
    )
    aliases: dict[int, set[str]] = defaultdict(set)
    for team in teams:
        team_id = int(team["team_id"])
        for raw in (team.get("canonical_name"), str(team.get("slug") or "").replace("-", " ")):
            normalized = normalize_lookup_text(str(raw or ""))
            if len(normalized) >= 4:
                aliases[team_id].add(normalized)

    alias_rows = db.query_all(
        f"""
        select team_id, alias_normalized
        from team_aliases
        where is_active = 1
          and (season_year is null or season_year = %(season)s)
          and team_id in ({placeholders})
        """,
        params,
    )
    for row in alias_rows:
        normalized = normalize_lookup_text(str(row.get("alias_normalized") or ""))
        if len(normalized) >= 4:
            aliases[int(row["team_id"])].add(normalized)
    return aliases


def _build_rival_mention_rows(
    db: Database,
    rows: list[dict[str, Any]],
    season: int,
    week: int,
    source_name: str,
) -> list[dict[str, Any]]:
    rivals_by_team = _load_rival_pairs(db, season, week)
    if not rivals_by_team:
        return []
    team_ids = {team_id for team_id in rivals_by_team}
    team_ids.update(rival_id for rivals in rivals_by_team.values() for rival_id in rivals)
    aliases_by_team = _load_rival_aliases(db, season, team_ids)
    grouped_docs: dict[tuple[int, int, str], set[int]] = defaultdict(set)
    grouped_authors: dict[tuple[int, int, str], set[str]] = defaultdict(set)

    for row in rows:
        team_id = int(row["team_id"])
        haystack = f" {normalize_lookup_text(str(row.get('document_text') or ''))} "
        if not haystack.strip():
            continue
        doc_id = int(row.get("conversation_document_id") or 0)
        author = str(row.get("author_key") or "").strip()
        audience_bucket = str(row.get("audience_bucket") or "unknown")
        for rival_team_id in rivals_by_team.get(team_id, set()):
            aliases = aliases_by_team.get(rival_team_id) or set()
            if any(f" {alias} " in haystack for alias in aliases):
                key = (team_id, rival_team_id, audience_bucket)
                grouped_docs[key].add(doc_id)
                if author:
                    grouped_authors[key].add(author)

    results: list[dict[str, Any]] = []
    for (team_id, rival_team_id, audience_bucket), docs in grouped_docs.items():
        mention_count = len(docs)
        if mention_count <= 0:
            continue
        authors = len(grouped_authors[(team_id, rival_team_id, audience_bucket)])
        results.append(
            {
                "team_id": team_id,
                "rival_team_id": rival_team_id,
                "season_year": season,
                "week": week,
                "mention_count": mention_count,
                "source_name": source_name,
                "audience_bucket": audience_bucket,
                "sample_authors": authors,
                "confidence": round(min(1.0, mention_count / 25.0, max(authors, 1) / 8.0), 3),
            }
        )
    return results


def _build_daily_rows(rows: list[dict[str, Any]], season: int, week: int) -> list[dict[str, Any]]:
    grouped: dict[tuple[int, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        timestamp: datetime | None = row.get("timestamp")
        if timestamp is None:
            continue
        key = (
            int(row["team_id"]),
            date_et(timestamp),
            str(row["source_name"]),
            str(row["audience_bucket"]),
        )
        grouped[key].append(row)

    results: list[dict[str, Any]] = []
    for (team_id, as_of_date, source_name, audience_bucket), entries in grouped.items():
        aggregate = _aggregate_entries(entries)
        results.append(
            {
                "team_id": team_id,
                "as_of_date": as_of_date,
                "season_year": season,
                "week": week,
                "source_name": source_name,
                "audience_bucket": audience_bucket,
                **_daily_aggregate_row(aggregate),
            }
        )
    return results


def _build_weekly_rows(
    rows: list[dict[str, Any]],
    season: int,
    week: int,
    source_name: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(int(row["team_id"]), str(row["audience_bucket"]))].append(row)

    weekly_rows: list[dict[str, Any]] = []
    storyline_rows: list[dict[str, Any]] = []
    for (team_id, audience_bucket), entries in grouped.items():
        aggregate = _aggregate_entries(entries)
        weekly_rows.append(
            {
                "season_year": season,
                "week": week,
                "team_id": team_id,
                "source_name": source_name,
                "audience_bucket": audience_bucket,
                **_weekly_or_game_aggregate_row(aggregate),
            }
        )
        storyline_rows.extend(
            _storyline_rows(
                season=season,
                week=week,
                game_id=None,
                team_id=team_id,
                source_name=source_name,
                audience_bucket=audience_bucket,
                window_label="weekly",
                period_start_utc=None,
                period_end_utc=None,
                entries=entries,
            )
        )
    return weekly_rows, storyline_rows


def _build_game_rows(
    db: Database,
    rows: list[dict[str, Any]],
    season: int,
    week: int,
    source_name: str,
    pregame_days: int,
    postgame_hours: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    games = db.query_all(
        """
        select game_id, start_time_utc, home_team_id, away_team_id
        from games
        where season_year = %(season)s
          and week = %(week)s
        """,
        {"season": season, "week": week},
    )
    game_feature_rows: list[dict[str, Any]] = []
    storyline_rows: list[dict[str, Any]] = []
    for game in games:
        game_id = int(game["game_id"])
        kickoff = _parse_datetime(str(game.get("start_time_utc") or ""))
        if kickoff is None:
            continue
        for team_id in [int(game["home_team_id"]), int(game["away_team_id"])]:
            team_entries = [row for row in rows if int(row["team_id"]) == team_id and row.get("timestamp") is not None]
            for audience_bucket in sorted({str(row["audience_bucket"]) for row in team_entries}):
                bucket_entries = [row for row in team_entries if str(row["audience_bucket"]) == audience_bucket]
                windows = {
                    f"pregame_{pregame_days}d": [
                        row for row in bucket_entries
                        if kickoff - timedelta(days=pregame_days) <= row["timestamp"] < kickoff
                    ],
                    f"postgame_{postgame_hours}h": [
                        row for row in bucket_entries
                        if kickoff <= row["timestamp"] < kickoff + timedelta(hours=postgame_hours)
                    ],
                }
                for window_label, window_entries in windows.items():
                    if not window_entries:
                        continue
                    aggregate = _aggregate_entries(window_entries)
                    period_start = min(row["timestamp"] for row in window_entries).isoformat()
                    period_end = max(row["timestamp"] for row in window_entries).isoformat()
                    game_feature_rows.append(
                        {
                            "game_id": game_id,
                            "team_id": team_id,
                            "season_year": season,
                            "week": week,
                            "source_name": source_name,
                            "audience_bucket": audience_bucket,
                            "window_label": window_label,
                            "period_start_utc": period_start,
                            "period_end_utc": period_end,
                            **_weekly_or_game_aggregate_row(aggregate),
                        }
                    )
                    storyline_rows.extend(
                        _storyline_rows(
                            season=season,
                            week=week,
                            game_id=game_id,
                            team_id=team_id,
                            source_name=source_name,
                            audience_bucket=audience_bucket,
                            window_label=window_label,
                            period_start_utc=period_start,
                            period_end_utc=period_end,
                            entries=window_entries,
                        )
                    )
    return game_feature_rows, storyline_rows


def _aggregate_entries(entries: list[dict[str, Any]]) -> dict[str, Any]:
    mention_count = len(entries)
    author_keys = {str(entry.get("author_key") or "") for entry in entries if str(entry.get("author_key") or "").strip()}
    subchannels = {str(entry.get("source_subchannel") or "") for entry in entries if str(entry.get("source_subchannel") or "").strip()}
    positive_count = sum(1 for entry in entries if entry.get("sentiment_label") == "positive")
    neutral_count = sum(1 for entry in entries if entry.get("sentiment_label") == "neutral")
    negative_count = sum(1 for entry in entries if entry.get("sentiment_label") == "negative")
    sentiment_total = sum(float(entry.get("sentiment_score") or 0.0) for entry in entries)
    emotion_counts: dict[str, int] = defaultdict(int)
    for entry in entries:
        primary = str(entry.get("emotion_primary") or "").strip()
        secondary = str(entry.get("emotion_secondary") or "").strip()
        if primary:
            emotion_counts[primary] += 1
        if secondary:
            emotion_counts[secondary] += 1
    texts = [str(entry.get("document_text") or "") for entry in entries]
    keywords = extract_keywords(texts, top_n=6)
    unique_author_count = len(author_keys)
    mean_sentiment = sentiment_total / mention_count if mention_count else 0.0
    return {
        "mention_count": mention_count,
        "unique_author_count": unique_author_count,
        "positive_doc_count": positive_count,
        "neutral_doc_count": neutral_count,
        "negative_doc_count": negative_count,
        "mean_sentiment_score": round(mean_sentiment, 4),
        "net_sentiment_score": round((positive_count - negative_count) / mention_count, 4) if mention_count else 0.0,
        "joy_share": _share(emotion_counts, mention_count, "joy"),
        "anger_share": _share(emotion_counts, mention_count, "anger"),
        "fear_share": _share(emotion_counts, mention_count, "fear"),
        "trust_share": _share(emotion_counts, mention_count, "trust"),
        "sadness_share": _share(emotion_counts, mention_count, "sadness"),
        "surprise_share": _share(emotion_counts, mention_count, "surprise"),
        "attention_score": attention_score(mention_count=mention_count, unique_author_count=unique_author_count),
        "sample_quality_score": sample_quality_score(
            mention_count=mention_count,
            unique_author_count=unique_author_count,
            subchannel_count=len(subchannels),
        ),
        "top_terms_json": json.dumps(keywords, ensure_ascii=True),
        "top_storyline_json": json.dumps(keywords, ensure_ascii=True),
    }


def _daily_aggregate_row(aggregate: dict[str, Any]) -> dict[str, Any]:
    return {
        "mention_count": aggregate["mention_count"],
        "unique_author_count": aggregate["unique_author_count"],
        "positive_doc_count": aggregate["positive_doc_count"],
        "neutral_doc_count": aggregate["neutral_doc_count"],
        "negative_doc_count": aggregate["negative_doc_count"],
        "mean_sentiment_score": aggregate["mean_sentiment_score"],
        "net_sentiment_score": aggregate["net_sentiment_score"],
        "joy_share": aggregate["joy_share"],
        "anger_share": aggregate["anger_share"],
        "fear_share": aggregate["fear_share"],
        "trust_share": aggregate["trust_share"],
        "sadness_share": aggregate["sadness_share"],
        "surprise_share": aggregate["surprise_share"],
        "attention_score": aggregate["attention_score"],
        "sample_quality_score": aggregate["sample_quality_score"],
        "top_terms_json": aggregate["top_terms_json"],
    }


def _weekly_or_game_aggregate_row(aggregate: dict[str, Any]) -> dict[str, Any]:
    return {
        "mention_count": aggregate["mention_count"],
        "unique_author_count": aggregate["unique_author_count"],
        "positive_doc_count": aggregate["positive_doc_count"],
        "neutral_doc_count": aggregate["neutral_doc_count"],
        "negative_doc_count": aggregate["negative_doc_count"],
        "mean_sentiment_score": aggregate["mean_sentiment_score"],
        "net_sentiment_score": aggregate["net_sentiment_score"],
        "joy_share": aggregate["joy_share"],
        "anger_share": aggregate["anger_share"],
        "fear_share": aggregate["fear_share"],
        "trust_share": aggregate["trust_share"],
        "sadness_share": aggregate["sadness_share"],
        "surprise_share": aggregate["surprise_share"],
        "attention_score": aggregate["attention_score"],
        "sample_quality_score": aggregate["sample_quality_score"],
        "top_storyline_json": aggregate["top_storyline_json"],
    }


def _storyline_rows(
    season: int,
    week: int,
    game_id: int | None,
    team_id: int,
    source_name: str,
    audience_bucket: str,
    window_label: str,
    period_start_utc: str | None,
    period_end_utc: str | None,
    entries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    keywords = extract_keywords((str(entry.get("document_text") or "") for entry in entries), top_n=6)
    urls = []
    seen_urls: set[str] = set()
    for entry in entries:
        url = str(entry.get("source_url") or "").strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        urls.append(url)
        if len(urls) >= 3:
            break
    results: list[dict[str, Any]] = []
    for index, keyword in enumerate(keywords[:3], start=1):
        label = keyword.replace("_", " ").title()
        summary = f"Conversation centered on {label.lower()}."
        results.append(
            {
                "season_year": season,
                "week": week,
                "game_id": game_id,
                "team_id": team_id,
                "source_name": source_name,
                "audience_bucket": audience_bucket,
                "window_label": window_label,
                "period_start_utc": period_start_utc,
                "period_end_utc": period_end_utc,
                "storyline_rank": index,
                "storyline_key": keyword,
                "storyline_label": label,
                "storyline_summary": summary,
                "keywords_json": json.dumps(keywords, ensure_ascii=True),
                "representative_source_urls_json": json.dumps(urls, ensure_ascii=True),
                "sample_document_count": len(entries),
                "llm_provider": None,
                "llm_model": None,
            }
        )
    return results


def _timestamp_to_iso(value: Any) -> str:
    try:
        timestamp = float(value)
    except (TypeError, ValueError):
        return datetime.now(UTC).isoformat()
    return datetime.fromtimestamp(timestamp, tz=UTC).isoformat()


def _parse_datetime(value: str) -> datetime | None:
    text = value.strip()
    if not text:
        return None
    text = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _share(counts: dict[str, int], mention_count: int, key: str) -> float:
    if mention_count <= 0:
        return 0.0
    return round(float(counts.get(key) or 0) / mention_count, 4)
