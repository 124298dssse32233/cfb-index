"""Build a Cmd-K-style self-contained theme-toggle demo.

Output: docs/mockups/theme_toggle_demo.html

The demo loads:
  - team_pages/assets/tokens.css  (dark-default token system)
  - docs/design-system/assets/tokens-bridge.css  (Path C bridge — flips
    semantic tokens based on data-theme attribute)
  - src/cfb_rankings/theme/assets/theme_toggle.{css,js}

Then renders a sample page that uses semantic tokens. Click the
toggle button in the top-right to cycle system → light → dark → system
and watch every styled element re-color in real time.

Verifies the v5-11.5 Path C end-to-end without touching any production
renderer.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> None:
    from cfb_rankings.theme import (  # noqa: E402
        THEME_INIT_SCRIPT,
        render_theme_toggle_button,
    )

    tokens_css = (
        ROOT / "src" / "cfb_rankings" / "team_pages" / "assets" / "tokens.css"
    ).read_text(encoding="utf-8")
    bridge_css = (
        ROOT / "docs" / "design-system" / "assets" / "tokens-bridge.css"
    ).read_text(encoding="utf-8")
    toggle_css = (
        ROOT / "src" / "cfb_rankings" / "theme" / "assets" / "theme_toggle.css"
    ).read_text(encoding="utf-8")
    toggle_js = (
        ROOT / "src" / "cfb_rankings" / "theme" / "assets" / "theme_toggle.js"
    ).read_text(encoding="utf-8")

    body_html = """
<header class="demo-head">
  <div class="demo-brand">CFB Index · v5-11.5 demo</div>
  """ + render_theme_toggle_button() + """
</header>

<main class="demo-wrap">
  <h1>Theme toggle &mdash; Path C end-to-end</h1>
  <p class="lede">
    Press the sun/moon/auto button (top right) to cycle through three
    states: <strong>system</strong> &middot; <strong>light</strong> &middot;
    <strong>dark</strong>. The choice persists in localStorage so the
    page renders correctly on reload.
  </p>

  <section class="demo-card">
    <h2>Surface ramp</h2>
    <div class="demo-swatches">
      <div class="swatch" data-which="base">--semantic-bg-base</div>
      <div class="swatch" data-which="elevated">--semantic-bg-elevated</div>
      <div class="swatch" data-which="card">--semantic-bg-card</div>
      <div class="swatch" data-which="raised">--semantic-bg-raised</div>
    </div>
  </section>

  <section class="demo-card">
    <h2>Foreground ramp</h2>
    <p class="demo-fg" data-which="primary">--semantic-fg-primary</p>
    <p class="demo-fg" data-which="secondary">--semantic-fg-secondary</p>
    <p class="demo-fg" data-which="muted">--semantic-fg-muted</p>
  </section>

  <section class="demo-card">
    <h2>Live theme state</h2>
    <pre class="demo-state"><code id="state-display">(loading...)</code></pre>
    <p class="demo-hint">
      The state above updates whenever the toggle cycles, fired via the
      <code>cfb-theme-changed</code> CustomEvent. Other components
      (charts, etc.) can listen to this event to re-render with the
      new colors.
    </p>
  </section>

  <section class="demo-card">
    <h2>Programmatic API</h2>
    <p>
      <button class="demo-btn" onclick="window.cfbTheme.set('light')">Force light</button>
      <button class="demo-btn" onclick="window.cfbTheme.set('dark')">Force dark</button>
      <button class="demo-btn" onclick="window.cfbTheme.system()">Reset to system</button>
    </p>
  </section>
</main>
"""

    page_css = """
body {
  background: var(--semantic-bg-base, var(--bg-0, #0b0d12));
  color: var(--semantic-fg-primary, var(--fg-primary, #f5f6fa));
  font-family: var(--font-body, "Inter", system-ui, sans-serif);
  margin: 0;
  min-height: 100vh;
  transition: background-color 200ms ease, color 200ms ease;
}

.demo-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid var(--semantic-line, var(--stroke-default, rgba(255,255,255,0.08)));
  background: var(--semantic-bg-elevated, var(--bg-1, #12151d));
}
.demo-brand {
  font-family: var(--font-display, "Inter", sans-serif);
  font-weight: 600;
  font-size: 14px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--semantic-fg-secondary, var(--fg-secondary, #c6cad6));
}

.demo-wrap { max-width: 720px; margin: 0 auto; padding: 48px 24px; }

h1 {
  font-family: var(--font-display, "Inter", sans-serif);
  font-size: 32px;
  margin: 0 0 12px;
  color: var(--semantic-fg-primary, #f5f6fa);
}
h2 {
  font-size: 14px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--semantic-fg-muted, var(--fg-muted, #8a90a1));
  margin: 0 0 16px;
}
.lede {
  font-size: 16px;
  line-height: 1.6;
  color: var(--semantic-fg-secondary, var(--fg-secondary, #c6cad6));
  max-width: 56ch;
}

.demo-card {
  background: var(--semantic-bg-card, var(--bg-card, #171b24));
  border: 1px solid var(--semantic-line, rgba(255,255,255,0.08));
  border-radius: 12px;
  padding: 24px;
  margin: 24px 0;
}

.demo-swatches { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
.swatch {
  padding: 16px;
  border-radius: 8px;
  font-family: var(--font-mono, monospace);
  font-size: 12px;
  border: 1px solid var(--semantic-line, rgba(255,255,255,0.08));
  color: var(--semantic-fg-muted, #8a90a1);
}
.swatch[data-which="base"]     { background: var(--semantic-bg-base, #0b0d12); }
.swatch[data-which="elevated"] { background: var(--semantic-bg-elevated, #12151d); }
.swatch[data-which="card"]     { background: var(--semantic-bg-card, #171b24); }
.swatch[data-which="raised"]   { background: var(--semantic-bg-raised, #1e2330); }

.demo-fg { font-family: var(--font-mono, monospace); font-size: 13px; margin: 4px 0; }
.demo-fg[data-which="primary"]   { color: var(--semantic-fg-primary, #f5f6fa); }
.demo-fg[data-which="secondary"] { color: var(--semantic-fg-secondary, #c6cad6); }
.demo-fg[data-which="muted"]     { color: var(--semantic-fg-muted, #8a90a1); }

.demo-state {
  background: var(--semantic-bg-base, #0b0d12);
  border: 1px solid var(--semantic-line, rgba(255,255,255,0.08));
  border-radius: 6px;
  padding: 12px;
  font-family: var(--font-mono, monospace);
  font-size: 13px;
  color: var(--semantic-fg-primary, #f5f6fa);
  margin: 0;
}
.demo-hint {
  font-size: 13px;
  color: var(--semantic-fg-muted, #8a90a1);
  margin-top: 8px;
}

.demo-btn {
  font-family: var(--font-body, "Inter", sans-serif);
  font-size: 13px;
  padding: 8px 14px;
  background: transparent;
  color: var(--semantic-fg-secondary, #c6cad6);
  border: 1px solid var(--semantic-line, rgba(255,255,255,0.12));
  border-radius: 6px;
  cursor: pointer;
  margin-right: 6px;
}
.demo-btn:hover {
  border-color: var(--semantic-accent, var(--accent-primary, #c5b358));
  color: var(--semantic-fg-primary, #f5f6fa);
}
"""

    state_updater = """
function updateState() {
  var d = document.getElementById('state-display');
  if (!d || !window.cfbTheme) return;
  d.textContent =
    'pref:      ' + window.cfbTheme.current() + '\\n' +
    'effective: ' + window.cfbTheme.effective() + '\\n' +
    'html[data-theme]: ' + (document.documentElement.getAttribute('data-theme') || '(none — follows OS)');
}
document.addEventListener('cfb-theme-changed', updateState);
document.addEventListener('DOMContentLoaded', updateState);
"""

    html_out = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Theme Toggle Demo — Sprint v5-11.5</title>
<meta name="viewport" content="width=device-width, initial-scale=1">

<script>{THEME_INIT_SCRIPT}</script>

<style>
{tokens_css}

{bridge_css}

{toggle_css}

{page_css}
</style>
</head>
<body>
{body_html}

<script>{toggle_js}</script>
<script>{state_updater}</script>
</body>
</html>"""

    out_path = ROOT / "docs" / "mockups" / "theme_toggle_demo.html"
    out_path.write_text(html_out, encoding="utf-8")
    print(f"wrote {out_path.relative_to(ROOT)} ({len(html_out):,} chars)")


if __name__ == "__main__":
    main()
