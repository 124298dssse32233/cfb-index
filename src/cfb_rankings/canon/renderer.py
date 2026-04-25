"""Canon HTML renderer.

Composes index, per-list, and per-entry pages from templates + DB data.
Mirrors team_pages' single-file-per-page convention: every output file
is a standalone HTML document with the canon CSS inlined, no external
asset fetches required.

Templates live at ``canon/templates/*.html`` and use ``{name}`` /
``{name_html}`` substitution (no Jinja dependency, matching the
team_pages choice).
"""
from __future__ import annotations

import html as _html
import sqlite3
from pathlib import Path
from typing import Iterable

from .data import (
    fetch_list_meta, fetch_all_list_metas, fetch_entries,
    CanonListMeta, CanonEntry,
)


_ROOT = Path(__file__).resolve().parent
_TEMPLATES = _ROOT / "templates"
_ASSETS = _ROOT / "assets"


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _read_template(name: str) -> str:
    return (_TEMPLATES / name).read_text(encoding="utf-8")


def _read_styles() -> str:
    return (_ASSETS / "canon.css").read_text(encoding="utf-8")


def _h(s: str | None) -> str:
    """HTML-escape a value, treating None as empty string."""
    return _html.escape(s, quote=True) if s else ""


def _safe_path_segment(s: str) -> str:
    return "".join(c for c in s if c.isalnum() or c in "-_").lower()


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _delta_class(label: str | None) -> str:
    if not label or label.startswith("→"):
        return "flat"
    if label.startswith("↑ NEW") or "NEW" in label:
        return "new"
    if label.startswith("↑"):
        return "up"
    if label.startswith("↓"):
        return "down"
    return "flat"


def _cohort_label_class(label: str | None) -> str:
    if not label:
        return "consensus"
    return label.replace(" ", "-").lower()


# --------------------------------------------------------------------------
# Top entries (ranks 1-N), mid entries (ranks N+1..M), footer entries
# --------------------------------------------------------------------------

def _render_top_entry(e: CanonEntry, list_slug: str, anchor_url: str) -> str:
    chips: list[str] = []
    if e.program_label:
        chips.append(f'<span class="canon-chip canon-chip--program">{_h(e.program_label)}</span>')
    if e.era_label:
        chips.append(f'<span class="canon-chip canon-chip--era">{_h(e.era_label)}</span>')
    if e.rank_delta_label:
        chips.append(
            f'<span class="canon-rank-delta canon-rank-delta--{_delta_class(e.rank_delta_label)}">'
            f'{_h(e.rank_delta_label)}</span>'
        )

    chips_html = "".join(chips)

    # mini-viz only when stat/casual ranks meaningfully diverge from each other
    if (
        e.cohort_split_stat_rank is not None
        and e.cohort_split_casual_rank is not None
    ):
        verdict_class = _cohort_label_class(e.cohort_split_label).replace(
            "-divergence", ""
        )
        mini_viz = (
            '<div class="canon-mini-viz" aria-label="Cohort divergence">'
            '<span class="canon-mini-viz__label">Cohort split</span>'
            f'<span class="canon-mini-viz__rank canon-mini-viz__rank--stat">stat #{e.cohort_split_stat_rank}</span>'
            '<span class="canon-mini-viz__divider">|</span>'
            f'<span class="canon-mini-viz__rank canon-mini-viz__rank--casual">casual #{e.cohort_split_casual_rank}</span>'
            f'<span class="canon-mini-viz__verdict canon-mini-viz__verdict--{verdict_class}">{_h(e.cohort_split_label or "")}</span>'
            '</div>'
        )
    else:
        mini_viz = ""

    statline_html = (
        f'<p class="canon-top-entry__statline">{_h(e.statline)}</p>'
        if e.statline else ""
    )
    paragraph_html = (
        f'<p class="canon-top-entry__paragraph">{_h(e.editorial_paragraph)}</p>'
        if e.editorial_paragraph else ""
    )

    return (
        '<article class="canon-top-entry">'
        f'<div class="canon-top-entry__rank">{e.rank}</div>'
        '<div class="canon-top-entry__body">'
        f'<h2 class="canon-top-entry__title">'
        f'<a href="{anchor_url}">{_h(e.entity_display_name)}</a>'
        '</h2>'
        f'<div class="canon-top-entry__chips">{chips_html}</div>'
        f'{statline_html}'
        f'{paragraph_html}'
        f'{mini_viz}'
        '</div>'
        '</article>'
    )


def _render_mid_entry(e: CanonEntry, anchor_url: str) -> str:
    delta_html = ""
    if e.rank_delta_label:
        delta_html = (
            f'<span class="canon-rank-delta canon-rank-delta--{_delta_class(e.rank_delta_label)}">'
            f'{_h(e.rank_delta_label)}</span>'
        )
    return (
        '<li class="canon-mid-entry">'
        f'<div class="canon-mid-entry__rank">{e.rank}</div>'
        '<div class="canon-mid-entry__body">'
        f'<p class="canon-mid-entry__title"><a href="{anchor_url}">{_h(e.entity_display_name)}</a></p>'
        f'<p class="canon-mid-entry__summary">{_h(e.summary_short)}</p>'
        '</div>'
        f'<div class="canon-mid-entry__delta">{delta_html}</div>'
        '</li>'
    )


def _render_footer_entry(e: CanonEntry, anchor_url: str) -> str:
    return (
        '<li class="canon-footer-entry">'
        f'<div class="canon-footer-entry__rank">#{e.rank}</div>'
        '<div class="canon-footer-entry__line">'
        f'<a href="{anchor_url}">{_h(e.entity_display_name)}</a>'
        f'<span class="canon-footer-entry__line--summary"> — {_h(e.summary_short)}</span>'
        '</div>'
        '</li>'
    )


# --------------------------------------------------------------------------
# Per-list page
# --------------------------------------------------------------------------

def _split_buckets(entries: list[CanonEntry], list_slug: str) -> tuple[
    list[CanonEntry], list[CanonEntry], list[CanonEntry], int, int,
]:
    """Return (top, mid, footer, mid_start, mid_end) given list slug.

    * Players: top=ranks 1-5, mid=6-25, footer=26-100
    * Games:   top=ranks 1-5, mid=6-15, footer=16-50
    * Coaching: top=ranks 1-5, mid=6-15, footer=16-25 (all have paragraphs)
    """
    if list_slug == "the-100-best-players-cfp-era":
        top = [e for e in entries if e.rank <= 5]
        mid = [e for e in entries if 6 <= e.rank <= 25]
        footer = [e for e in entries if e.rank >= 26]
        return top, mid, footer, 6, 25
    if list_slug == "the-50-most-defining-games-cfp-era":
        top = [e for e in entries if e.rank <= 5]
        mid = [e for e in entries if 6 <= e.rank <= 15]
        footer = [e for e in entries if e.rank >= 16]
        return top, mid, footer, 6, 15
    if list_slug == "the-25-best-coaching-hires-2020s":
        top = [e for e in entries if e.rank <= 5]
        mid = [e for e in entries if 6 <= e.rank <= 15]
        footer = [e for e in entries if e.rank >= 16]
        return top, mid, footer, 6, 15
    # default fallback
    top = entries[:5]
    mid = entries[5:25]
    footer = entries[25:]
    return top, mid, footer, 6, 25


def _entry_url(list_slug: str, e: CanonEntry) -> str:
    return f"/canon/{list_slug}/{_safe_path_segment(e.entity_slug)}.html"


def _stat_strip_data(entries: list[CanonEntry]) -> dict:
    """Compute the four metrics shown in the stat-strip header."""
    consensus = sum(1 for e in entries if e.cohort_split_label == "consensus")
    slight = sum(1 for e in entries if e.cohort_split_label == "slight divergence")
    wide = sum(1 for e in entries if e.cohort_split_label == "wide divergence")
    top25 = [e for e in entries if e.rank <= 25]
    deltas = [
        abs(e.prior_year_rank - e.rank)
        for e in top25
        if e.prior_year_rank is not None
    ]
    if deltas:
        mean = sum(deltas) / len(deltas)
        mean_str = f"{mean:.1f}"
    else:
        mean_str = "— (v1 edition)"
    return {
        "consensus_count": consensus,
        "slight_div_count": slight,
        "wide_div_count": wide,
        "mean_delta": mean_str,
    }


def render_canon_list(
    con: sqlite3.Connection,
    list_slug: str,
    output_dir: Path | str,
) -> Path:
    """Render the per-list page (and per-entry pages for entries with paragraphs)."""
    meta = fetch_list_meta(con, list_slug)
    if meta is None:
        raise ValueError(f"list_slug not seeded: {list_slug!r}")
    entries = fetch_entries(con, list_slug)
    if not entries:
        raise ValueError(f"no entries for list_slug={list_slug!r}; "
                         f"run generate-canon-list first")

    output_dir = Path(output_dir)
    canon_dir = _ensure_dir(output_dir / "canon")
    list_entry_dir = _ensure_dir(canon_dir / list_slug)

    # ---- per-entry pages
    entry_template = _read_template("canon_entry.html")
    styles = _read_styles()
    for e in entries:
        _write_entry_page(
            entry_template, styles, meta, e, list_entry_dir,
        )

    # ---- list page
    top, mid, footer, mid_start, mid_end = _split_buckets(entries, list_slug)
    stat_strip = _stat_strip_data(entries)

    top_html = "".join(
        _render_top_entry(e, list_slug, _entry_url(list_slug, e)) for e in top
    )
    mid_html = "".join(
        _render_mid_entry(e, _entry_url(list_slug, e)) for e in mid
    )
    if footer:
        footer_html = "".join(
            _render_footer_entry(e, _entry_url(list_slug, e)) for e in footer
        )
        footer_section = (
            '<section class="canon-footer-entries" '
            f'aria-label="Ranks {footer[0].rank}–{footer[-1].rank}">'
            f'<h2 class="canon-footer-entries__title">'
            f'Ranks {footer[0].rank}–{footer[-1].rank}</h2>'
            '<ol class="canon-footer-entries__list" '
            f'start="{footer[0].rank}">'
            f'{footer_html}</ol></section>'
        )
    else:
        footer_section = ""

    template = _read_template("canon_list.html")
    page = template.format(
        styles_css=styles,
        list_title=_h(meta.title),
        list_description=_h(meta.description),
        edition_year=meta.edition_year,
        entry_count=meta.entry_count,
        published_at="2026-04-25",
        next_revision_year=meta.next_revision_year or "TBD",
        consensus_count=stat_strip["consensus_count"],
        slight_div_count=stat_strip["slight_div_count"],
        wide_div_count=stat_strip["wide_div_count"],
        mean_delta=stat_strip["mean_delta"],
        top_entries_html=top_html,
        mid_start=mid_start,
        mid_end=mid_end,
        mid_entries_html=mid_html,
        footer_entries_section=footer_section,
        methodology_notes=_h(meta.methodology_notes or ""),
    )

    out_path = canon_dir / f"{list_slug}.html"
    out_path.write_text(page, encoding="utf-8")
    return out_path


def _write_entry_page(
    template: str,
    styles: str,
    meta: CanonListMeta,
    e: CanonEntry,
    out_dir: Path,
) -> Path:
    program_chip = (
        f'<span class="canon-chip canon-chip--program">{_h(e.program_label)}</span>'
        if e.program_label else ""
    )
    era_chip = (
        f'<span class="canon-chip canon-chip--era">{_h(e.era_label)}</span>'
        if e.era_label else ""
    )
    paragraph_html = (
        f'<section class="canon-entry__paragraph-wrap" aria-label="Editorial">'
        f'<p class="canon-entry__paragraph">{_h(e.editorial_paragraph)}</p>'
        '</section>'
        if e.editorial_paragraph else ""
    )

    cross_refs: list[str] = []
    if e.program_slug:
        cross_refs.append(
            f'<li><a href="/teams/{_h(e.program_slug)}.html">'
            f'See the {_h(e.program_label or e.program_slug)} program page →</a></li>'
        )
    cross_refs.append(
        f'<li><a href="/canon/{meta.list_slug}.html">'
        f'Back to {_h(meta.title)} →</a></li>'
    )
    if cross_refs:
        cross_refs_html = (
            '<section class="canon-entry__cross-references" '
            'aria-label="Cross-references">'
            '<h2 class="canon-entry__section-title">Related</h2>'
            f'<ul>{"".join(cross_refs)}</ul>'
            '</section>'
        )
    else:
        cross_refs_html = ""

    page = template.format(
        styles_css=styles,
        list_title=_h(meta.title),
        list_slug=_h(meta.list_slug),
        edition_year=meta.edition_year,
        next_revision_year=meta.next_revision_year or "TBD",
        rank=e.rank,
        entity_display_name=_h(e.entity_display_name),
        summary_short=_h(e.summary_short),
        program_chip_html=program_chip,
        era_chip_html=era_chip,
        statline=_h(e.statline or "—"),
        paragraph_html=paragraph_html,
        cohort_stat_rank=e.cohort_split_stat_rank or e.rank,
        cohort_casual_rank=e.cohort_split_casual_rank or e.rank,
        cohort_label=_h(e.cohort_split_label or "consensus"),
        cohort_label_class=_cohort_label_class(e.cohort_split_label),
        prior_year_rank_text=str(e.prior_year_rank) if e.prior_year_rank else "—",
        rank_delta_label=_h(e.rank_delta_label or "—"),
        cross_reference_html=cross_refs_html,
    )

    out_path = out_dir / f"{_safe_path_segment(e.entity_slug)}.html"
    out_path.write_text(page, encoding="utf-8")
    return out_path


# --------------------------------------------------------------------------
# Index page
# --------------------------------------------------------------------------

def _render_list_card(meta: CanonListMeta) -> str:
    return (
        '<a class="canon-list-card" href="/canon/' + _h(meta.list_slug) + '.html">'
        f'<p class="canon-list-card__eyebrow">{meta.edition_year} edition</p>'
        f'<h2 class="canon-list-card__title">{_h(meta.title)}</h2>'
        f'<p class="canon-list-card__dek">{_h(meta.description)}</p>'
        '<div class="canon-list-card__meta">'
        f'<span>{meta.entry_count} entries</span>'
        f'<span>Next revision {meta.next_revision_year or "TBD"}</span>'
        '</div>'
        '</a>'
    )


def render_canon_index(
    con: sqlite3.Connection,
    output_dir: Path | str,
) -> Path:
    """Render the canon/ index landing page."""
    metas = fetch_all_list_metas(con)
    if not metas:
        raise ValueError("no canon_lists rows; run seed-canon-metadata first")
    output_dir = Path(output_dir)
    canon_dir = _ensure_dir(output_dir / "canon")

    edition_year = max((m.edition_year for m in metas), default=2026)
    next_rev = max(
        (m.next_revision_year for m in metas if m.next_revision_year), default=2027,
    )

    cards_html = "".join(_render_list_card(m) for m in metas)
    page = _read_template("canon_index.html").format(
        styles_css=_read_styles(),
        edition_year=edition_year,
        next_revision_year=next_rev,
        list_cards=cards_html,
    )
    out_path = canon_dir / "index.html"
    out_path.write_text(page, encoding="utf-8")
    return out_path


def render_all_canon(
    con: sqlite3.Connection,
    output_dir: Path | str,
) -> dict[str, int]:
    """Render index + every list + every per-entry page.

    Returns a counts dict: ``{'lists': N, 'entries': M, 'index': 1}``.
    """
    metas = fetch_all_list_metas(con)
    if not metas:
        raise ValueError("no canon_lists rows; run seed-canon-metadata first")

    counts = {"lists": 0, "entries": 0, "index": 0}
    for m in metas:
        try:
            render_canon_list(con, m.list_slug, output_dir)
            counts["lists"] += 1
            entries = fetch_entries(con, m.list_slug)
            counts["entries"] += len(entries)
        except ValueError as exc:
            print(f"  canon: {m.list_slug} skipped — {exc}")
    render_canon_index(con, output_dir)
    counts["index"] = 1
    return counts
