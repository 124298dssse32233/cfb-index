r"""Podcast transcription → fan-intel signal (faster-whisper, GPU).

The existing podcast layer ingests episode *metadata* (title + show-notes) via
``PodcastsMetaAdapter`` and stashes each episode's audio ``enclosure_url`` in
``raw_payload_json``. The legacy ``tools/transcribe_episode.py`` (whisper.cpp)
transcribes a single flagged episode into ``podcast_transcript_segments`` for
editorial citation only — it never enters the conversation pipeline, so podcasts
produce zero team/player sentiment today.

This module is the batch path that turns podcasts into REAL fan-intel signal:
for each recent episode it downloads the audio, transcribes it on the GPU with
faster-whisper, and lands the full transcript as a ``conversation_documents`` row
(``content_type='podcast_transcript'``, ``source_name='podcast_transcript'``).
The daily ``tag-team-mentions --sources podcast_transcript`` then alias-tags the
transcript to teams (a per-team show's transcript is dominated by that team; a
national show tags everyone it discusses), and ``tag-player-mentions`` picks up
players from the team-tagged transcript — so podcasts feed mood, Room cards, and
player signal exactly like Reddit/YouTube/news do.

Designed for a smooth daily trigger (it lives in the decoupled COLLECT job):
  * **Ledger-rotated** via ``collection_ledger`` (source ``podcast_asr``): new
    episodes first, then stalest; a broken enclosure gets an escalating cooldown
    instead of being retried every run.
  * **Hard wall-clock budget** (default 15 min) + **max-episodes** cap, so a
    backlog never makes the collector grind.
  * **Idempotent**: an episode that already has a transcript doc is skipped.
  * **Graceful skip**: if faster-whisper isn't installed it logs and no-ops
    (returns a skipped result) rather than failing the pipeline.

Setup (one time, see docs/podcast_transcription_setup_2026-06.md):
  .venv-ml already has CUDA torch; add faster-whisper there:
      .\.venv-ml\Scripts\python.exe -m pip install faster-whisper
  Then: .\.venv-ml\Scripts\python.exe manage.py collect-podcast-transcripts \
            --season 2025 --week 41 --max-episodes 2
"""
from __future__ import annotations

import datetime as _dt
import json
import logging
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from cfb_rankings.db import Database
from cfb_rankings.ingest.conversation import (
    _create_collection_run,
    _finish_collection_run,
)

logger = logging.getLogger(__name__)

_UA = "CFBIndex-FanIntel/0.1 (podcast-asr)"
_TRANSCRIPT_SOURCE = "podcast_transcript"
_MAX_BODY_CHARS = 200_000  # a 90-min episode is ~90k chars; cap guards runaways


class FasterWhisperUnavailable(RuntimeError):
    """faster-whisper (or its CUDA runtime) isn't importable — graceful skip."""


def _load_model(model_size: str, device: str, compute_type: str):
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except ImportError as exc:
        raise FasterWhisperUnavailable(
            "faster-whisper not installed (.venv-ml: pip install faster-whisper)"
        ) from exc
    try:
        return WhisperModel(model_size, device=device, compute_type=compute_type)
    except Exception as exc:  # noqa: BLE001 — CUDA/cuDNN/model-download failures → skip cleanly
        # Fall back to CPU int8 once before giving up (lets a box without a
        # working CUDA runtime still transcribe, just slower).
        if device != "cpu":
            logger.warning("faster-whisper cuda init failed (%s); falling back to CPU int8", exc)
            try:
                return WhisperModel(model_size, device="cpu", compute_type="int8")
            except Exception as exc2:  # noqa: BLE001
                raise FasterWhisperUnavailable(f"WhisperModel init failed: {exc2}") from exc2
        raise FasterWhisperUnavailable(f"WhisperModel init failed: {exc}") from exc


def _download(url: str, dest: Path, timeout: float = 180.0) -> int:
    req = Request(url, headers={"User-Agent": _UA, "Accept": "*/*"})
    total = 0
    with urlopen(req, timeout=timeout) as resp, dest.open("wb") as fh:
        while True:
            chunk = resp.read(128 * 1024)
            if not chunk:
                break
            fh.write(chunk)
            total += len(chunk)
    return total


def _candidate_episodes(db: Database, *, max_age_days: int) -> list[dict[str, Any]]:
    """Recent podcast_episode docs that have an enclosure and no transcript yet."""
    cutoff = (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=max_age_days)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    rows = db.query_all(
        """
        select cd.conversation_document_id, cd.source_name, cd.source_document_id,
               cd.dedup_key, cd.raw_payload_json, cd.external_created_at_utc,
               cd.title_text, cd.source_url, cd.source_subchannel
          from conversation_documents cd
         where cd.content_type = 'podcast_episode'
           and coalesce(cd.external_created_at_utc, '') >= :cutoff
           and cd.raw_payload_json like '%enclosure_url%'
           and not exists (
             select 1 from conversation_documents tx
              where tx.source_name = :tsrc
                and tx.source_parent_document_id = cd.source_document_id
           )
         order by cd.external_created_at_utc desc
        """,
        {"cutoff": cutoff, "tsrc": _TRANSCRIPT_SOURCE},
    )
    out: list[dict[str, Any]] = []
    for r in rows:
        try:
            payload = json.loads(r.get("raw_payload_json") or "{}")
        except (json.JSONDecodeError, TypeError):
            payload = {}
        enclosure = payload.get("enclosure_url")
        if not enclosure:
            continue
        r = dict(r)
        r["_enclosure"] = enclosure
        r["_show_slug"] = (r.get("source_name") or "").removeprefix("podcast_") or "podcast"
        out.append(r)
    return out


def _transcript_doc_row(ep: dict[str, Any], run_id: int, text: str, *,
                        model_size: str, duration_s: float | None) -> dict[str, Any]:
    ep_sdid = str(ep["source_document_id"])
    return {
        "collection_run_id": run_id,
        "source_name": _TRANSCRIPT_SOURCE,
        "source_document_id": f"transcript:{ep_sdid}",
        "source_parent_document_id": ep_sdid,
        "source_author_id": "",
        "source_author_name": str(ep.get("_show_slug") or ""),
        "source_channel": "podcast",
        "source_subchannel": str(ep.get("_show_slug") or ""),
        "source_url": ep.get("source_url"),
        "content_type": "podcast_transcript",
        "language_code": "en",
        "title_text": str(ep.get("title_text") or "")[:500],
        "body_text": text[:_MAX_BODY_CHARS],
        "external_created_at_utc": ep.get("external_created_at_utc"),
        "like_count": 0,
        "reply_count": 0,
        "repost_count": 0,
        "view_count": None,
        "is_deleted": 0,
        "is_removed": 0,
        "raw_payload_json": json.dumps({
            "show_slug": ep.get("_show_slug"),
            "asr_model": model_size,
            "enclosure_url": ep.get("_enclosure"),
            "duration_seconds": duration_s,
            "episode_dedup_key": ep.get("dedup_key"),
        }, ensure_ascii=True),
        "raw_text_purged_at_utc": None,
        "raw_payload_purged_at_utc": None,
        "raw_retention_policy": "podcast_asr_derived",
    }


_DOC_UPDATE_COLUMNS = [
    "collection_run_id", "source_parent_document_id", "source_author_id",
    "source_author_name", "source_channel", "source_subchannel", "source_url",
    "content_type", "language_code", "title_text", "body_text",
    "external_created_at_utc", "like_count", "reply_count", "repost_count",
    "view_count", "is_deleted", "is_removed", "raw_payload_json",
    "raw_text_purged_at_utc", "raw_payload_purged_at_utc", "raw_retention_policy",
]


def collect_podcast_transcripts(
    db: Database,
    season: int,
    week: int,
    *,
    model_size: str = "small.en",
    device: str = "cuda",
    compute_type: str = "float16",
    max_episodes: int = 6,
    budget_seconds: float = 900.0,
    max_age_days: int = 21,
    beam_size: int = 1,
    show_filter: list[str] | None = None,
) -> dict[str, Any]:
    """Transcribe a rotated, time-boxed batch of recent podcast episodes.

    Returns counts. Raises FasterWhisperUnavailable (callers map to a clean skip)
    when the ASR backend can't load.
    """
    from cfb_rankings.ingest.collection_ledger import Budget, mark_fail, mark_ok, select_batch

    candidates = _candidate_episodes(db, max_age_days=max_age_days)
    if show_filter:
        keep = {s.lower() for s in show_filter}
        candidates = [c for c in candidates if (c.get("_show_slug") or "").lower() in keep]
    if not candidates:
        logger.info("podcast_asr: no untranscribed episodes in the last %dd window", max_age_days)
        return {"episodes": 0, "transcribed": 0, "failed": 0, "skipped_no_audio": 0, "chars": 0}

    by_key = {str(c["dedup_key"] or c["source_document_id"]): c for c in candidates}
    batch_keys = select_batch(db, "podcast_asr", list(by_key.keys()), budget=max_episodes)

    # Load the model once (expensive) — only after we know there's work to do.
    model = _load_model(model_size, device, compute_type)

    run_id = _create_collection_run(
        db=db, source_name=_TRANSCRIPT_SOURCE, collection_scope="podcast-asr",
        target_label=f"{season} week {week} transcripts", season=season, week=week,
        raw_config={"model": model_size, "device": device, "max_episodes": max_episodes,
                    "budget_seconds": budget_seconds},
    )
    clock = Budget(budget_seconds)
    transcribed = failed = skipped_no_audio = total_chars = 0
    try:
        for key in batch_keys:
            if clock.expired():
                logger.info("podcast_asr: wall-clock budget reached; deferring rest to next run")
                break
            ep = by_key[key]
            enclosure = ep["_enclosure"]
            try:
                with tempfile.TemporaryDirectory() as tmp:
                    audio = Path(tmp) / "episode.audio"
                    nbytes = _download(enclosure, audio)
                    if nbytes < 1024:
                        skipped_no_audio += 1
                        mark_fail(db, "podcast_asr", key)
                        continue
                    segments, info = model.transcribe(str(audio), beam_size=beam_size, vad_filter=True)
                    text = " ".join(seg.text.strip() for seg in segments).strip()
                    duration_s = float(getattr(info, "duration", 0.0) or 0.0)
            except Exception as exc:  # noqa: BLE001 — one bad episode must not stop the batch
                logger.warning("podcast_asr: transcription failed for %s (%s): %s",
                               ep.get("_show_slug"), enclosure, exc)
                failed += 1
                mark_fail(db, "podcast_asr", key)
                continue

            if not text:
                skipped_no_audio += 1
                mark_fail(db, "podcast_asr", key)
                continue

            row = _transcript_doc_row(ep, run_id, text, model_size=model_size, duration_s=duration_s)
            db.upsert_many(
                "conversation_documents", [row],
                conflict_columns=["source_name", "source_document_id"],
                update_columns=_DOC_UPDATE_COLUMNS,
            )
            transcribed += 1
            total_chars += len(text)
            mark_ok(db, "podcast_asr", key, interval_hours=24 * 365)  # transcribe once
            logger.info("podcast_asr: %s — %d chars (%.0fs audio)",
                        ep.get("_show_slug"), len(text), duration_s)

        _finish_collection_run(
            db=db, run_id=run_id, status="completed", item_count=transcribed,
            notes=f"transcribed={transcribed} failed={failed} no_audio={skipped_no_audio} "
                  f"chars={total_chars} batch={len(batch_keys)}",
        )
    except Exception as exc:
        _finish_collection_run(db=db, run_id=run_id, status="failed", item_count=transcribed, notes=str(exc))
        raise

    return {"episodes": len(batch_keys), "transcribed": transcribed, "failed": failed,
            "skipped_no_audio": skipped_no_audio, "chars": total_chars}


__all__ = ["collect_podcast_transcripts", "FasterWhisperUnavailable"]
