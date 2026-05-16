"""Tests for src/cfb_rankings/common/head_chrome.py.

Verifies the BASE_URL composition + head-chrome emitter:

* DEFAULT_BASE_URL fallback when the env var is unset.
* CFB_INDEX_BASE_URL env-var override (via monkeypatch).
* absolute_url() join semantics across the path-shape matrix:
    - leading-slash and no-leading-slash paths
    - empty/None path
    - already-absolute URLs (passthrough)
    - paths carrying query strings and fragments
* render_head_chrome() emits canonical + og:* + twitter:* HTML lines,
  including absolute URL composition for the OG image.

These tests are pure-Python and rely on no DB / filesystem. They run
identically on Windows and Linux (no path-separator assumptions).
"""
from __future__ import annotations

import pytest

from cfb_rankings.common import head_chrome
from cfb_rankings.common.head_chrome import (
    DEFAULT_BASE_URL,
    DEFAULT_OG_IMAGE,
    absolute_url,
    base_url,
    render_head_chrome,
)


# ---------------------------------------------------------------------------
# base_url() — env-var resolution
# ---------------------------------------------------------------------------


def test_base_url_default_when_env_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    """With CFB_INDEX_BASE_URL unset, base_url() returns DEFAULT_BASE_URL."""
    monkeypatch.delenv("CFB_INDEX_BASE_URL", raising=False)
    head_chrome._reload_base_url()
    assert base_url() == DEFAULT_BASE_URL


def test_base_url_uses_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """CFB_INDEX_BASE_URL takes precedence over the default."""
    monkeypatch.setenv("CFB_INDEX_BASE_URL", "https://staging.example.com")
    head_chrome._reload_base_url()
    assert base_url() == "https://staging.example.com"


def test_base_url_strips_trailing_slash(monkeypatch: pytest.MonkeyPatch) -> None:
    """Trailing slash on the env value is stripped so joining stays clean."""
    monkeypatch.setenv("CFB_INDEX_BASE_URL", "https://staging.example.com/")
    head_chrome._reload_base_url()
    assert base_url() == "https://staging.example.com"


# ---------------------------------------------------------------------------
# absolute_url() — join matrix
# ---------------------------------------------------------------------------


def test_absolute_url_leading_slash(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CFB_INDEX_BASE_URL", raising=False)
    head_chrome._reload_base_url()
    assert (
        absolute_url("/teams/alabama.html")
        == f"{DEFAULT_BASE_URL}/teams/alabama.html"
    )


def test_absolute_url_no_leading_slash(monkeypatch: pytest.MonkeyPatch) -> None:
    """A path without the leading slash still joins cleanly."""
    monkeypatch.delenv("CFB_INDEX_BASE_URL", raising=False)
    head_chrome._reload_base_url()
    assert (
        absolute_url("teams/alabama.html")
        == f"{DEFAULT_BASE_URL}/teams/alabama.html"
    )


def test_absolute_url_empty_returns_base(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CFB_INDEX_BASE_URL", raising=False)
    head_chrome._reload_base_url()
    assert absolute_url("") == DEFAULT_BASE_URL


def test_absolute_url_none_returns_base(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CFB_INDEX_BASE_URL", raising=False)
    head_chrome._reload_base_url()
    assert absolute_url(None) == DEFAULT_BASE_URL


def test_absolute_url_passthrough_https() -> None:
    """Already-absolute https URLs pass through unchanged."""
    assert absolute_url("https://other.example.com/x") == "https://other.example.com/x"


def test_absolute_url_passthrough_http() -> None:
    """Already-absolute http URLs pass through unchanged."""
    assert absolute_url("http://other.example.com/x") == "http://other.example.com/x"


def test_absolute_url_preserves_query_and_fragment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CFB_INDEX_BASE_URL", raising=False)
    head_chrome._reload_base_url()
    assert (
        absolute_url("/teams/alabama.html?week=12#schedule")
        == f"{DEFAULT_BASE_URL}/teams/alabama.html?week=12#schedule"
    )


def test_absolute_url_respects_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CFB_INDEX_BASE_URL", "https://staging.example.com")
    head_chrome._reload_base_url()
    assert (
        absolute_url("/teams/alabama.html")
        == "https://staging.example.com/teams/alabama.html"
    )


# ---------------------------------------------------------------------------
# render_head_chrome() — output shape
# ---------------------------------------------------------------------------


def test_render_head_chrome_minimal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CFB_INDEX_BASE_URL", raising=False)
    head_chrome._reload_base_url()

    html = render_head_chrome(page_path="/foo.html")

    # canonical
    assert f'<link rel="canonical" href="{DEFAULT_BASE_URL}/foo.html">' in html
    # og:url + og:type + og:site_name + default og:image
    assert f'<meta property="og:url" content="{DEFAULT_BASE_URL}/foo.html">' in html
    assert '<meta property="og:type" content="article">' in html
    assert '<meta property="og:site_name" content="THE CFB INDEX">' in html
    assert (
        f'<meta property="og:image" content="{DEFAULT_BASE_URL}{DEFAULT_OG_IMAGE}">'
        in html
    )
    # twitter card + image
    assert '<meta name="twitter:card" content="summary_large_image">' in html
    assert (
        f'<meta name="twitter:image" content="{DEFAULT_BASE_URL}{DEFAULT_OG_IMAGE}">'
        in html
    )


def test_render_head_chrome_with_title_and_description(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CFB_INDEX_BASE_URL", raising=False)
    head_chrome._reload_base_url()

    html = render_head_chrome(
        page_path="/teams/alabama.html",
        title="Alabama Crimson Tide",
        description="The Tide's 2026 season story",
    )

    assert '<meta property="og:title" content="Alabama Crimson Tide">' in html
    assert (
        '<meta property="og:description" content="The Tide&#x27;s 2026 season story">'
        in html
    )
    assert '<meta name="twitter:title" content="Alabama Crimson Tide">' in html


def test_render_head_chrome_og_image_passthrough_absolute() -> None:
    """Absolute og_image_path is not re-joined to BASE_URL."""
    html = render_head_chrome(
        page_path="/foo.html",
        og_image_path="https://cdn.example.com/og/foo.png",
    )
    assert (
        '<meta property="og:image" content="https://cdn.example.com/og/foo.png">'
        in html
    )
    assert (
        '<meta name="twitter:image" content="https://cdn.example.com/og/foo.png">'
        in html
    )


def test_render_head_chrome_og_image_relative_joined(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Relative og_image_path is joined to BASE_URL."""
    monkeypatch.delenv("CFB_INDEX_BASE_URL", raising=False)
    head_chrome._reload_base_url()
    html = render_head_chrome(
        page_path="/foo.html",
        og_image_path="/og/alabama.png",
    )
    assert (
        f'<meta property="og:image" content="{DEFAULT_BASE_URL}/og/alabama.png">'
        in html
    )


def test_render_head_chrome_escapes_user_strings() -> None:
    """Quotes and angle brackets in user strings are HTML-escaped."""
    html = render_head_chrome(
        page_path="/foo.html",
        title='Bama "vs" Auburn',
        description="<script>alert(1)</script>",
    )
    # double-quote → &quot;  ; angle brackets → &lt; / &gt;
    assert "Bama &quot;vs&quot; Auburn" in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    # raw script tag must NOT survive
    assert "<script>alert(1)</script>" not in html


def test_render_head_chrome_website_type() -> None:
    """og_type='website' overrides the default 'article'."""
    html = render_head_chrome(page_path="/", og_type="website")
    assert '<meta property="og:type" content="website">' in html
    assert '<meta property="og:type" content="article">' not in html


def test_render_head_chrome_canonical_with_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Canonical URL uses the env-var BASE_URL when set."""
    monkeypatch.setenv("CFB_INDEX_BASE_URL", "https://staging.example.com")
    head_chrome._reload_base_url()
    html = render_head_chrome(page_path="/foo.html")
    assert (
        '<link rel="canonical" href="https://staging.example.com/foo.html">' in html
    )
