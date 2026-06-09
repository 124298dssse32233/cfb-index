"""Tests for cfb_rankings.chronicle.lora_corpus."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cfb_rankings.chronicle.lora_corpus import (
    SENTINEL,
    VoicePassage,
    build_corpus,
    deduplicate,
    extract_from_profiles,
    validate_corpus,
)


SAMPLE_PROFILE = """---
team_id: 999
program_name: TestU
display_name: TestU
program_slug: testu
program_tier: 2
voice_register: stoic-mountain
tonal_template: stoic-mountain
identity_phrase: "TestU is the canonical mid-major whose identity is forged in defiance."
mantra: "Climb on."
stock_phrases:
  - "The mountain does not flinch."
  - "Every game is altitude training."
cultural_anchors:
  one_sentence: "TestU is what mid-major identity looks like when the program refuses to flinch."
---

## program_history

TestU football's all-time canon moment is the 1998 upset of the top-ranked
program in the country. The Mountaineers' three-peat conference title run
from 2004 to 2006 cemented the program as a structural feature of the
mid-major landscape, not an accident. The 2014 FBS reclassification opened
the modern era, and the program's sustained competitive cycles since have
proved that the mountain was always the point.

## fanbase_summary

Mountaineer fans are stoic in a way that the larger flagship-state programs
never quite manage. The mountain-town geography, the Climb On mantra, the
1998 upset canon — these combine into a fanbase distinct from any other in
the conference. Black-and-gold is non-negotiable; the costume of the rival
mascot is irrelevant.

## stat_block

- Wins: 47
- Losses: 12
- Conference titles: 3
- Bowl appearances: 8
- Coaches: 2
"""


def _write_profile(tmp_path: Path, name: str, content: str) -> Path:
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir(exist_ok=True)
    p = profiles_dir / f"{name}.md"
    p.write_text(content, encoding="utf-8")
    return profiles_dir


def test_extract_from_profiles_finds_passages(tmp_path: Path) -> None:
    profiles_dir = _write_profile(tmp_path, "testu", SAMPLE_PROFILE)
    passages = extract_from_profiles(profiles_dir)
    assert passages, "should produce at least one passage"
    sources = {p.source for p in passages}
    assert sources == {"profile"}
    # Expect both the frontmatter style snippet and at least one body section.
    section_ids = {p.source_id for p in passages}
    assert any("frontmatter_cues" in s for s in section_ids)
    assert any("program_history" in s for s in section_ids)
    assert any("fanbase_summary" in s for s in section_ids)


def test_extract_skips_short_passages(tmp_path: Path) -> None:
    """Short sections fall under min_words filter inside build_corpus."""
    short_profile = """---
team_id: 1
program_slug: tiny
identity_phrase: "Tiny is tiny."
---

## program_history

One sentence only here.
"""
    profiles_dir = _write_profile(tmp_path, "tiny", short_profile)
    passages = extract_from_profiles(profiles_dir)
    # extract_from_profiles itself does not enforce min_words, but build_corpus does.
    out = tmp_path / "out.jsonl"
    stats = build_corpus(
        out_path=out,
        sources=["profile"],
        min_words=50,
        max_words=2000,
        profiles_dir=profiles_dir,
        db=None,
    )
    # The "One sentence only here." passage is well under 50 words and must be excluded.
    assert stats.total_passages == 0 or all(
        w >= 50 for w in _passage_word_counts_from_jsonl(out)
    )


def _passage_word_counts_from_jsonl(path: Path) -> list[int]:
    import re

    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        out.append(len(re.findall(r"\b\w+\b", obj["text"])))
    return out


def test_extract_skips_stat_blocks(tmp_path: Path) -> None:
    profiles_dir = _write_profile(tmp_path, "testu", SAMPLE_PROFILE)
    passages = extract_from_profiles(profiles_dir)
    # The "## stat_block" section is bullet-list — must not appear as a passage.
    assert not any("stat_block" in p.source_id for p in passages), (
        "stat_block section should be filtered by the bullet-list heuristic"
    )


def test_deduplicate_removes_near_duplicates() -> None:
    p1 = VoicePassage(
        text=(
            "Alabama is the program the rest of college football measures itself "
            "against. The process does not flinch at rankings and the standard does "
            "not move when the season turns."
        ),
        source="profile",
        source_id="alabama#a",
        word_count=30,
        quality_score=1.0,
    )
    # Very slightly altered — Jaccard should be > 0.85.
    p2 = VoicePassage(
        text=(
            "Alabama is the program the rest of college football measures itself "
            "against. The process does not flinch at rankings and the standard does "
            "not move when the season turns indeed."
        ),
        source="profile",
        source_id="alabama#b",
        word_count=31,
        quality_score=0.9,
    )
    p3 = VoicePassage(
        text=(
            "Oregon football is a velocity story — the Nike-funded program that "
            "rebuilt the recruiting map of the West Coast."
        ),
        source="profile",
        source_id="oregon#a",
        word_count=22,
        quality_score=1.0,
    )
    out = deduplicate([p1, p2, p3], min_diff_ratio=0.85)
    ids = {p.source_id for p in out}
    assert "oregon#a" in ids
    # Exactly one of the alabama variants survives — the higher-quality one.
    alabama_kept = ids & {"alabama#a", "alabama#b"}
    assert len(alabama_kept) == 1
    assert "alabama#a" in alabama_kept  # higher quality wins


def test_voice_passage_to_training_text_has_sentinel() -> None:
    p = VoicePassage(
        text="Some prose.",
        source="profile",
        source_id="x",
        word_count=2,
    )
    rendered = p.to_training_text()
    assert rendered.startswith(SENTINEL)
    assert "Some prose." in rendered


def test_build_corpus_writes_valid_jsonl(tmp_path: Path) -> None:
    profiles_dir = _write_profile(tmp_path, "testu", SAMPLE_PROFILE)
    out = tmp_path / "voice.jsonl"
    stats = build_corpus(
        out_path=out,
        sources=["profile"],
        min_words=30,
        max_words=2000,
        profiles_dir=profiles_dir,
        db=None,
    )
    assert out.exists()
    assert stats.total_passages > 0
    for line in out.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        assert "text" in obj
        assert obj["text"].startswith(SENTINEL)


def test_validate_corpus_catches_malformed(tmp_path: Path) -> None:
    bad = tmp_path / "bad.jsonl"
    bad.write_text(
        '{"text": "[CFB-INDEX-VOICE]\\nA real passage that is long enough '
        'to look like prose for at least thirty words and then some more so the '
        'short-warning heuristic does not fire on this synthetic case."}\n'
        "this line is not json at all\n"
        '{"text": "no sentinel here"}\n',
        encoding="utf-8",
    )
    report = validate_corpus(bad)
    assert report.line_count == 3
    assert report.invalid_json_lines == [2]
    assert report.sentinel_present_count == 1
    # one warning for line 3 missing sentinel
    assert any("missing sentinel" in w for w in report.warnings)


def test_build_corpus_respects_sources_filter(tmp_path: Path) -> None:
    profiles_dir = _write_profile(tmp_path, "testu", SAMPLE_PROFILE)
    out = tmp_path / "voice.jsonl"
    # Only "edition" requested but db is None and there are no profile sources.
    stats = build_corpus(
        out_path=out,
        sources=["edition"],
        min_words=30,
        max_words=2000,
        profiles_dir=profiles_dir,
        db=None,
    )
    assert stats.total_passages == 0
    assert "profile" not in stats.by_source

    # Now ask for profiles only — must see profile passages.
    stats2 = build_corpus(
        out_path=out,
        sources=["profile"],
        min_words=30,
        max_words=2000,
        profiles_dir=profiles_dir,
        db=None,
    )
    assert stats2.total_passages > 0
    assert stats2.by_source.get("profile", 0) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
