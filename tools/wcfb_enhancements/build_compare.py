#!/usr/bin/env python3
"""
tools/wcfb_enhancements/build_compare.py — write output/site/compare/index.html

Generates a self-contained side-by-side team comparison page using the 17
profiled programs in profiles/*.md. Designed to override whatever stub the
upstream build-site step produced, so we always have a real comparison tool.

Usage:
    python tools/wcfb_enhancements/build_compare.py [site_dir]
Default site_dir: output/site
"""
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("[build_compare] WARNING: pyyaml missing — falling back to no-yaml mode")
    yaml = None


PROFILE_DIR = Path("profiles")


def load_programs():
    programs = []
    for f in sorted(PROFILE_DIR.glob("*.md")):
        try:
            txt = f.read_text(encoding="utf-8")
        except Exception:
            continue
        if not txt.startswith("---"):
            continue
        parts = txt.split("---", 2)
        if len(parts) < 3:
            continue
        if not yaml:
            continue
        try:
            meta = yaml.safe_load(parts[1])
        except Exception:
            continue
        slug = meta.get("program_slug")
        name = meta.get("display_name") or meta.get("program_name")
        accent = (meta.get("accent_hex") or "#c9a24a").strip().strip('"')
        identity = (meta.get("identity_phrase") or "").strip().strip('"')
        mantra = (meta.get("mantra") or "").strip().strip('"')
        if not slug or not name:
            continue
        programs.append({
            "slug": slug,
            "name": name,
            "accent": accent,
            "identity": identity,
            "mantra": mantra,
        })
    return programs


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Compare Programs — CFB Index</title>
<meta name="description" content="Side-by-side comparison of college football programs. Pick any two of the 17 profiled programs to see identity, accent color, mantra, and a link to the full team page.">
<meta property="og:title" content="Compare Programs — CFB Index">
<meta property="og:description" content="Pick any two profiled programs to compare side-by-side.">
<meta property="og:type" content="website">
<meta property="og:image" content="/og-image.svg">
<style>
:root {
  --bg: #f6f1e6;
  --ink: #1a1a1a;
  --muted: #7a7a7a;
  --card: #ffffff;
  --stroke: rgba(26,26,26,0.14);
  --accent: #c9a24a;
}
html, body {
  margin: 0; padding: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  font-size: 15px;
  line-height: 1.5;
}
.page { max-width: 1100px; margin: 0 auto; padding: 40px 24px 100px; }
.chrome {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 0 28px;
  border-bottom: 1px solid var(--stroke);
  margin-bottom: 32px;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}
.chrome a { color: var(--ink); text-decoration: none; }
.brand { font-family: 'Source Serif Pro', Georgia, serif; font-size: 22px; font-weight: 700; letter-spacing: 0.04em; text-transform: none; }
.brand .slash { color: var(--accent); margin: 0 6px; }
.nav a { margin-left: 24px; }
.nav a:hover { color: var(--accent); }

h1.wcfb-compare__title { letter-spacing: -0.01em; }
.lede { color: var(--muted); margin: 0 0 32px; max-width: 60ch; font-size: 16px; }

.pickers {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 16px;
  align-items: center;
  margin-bottom: 28px;
}
.picker {
  display: block;
  width: 100%;
  padding: 14px 16px;
  background: var(--card);
  border: 1px solid var(--stroke);
  border-radius: 10px;
  font: inherit;
  color: var(--ink);
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 12 8'><path fill='%231a1a1a' d='M6 8 0 0h12z'/></svg>");
  background-repeat: no-repeat;
  background-position: right 14px center;
  background-size: 10px 7px;
  padding-right: 36px;
}
.picker:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.vs {
  font-family: 'Source Serif Pro', Georgia, serif;
  font-weight: 700;
  font-size: 22px;
  color: var(--muted);
  letter-spacing: 0.04em;
}

.panes {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
}
.pane {
  background: var(--card);
  border: 1px solid var(--stroke);
  border-radius: 16px;
  padding: 0;
  min-height: 280px;
  overflow: hidden;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
  display: flex; flex-direction: column;
}
.pane__accent { height: 6px; background: var(--accent); }
.pane__inner { padding: 24px; flex: 1; display: flex; flex-direction: column; gap: 14px; }
.pane__header { display: flex; align-items: center; gap: 14px; padding-bottom: 14px; border-bottom: 1px solid var(--stroke); }
.pane__logo { width: 56px; height: 56px; object-fit: contain; flex-shrink: 0; }
.pane__name { font-family: 'Source Serif Pro', Georgia, serif; font-size: 26px; font-weight: 700; line-height: 1.05; }
.pane__identity { font-family: 'Source Serif Pro', Georgia, serif; font-size: 16px; line-height: 1.5; color: var(--ink); }
.pane__mantra {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted);
  padding-top: 6px;
  border-top: 1px dotted var(--stroke);
}
.pane__cta {
  display: inline-block;
  margin-top: auto;
  align-self: flex-start;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--accent);
  border-bottom: 2px solid var(--accent);
  padding-bottom: 2px;
  text-decoration: none;
  transition: transform 0.12s ease;
}
.pane__cta:hover { transform: translateX(2px); }
.empty {
  font-family: 'Source Serif Pro', Georgia, serif;
  font-style: italic;
  color: var(--muted);
  font-size: 16px;
  text-align: center;
  padding: 60px 20px;
}

@media (max-width: 720px) {
  .page { padding: 24px 16px 100px; }
  .pickers { grid-template-columns: 1fr; }
  .vs { display: none; }
  .panes { grid-template-columns: 1fr; }
}

.help {
  margin-top: 40px;
  padding: 20px 24px;
  background: rgba(26,26,26,0.04);
  border-left: 3px solid var(--accent);
  border-radius: 0 8px 8px 0;
  color: var(--muted);
  font-size: 14px;
  line-height: 1.6;
}
.help strong { color: var(--ink); }
</style>
</head>
<body>
<div class="page">

  <header class="chrome">
    <a href="/" class="brand">CFB<span class="slash">/</span>Index</a>
    <nav class="nav">
      <a href="/">Home</a>
      <a href="/rankings/">Rankings</a>
      <a href="/hub/">Hub</a>
      <a href="/compare/" aria-current="page" style="color: var(--accent);">Compare</a>
      <a href="/methodology/">Methodology</a>
    </nav>
  </header>

  <main class="wcfb-compare">
    <h1 class="wcfb-compare__title">Compare two programs.</h1>
    <p class="lede">Identity, mantra, and a link to the full profile — laid out side by side. Picks are remembered in the URL, so you can share a comparison.</p>

    <div class="pickers">
      <select id="wcfb-pick-a" class="picker" aria-label="First program">
        <option value="">Pick a program…</option>
__PICKER_OPTIONS_A__
      </select>
      <span class="vs">vs</span>
      <select id="wcfb-pick-b" class="picker" aria-label="Second program">
        <option value="">Pick a program…</option>
__PICKER_OPTIONS_B__
      </select>
    </div>

    <div class="panes">
      <article class="pane" id="wcfb-pane-a" aria-live="polite">
        <div class="empty">Pick a program above to begin.</div>
      </article>
      <article class="pane" id="wcfb-pane-b" aria-live="polite">
        <div class="empty">Pick a second program to compare.</div>
      </article>
    </div>

    <div class="help">
      <strong>How this works:</strong> we currently profile 17 programs in depth.
      Picking two will show identity, accent, and mantra on each side.
      Deeper stat-by-stat comparison (power, resume, schedule strength) lands when
      the live ranking model populates this season. Share a comparison by copying
      the URL — your picks are encoded as <code>?a=alabama&amp;b=georgia</code>.
    </div>
  </main>
</div>

<script id="wcfb-program-data" type="application/json">__PROGRAM_JSON__</script>
<script>
(function () {
  var DATA = JSON.parse(document.getElementById('wcfb-program-data').textContent);
  var PICKS = Object.fromEntries(DATA.map(function (p) { return [p.slug, p]; }));

  function getParam(k) {
    var u = new URL(location.href);
    return u.searchParams.get(k);
  }
  function setParam(k, v) {
    var u = new URL(location.href);
    if (v) u.searchParams.set(k, v); else u.searchParams.delete(k);
    history.replaceState({}, '', u.toString());
  }
  function renderPane(paneId, slug) {
    var pane = document.getElementById(paneId);
    var p = PICKS[slug];
    if (!p) {
      pane.innerHTML = '<div class="empty">' +
        (paneId === 'wcfb-pane-a' ? 'Pick a program above to begin.' : 'Pick a second program to compare.') +
        '</div>';
      return;
    }
    var logo = '/assets/team-art/' + p.slug + '/logo_primary.png';
    pane.innerHTML =
      '<div class="pane__accent" style="background:' + p.accent + ';"></div>' +
      '<div class="pane__inner">' +
        '<div class="pane__header">' +
          '<img class="pane__logo" src="' + logo + '" alt="' + p.name + ' logo" loading="lazy" onerror="this.style.display=\\'none\\'">' +
          '<div class="pane__name">' + p.name + '</div>' +
        '</div>' +
        '<p class="pane__identity">' + (p.identity || '') + '</p>' +
        (p.mantra ? '<p class="pane__mantra">' + p.mantra + '</p>' : '') +
        '<a class="pane__cta" href="/teams/' + p.slug + '.html">Open ' + p.name + ' →</a>' +
      '</div>';
  }
  function syncFromState() {
    var a = document.getElementById('wcfb-pick-a').value;
    var b = document.getElementById('wcfb-pick-b').value;
    renderPane('wcfb-pane-a', a);
    renderPane('wcfb-pane-b', b);
    setParam('a', a); setParam('b', b);
  }
  // Init from URL
  var initA = getParam('a'), initB = getParam('b');
  if (initA) document.getElementById('wcfb-pick-a').value = initA;
  if (initB) document.getElementById('wcfb-pick-b').value = initB;
  document.getElementById('wcfb-pick-a').addEventListener('change', syncFromState);
  document.getElementById('wcfb-pick-b').addEventListener('change', syncFromState);
  syncFromState();
})();
</script>
</body>
</html>
"""


def build_options(programs, exclude=None):
    parts = []
    for p in programs:
        sel = ""
        parts.append(
            f'        <option value="{p["slug"]}"{sel}>{p["name"]}</option>'
        )
    return "\n".join(parts)


def main() -> int:
    site_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("output/site")
    if not site_dir.exists():
        print(f"[build_compare] ERROR: site dir does not exist: {site_dir}")
        return 1

    programs = load_programs()
    if not programs:
        print("[build_compare] no programs loaded — skipping")
        return 0

    target_dir = site_dir / "compare"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "index.html"

    html = HTML_TEMPLATE
    html = html.replace("__PICKER_OPTIONS_A__", build_options(programs))
    html = html.replace("__PICKER_OPTIONS_B__", build_options(programs))
    html = html.replace("__PROGRAM_JSON__", json.dumps(programs))

    target.write_text(html, encoding="utf-8")
    print(f"[build_compare] wrote {target} ({target.stat().st_size} bytes, "
          f"{len(programs)} programs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
