"""GitHub-issue alerting for the Data Health gate — one issue per regression CLASS.

The spec is explicit (§ "Surface + alerting"): **one deduped issue per regression
class, NOT per instance** — otherwise 136 unhealthy source instances would open
136 issues. So we roll the flagged ``CheckResult`` rows up into a small set of
classes, each with a STABLE title so re-runs dedupe against the open issue rather
than spamming a new one every build.

Regression classes (stable titles):
  * ``[data-health] <dataset> missing/sparse seasons`` — one per spine dataset
    with a critical completeness failure (e.g. ``games missing 2023``-style).
  * ``[data-health] N source feeds unhealthy``          — the freshness pillar.
  * ``[data-health] provenance coverage dropped``       — the provenance ratchet.
  * ``[data-health] <pillar> regressions``              — generic per-pillar catch
    for any other flagged pillar (validity / integrity / ...), so nothing slips
    through unalerted.

``open_issues(payloads, dry_run)`` mirrors ``scripts/verify_module_coverage.py``
exactly: same ``gh`` discovery, same label-create, same dedupe-by-search-then-
create flow, and the same "alerting must never crash the checker" guarantee. With
``dry_run`` it PRINTS what it would open and creates nothing.

Stdlib only.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from collections import defaultdict

# Label all data-health issues share — used for the dedupe search + auto-create.
ISSUE_LABEL = "data-health"

# Title prefix that makes every data-health issue greppable and stable.
_PREFIX = "[data-health]"


def _field(result, name: str):
    """Read ``name`` off a CheckResult object or a plain dict snapshot row."""
    if isinstance(result, dict):
        return result.get(name)
    return getattr(result, name, None)


def _is_flagged(result) -> bool:
    """A row worth alerting on: a hard ``fail`` (unknown is degraded, not a regression)."""
    return _field(result, "status") == "fail"


def _season_label(result) -> str:
    season = _field(result, "season")
    return "" if season is None else str(season)


# === class grouping =========================================================


def build_issue_payloads(gate, results) -> list[dict]:
    """Group the flagged results into per-class issue payloads.

    Returns a list of ``{"title": str, "body": str}`` — ONE entry per regression
    class with at least one flagged row. Titles are stable (no timestamps / no
    counts that churn run-to-run for completeness/provenance) so re-runs dedupe.

    Only ``fail`` rows drive issues. A GREEN/clean run returns ``[]`` (nothing to
    open). ``gate`` is accepted for the overall summary line in each body.
    """
    flagged = [r for r in results if _is_flagged(r)]
    if not flagged:
        return []

    overall = (gate or {}).get("overall", "?")
    summary = (gate or {}).get("summary", "")

    # dataset -> set(season labels) for critical completeness misses.
    completeness_missing: dict[str, set[str]] = defaultdict(set)
    # freshness source-class failures (collapse to one "N feeds unhealthy" issue).
    freshness_classes: list[str] = []
    freshness_overall_detail = ""
    # provenance failures (the ratchet drop).
    provenance_details: list[str] = []
    # any other pillar's failures -> one issue per pillar.
    other_by_pillar: dict[str, list[str]] = defaultdict(list)

    for r in flagged:
        pillar = _field(r, "pillar")
        check_id = _field(r, "check_id") or ""
        detail = _field(r, "detail") or ""

        if pillar == "completeness":
            dataset = _field(r, "dataset") or "unknown"
            season = _season_label(r)
            completeness_missing[dataset].add(season)
        elif pillar == "freshness":
            if check_id == "freshness.inventory.overall":
                freshness_overall_detail = detail
            elif check_id.startswith("freshness.source_class."):
                freshness_classes.append(
                    check_id[len("freshness.source_class."):]
                )
            else:
                freshness_classes.append(_field(r, "dataset") or check_id)
        elif pillar == "provenance":
            provenance_details.append(detail)
        else:
            other_by_pillar[str(pillar)].append(detail)

    payloads: list[dict] = []
    header = (
        f"Automated from `scripts/verify_data_health.py`. Overall gate: **{overall}**.\n\n"
        f"> {summary}\n\n"
    )

    # --- completeness: one issue per dataset (stable title, seasons in body) ---
    for dataset in sorted(completeness_missing):
        seasons = sorted(s for s in completeness_missing[dataset] if s)
        season_str = ", ".join(seasons) if seasons else "one or more seasons"
        title = f"{_PREFIX} {dataset} missing/sparse seasons"
        body = (
            header
            + f"The **{dataset}** spine dataset has critical completeness "
            f"failure(s) for: **{season_str}**.\n\n"
            f"Each failing season is a hole or half-season in a required spine "
            f"table — a publish-blocking data gap. Re-ingest the missing "
            f"season(s) and re-run `python scripts/verify_data_health.py` to clear."
        )
        payloads.append({"title": title, "body": body})

    # --- freshness: ONE issue for all unhealthy source feeds ---
    if freshness_classes or freshness_overall_detail:
        classes = sorted(set(freshness_classes))
        title = f"{_PREFIX} source feeds unhealthy"
        listed = "\n".join(f"- `{c}`" for c in classes) if classes else "- (see overall)"
        body = (
            header
            + "One or more source feeds are unhealthy (latest run errored / "
            "empty, or overdue vs their own cadence).\n\n"
            f"{freshness_overall_detail}\n\n"
            f"Unhealthy source class(es):\n{listed}\n\n"
            "Check the collector logs for the listed class(es); a stale/erroring "
            "feed is a schedule miss, not a corrupt DB."
        )
        payloads.append({"title": title, "body": body})

    # --- provenance: the canonical-coverage ratchet drop ---
    if provenance_details:
        title = f"{_PREFIX} provenance coverage dropped"
        detail_block = "\n".join(f"- {d}" for d in provenance_details)
        body = (
            header
            + "Canonical `source_id` provenance coverage regressed below its "
            "high-water mark — WP-0.7 provenance labelling is silently eroding.\n\n"
            f"{detail_block}\n\n"
            "Investigate the most recent ingest: a feed likely started writing "
            "rows without a resolvable `source_id` (legacy_unverified)."
        )
        payloads.append({"title": title, "body": body})

    # --- generic per-pillar catch-all for everything else (validity/integrity) ---
    for pillar in sorted(other_by_pillar):
        details = other_by_pillar[pillar]
        title = f"{_PREFIX} {pillar} regressions"
        detail_block = "\n".join(f"- {d}" for d in details)
        body = (
            header
            + f"The **{pillar}** pillar reported {len(details)} failing "
            f"assertion(s):\n\n{detail_block}\n\n"
            f"Run `python scripts/verify_data_health.py` for the full report "
            f"(with the failing SQL per assertion)."
        )
        payloads.append({"title": title, "body": body})

    return payloads


# === gh issue creation (mirrors verify_module_coverage.py) ==================


def _ensure_label(gh: str) -> None:
    """Create the shared label if missing — idempotent, errors swallowed."""
    try:
        subprocess.run(
            [gh, "label", "create", ISSUE_LABEL, "--color", "D93F0B",
             "--description", "Data Health gate regression (per-class)"],
            capture_output=True, text=True, timeout=60,
        )
    except Exception:  # noqa: BLE001 — label creation must never crash alerting
        pass


def _issue_exists(gh: str, title: str) -> bool:
    """True if an OPEN data-health issue with this exact title already exists.

    Stable titles mean a still-broken class dedupes against its open issue instead
    of opening a new one each run. Any gh failure -> treat as "unknown / does not
    exist" so we err toward surfacing rather than silently suppressing.
    """
    try:
        existing = subprocess.run(
            [gh, "issue", "list", "--label", ISSUE_LABEL, "--state", "open",
             "--search", title, "--json", "title", "--limit", "50"],
            capture_output=True, text=True, timeout=60,
        )
    except Exception:  # noqa: BLE001
        return False
    if existing.returncode != 0:
        return False
    out = existing.stdout or ""
    # The search is fuzzy; confirm an exact title match before suppressing.
    return f'"title": {json.dumps(title)}' in out or title in out


def open_issues(payloads, dry_run: bool) -> int:
    """Open (or, in dry-run, print) one gh issue per payload. Returns count acted on.

    dry_run=True  -> PRINT each title + first body line; create nothing.
    dry_run=False -> shell to ``gh issue create`` per payload, deduped by title.

    Never raises: ``gh`` missing / unauthed / erroring degrades to a printed
    warning, exactly like ``verify_module_coverage.py`` — alerting must never
    crash the checker or block a publish.
    """
    payloads = list(payloads or [])
    if not payloads:
        return 0

    if dry_run:
        print(f"[dry-run] would open {len(payloads)} data-health issue(s):")
        for p in payloads:
            first_line = (p.get("body", "").splitlines() or [""])[0]
            print(f"  - {p['title']}")
            if first_line:
                print(f"      {first_line}")
        return len(payloads)

    gh = shutil.which("gh")
    if not gh:
        print("::warning::gh not on PATH; skipping issue creation. Would have opened:")
        for p in payloads:
            print(f"  - {p['title']}")
        return 0

    _ensure_label(gh)

    opened = 0
    for p in payloads:
        title, body = p["title"], p.get("body", "")
        try:
            if _issue_exists(gh, title):
                print(f"   (open issue already exists; not duplicating) {title}")
                continue
            created = subprocess.run(
                [gh, "issue", "create", "--label", ISSUE_LABEL,
                 "--title", title, "--body", body],
                capture_output=True, text=True, timeout=60,
            )
            if created.returncode == 0:
                print(f"   opened: {title} -> {created.stdout.strip()}")
                opened += 1
            else:
                print(f"::warning::gh issue create failed for {title!r}: "
                      f"{created.stderr.strip()}")
        except Exception as exc:  # noqa: BLE001 — alerting must never crash the gate
            print(f"::warning::issue creation errored for {title!r}: {exc}")
    return opened
