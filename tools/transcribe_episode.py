"""Selective Whisper.cpp transcription — TASK 7.2.

Download one podcast episode's audio, transcribe locally using whisper-cpp,
store per-segment rows for downstream editorial use. NOT invoked by cron —
triggered manually when Kevin flags an episode for deeper analysis.

Usage:
    python tools/transcribe_episode.py --episode-dedup-key <sha1>
    python tools/transcribe_episode.py --enclosure-url <url> --show-slug finebaum_rss

Requires ``whisper-cpp`` binary on PATH or via ``WHISPER_CPP_BIN`` env var.
Model is configurable via ``WHISPER_MODEL`` (default: ``small.en``).

Segments land in a new ``podcast_transcript_segments`` table (created on
first run). Source tier is D (editorial citation only). Rows are pseudonym-
free — ASR cannot reliably attribute speaker.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "src"))

from cfb_rankings.config import AppConfig  # noqa: E402
from cfb_rankings.db import Database  # noqa: E402
from cfb_rankings.migrations import apply_runtime_migrations  # noqa: E402


def _ensure_schema(db: Database) -> None:
    db.execute(
        """
        create table if not exists podcast_transcript_segments (
            segment_id integer primary key autoincrement,
            conversation_document_id integer,
            source_id text not null,
            episode_dedup_key text not null,
            segment_index integer not null,
            start_seconds real,
            end_seconds real,
            text_content text,
            model_name text,
            created_at_utc text not null default current_timestamp
        )
        """
    )
    db.execute(
        "create index if not exists idx_podcast_segments_ep "
        "on podcast_transcript_segments (episode_dedup_key, segment_index)"
    )


def _find_whisper_bin() -> str:
    bin_path = os.environ.get("WHISPER_CPP_BIN") or shutil.which("whisper-cpp") \
        or shutil.which("main") or shutil.which("whisper.cpp")
    if not bin_path:
        raise RuntimeError(
            "whisper-cpp not found. Install whisper.cpp and set WHISPER_CPP_BIN, "
            "or place 'whisper-cpp' / 'main' on PATH."
        )
    return bin_path


def _download(url: str, dest: Path) -> None:
    req = Request(url, headers={"User-Agent": "CFBIndex-FanIntel/0.1"})
    with urlopen(req, timeout=120) as resp, dest.open("wb") as fh:
        while True:
            chunk = resp.read(64 * 1024)
            if not chunk:
                break
            fh.write(chunk)


def _run_whisper(bin_path: str, audio_path: Path, model: str = "small.en") -> list[dict]:
    """Run whisper-cpp and parse its JSON output."""
    out_base = audio_path.with_suffix("")
    cmd = [
        bin_path, "-m", os.environ.get("WHISPER_MODEL_PATH", f"models/ggml-{model}.bin"),
        "-f", str(audio_path), "-oj", "-of", str(out_base),
    ]
    subprocess.run(cmd, check=True)
    json_path = out_base.with_suffix(".json")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    return data.get("transcription") or []


def transcribe(db: Database, *, episode_dedup_key: str | None = None,
               enclosure_url: str | None = None, show_slug: str | None = None,
               model: str = "small.en") -> int:
    """Transcribe one episode; returns number of segments written."""
    _ensure_schema(db)
    # Resolve enclosure URL + source_id
    if episode_dedup_key:
        doc = db.query_one(
            "select conversation_document_id, source_id, raw_payload_json, canonical_url "
            "from conversation_documents where dedup_key = :k",
            {"k": episode_dedup_key},
        )
        if not doc:
            raise RuntimeError(f"no conversation_document with dedup_key={episode_dedup_key}")
        doc_id = doc["conversation_document_id"]
        source_id = doc["source_id"]
        payload = json.loads(doc["raw_payload_json"] or "{}") if doc["raw_payload_json"] else {}
        enclosure = payload.get("enclosure_url") or doc["canonical_url"]
    else:
        if not (enclosure_url and show_slug):
            raise ValueError("supply --episode-dedup-key, or both --enclosure-url and --show-slug")
        doc_id = None
        source_id = f"podcast_{show_slug.lower()}"
        enclosure = enclosure_url
        episode_dedup_key = hashlib.sha1(
            f"manual|{source_id}|{enclosure}".encode()
        ).hexdigest()
    if not enclosure:
        raise RuntimeError("no enclosure URL available for this episode")

    bin_path = _find_whisper_bin()
    with tempfile.TemporaryDirectory() as tmpdir:
        audio = Path(tmpdir) / "episode.mp3"
        print(f"[transcribe] downloading {enclosure}")
        _download(enclosure, audio)
        print(f"[transcribe] running whisper-cpp (model={model})")
        segments = _run_whisper(bin_path, audio, model)

    written = 0
    for i, seg in enumerate(segments):
        db.execute(
            """
            insert into podcast_transcript_segments (
                conversation_document_id, source_id, episode_dedup_key,
                segment_index, start_seconds, end_seconds, text_content, model_name
            ) values (:doc, :sid, :ek, :i, :s, :e, :t, :m)
            """,
            {
                "doc": doc_id, "sid": source_id, "ek": episode_dedup_key,
                "i": i,
                "s": (seg.get("offsets", {}).get("from") or 0) / 1000.0,
                "e": (seg.get("offsets", {}).get("to") or 0) / 1000.0,
                "t": seg.get("text") or "",
                "m": model,
            },
        )
        written += 1
    print(f"[transcribe] wrote {written} segments for source_id={source_id}")
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episode-dedup-key",
                        help="dedup_key of a row in conversation_documents.")
    parser.add_argument("--enclosure-url",
                        help="Audio enclosure URL (bypass DB lookup).")
    parser.add_argument("--show-slug",
                        help="Required when --enclosure-url is used.")
    parser.add_argument("--model", default="small.en",
                        help="Whisper model name (default: small.en).")
    args = parser.parse_args()

    config = AppConfig.from_env()
    db = Database(config.database_url)
    apply_runtime_migrations(db)
    transcribe(db,
               episode_dedup_key=args.episode_dedup_key,
               enclosure_url=args.enclosure_url,
               show_slug=args.show_slug,
               model=args.model)


if __name__ == "__main__":
    main()
