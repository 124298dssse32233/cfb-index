"""Haiku-based sentiment classifier for player-linked conversation targets.

Scope: conversation_document_targets rows where player_id IS NOT NULL and
sentiment_label IS NULL. Team rows are already labelled by the conversation
pipeline. This module fills the remaining ~19k player targets.

Usage:
    python manage.py classify-player-sentiment           # all unlabelled
    python manage.py classify-player-sentiment --limit 500   # partial run
    python manage.py classify-player-sentiment --dry-run     # count only

Architecture:
    Batch 50 doc bodies → single Haiku prompt → parse JSON array of labels →
    UPDATE conversation_document_targets.sentiment_label + model metadata.

    Falls back gracefully when llm_runtime returns offline-stub (no API key).
    Each batch is a single DB transaction — partial runs are safe to resume.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

log = logging.getLogger(__name__)

_HAIKU_MODEL = "claude-haiku-4-5-20251001"
_BATCH_SIZE = 50

_SYSTEM_PROMPT = """\
You are a fast sentiment classifier for college football fan conversation.
Classify each document excerpt as exactly one of: positive, neutral, negative.
Apply fan-voice context: excitement/hype = positive, frustration/criticism = negative,
factual/neutral discussion = neutral. Sarcasm: classify by underlying sentiment.
Return ONLY a JSON array of strings matching the order of inputs, e.g.:
["positive","neutral","negative"]
No explanation, no keys, just the array."""


def _build_batch_prompt(texts: list[str]) -> str:
    numbered = "\n".join(
        f"{i+1}. {t[:300].replace(chr(10), ' ')}" for i, t in enumerate(texts)
    )
    return (
        f"Classify the sentiment of each excerpt (1-{len(texts)}):\n\n{numbered}"
    )


def _parse_labels(raw: str, batch_size: int) -> list[str | None]:
    """Parse Haiku JSON response into a list of label strings."""
    VALID = {"positive", "neutral", "negative"}
    try:
        data = json.loads(raw.strip())
        if isinstance(data, list) and len(data) == batch_size:
            return [v if v in VALID else None for v in data]
    except (json.JSONDecodeError, TypeError):
        pass
    # Fallback: extract quoted words from raw text
    import re
    found = re.findall(r'"(positive|neutral|negative)"', raw)
    padded: list[str | None] = [None] * batch_size
    for i, label in enumerate(found[:batch_size]):
        padded[i] = label
    return padded


def classify_player_targets(
    db_conn: Any,
    limit: int | None = None,
    dry_run: bool = False,
) -> dict[str, int]:
    """Classify all unlabelled player-linked conversation targets.

    Returns a summary dict: {labelled, skipped, batches, errors}.
    Skips rows where body_text is empty or None — these cannot be classified.
    """
    from cfb_rankings.llm_runtime import generate_with_voice_check

    cur = db_conn.cursor()

    # Count and fetch unlabelled player targets
    cur.execute(
        """
        SELECT cdt.conversation_document_target_id, cd.body_text
        FROM conversation_document_targets cdt
        JOIN conversation_documents cd
            ON cd.conversation_document_id = cdt.conversation_document_id
        WHERE cdt.player_id IS NOT NULL
          AND cdt.sentiment_label IS NULL
          AND cd.body_text IS NOT NULL
          AND cd.body_text != ''
        ORDER BY cdt.conversation_document_target_id
        """
        + (f" LIMIT {int(limit)}" if limit else ""),
    )
    rows = cur.fetchall()
    total = len(rows)

    if dry_run:
        cur.execute(
            """
            SELECT COUNT(*) FROM conversation_document_targets
            WHERE player_id IS NOT NULL AND sentiment_label IS NULL
            """
        )
        unlabelled_total = cur.fetchone()[0]
        return {"dry_run": True, "with_text": total, "total_unlabelled": unlabelled_total}

    log.info("classify_player_targets: %d rows to classify", total)

    labelled = 0
    skipped = 0
    errors = 0
    batches = 0
    start = time.time()

    for batch_start in range(0, total, _BATCH_SIZE):
        batch = rows[batch_start : batch_start + _BATCH_SIZE]
        ids = [r[0] for r in batch]
        texts = [r[1] for r in batch]

        prompt = _build_batch_prompt(texts)
        result = generate_with_voice_check(
            prompt,
            system=_SYSTEM_PROMPT,
            model=_HAIKU_MODEL,
            max_tokens=256,
            max_retries=0,
            fallback_to_offline=True,
        )
        batches += 1

        if result["mode"] == "offline-stub" or not result["text"]:
            log.warning("batch %d: offline-stub, skipping %d rows", batches, len(batch))
            skipped += len(batch)
            continue

        labels = _parse_labels(result["text"], len(batch))

        updates = [
            (label, _HAIKU_MODEL, tid)
            for label, tid in zip(labels, ids)
            if label is not None
        ]
        none_count = sum(1 for l in labels if l is None)
        skipped += none_count
        errors += none_count  # unparseable = soft error

        if updates:
            cur.executemany(
                """
                UPDATE conversation_document_targets
                SET sentiment_label = ?,
                    model_name = ?
                WHERE conversation_document_target_id = ?
                """,
                updates,
            )
            db_conn.commit()
            labelled += len(updates)

        elapsed = time.time() - start
        log.info(
            "batch %d/%d | labelled=%d skipped=%d elapsed=%.1fs",
            batches,
            -(-total // _BATCH_SIZE),
            labelled,
            skipped,
            elapsed,
        )

    return {
        "labelled": labelled,
        "skipped": skipped,
        "batches": batches,
        "errors": errors,
        "total": total,
    }
