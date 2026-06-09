# scripts/comprehensive_finish.ps1
#
# Master "make it the most comprehensive end product" finisher. Run AFTER the
# Reddit backfill so it works on the complete corpus and is the only DB writer.
# Mirrors .github/workflows/world_class_enrich.yml (local-adapted: no GH artifact
# download / published-branch push) and prepends the 2023 gap-fill + per-week mood.
# Continue-on-error throughout; logs to logs/. Uses local Ollama for Tier-A (free)
# and cloud Claude for Tier-B editorial (metered). Expect MANY hours.

$ErrorActionPreference = "Continue"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$SEASON = "2025"

$env:PYTHONUTF8 = "1"
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) { $env:Path = (Split-Path -Parent $VenvPython) + ";" + $env:Path }
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*)\s*$') {
            $n = $matches[1]; $v = $matches[2] -replace '^"(.*)"$', '$1' -replace "^'(.*)'$", '$1'
            [Environment]::SetEnvironmentVariable($n, $v, "Process")
        }
    }
}
$LogDir = Join-Path $RepoRoot "logs"; if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory $LogDir | Out-Null }
$LogPath = Join-Path $LogDir ("comprehensive_finish_{0:yyyy-MM-dd_HHmmss}.log" -f (Get-Date))
function Log([string]$m) { $s = Get-Date -Format "yyyy-MM-ddTHH:mm:ssK"; "$s  $m" | Tee-Object -FilePath $LogPath -Append }
function Run([string]$label, [string[]]$a) {
    Log "== $label =="
    & python -u manage.py @a *>&1 | Tee-Object -FilePath $LogPath -Append
    if ($LASTEXITCODE -ne 0) { Log "   $label exited $LASTEXITCODE (continuing)" }
}
function Tool([string]$label, [string]$rel) {
    Log "== tool: $label =="
    & python -u $rel *>&1 | Tee-Object -FilePath $LogPath -Append
    if ($LASTEXITCODE -ne 0) { Log "   $label exited $LASTEXITCODE (continuing)" }
}

$sw = [System.Diagnostics.Stopwatch]::StartNew()
Log "==== comprehensive_finish START ===="

# ── STEP 1: fill the 2023 season gap (games/models/heisman + stats + context) ──
Run "cfbd-history 2023 (+models)"   @("backfill-cfbd-history","--start-season","2023","--end-season","2023","--include-postseason","--run-models","--skip-play-level")
Run "game-player-stats 2023"        @("backfill-game-player-stats","--start-season","2023","--end-season","2023","--include-postseason","--missing-only")
Run "player-context 2023"           @("backfill-player-context","--start-season","2023","--end-season","2023")

# ── STEP 2: deeper per-week team mood aggregation (all offseason weeks) ──
Log "== sub-script: force_offseason_mood_aggregation.ps1 =="
& (Join-Path $RepoRoot "scripts\force_offseason_mood_aggregation.ps1")
Log "   mood aggregation returned $LASTEXITCODE"

# ── STEP 3: full AI enrichment (mirrors world_class_enrich.yml) ──
# Wire
Run "wire-ingest"                   @("wire-ingest","--days","7")
Run "wire-generate-editorial"       @("wire-generate-editorial","--days","14")
Run "render-wire"                   @("render-wire")
# Daily edition
Run "seed-editions"                 @("seed-editions")
Run "generate-daily"                @("generate-daily")
Run "render-daily"                  @("render-daily")
# Mailbag
Run "mailbag-seed-submissions"      @("mailbag-seed-submissions","--n","5")
Run "mailbag-curate-submissions"    @("mailbag-curate-submissions")
Run "mailbag-generate-answers"      @("mailbag-generate-answers")
Run "render-mailbag"                @("render-mailbag")
# Reactions
Run "reactions-check-triggers"      @("reactions-check-triggers","--hours","168","--auto")
Run "render-reactions"              @("render-reactions")
# Team-page AI
Run "load-team-profiles"            @("load-team-profiles")
Run "generate-narratives"           @("generate-narratives","--llm","claude")
Run "generate-chronicle"            @("generate-chronicle","--workers","3")
Run "refresh-savant"                @("refresh-savant","--season",$SEASON)
Run "refresh-season-arc"            @("refresh-season-arc","--latest-season",$SEASON)
Run "refresh-rivalry"               @("refresh-rivalry")
Run "render-team-pages"             @("render-team-pages")
# Retro
Run "seed-retro-all"                @("seed-retro-all")
Run "build-retro-pages"             @("build-retro-pages")
# Player mood season rollup (per-week already done in STEP 2)
Run "compute-player-season-mood"    @("compute-player-season-mood","--season",$SEASON)
# Awards (extend to full 2014-2025 history)
Run "scrape-wiki-awards 2014-2025"  @("scrape-wiki-awards","--start-year","2014","--end-year",$SEASON,"--auto-import")
# Canon lists
Run "seed-canon-metadata"           @("seed-canon-metadata")
Run "canon: 100 best players"       @("generate-canon-list","--list","the-100-best-players-cfp-era","--year","2026")
Run "canon: 50 defining games"      @("generate-canon-list","--list","the-50-most-defining-games-cfp-era","--year","2026")
Run "canon: 25 coaching hires"      @("generate-canon-list","--list","the-25-best-coaching-hires-2020s","--year","2026")
Run "render-canon-all"              @("render-canon-all")
# Receipts / best calls
Run "generate-best-calls"           @("generate-best-calls","--year","2025","--n","25","--opus-top","3")
Run "render-receipts"               @("render-receipts")
# Hub + editions + storylines + methodology + homepage
Run "hub-computed-evidence"         @("hub-computed-evidence")
Run "prepare-pulse"                 @("prepare-pulse")
Run "generate-edition-covers"       @("generate-edition-covers","--status","draft")
Run "render-storylines"             @("render-storylines")
Run "build-editions-archive"        @("build-editions-archive")
Run "build-methodology"             @("build-methodology")
Run "render-homepage"               @("render-homepage")
Run "render-wire (homepage patch)"  @("render-wire")

# ── STEP 4: post-process layer (local enhancement tools) ──
Tool "inject_rankings_logos"        "tools\inject_rankings_logos.py"
Tool "decorate_rankings_table"      "tools\wcfb_enhancements\decorate_rankings_table.py"
Tool "build_compare"                "tools\wcfb_enhancements\build_compare.py"
Tool "wcfb_install"                 "tools\wcfb_enhancements\install.py"

# ── STEP 5: final full build ──
Run "build-site (final)"            @("build-site")

$sw.Stop()
Log ("==== comprehensive_finish END (elapsed {0:N1} min) ====" -f $sw.Elapsed.TotalMinutes)
