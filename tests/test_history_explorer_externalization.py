"""Tests for the history-explorer table externalization (WS-11 page weight).

/history/index.html ships an interactive explorer table of every modeled
team-season (~5k server-rendered rows, ~360KB gzipped). Inlined in full, it
dominated the page payload even though the filter/sort UI only needs a slice
visible for first paint. The fix inlines the first 150 rows (instant paint /
SEO / no-JS) and streams the remaining rows' server-rendered HTML to a sidecar
history/explorer-tail.json via a `tail_writer` callback; the filter script
fetches it on load, appends the rows, and rebuilds its in-memory row list so
filter+sort still spans every season. These tests pin both branches.
"""
from __future__ import annotations

import json

from cfb_rankings import reporting


def _explorer_row(i: int) -> dict:
    return {
        "team_id": i,
        "team_name": f"Team {i}",
        "slug": f"team-{i}",
        "season_year": 2025 - (i % 12),
        "level_code": "FBS",
        "conference_name": "SEC",
        "record": "10-2",
        "wins": 10,
        "losses": 2,
        "games_played": 12,
        "margin": 7,
        "win_pct": 0.833,
        "end_power": 5.0,
        "end_resume": 80.0,
        "final_rank": i,
        "lens_label": "Lens",
        "lens_body": "body",
        "program_url": f"../programs/team-{i}.html",
        "season_url": None,
    }


def _hub(n_rows: int) -> dict:
    return {
        "loaded_seasons": 12,
        "team_seasons": n_rows,
        "first_season": 2014,
        "last_season": 2025,
        "explorer_rows": [_explorer_row(i) for i in range(1, n_rows + 1)],
    }


_SUMMARY = {"season_year": 2025}
_PULSE: dict = {}

_ROW_MARK = 'class="history-explorer-row"'
_TAIL_ATTR = 'data-history-tail="explorer-tail.json"'


def test_inline_mode_keeps_all_rows() -> None:
    # No tail_writer => every row inlined, no sidecar attribute.
    html = reporting.render_history_index_html(_SUMMARY, _hub(400), _PULSE)
    assert html.count(_ROW_MARK) == 400
    assert _TAIL_ATTR not in html


def test_external_mode_inlines_head_and_writes_tail() -> None:
    captured: dict[str, str] = {}
    html = reporting.render_history_index_html(
        _SUMMARY, _hub(400), _PULSE,
        tail_writer=lambda payload: captured.__setitem__("json", payload),
    )
    # Exactly the inline cap is rendered into the page...
    assert html.count(_ROW_MARK) == 150
    assert _TAIL_ATTR in html
    # ...and the remaining rows are streamed to the sidecar.
    assert "json" in captured
    tail = json.loads(captured["json"])
    assert tail["rows_html"].count(_ROW_MARK) == 250
    # No rows lost across the head/tail split.
    assert 150 + tail["rows_html"].count(_ROW_MARK) == 400


def test_external_mode_smaller_than_inline() -> None:
    inline = reporting.render_history_index_html(_SUMMARY, _hub(400), _PULSE)
    external = reporting.render_history_index_html(
        _SUMMARY, _hub(400), _PULSE, tail_writer=lambda payload: None
    )
    assert len(external) < len(inline)


def test_small_table_stays_inline_even_with_writer() -> None:
    # At or below the inline cap there's no tail to externalize.
    calls: list[str] = []
    html = reporting.render_history_index_html(
        _SUMMARY, _hub(150), _PULSE, tail_writer=lambda payload: calls.append(payload)
    )
    assert calls == []
    assert _TAIL_ATTR not in html
    assert html.count(_ROW_MARK) == 150
