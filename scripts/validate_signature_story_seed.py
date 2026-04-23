"""Validate seeds/signature_story_metrics.yaml.

Checks:
  1. Top-level structure is {cohorts: [...], metrics: [...]}.
  2. Every cohort has required fields and a unique id.
  3. Every metric has required fields, a valid cohort reference, and a
     narrative_weight in [0, 1].
  4. Every SQL template (both `sql_query_template` and `cohort_sql_template`)
     parses cleanly as a SQLite statement after substituting parameters and
     format placeholders ({cohort_filter}, {cohort_filter_pvm_or_team}).

Run:
    python scripts/validate_signature_story_seed.py

Exits 0 on success, 1 on any validation error. Errors printed one per line.
"""
from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

import yaml

SEED_PATH = Path(__file__).resolve().parent.parent / "seeds" / "signature_story_metrics.yaml"
DB_PATH = Path(__file__).resolve().parent.parent / "cfb_rankings.db"

REQUIRED_METRIC_FIELDS = {
    "id",
    "label",
    "unit",
    "higher_is_better",
    "position",
    "cohort",
    "min_volume",
    "volume_field",
    "narrative_weight",
    "narrative_template",
    "sql_query_template",
    "cohort_sql_template",
}
REQUIRED_COHORT_FIELDS = {"id", "label", "sql_filter", "min_qualifying_members"}

# Python-style %(name)s params in the templates — substitute with sqlite ? params.
PARAM_RE = re.compile(r"%\((\w+)\)s")

# Format placeholders like {cohort_filter} and {cohort_filter_pvm_or_team}.
PLACEHOLDERS = {
    "cohort_filter": "1 = 1",
    "cohort_filter_pvm": "1 = 1",
    "cohort_filter_pvm_or_team": "1 = 1",
}


def _substitute(sql: str) -> tuple[str, list[str]]:
    """Return (sqlite-ready SQL, list of bound param names in order)."""
    params: list[str] = []

    def _sub(match: re.Match[str]) -> str:
        params.append(match.group(1))
        return "?"

    prepared = PARAM_RE.sub(_sub, sql)
    for key, replacement in PLACEHOLDERS.items():
        prepared = prepared.replace("{" + key + "}", replacement)
    # Anything left like {foo} is an unknown placeholder — flag it.
    leftover = re.findall(r"\{(\w+)\}", prepared)
    if leftover:
        raise ValueError(f"unknown format placeholders: {leftover}")
    return prepared, params


def _try_parse(conn: sqlite3.Connection, sql: str, param_count: int) -> None:
    """Parse the statement without running it, using EXPLAIN."""
    # EXPLAIN still validates binding count; supply dummy args.
    conn.execute("EXPLAIN " + sql, [None] * param_count)


def _dummy_params(param_names: list[str], metric: dict) -> list:
    """Return plausible dummy values for the named params."""
    mapping = {
        "player_id": 4788,           # CJ Carr, confirmed exists
        "season_year": 2025,
        "week": 99,
        "min_volume": metric.get("min_volume", 0),
    }
    return [mapping.get(n, 0) for n in param_names]


def main() -> int:
    if not SEED_PATH.exists():
        print(f"error: seed file not found: {SEED_PATH}")
        return 1

    raw = yaml.safe_load(SEED_PATH.read_text(encoding="utf-8"))
    errors: list[str] = []

    if not isinstance(raw, dict):
        errors.append("top level is not a mapping")
        _print_and_exit(errors)

    cohorts = raw.get("cohorts") or []
    metrics = raw.get("metrics") or []

    cohort_ids: set[str] = set()
    for idx, c in enumerate(cohorts):
        missing = REQUIRED_COHORT_FIELDS - set(c or {})
        if missing:
            errors.append(f"cohort[{idx}] missing fields: {sorted(missing)}")
            continue
        if c["id"] in cohort_ids:
            errors.append(f"cohort[{idx}] duplicate id: {c['id']}")
        cohort_ids.add(c["id"])

    if DB_PATH.exists():
        conn = sqlite3.connect(DB_PATH)
    else:
        print(f"warn: db not found at {DB_PATH}; SQL parse check will use :memory:")
        conn = sqlite3.connect(":memory:")

    metric_ids: set[str] = set()
    for idx, m in enumerate(metrics):
        mid = (m or {}).get("id", f"<anon#{idx}>")
        missing = REQUIRED_METRIC_FIELDS - set(m or {})
        if missing:
            errors.append(f"metric[{mid}] missing fields: {sorted(missing)}")
            continue
        if m["id"] in metric_ids:
            errors.append(f"metric[{mid}] duplicate id")
        metric_ids.add(m["id"])
        if m["cohort"] not in cohort_ids:
            errors.append(f"metric[{mid}] references unknown cohort: {m['cohort']}")
        nw = m["narrative_weight"]
        if not (isinstance(nw, (int, float)) and 0.0 <= nw <= 1.0):
            errors.append(f"metric[{mid}] narrative_weight out of range: {nw!r}")

        for field in ("sql_query_template", "cohort_sql_template"):
            try:
                prepared, params = _substitute(m[field])
            except ValueError as exc:
                errors.append(f"metric[{mid}] {field}: {exc}")
                continue
            try:
                _try_parse(conn, prepared, len(params))
            except sqlite3.Error as exc:
                errors.append(f"metric[{mid}] {field}: SQL parse error — {exc}")
                continue
            # Harder check: can it execute against the real DB with dummy args?
            if DB_PATH.exists():
                dummy = _dummy_params(params, m)
                try:
                    conn.execute(prepared, dummy).fetchmany(1)
                except sqlite3.Error as exc:
                    errors.append(f"metric[{mid}] {field}: execution error — {exc}")

    return _print_and_exit(errors, metrics_count=len(metrics), cohorts_count=len(cohorts))


def _print_and_exit(errors: list[str], *, metrics_count: int = 0, cohorts_count: int = 0) -> int:
    if errors:
        print(f"FAILED ({len(errors)} errors)")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"OK: {cohorts_count} cohorts, {metrics_count} metrics — all SQL templates parse.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
