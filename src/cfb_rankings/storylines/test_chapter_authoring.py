"""Tests for storyline-thread chapter authoring helpers."""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from cfb_rankings.storylines.chapter_authoring import (
    append_chapter_to_seed,
    canonical_byline,
    format_chapter_for_seed,
    parse_llm_chapter_response,
    seed_path_for_slug,
    write_draft_scaffold,
)


class TestCanonicalByline:
    def test_strips_leading_the(self):
        # Title already starts with "The" — output must not double-prefix.
        assert canonical_byline("The Vandy Renaissance") == "From The Vandy Renaissance Department"
        assert canonical_byline("The 12-Team Playoff Settling") == "From The 12-Team Playoff Settling Department"

    def test_no_leading_the_passes_through(self):
        assert canonical_byline("Realignment Endgame") == "From The Realignment Endgame Department"

    def test_case_insensitive_strip(self):
        assert canonical_byline("the saban-to-deboer transition") == "From The saban-to-deboer transition Department"


class TestFormatChapterForSeed:
    """The Python source we generate from a chapter dict must be valid Python
    that round-trips: parsing it back yields the same chapter shape."""

    def _sample_chapter(self) -> dict:
        return {
            "chapter_number": 5,
            "title": "Test Chapter",
            "dek": "A test dek with \"quotes\" and apostrophes.",
            "body_markdown": "Para one.\n\nPara two with *italic* and **bold**.",
            "byline": "From The Test Department",
            "published_at": "2026-04-25 09:00:00",
            "read_time_minutes": 7,
            "referenced_chapter_ids": [1, 2],
            "referenced_sources": [
                {"kind": "beat-writer", "name": "Stewart Mandel", "label": "The Athletic",
                 "url": None, "date": "2026-04-21",
                 "quote": "An interesting take with \"smart quotes\"."},
            ],
            "pull_quote": "An interesting take with \"smart quotes\".",
        }

    def test_output_is_valid_python(self):
        ch = self._sample_chapter()
        formatted = format_chapter_for_seed(ch)
        # Wrap in a list literal and exec to verify it's valid Python.
        wrapper = "RESULT = [\n" + formatted + "\n]"
        ns: dict = {}
        exec(wrapper, ns)
        result = ns["RESULT"]
        assert len(result) == 1
        # Round-trip the key fields.
        assert result[0]["chapter_number"] == 5
        assert result[0]["title"] == "Test Chapter"
        assert result[0]["referenced_chapter_ids"] == [1, 2]
        assert result[0]["pull_quote"].startswith("An interesting")
        assert result[0]["referenced_sources"][0]["name"] == "Stewart Mandel"

    def test_handles_none_pull_quote(self):
        ch = self._sample_chapter()
        ch["pull_quote"] = None
        formatted = format_chapter_for_seed(ch)
        ns: dict = {}
        exec("RESULT = [\n" + formatted + "\n]", ns)
        assert ns["RESULT"][0]["pull_quote"] is None


class TestAppendChapterToSeed:
    """Splicing a new chapter into a seed module preserves the rest of the file
    and produces an importable module."""

    def _make_temp_seed(self, tmp_path: Path) -> Path:
        # Minimal valid seed module shape.
        seed = textwrap.dedent('''\
            """Test thread — chapter seeds."""
            THREAD_SLUG = "test-thread"

            CHAPTERS = [
                {
                    "chapter_number": 1,
                    "title": "First",
                    "dek": "First dek.",
                    "body_markdown": """First body.""",
                    "byline": "From The Test Department",
                    "published_at": "2026-04-01 09:00:00",
                    "read_time_minutes": 5,
                    "referenced_chapter_ids": [],
                    "referenced_sources": [],
                    "pull_quote": None,
                },
            ]
            ''')
        path = tmp_path / "test_thread.py"
        path.write_text(seed, encoding="utf-8")
        return path

    def test_appends_new_chapter_before_terminator(self, tmp_path, monkeypatch):
        seed_path = self._make_temp_seed(tmp_path)
        monkeypatch.setattr(
            "cfb_rankings.storylines.chapter_authoring._SLUG_TO_MODULE",
            {"test-thread": "test_thread"},
        )
        monkeypatch.setattr(
            "cfb_rankings.storylines.chapter_authoring.SEEDS_DIR",
            tmp_path,
        )
        new_chapter = {
            "chapter_number": 2,
            "title": "Second",
            "dek": "Second dek.",
            "body_markdown": "Second body content.",
            "byline": "From The Test Department",
            "published_at": "2026-04-22 09:00:00",
            "read_time_minutes": 6,
            "referenced_chapter_ids": [1],
            "referenced_sources": [
                {"kind": "beat-writer", "name": "X", "label": "Y", "url": None, "date": "2026-04-20"},
            ],
            "pull_quote": None,
        }
        result_path = append_chapter_to_seed("test-thread", new_chapter)
        assert result_path == seed_path
        # Re-read and validate via exec.
        text = seed_path.read_text(encoding="utf-8")
        ns: dict = {}
        exec(text, ns)
        assert len(ns["CHAPTERS"]) == 2
        assert ns["CHAPTERS"][0]["chapter_number"] == 1
        assert ns["CHAPTERS"][1]["chapter_number"] == 2
        assert ns["CHAPTERS"][1]["title"] == "Second"
        assert ns["CHAPTERS"][1]["referenced_chapter_ids"] == [1]


class TestParseLLMChapterResponse:
    META = {"title": "Test Thread"}

    def _valid_response_obj(self) -> dict:
        return {
            "chapter_number": 5,
            "title": "Generated",
            "dek": "Generated dek.",
            "body_markdown": "Generated body.",
            "byline": "wrong byline that will get overridden",
            "published_at": "2026-04-25 09:00:00",
            "read_time_minutes": 7,
            "referenced_chapter_ids": [1, 2, 3],
            "referenced_sources": [
                {"kind": "beat-writer", "name": "X", "label": "Y", "url": None, "date": "2026-04-20"},
            ],
            "pull_quote": "A pull quote.",
        }

    def test_parses_fenced_json(self):
        body = self._valid_response_obj()
        text = "Some preamble.\n```json\n" + json.dumps(body) + "\n```\nTrailing text."
        result = parse_llm_chapter_response(text, thread_slug="test", chapter_number=5, meta=self.META)
        assert result["title"] == "Generated"
        # Byline is forced to canonical form regardless of LLM output.
        assert result["byline"] == "From The Test Thread Department"

    def test_parses_raw_json(self):
        body = self._valid_response_obj()
        text = json.dumps(body)
        result = parse_llm_chapter_response(text, thread_slug="test", chapter_number=5, meta=self.META)
        assert result["chapter_number"] == 5

    def test_chapter_number_forced_to_caller_value(self):
        body = self._valid_response_obj()
        body["chapter_number"] = 999  # LLM drift
        text = "```json\n" + json.dumps(body) + "\n```"
        result = parse_llm_chapter_response(text, thread_slug="test", chapter_number=5, meta=self.META)
        assert result["chapter_number"] == 5

    def test_missing_required_field_raises(self):
        body = self._valid_response_obj()
        del body["body_markdown"]
        text = "```json\n" + json.dumps(body) + "\n```"
        with pytest.raises(ValueError, match="missing required fields"):
            parse_llm_chapter_response(text, thread_slug="test", chapter_number=5, meta=self.META)

    def test_empty_response_raises(self):
        with pytest.raises(ValueError, match="empty"):
            parse_llm_chapter_response("", thread_slug="test", chapter_number=5, meta=self.META)

    def test_no_json_in_response_raises(self):
        with pytest.raises(ValueError, match="no JSON object"):
            parse_llm_chapter_response("just prose, no JSON", thread_slug="test", chapter_number=5, meta=self.META)


class TestWriteDraftScaffold:
    META = {"title": "Test Thread"}

    def test_scaffold_is_valid_python(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "cfb_rankings.storylines.chapter_authoring.DRAFTS_DIR", tmp_path,
        )
        path = write_draft_scaffold("test-slug", self.META, 3, note="Test scaffold.")
        assert path.exists()
        text = path.read_text(encoding="utf-8")
        ns: dict = {}
        exec(text, ns)
        assert ns["THREAD_SLUG"] == "test-slug"
        assert len(ns["CHAPTERS"]) == 1
        # Byline correctly canonicalized (no double "The").
        assert ns["CHAPTERS"][0]["byline"] == "From The Test Thread Department"
        assert ns["CHAPTERS"][0]["referenced_chapter_ids"] == [1, 2]

    def test_scaffold_with_llm_text_embeds_raw(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "cfb_rankings.storylines.chapter_authoring.DRAFTS_DIR", tmp_path,
        )
        path = write_draft_scaffold(
            "test-slug", self.META, 2,
            llm_text="raw LLM\nresponse content",
            violations=["banned-phrase-1"],
            note="voice failed",
        )
        text = path.read_text(encoding="utf-8")
        assert "# raw LLM" in text
        assert "# response content" in text
        assert "banned-phrase-1" in text
