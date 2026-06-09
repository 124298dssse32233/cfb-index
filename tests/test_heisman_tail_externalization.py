"""Tests for the Heisman-board tail-payload externalization (WS-11 page weight).

The /heisman/ index inlines the top 1000 board rows as a table, then defers the
long tail (~15k rows) behind a "Load full board" button. Historically the tail
was inlined as a <script type="application/json"> blob — shipped on every page
load (~1MB gzipped) even though it only rendered on click. The fix routes that
blob to a sidecar board-tail.json via a `tail_writer` callback, fetched on
demand. These tests pin both behaviors so the regression can't sneak back.
"""
from __future__ import annotations

import json

from cfb_rankings import reporting
from cfb_rankings.reporting import HeismanRankingRow, render_heisman_page_html


def _row(rank: int) -> HeismanRankingRow:
    return HeismanRankingRow(
        overall_rank=rank,
        player_id=rank,
        player_slug=f"player-{rank}",
        full_name=f"Player {rank}",
        team_id=rank,
        team_slug=f"team-{rank}",
        team_name=f"Team {rank}",
        conference_name="SEC",
        position="QB",
        class_year="JR",
        season_year=2025,
        week=15,
        nowcast_rank=rank,
        forecast_rank=rank,
        win_probability=0.1,
        finalist_probability=0.2,
        any_ballot_probability=0.3,
        expected_ballot_share=0.4,
        latent_score=1.0,
    )


def _snapshot(n_rows: int) -> dict:
    return {
        "season_year": 2025,
        "week": 15,
        "has_market_data": False,
        "rows": [_row(i) for i in range(1, n_rows + 1)],
    }


_SUMMARY = {"season_year": 2025}


def test_inline_mode_keeps_payload_in_html() -> None:
    # No tail_writer => legacy behavior: the tail blob is inlined.
    snap = _snapshot(1200)  # 200 rows past the 1000-row inline cap
    html = render_heisman_page_html(_SUMMARY, snap, [], None)
    assert '<script type="application/json" id="heisman-tail-payload">' in html


def test_external_mode_writes_sidecar_and_strips_inline_blob() -> None:
    snap = _snapshot(1200)
    captured: dict[str, str] = {}
    html = render_heisman_page_html(
        _SUMMARY, snap, [], None,
        tail_writer=lambda payload: captured.__setitem__("json", payload),
    )
    # The inline JSON blob must be gone...
    assert '<script type="application/json" id="heisman-tail-payload">' not in html
    # ...and the JS must fetch the sidecar instead.
    assert "fetch('board-tail.json')" in html
    # The writer received a valid payload with the 200 tail rows.
    assert "json" in captured
    parsed = json.loads(captured["json"])
    assert parsed["tail_count"] == 200
    assert parsed["tail_rows_html"]


def test_external_mode_smaller_than_inline() -> None:
    snap = _snapshot(1200)
    inline = render_heisman_page_html(_SUMMARY, snap, [], None)
    external = render_heisman_page_html(
        _SUMMARY, snap, [], None, tail_writer=lambda payload: None
    )
    assert len(external) < len(inline)


def test_no_tail_no_writer_call() -> None:
    # When the board fits within the inline cap, there's no tail to write.
    snap = _snapshot(50)
    calls: list[str] = []
    html = render_heisman_page_html(
        _SUMMARY, snap, [], None, tail_writer=lambda payload: calls.append(payload)
    )
    assert calls == []
    assert '<script type="application/json" id="heisman-tail-payload">' not in html
