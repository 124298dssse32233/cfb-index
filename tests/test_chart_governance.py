"""Chart-vocabulary governance lint (WS-08, D-007).

The ``cfb_rankings.charts`` package docstring states the intent plainly: the
locked 9-type chart vocabulary must stay governable, "so a CI lint can forbid
``def render_*_chart`` outside this package." This test is that lint.

It walks the package AST and finds every chart-type renderer — a top-level
``def render_*`` whose name carries a locked-vocabulary keyword (chart,
heatmap, choropleth, sankey, trajectory, sparkline, bump, percentile_bar,
small_multiple). Each one must either live under ``charts/`` or be listed in
``PENDING_CENTRALIZATION`` — the explicit registry of the original-six
renderers that still render inline and are scheduled to migrate into the
package (per the package docstring: "the others migrate here as they are
refactored to the shared component").

Two-way teeth:
  * A NEW chart renderer added outside ``charts/`` and not registered fails the
    build — chart-vocabulary sprawl can't sneak in.
  * The registry can't rot: every PENDING entry must still resolve to a real
    function, so migrating/renaming/deleting one forces its removal here.
"""
from __future__ import annotations

import ast
from pathlib import Path

_PKG = Path(__file__).resolve().parents[1] / "src" / "cfb_rankings"

# Locked-vocabulary keywords that mark a function as a chart-type renderer.
_CHART_KEYWORDS = (
    "chart", "heatmap", "choropleth", "sankey", "trajectory",
    "sparkline", "bump", "percentile_bar", "small_multiple",
)

# Inline chart renderers that predate the centralised charts/ package and are
# scheduled to migrate into it (D-007). This is migration debt made explicit:
# remove an entry when its renderer moves under charts/ (or is renamed/deleted).
# Paths are POSIX-relative to src/cfb_rankings/.
PENDING_CENTRALIZATION: frozenset[tuple[str, str]] = frozenset({
    ("dynasty_heatmap.py", "render_dynasty_heatmap_svg"),
    ("player_pages/development_trajectory.py", "render_development_trajectory"),
    ("player_pages/heisman_trajectory.py", "render_heisman_trajectory"),
    ("rankings_sparklines.py", "render_rank_trajectory_sparkline"),
    ("team_pages/game_recap_hero.py", "render_wp_chart"),
    ("team_pages/trajectory_chip.py", "render_trajectory_chip"),
    ("theme/percentile_bar.py", "render_percentile_bar"),
    ("theme/percentile_bar.py", "render_percentile_bars_grid"),
})


def _is_chart_renderer(name: str) -> bool:
    if not name.startswith("render_"):
        return False
    if name.endswith("_page"):  # page renderers are not chart components
        return False
    return any(kw in name for kw in _CHART_KEYWORDS)


def _chart_renderers() -> set[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    for path in _PKG.rglob("*.py"):
        rel = path.relative_to(_PKG).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover - defensive
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and _is_chart_renderer(node.name):
                found.add((rel, node.name))
    return found


def test_no_unregistered_chart_renderers_outside_package() -> None:
    offenders = {
        (rel, name)
        for (rel, name) in _chart_renderers()
        if not rel.startswith("charts/") and (rel, name) not in PENDING_CENTRALIZATION
    }
    assert not offenders, (
        "New chart-type renderer(s) defined outside cfb_rankings/charts/. Move "
        "them into the charts package (D-007), or — if they are inline renderers "
        "pending centralisation — add them to PENDING_CENTRALIZATION:\n  "
        + "\n  ".join(sorted(f"{r}::{n}" for r, n in offenders))
    )


def test_pending_centralization_registry_has_no_stale_entries() -> None:
    live = _chart_renderers()
    stale = {entry for entry in PENDING_CENTRALIZATION if entry not in live}
    assert not stale, (
        "PENDING_CENTRALIZATION lists renderer(s) that no longer exist (migrated, "
        "renamed, or deleted). Remove the stale entr(ies):\n  "
        + "\n  ".join(sorted(f"{r}::{n}" for r, n in stale))
    )


def test_charts_package_is_the_canonical_home() -> None:
    # Positive assertion: the centralised renderers actually live in the package.
    from cfb_rankings import charts

    assert hasattr(charts, "render_state_choropleth")
    assert hasattr(charts, "render_annotation_overlay")
