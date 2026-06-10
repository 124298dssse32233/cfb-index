"""Chronicle pipeline CLI entry point.

Usage:
    python -m cfb_rankings.chronicle.run generate --tier S --batch-id 2026-w12-S
    python -m cfb_rankings.chronicle.run generate --tier T1 --max-cards 100 --no-cloud
    python -m cfb_rankings.chronicle.run generate --use-lkg-only --tier S
    python -m cfb_rankings.chronicle.run health
    python -m cfb_rankings.chronicle.run seed --from-voice-validator

Subcommands (via argparse subparsers):
    generate   — run the full generation pipeline for a tier/card-type set (default)
    health     — runtime health check (GPU, llama-server, DB)
    seed       — populate banlist / narrative state for initial bootstrap

Pipeline flow for ``generate``:
    1. Build router (runtime.build_default_router)
    2. Determine target entities for the requested tier (retriever.entities_for_tier)
    3. For each entity, retrieve evidence (retriever.retrieve_evidence)
    4. Call Planner → Writer → FactCritic → VoiceCritic → Refiner agents
       (TODO P3: cfb_rankings.chronicle.pipeline — not yet implemented)
    5. Store raw card output in chronicle_card_cache (cache.store_card)
    6. Run batch eval (eval.evaluate_batch)
    7. Promote passing cards to LKG (lkg.promote_to_lkg)
    8. Record batch observation for antislop drift tracking
       (TODO P2: cfb_rankings.chronicle.antislop — not yet implemented)
    9. Run drift detection (eval.detect_drift)
    10. Emit batch summary to stdout + GitHub Actions step summary

Module stubs referenced here are wired in during their respective pipeline
phases:
    P1: runtime (LocalLlamaBackend + DeepInfraBackend + Router)    ← in progress
    P2: antislop (record_batch_observation, update_ban_list)        ← in progress
    P3: pipeline (Planner, Writer, FactCritic, VoiceCritic, Refiner) ← pending
    P4: eval (evaluate_batch, detect_drift, write_to_langfuse)      ← in progress
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import date, timezone, datetime
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="cfb_rankings.chronicle.run",
        description="Chronicle card-generation pipeline CLI",
    )
    sub = p.add_subparsers(dest="cmd")

    # ---- generate subcommand -----------------------------------------------
    gen = sub.add_parser("generate", help="Generate cards for a tier")
    gen.add_argument(
        "--tier",
        choices=["S", "T1", "T2", "T3"],
        required=True,
        help="Tier S = Tier S Flashpoint (top-25/10); T1 = Tier 1; T2 = Tier 2; T3 = Tier 3",
    )
    gen.add_argument(
        "--card-types",
        default="",
        help=(
            "Comma-separated card type filter — e.g. 'flashpoint,player_arc'. "
            "Empty string (default) = all defaults for the tier."
        ),
    )
    gen.add_argument(
        "--max-cards",
        type=int,
        default=0,
        help="Hard cap on cards generated this run (0 = no cap)",
    )
    gen.add_argument(
        "--batch-id",
        default=None,
        help=(
            "Stable identifier for this batch, e.g. '2026-w12-S'. "
            "Defaults to ISO year-week + tier if not provided."
        ),
    )
    gen.add_argument(
        "--use-lkg-only",
        action="store_true",
        help=(
            "Skip generation entirely. Use LKG cards already on disk. "
            "Triggers an emergency site rebuild from cached content."
        ),
    )
    # --allow-cloud / --no-cloud are mutually exclusive flags.
    # Default: allow-cloud is ON for all tiers (DeepInfra fallback available).
    cloud_group = gen.add_mutually_exclusive_group()
    cloud_group.add_argument(
        "--allow-cloud",
        dest="allow_cloud",
        action="store_true",
        default=True,
        help="Allow DeepInfra cloud fallback for Tier 2/3 (default: enabled)",
    )
    cloud_group.add_argument(
        "--no-cloud",
        dest="allow_cloud",
        action="store_false",
        help="Disable DeepInfra cloud fallback — local backends only",
    )
    gen.add_argument(
        "--dry-run",
        action="store_true",
        help="Plan what would be generated but make no LLM calls and write nothing",
    )
    gen.add_argument(
        "--db",
        default="cfb_rankings.db",
        help="Path to SQLite DB (default: cfb_rankings.db in CWD)",
    )

    # ---- health subcommand -------------------------------------------------
    health = sub.add_parser("health", help="Health-check the runtime (GPU, llama-server, DB)")
    health.add_argument(
        "--db",
        default="cfb_rankings.db",
        help="Path to SQLite DB (default: cfb_rankings.db in CWD)",
    )

    # ---- seed subcommand ---------------------------------------------------
    seed = sub.add_parser("seed", help="Bootstrap narrative state + banlist")
    seed.add_argument(
        "--from-voice-validator",
        action="store_true",
        help="Seed ban-list from voice-validator outputs in logs/chronicle/",
    )
    seed.add_argument(
        "--db",
        default="cfb_rankings.db",
        help="Path to SQLite DB (default: cfb_rankings.db in CWD)",
    )

    return p.parse_args(argv)


# ---------------------------------------------------------------------------
# Batch ID helper
# ---------------------------------------------------------------------------

def _default_batch_id(tier: str) -> str:
    """Generate a stable batch ID like '2026-w21-S'."""
    today = date.today()
    iso = today.isocalendar()
    return f"{iso[0]}-w{iso[1]:02d}-{tier}"


# ---------------------------------------------------------------------------
# Step summary helper (GitHub Actions)
# ---------------------------------------------------------------------------

def _write_step_summary(text: str) -> None:
    """Append text to $GITHUB_STEP_SUMMARY if running in GitHub Actions."""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        try:
            Path(summary_path).open("a", encoding="utf-8").write(text + "\n")
        except OSError:
            pass  # Non-fatal — summary is best-effort


# ---------------------------------------------------------------------------
# cmd_generate
# ---------------------------------------------------------------------------

def cmd_generate(args: argparse.Namespace) -> int:
    """Run the full five-agent generation pipeline for a tier.

    Flow:
      1. Build router via build_default_router(allow_cloud=args.allow_cloud)
      2. Open DB
      3. On --dry-run: select entities and print would-generate list, then exit
      4. Call run_tier_batch(db, tier, router, config, max_cards, card_types)
      5. Print aggregate stats + write GitHub Actions step summary
    """
    import sqlite3

    from cfb_rankings.chronicle import lkg as lkg_mod
    from cfb_rankings.chronicle.pipeline import PipelineConfig, run_tier_batch
    from cfb_rankings.chronicle.runtime import CardTier, build_default_router

    tier_str = args.tier
    batch_id = args.batch_id or _default_batch_id(tier_str)
    max_cards = args.max_cards
    card_types_filter: list[str] = (
        [ct.strip() for ct in args.card_types.split(",") if ct.strip()]
        if args.card_types
        else []
    )

    log.info(
        "chronicle generate — tier=%s batch_id=%s max_cards=%s "
        "use_lkg_only=%s allow_cloud=%s dry_run=%s card_types=%s",
        tier_str, batch_id, max_cards, args.use_lkg_only,
        args.allow_cloud, args.dry_run, card_types_filter or "(tier defaults)",
    )

    # ---- LKG-only shortcut -------------------------------------------------
    if args.use_lkg_only:
        log.info("[generate] --use-lkg-only: skipping generation, loading LKG from disk")
        try:
            imported = lkg_mod.import_lkg_from_disk()
        except Exception as exc:
            log.error("[generate] LKG import failed: %s", exc)
            imported = {"cards_imported": 0}
        n_imported = imported.get("cards_imported", 0) if isinstance(imported, dict) else imported
        log.info("[generate] LKG-only import done: %s cards loaded", n_imported)
        _write_step_summary(
            f"## Chronicle — LKG-only mode\n\n"
            f"- Batch: `{batch_id}`\n"
            f"- Tier: {tier_str}\n"
            f"- Cards imported from disk: {n_imported}\n"
        )
        return 0

    # ---- Resolve tier enum -------------------------------------------------
    tier_map = {"S": CardTier.S, "T1": CardTier.T1, "T2": CardTier.T2, "T3": CardTier.T3}
    tier = tier_map.get(tier_str, CardTier.T3)

    # ---- Build router ------------------------------------------------------
    log.info("[generate] Step 1: building router (allow_cloud=%s)", args.allow_cloud)
    try:
        router = build_default_router(allow_cloud=args.allow_cloud)
    except Exception as exc:
        log.error("[generate] Router build failed: %s — aborting", exc)
        return 1

    # ---- Open DB -----------------------------------------------------------
    db_path = Path(args.db)
    if not db_path.exists():
        log.error("[generate] DB not found at %s — aborting", db_path)
        print(f"ERROR: DB not found at {db_path}")
        return 1

    # Use a thin sqlite3 wrapper that satisfies the chronicle module contracts
    class _DB:
        """Minimal sqlite3 wrapper compatible with chronicle modules."""

        def __init__(self, path: str) -> None:
            import sqlite3 as _sq
            self._conn = _sq.connect(path)
            self._conn.row_factory = _sq.Row

        def query_all(self, sql: str, params=()) -> list[dict]:
            try:
                cur = self._conn.execute(sql, params)
                rows = cur.fetchall()
                return [dict(r) for r in rows]
            except Exception as exc:
                log.debug("_DB.query_all failed: %s | %s", sql[:60], exc)
                return []

        def query_one(self, sql: str, params=()) -> dict | None:
            rows = self.query_all(sql, params)
            return rows[0] if rows else None

        def execute(self, sql: str, params=()) -> Any:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            return cur

        def commit(self) -> None:
            self._conn.commit()

    db = _DB(str(db_path))

    # ---- Dry-run: show what would be generated and exit --------------------
    if args.dry_run:
        log.info("[generate] --dry-run: selecting entities and printing plan")
        from cfb_rankings.chronicle.pipeline import _select_entities_for_tier
        targets = _select_entities_for_tier(db, tier, max_count=max_cards or 0)
        print(f"Dry run — tier={tier_str} batch_id={batch_id}")
        print(f"Would generate cards for {len(targets)} entities:")
        for t in targets[:20]:
            card_type_str = ", ".join(t.card_types or []) or "(tier defaults)"
            print(f"  {t.entity_kind}/{t.slug}  slots={t.n_slots}  types=[{card_type_str}]")
        if len(targets) > 20:
            print(f"  ... and {len(targets) - 20} more")
        return 0

    # ---- Build PipelineConfig ----------------------------------------------
    config = PipelineConfig.for_tier(tier)

    # ---- Run batch ---------------------------------------------------------
    log.info("[generate] Step 2: running pipeline batch tier=%s max_cards=%d", tier_str, max_cards)
    try:
        page_results = run_tier_batch(
            db=db,
            tier=tier,
            router=router,
            config=config,
            max_cards=max_cards,
            card_types_override=card_types_filter or None,
            batch_id=batch_id,
        )
    except Exception as exc:
        log.error("[generate] run_tier_batch raised: %s", exc, exc_info=True)
        print(f"ERROR: pipeline batch failed: {exc}")
        return 1

    # ---- Aggregate stats ---------------------------------------------------
    n_pages = len(page_results)
    total_shipped = sum(r.shipped_count for r in page_results)
    total_suppressed = sum(r.suppressed_count for r in page_results)
    total_failed = sum(r.failed_count for r in page_results)

    # Count cache hits
    total_cache_hits = sum(
        sum(1 for cr in r.cards if cr.action == "cache_hit")
        for r in page_results
    )

    # ---- Step summary output -----------------------------------------------
    summary = (
        f"## Chronicle batch `{batch_id}`\n\n"
        f"| Field | Value |\n"
        f"|---|---|\n"
        f"| Tier | {tier_str} |\n"
        f"| Card types | {', '.join(card_types_filter) or '(tier defaults)'} |\n"
        f"| Pages processed | {n_pages} |\n"
        f"| Cards shipped | {total_shipped} |\n"
        f"| Cards suppressed | {total_suppressed} |\n"
        f"| Cards failed | {total_failed} |\n"
        f"| Cache hits | {total_cache_hits} |\n"
    )
    print(summary)
    _write_step_summary(summary)

    log.info(
        "[generate] done — tier=%s batch_id=%s pages=%d shipped=%d suppressed=%d failed=%d",
        tier_str, batch_id, n_pages, total_shipped, total_suppressed, total_failed,
    )
    return 0


# ---------------------------------------------------------------------------
# cmd_health
# ---------------------------------------------------------------------------

def cmd_health(args: argparse.Namespace) -> int:
    """Health-check the runtime: GPU, llama-server endpoints, DB."""
    import sqlite3

    errors: list[str] = []
    print("Chronicle runtime health check")
    print("=" * 40)

    # GPU check
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.free",
             "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            gpu_info = result.stdout.strip()
            print(f"  GPU          OK — {gpu_info}")
        else:
            msg = "nvidia-smi returned non-zero"
            print(f"  GPU          FAIL — {msg}")
            errors.append(msg)
    except FileNotFoundError:
        msg = "nvidia-smi not found"
        print(f"  GPU          FAIL — {msg}")
        errors.append(msg)
    except Exception as exc:
        msg = str(exc)
        print(f"  GPU          FAIL — {msg}")
        errors.append(msg)

    # LLM backend checks — Ollama is the production path (2026-05-24
    # activation); the two llama-server ports are the original design and
    # remain an accepted alternative. Healthy = EITHER backend serving the
    # configured models, so an Ollama-only box (RTX 3090, 2026-06) passes
    # without phantom llama-server errors.
    import json as _json
    import os as _os
    import urllib.request
    import urllib.error
    ollama_ok = False
    try:
        req = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5)
        tags = _json.loads(req.read().decode())
        pulled = {m.get("name", "") for m in tags.get("models", [])}
        writer = _os.environ.get(
            "CHRONICLE_OLLAMA_WRITER", "mistral-nemo:12b-instruct-2407-q4_K_M")
        planner = _os.environ.get("CHRONICLE_OLLAMA_PLANNER", "qwen3:8b")
        missing = [m for m in (writer, planner)
                   if m not in pulled and f"{m}:latest" not in pulled]
        if missing:
            msg = f"Ollama up but missing models: {missing} (pulled: {sorted(pulled)})"
            print(f"  ollama:11434  FAIL — {msg}")
            errors.append(msg)
        else:
            ollama_ok = True
            print(f"  ollama:11434  OK — writer={writer} planner={planner}")
    except (urllib.error.URLError, OSError, ValueError) as exc:
        print(f"  ollama:11434  down — {exc} (checking llama-server fallback)")

    if not ollama_ok:
        for port, label in [(8001, "llama-server:8001 (Tier S/T1)"),
                            (8002, "llama-server:8002 (Tier 2/3)")]:
            try:
                req = urllib.request.urlopen(
                    f"http://localhost:{port}/health", timeout=5
                )
                body = req.read().decode()
                print(f"  {label}  OK — {body[:60]}")
            except urllib.error.URLError as exc:
                msg = str(exc.reason)
                print(f"  {label}  FAIL — {msg}")
                errors.append(f":{port} {msg}")

    # DB check
    db_path = Path(args.db)
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            team_count = conn.execute(
                "SELECT COUNT(*) FROM teams"
            ).fetchone()[0]
            conn.close()
            print(f"  DB           OK — {db_path} ({team_count} teams)")
        except Exception as exc:
            msg = str(exc)
            print(f"  DB           FAIL — {msg}")
            errors.append(msg)
    else:
        msg = f"{db_path} not found"
        print(f"  DB           FAIL — {msg}")
        errors.append(msg)

    # Runtime module import check
    try:
        from cfb_rankings.chronicle.runtime import build_default_router
        router = build_default_router()
        print(f"  runtime      OK — {len(router.routes)} routes configured")
    except Exception as exc:
        msg = str(exc)
        print(f"  runtime      FAIL — {msg}")
        errors.append(msg)

    print("=" * 40)
    if errors:
        print(f"HEALTH CHECK FAILED ({len(errors)} error(s)):")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("All health checks passed.")
    return 0


# ---------------------------------------------------------------------------
# cmd_seed
# ---------------------------------------------------------------------------

def cmd_seed(args: argparse.Namespace) -> int:
    """Bootstrap banlist + narrative state.

    If --from-voice-validator is set, reads voice-validator output files from
    logs/chronicle/ and populates the slop ban-list table.

    TODO P2: wire in antislop.bootstrap_from_voice_validator() once antislop
    module is built. For now, emits a diagnostic log and exits clean so the
    workflow step doesn't hard-fail during bootstrap.
    """
    log.info("[seed] from_voice_validator=%s db=%s", args.from_voice_validator, args.db)

    if args.from_voice_validator:
        log.info("[seed] TODO P2: antislop.bootstrap_from_voice_validator()")
        print("seed --from-voice-validator: stub (P2 pending) — no-op for now")
    else:
        log.info("[seed] TODO P3: narrative state bootstrap")
        print("seed: stub (P3 pending) — no-op for now")

    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    args = parse_args(argv)

    dispatch = {
        "generate": cmd_generate,
        "health": cmd_health,
        "seed": cmd_seed,
    }

    handler = dispatch.get(args.cmd)
    if handler is None:
        sys.exit(f"unknown command: {args.cmd!r}")

    rc = handler(args)
    if rc:
        sys.exit(rc)


if __name__ == "__main__":
    main()
