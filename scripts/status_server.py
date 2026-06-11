"""CFB Index — live pipeline status dashboard.

A tiny, dependency-free web page you can keep open in a browser to watch the
data pipeline without asking anyone. It reads the log files the nightly jobs
(and any manual run) write, and shows -- in plain language -- whether anything
is running right now, how the last run went, and whether the live site is current.

Run it with the "View Build Status.bat" launcher (one double-click), or directly:
    .venv\\Scripts\\python.exe scripts\\status_server.py
Then open http://localhost:8787 in your browser. The page refreshes itself every
few seconds. Close the server window to stop it.

Stdlib only -- nothing to install. Binds to localhost (127.0.0.1) so it is only
reachable from this PC.
"""
from __future__ import annotations

import glob
import html
import os
import re
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = REPO_ROOT / "logs"
PORT = 8787
REFRESH_SECONDS = 8
# A pipeline whose log was touched within this many seconds, with no "end"
# marker, is treated as "running right now".
RUNNING_WINDOW_SECONDS = 150

# Lines that are pure PowerShell error-plumbing noise -- hidden from the friendly view.
_NOISE = re.compile(
    r"CategoryInfo|FullyQualifiedErrorId|RemoteException|^\s*\+|char:\d|"
    r"NativeCommandError|^\s*$|At C:\\|^\s*~+\s*$"
)
_STEP = re.compile(r"==\s+(.+?)\s+==\s*$")
_TS = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+\-]\d{2}:\d{2})")


# ---------------------------------------------------------------------------
# Reading + parsing logs
# ---------------------------------------------------------------------------

def _read_text(path: Path) -> str:
    """Read a log file regardless of whether PowerShell wrote it UTF-8 or UTF-16."""
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-16", "utf-8", "latin-1"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return raw.decode("utf-8", errors="replace")


def _newest(pattern: str) -> "Path | None":
    matches = glob.glob(str(LOG_DIR / pattern))
    if not matches:
        return None
    return Path(max(matches, key=os.path.getmtime))


def _ago(dt: datetime) -> str:
    secs = (datetime.now(timezone.utc) - dt).total_seconds()
    if secs < 0:
        secs = 0
    if secs < 60:
        return f"{int(secs)} sec ago"
    if secs < 3600:
        return f"{int(secs // 60)} min ago"
    if secs < 86400:
        h = int(secs // 3600)
        return f"{h} hour{'s' if h != 1 else ''} ago"
    d = int(secs // 86400)
    return f"{d} day{'s' if d != 1 else ''} ago"


def _last_ts(text: str) -> "datetime | None":
    last = None
    for line in text.splitlines():
        m = _TS.match(line.strip())
        if m:
            last = m.group(1)
    if not last:
        return None
    try:
        return datetime.fromisoformat(last)
    except ValueError:
        return None


def _last_run(text: str) -> str:
    """Isolate the MOST RECENT run inside an accumulating per-day log.

    collect.ps1 / build_publish.ps1 append to one file per day, so a single log
    can hold several runs (e.g. this morning's failed build AND a later good one).
    We slice from the last '==== <name> start ====' marker to the end so status
    reflects only the current/latest run, not a stale earlier 'end' marker.
    """
    starts = [m.start() for m in re.finditer(r"={4}\s+\w+\s+start\s+={4}", text)]
    return text[starts[-1]:] if starts else text


def parse_pipeline(path: "Path | None", label: str) -> dict:
    """Turn one pipeline log into a friendly status dict."""
    if path is None:
        return {"label": label, "state": "never", "headline": "Hasn't run yet",
                "detail": "No log found.", "step": None, "when": None, "lines": []}

    text = _last_run(_read_text(path))  # only the latest run in an accumulating daily log
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    fresh = (datetime.now(timezone.utc) - mtime).total_seconds() < RUNNING_WINDOW_SECONDS

    has_clean = "end (clean)" in text
    has_failed = "end (FAILED" in text

    # The most recent "== step ==" header (skip the ==== start/end ==== markers).
    step = None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("===="):
            continue
        m = _STEP.search(s)
        if m:
            step = m.group(1)

    if has_failed:
        state, headline = "failed", "Last run hit a problem"
    elif has_clean:
        state, headline = "ok", "Finished cleanly"
    elif fresh:
        state, headline = "running", "Running right now"
    else:
        state, headline = "stopped", "Stopped before finishing"

    when = _last_ts(text) or mtime

    # Curated highlight lines (friendly), newest-relevant kept.
    highlights: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if _NOISE.search(s):
            continue
        if any(k in s for k in (
            "verify-collect-volume:", "module coverage", "Built ", "rendered ",
            "Static site build finished", "site is live", "-> HTTP 200",
            "docs collected", "scored in", "teams=", "rows=", "inserted=",
            "deploy URL:", "end (clean)", "end (FAILED", "SKIPPED",
        )):
            highlights.append(s)

    # Recent activity = last meaningful lines (steps + results), noise filtered.
    activity: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if _NOISE.search(s):
            continue
        activity.append(s)
    activity = activity[-16:]

    return {
        "label": label, "state": state, "headline": headline,
        "step": step, "when": when, "path": path.name,
        "highlights": highlights[-6:], "lines": activity,
    }


def parse_deploy() -> dict:
    """Live-site status, taken from the most recent successful health-check the
    build log recorded. We read the build_publish log (where the publish step's
    output is mirrored in clean UTF-8) rather than the dedicated Vercel log, which
    PowerShell writes as UTF-16 with the CLI's spacing stripped."""
    path = _newest("fanintel_build_publish_*.log")
    if path is None:
        return {"state": "never", "url": None, "when": None, "http": None}
    text = _read_text(path)
    # The final "HEALTH https://...vercel.app -> HTTP 200" line of the last deploy.
    last = None
    for line in text.splitlines():
        m = re.search(r"(\d{4}-\d{2}-\d{2}T[\d:]+[+\-]\d{2}:\d{2}).*?HEALTH\s+"
                      r"(https://[A-Za-z0-9.\-]+vercel\.app)\s*->\s*HTTP\s*(\d{3})", line)
        if m:
            last = m
    if not last:
        skipped = "publish: SKIPPED" in _last_run(text)
        return {"state": "skipped" if skipped else "unknown", "url": None,
                "when": None, "http": None}
    try:
        when = datetime.fromisoformat(last.group(1))
    except ValueError:
        when = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    http = last.group(3)
    return {"state": "ok" if http == "200" else "unknown",
            "url": last.group(2), "when": when, "http": http}


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

_DOT = {"ok": "#34d399", "running": "#fbbf24", "failed": "#f87171",
        "stopped": "#fb923c", "never": "#94a3b8", "unknown": "#94a3b8"}
_WORD = {"ok": "Done", "running": "Running", "failed": "Problem",
         "stopped": "Stopped", "never": "Idle", "unknown": "Unknown"}


def _esc(s: str) -> str:
    return html.escape(s, quote=True)


def _card(p: dict) -> str:
    color = _DOT.get(p["state"], "#94a3b8")
    when = f'{_ago(p["when"])}' if p.get("when") else "—"
    step = f'<div class="step">Step: <b>{_esc(p["step"])}</b></div>' if p.get("step") else ""
    hi = ""
    if p.get("highlights"):
        items = "".join(f"<li>{_esc(h)}</li>" for h in p["highlights"])
        hi = f'<ul class="hi">{items}</ul>'
    pulse = ' pulse' if p["state"] == "running" else ""
    return f"""
    <div class="card">
      <div class="card-h">
        <span class="dot{pulse}" style="background:{color}"></span>
        <span class="ttl">{_esc(p["label"])}</span>
        <span class="badge" style="color:{color};border-color:{color}">{_WORD.get(p["state"],"?")}</span>
      </div>
      <div class="headline">{_esc(p["headline"])}</div>
      <div class="when">{when}</div>
      {step}
      {hi}
    </div>"""


def render() -> str:
    collect = parse_pipeline(_newest("fanintel_collect_*.log"), "Step 1 · Collect data")
    build = parse_pipeline(_newest("fanintel_build_publish_*.log"), "Step 2 · Build & deploy")
    deploy = parse_deploy()

    running = [p for p in (collect, build) if p["state"] == "running"]
    if running:
        banner_txt = f'🔄 {running[0]["label"].split("·")[-1].strip()} is running right now'
        banner_cls = "run"
    elif any(p["state"] == "failed" for p in (collect, build)):
        banner_txt = "⚠️ The last run hit a problem — see the cards below"
        banner_cls = "bad"
    else:
        banner_txt = "✅ Everything's idle and the last runs finished cleanly"
        banner_cls = "good"

    # Live site card
    dcolor = _DOT.get(deploy["state"], "#94a3b8")
    if deploy["url"]:
        site = (f'<a href="{_esc(deploy["url"])}" target="_blank">{_esc(deploy["url"])}</a>'
                f'{" · HTTP " + deploy["http"] if deploy["http"] else ""}')
    else:
        site = "No deploy recorded yet"
    site_when = _ago(deploy["when"]) if deploy.get("when") else "—"
    site_card = f"""
    <div class="card">
      <div class="card-h">
        <span class="dot" style="background:{dcolor}"></span>
        <span class="ttl">Live site</span>
      </div>
      <div class="headline">{site}</div>
      <div class="when">Last deployed {site_when}</div>
    </div>"""

    # Recent activity from whichever pipeline is active/most recent
    active = running[0] if running else (build if (build.get("when") and (not collect.get("when") or build["when"] >= collect["when"])) else collect)
    act_rows = "".join(f'<div class="logline">{_esc(l)}</div>' for l in active.get("lines", [])) or '<div class="logline dim">No recent activity.</div>'

    now = datetime.now().strftime("%I:%M:%S %p").lstrip("0")
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="{REFRESH_SECONDS}">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CFB Index — Pipeline Status</title>
<style>
  :root {{ color-scheme: dark; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; background:#0b0f17; color:#e5e7eb;
         font:15px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; }}
  .wrap {{ max-width:920px; margin:0 auto; padding:28px 20px 60px; }}
  h1 {{ font-size:22px; margin:0 0 4px; letter-spacing:.2px; }}
  .sub {{ color:#94a3b8; font-size:13px; margin-bottom:22px; }}
  .banner {{ padding:16px 20px; border-radius:14px; font-size:17px; font-weight:600;
            margin-bottom:22px; border:1px solid #1f2937; }}
  .banner.good {{ background:#0c2a1f; border-color:#14532d; }}
  .banner.run  {{ background:#2a230c; border-color:#854d0e; }}
  .banner.bad  {{ background:#2a1212; border-color:#7f1d1d; }}
  .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
  @media (max-width:680px) {{ .grid {{ grid-template-columns:1fr; }} }}
  .card {{ background:#111827; border:1px solid #1f2937; border-radius:14px; padding:16px 18px; }}
  .card-h {{ display:flex; align-items:center; gap:9px; margin-bottom:8px; }}
  .ttl {{ font-weight:600; font-size:13px; color:#cbd5e1; text-transform:uppercase; letter-spacing:.5px; }}
  .badge {{ margin-left:auto; font-size:11px; border:1px solid; border-radius:999px; padding:1px 9px; font-weight:600; }}
  .dot {{ width:11px; height:11px; border-radius:50%; flex:none; }}
  .dot.pulse {{ animation:p 1.2s ease-in-out infinite; }}
  @keyframes p {{ 0%,100%{{opacity:1}} 50%{{opacity:.35}} }}
  .headline {{ font-size:18px; font-weight:600; margin:2px 0 2px; }}
  .when {{ color:#94a3b8; font-size:13px; }}
  .step {{ margin-top:8px; font-size:13px; color:#cbd5e1; }}
  ul.hi {{ margin:10px 0 0; padding-left:18px; color:#9ca3af; font-size:12.5px; }}
  ul.hi li {{ margin:2px 0; }}
  .section-t {{ margin:28px 0 10px; font-size:13px; text-transform:uppercase; letter-spacing:.5px; color:#94a3b8; }}
  .logbox {{ background:#0a0e15; border:1px solid #1f2937; border-radius:12px; padding:12px 14px;
            font:12.5px/1.55 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; overflow-x:auto; }}
  .logline {{ white-space:pre-wrap; color:#cbd5e1; }}
  .logline.dim {{ color:#6b7280; }}
  .foot {{ margin-top:22px; color:#6b7280; font-size:12px; text-align:center; }}
  a {{ color:#60a5fa; }}
</style></head>
<body><div class="wrap">
  <h1>CFB Index — Pipeline Status</h1>
  <div class="sub">Live view of your data pipeline. This page refreshes itself every {REFRESH_SECONDS} seconds.</div>
  <div class="banner {banner_cls}">{banner_txt}</div>
  <div class="grid">
    {_card(collect)}
    {_card(build)}
  </div>
  <div style="margin-top:14px">{site_card}</div>
  <div class="section-t">Recent activity — {_esc(active["label"])}</div>
  <div class="logbox">{act_rows}</div>
  <div class="foot">Updated {now} · auto-refreshes every {REFRESH_SECONDS}s · close the server window to stop</div>
</div></body></html>"""


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path.startswith("/favicon"):
            self.send_response(204); self.end_headers(); return
        try:
            body = render().encode("utf-8")
        except Exception as exc:  # noqa: BLE001 — never let a parse error kill the page
            body = (f"<html><body style='font-family:sans-serif;background:#111;color:#eee;padding:40px'>"
                    f"<h2>Status page hit an error</h2><pre>{html.escape(repr(exc))}</pre>"
                    f"<p>It will retry automatically.</p>"
                    f"<meta http-equiv='refresh' content='{REFRESH_SECONDS}'></body></html>").encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # silence per-request console spam
        pass


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print("=" * 56)
    print("  CFB Index build-status dashboard is running.")
    print(f"  Open this in your browser:  http://localhost:{PORT}")
    print("  Close this window to stop it.")
    print("=" * 56)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
