# Re-export shim: tests import from cfb_rankings.team_pages.story_words
from cfb_rankings.team_pages.story_words_module import render_story_words, STORY_WORDS_CSS  # noqa: F401

__all__ = ["render_story_words", "STORY_WORDS_CSS"]
