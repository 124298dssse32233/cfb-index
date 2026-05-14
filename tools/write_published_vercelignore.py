#!/usr/bin/env python3
"""
write_published_vercelignore.py — write a correct .vercelignore to
output/site/ for the published branch.

Critical: must NOT exclude *.png / *.jpg / *.jpeg — those globs would
nuke team logos and OG images from the Vercel deployment.
"""
from pathlib import Path

CONTENT = """# Database files
*.db
*.db-shm
*.db-wal

# Build artifacts
__pycache__/
*.pyc
*.pyo
*.pyd

# Dependencies
.deps/
.vendor/
.virtualenv/

# Logs
logs/
*.log

# Temporary files
tmp/
tmp_*/
*.tmp

# Development files
.claude/
.worktrees/
.env
.env.*

# Backups
backups/
*.bak
*.backup

# Documentation
CLAUDE*.md
OCTOPUS*.md

# Note: do NOT exclude *.png / *.jpg / *.jpeg here — team logos,
# OG images, and similar assets are PNG/JPG and live under
# assets/team-art/ and assets/. Excluding them broke logo rendering
# on the live site for ~24h (2026-05-14). Use precise paths if any
# specific screenshot needs excluding.

# Test files
tests/
tmp_*.db

# Large source-only directories (not under output/site, but safety)
research/
design-ref/
_fig*/
"""

def main():
    target = Path("output/site/.vercelignore")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(CONTENT, encoding="utf-8")
    print(f"wrote {target} ({target.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
