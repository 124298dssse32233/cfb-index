"""Wave-1+2 integration voice-validator sweep.

Walks every rendered HTML file under output/site/ and checks the visible
text (script/style stripped) against the canonical fan-voice validator.
Writes a CSV-style report to stdout: source-path, violation-count,
distinct-violations.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from cfb_rankings.team_pages.voice_validator import (  # noqa: E402
    validate_fan_voice,
    BANNED_PHRASES,
)


_SCRIPT = re.compile(r"<script\b[^>]*>.*?</script>", re.DOTALL | re.IGNORECASE)
_STYLE = re.compile(r"<style\b[^>]*>.*?</style>", re.DOTALL | re.IGNORECASE)
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def _visible_text(html: str) -> str:
    txt = _SCRIPT.sub(" ", html)
    txt = _STYLE.sub(" ", txt)
    txt = _TAG.sub(" ", txt)
    return _WS.sub(" ", txt).strip()


def main() -> int:
    site_root = REPO / "output" / "site"
    if not site_root.exists():
        print("output/site missing", file=sys.stderr)
        return 1

    total_files = 0
    total_violations = 0
    files_with_violations = 0
    by_phrase: dict[str, int] = {}
    sample_offenders: list[tuple[str, list[str]]] = []

    for path in sorted(site_root.rglob("*.html")):
        total_files += 1
        try:
            html = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        visible = _visible_text(html)
        ok, violations = validate_fan_voice(visible, source=str(path))
        if not ok:
            files_with_violations += 1
            total_violations += len(violations)
            for v in violations:
                by_phrase[v] = by_phrase.get(v, 0) + 1
            if len(sample_offenders) < 20:
                rel = path.relative_to(REPO)
                sample_offenders.append((str(rel), sorted(set(violations))))

    print(f"banlist size       : {len(BANNED_PHRASES)} phrases")
    print(f"scanned files      : {total_files}")
    print(f"files w/ violations: {files_with_violations}")
    print(f"total violations   : {total_violations}")
    print()
    if by_phrase:
        print("Top offending phrases:")
        for phrase, count in sorted(by_phrase.items(), key=lambda kv: -kv[1])[:25]:
            print(f"  {count:>5}  {phrase}")
        print()
        print("Sample offenders (first 20):")
        for rel, phrases in sample_offenders:
            print(f"  {rel}")
            print(f"    -> {', '.join(phrases)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
