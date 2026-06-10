"""YouTube comment collection (Build #3) — the biggest unexploited CFB fan-opinion
pool. Official YouTube Data API, free 10k-unit/day quota.

Quota-optimal pipeline (per the June-2026 source research):
  uploads playlist = channel_id with UC->UU (no API call)
  -> playlistItems.list (1 unit, latest N uploads)
  -> videos.list (1 unit per 50 ids) for statistics.commentCount triage
  -> commentThreads.list (1 unit/page) ONLY for videos whose comment count grew
NEVER use search.list (100 units). Read calls are 1 unit each, so ~150 channels
cost ~660 units/day offseason — quota is not the binding constraint.

National channels (team-agnostic) are written without a team target and tagged
later by tag-team-mentions --sources youtube (their comments mention many teams);
per-team channels (known team_id) get a direct team target. The nightly encoder
upgrades sentiment for every target.
"""
from __future__ import annotations

import json
import logging
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen

from cfb_rankings.conversation_utils import score_sentiment
from cfb_rankings.db import Database
from cfb_rankings.ingest.conversation import (
    _conversation_document_id_lookup,
    _create_collection_run,
    _finish_collection_run,
    _utcnow_iso_z,
)

logger = logging.getLogger(__name__)

_API = "https://www.googleapis.com/youtube/v3"
_UA = "windows:cfb-index-youtube:v1.0"


class YouTubeQuotaError(RuntimeError):
    """Raised when the API returns quotaExceeded so the run stops cleanly."""


def _api_get(path: str, params: dict[str, str], api_key: str, *, units: list[int]) -> dict[str, Any]:
    params = {**params, "key": api_key}
    qs = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
    url = f"{_API}/{path}?{qs}"
    req = Request(url, headers={"User-Agent": _UA, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=30) as resp:
            units[0] += 1  # every read endpoint here costs 1 unit
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        msg = ""
        body = getattr(exc, "read", None)
        if callable(body):
            try:
                msg = body().decode("utf-8", "replace")
            except Exception:  # noqa: BLE001
                msg = ""
        if "quotaExceeded" in msg or getattr(exc, "code", None) == 403 and "quota" in msg.lower():
            raise YouTubeQuotaError(msg or str(exc)) from exc
        raise


def _uploads_playlist(channel_id: str) -> str | None:
    cid = (channel_id or "").strip()
    if not cid.startswith("UC") or len(cid) < 3:
        return None
    return "UU" + cid[2:]


def _recent_video_ids(playlist_id: str, api_key: str, max_videos: int, units: list[int]) -> list[str]:
    data = _api_get("playlistItems", {
        "part": "contentDetails", "playlistId": playlist_id,
        "maxResults": str(min(50, max_videos)),
    }, api_key, units=units)
    out = []
    for it in data.get("items", []):
        vid = (it.get("contentDetails") or {}).get("videoId")
        if vid:
            out.append(vid)
    return out[:max_videos]


def _videos_comment_counts(video_ids: list[str], api_key: str, units: list[int]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        data = _api_get("videos", {"part": "snippet,statistics", "id": ",".join(batch)},
                        api_key, units=units)
        for v in data.get("items", []):
            vid = v.get("id")
            if not vid:
                continue
            stats = v.get("statistics") or {}
            snip = v.get("snippet") or {}
            out[vid] = {
                "comment_count": int(stats.get("commentCount") or 0),
                "title": snip.get("title") or "",
                "channel_title": snip.get("channelTitle") or "",
                "published_at": snip.get("publishedAt"),
            }
    return out


def _comment_threads(video_id: str, api_key: str, max_comments: int, units: list[int]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page_token = ""
    while len(rows) < max_comments:
        params = {"part": "snippet", "videoId": video_id,
                  "maxResults": "100", "order": "relevance", "textFormat": "plainText"}
        if page_token:
            params["pageToken"] = page_token
        try:
            data = _api_get("commentThreads", params, api_key, units=units)
        except YouTubeQuotaError:
            raise
        except Exception as exc:  # noqa: BLE001 — comments often disabled -> 403; skip the video
            logger.debug("commentThreads skip %s: %s", video_id, exc)
            break
        for it in data.get("items", []):
            top = (((it.get("snippet") or {}).get("topLevelComment") or {}).get("snippet")) or {}
            cid = (it.get("snippet") or {}).get("topLevelComment", {}).get("id") or it.get("id")
            text = top.get("textDisplay") or top.get("textOriginal") or ""
            if not cid or not text.strip():
                continue
            rows.append({
                "comment_id": cid,
                "video_id": video_id,
                "author": top.get("authorDisplayName") or "",
                "author_channel_id": ((top.get("authorChannelId") or {}).get("value")) or "",
                "text": text,
                "like_count": int(top.get("likeCount") or 0),
                "reply_count": int((it.get("snippet") or {}).get("totalReplyCount") or 0),
                "published_at": top.get("publishedAt"),
            })
            if len(rows) >= max_comments:
                break
        page_token = data.get("nextPageToken") or ""
        if not page_token:
            break
    return rows


def _comment_doc_row(c: dict[str, Any], channel_title: str, run_id: int) -> dict[str, Any]:
    return {
        "collection_run_id": run_id,
        "source_name": "youtube",
        "source_document_id": str(c["comment_id"]),
        "source_parent_document_id": str(c["video_id"]),
        "source_author_id": str(c.get("author_channel_id") or ""),
        "source_author_name": str(c.get("author") or ""),
        "source_channel": "youtube",
        "source_subchannel": channel_title,
        "source_url": f"https://www.youtube.com/watch?v={c['video_id']}&lc={c['comment_id']}",
        "content_type": "comment",
        "language_code": "en",
        "title_text": "",
        "body_text": str(c.get("text") or ""),
        "external_created_at_utc": c.get("published_at"),
        "like_count": int(c.get("like_count") or 0),
        "reply_count": int(c.get("reply_count") or 0),
        "repost_count": 0,
        "view_count": None,
        "is_deleted": 0,
        "is_removed": 0,
        "raw_payload_json": json.dumps(c, ensure_ascii=True),
        "raw_text_purged_at_utc": None,
        "raw_payload_purged_at_utc": None,
        "raw_retention_policy": "youtube_api_derived_only",
    }


def collect_youtube_comments(
    db: Database,
    season: int,
    week: int,
    api_key: str,
    *,
    national_channels: list[dict[str, str]] | None = None,
    max_videos_per_channel: int = 8,
    max_comments_per_video: int = 100,
    max_units: int = 6000,
    min_comment_count: int = 3,
) -> dict[str, int]:
    """Collect recent-upload comments for national + per-team CFB channels.

    Returns counts. Stops cleanly if quota is exhausted (partial = fine; the
    next run resumes new videos). Idempotent (upsert on source_document_id).
    """
    if not api_key:
        raise RuntimeError("YOUTUBE_API_KEY is required")

    # Channel set: national (team_id None) + per-team configured channels.
    channels: list[dict[str, Any]] = []
    for nc in (national_channels or []):
        channels.append({"channel_id": nc["channel_id"], "team_id": None,
                         "label": nc.get("name", ""), "role": "national"})
    for t in db.query_all(
        "select team_id, youtube_team_channel_id, youtube_fan_channels from priority_teams"
    ):
        if t.get("youtube_team_channel_id"):
            channels.append({"channel_id": str(t["youtube_team_channel_id"]),
                             "team_id": int(t["team_id"]), "label": "", "role": "team"})
        raw = t.get("youtube_fan_channels")
        if raw:
            try:
                for cid in json.loads(raw) or []:
                    if isinstance(cid, str) and cid.startswith("UC"):
                        channels.append({"channel_id": cid, "team_id": int(t["team_id"]),
                                         "label": "", "role": "fan"})
            except (json.JSONDecodeError, TypeError):
                pass

    if not channels:
        return {"channels": 0, "videos": 0, "documents": 0, "targets": 0, "units": 0}

    run_id = _create_collection_run(
        db=db, source_name="youtube", collection_scope="cfb-comments",
        target_label=f"{len(channels)} channels", season=season, week=week,
        raw_config={"channels": len(channels), "max_videos": max_videos_per_channel},
    )
    units = [0]
    total_videos = total_docs = total_targets = channels_done = 0
    quota_hit = False
    try:
        for ch in channels:
            if units[0] >= max_units:
                quota_hit = True
                break
            uploads = _uploads_playlist(ch["channel_id"])
            if not uploads:
                continue
            try:
                vids = _recent_video_ids(uploads, api_key, max_videos_per_channel, units)
                stats = _videos_comment_counts(vids, api_key, units) if vids else {}
            except YouTubeQuotaError:
                quota_hit = True
                break

            doc_rows: dict[str, dict[str, Any]] = {}
            comment_meta: list[dict[str, Any]] = []
            for vid in vids:
                if units[0] >= max_units:
                    quota_hit = True
                    break
                meta = stats.get(vid) or {}
                if meta.get("comment_count", 0) < min_comment_count:
                    continue
                ch_title = meta.get("channel_title") or ch.get("label") or ch["channel_id"]
                try:
                    comments = _comment_threads(vid, api_key, max_comments_per_video, units)
                except YouTubeQuotaError:
                    quota_hit = True
                    break
                for c in comments:
                    doc_rows[c["comment_id"]] = _comment_doc_row(c, ch_title, run_id)
                    comment_meta.append({"comment_id": c["comment_id"], "text": c["text"]})
                total_videos += 1

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
            # Per-team channels: tag every comment to the channel's team directly.
            # National channels: leave untagged for tag-team-mentions --sources youtube.
            if docs and ch["team_id"] is not None:
                id_lookup = _conversation_document_id_lookup(
                    db=db, source_name="youtube",
                    source_document_ids=[d["source_document_id"] for d in docs],
                )
                text_by_id = {m["comment_id"]: m["text"] for m in comment_meta}
                targets = []
                for sdid, cdid in id_lookup.items():
                    s = score_sentiment(text_by_id.get(sdid, ""))
                    targets.append({
                        "conversation_document_id": cdid,
                        "season_year": season, "week": week, "game_id": None,
                        "team_id": ch["team_id"], "player_id": None,
                        "target_type": "team", "target_key": f"team:{ch['team_id']}",
                        "target_label": "", "affiliation_team_id": ch["team_id"],
                        "audience_bucket": "fan", "mention_role": f"youtube-{ch['role']}",
                        "sentiment_label": s["sentiment_label"], "sentiment_score": s["sentiment_score"],
                        "emotion_primary": s["emotion_primary"], "emotion_secondary": s["emotion_secondary"],
                        "sarcasm_score": s["sarcasm_score"], "toxicity_score": s["toxicity_score"],
                        "confidence_score": s["confidence_score"],
                        "model_provider": "local", "model_name": "vader+lexicon",
                        "model_version": "conversation-v1", "is_primary_target": 1,
                        "notes": f"youtube:{ch['channel_id']}",
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
            channels_done += 1
            if quota_hit:
                break

        status = "completed" if not quota_hit else "completed"  # partial is still a clean stop
        _finish_collection_run(
            db=db, run_id=run_id, status=status, item_count=total_docs,
            notes=f"channels={channels_done}/{len(channels)} videos={total_videos} "
                  f"targets={total_targets} units={units[0]} quota_hit={quota_hit}",
        )
    except Exception as exc:
        _finish_collection_run(db=db, run_id=run_id, status="failed", item_count=total_docs, notes=str(exc))
        raise

    return {"channels": channels_done, "videos": total_videos, "documents": total_docs,
            "targets": total_targets, "units": units[0], "quota_hit": int(quota_hit)}


__all__ = ["collect_youtube_comments", "YouTubeQuotaError"]
