#!/usr/bin/env python3
"""Bias audit for player_discourse_terms (Language Layer Wave 3).

Run BEFORE committing player descriptors to production:
  python scripts/audit_player_descriptors.py

Prints the top-N terms for the top-50 players by total_windows.
Exits non-zero if any hard-blocked term from the descriptor_blocklist
survived (enforcement is in descriptors.py, but this is the safety net).

Usage:
  python scripts/audit_player_descriptors.py [--db PATH] [--season YEAR] [--top-players 50]
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def load_blocklist():
    try:
        import yaml
        f = ROOT / "seeds" / "discourse_descriptor_blocklist.yaml"
        data = yaml.safe_load(f.read_text(encoding="utf-8"))
        return {str(t).lower() for t in (data.get("descriptor_blocklist") or [])}
    except Exception:
        return set()

def main():
    ap = argparse.ArgumentParser(description="Bias audit for player_discourse_terms")
    ap.add_argument("--db", default=str(ROOT / "cfb_rankings.db"))
    ap.add_argument("--season", type=int, default=None)
    ap.add_argument("--top-players", type=int, default=50)
    args = ap.parse_args()

    import sqlite3
    con = sqlite3.connect(args.db)
    con.row_factory = sqlite3.Row

    season_filter = ""
    season_params = []
    if args.season:
        season_filter = "AND pdt.season_year = ?"
        season_params = [args.season]

    # Top players by window coverage
    players = con.execute(f"""
        SELECT p.player_id, p.first_name, p.last_name,
               SUM(pdt.total_windows) AS tw
          FROM players p
          JOIN player_discourse_terms pdt ON pdt.player_id = p.player_id
         WHERE 1=1 {season_filter}
         GROUP BY p.player_id
         ORDER BY tw DESC
         LIMIT ?
    """, season_params + [args.top_players]).fetchall()

    if not players:
        print("No player_discourse_terms rows found -- nothing to audit.", file=sys.stderr)
        sys.exit(0)

    blocklist = load_blocklist()
    violations = []

    print(f"=== Player Descriptor Bias Audit ({len(players)} players) ===")
    for row in players:
        pid = row["player_id"]
        name = f"{row['first_name'] or ''} {row['last_name'] or ''}".strip()
        terms = con.execute(f"""
            SELECT term, term_rank, rate_ratio, z_score
              FROM player_discourse_terms
             WHERE player_id = ? {season_filter}
             ORDER BY term_rank
             LIMIT 10
        """, [pid] + season_params).fetchall()
        term_strs = [f"{t['term']}(x{t['rate_ratio']:.1f})" for t in terms]
        print(f"  {name:30s} [{', '.join(term_strs)}]")
        for t in terms:
            term = t["term"].lower()
            if term in blocklist or any(b in term for b in blocklist):
                violations.append((name, term))

    if violations:
        print(f"\nERROR: {len(violations)} blocked term(s) survived into output:")
        for name, term in violations:
            print(f"  {name}: {term!r}")
        sys.exit(1)
    else:
        print(f"\nAudit PASSED -- no blocked terms found in top {len(players)} players.")
        sys.exit(0)

if __name__ == "__main__":
    main()
