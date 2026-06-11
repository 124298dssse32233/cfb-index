# scripts/build_publish.ps1
#
# BUILD + PUBLISH half of the decoupled pipeline (cadence architecture, 2026-06).
# Reads SQLite AS-OF-NOW (it does NOT fetch any source over the network), so it
# ships whatever data is present and is structurally un-blockable by a slow/failed
# collect.ps1 run. Schedule at a fixed daily slot (e.g. 09:00). In-season CFBD week
# ingest + model runs are kept here as fast, gated pre-build steps.
#
# Activate via register_split_tasks.ps1; until then daily_ingest.ps1 is active.

$PipelineName = "build_publish"
. "$PSScriptRoot\_pipeline_common.ps1"

# =========================================================================
# C. CFBD weekly refresh - in-season only (fast; needs fresh game data)
# =========================================================================
if ($global:IsInSeason) {
    Run "cfbd: ingest-cfbd-week --season=$($global:CurSeason) --week=$($global:SeasonWeek)" {
        python manage.py ingest-cfbd-week --season $global:CurSeason --week $global:SeasonWeek
    }
} else {
    Log "   (offseason: skipping ingest-cfbd-week)"
}

# =========================================================================
# D. Aggregators - current week (canonical keys from resolve-week)
# =========================================================================
Run "aggregate: compute-cohort-week --week=$($global:IsoWeekKey)" {
    python manage.py compute-cohort-week --week $global:IsoWeekKey
} -Critical
Run "aggregate: compute-divergence --week=$($global:IsoWeekKey)" {
    python manage.py compute-divergence --week $global:IsoWeekKey
}
Run "aggregate: compute-mood-week --week=$($global:PrevMonday)" {
    python manage.py compute-mood-week --week $global:PrevMonday --no-from-seed
} -Critical
Run "aggregate: compute-rivalry-ratios --week=$($global:PrevMonday)" {
    python manage.py compute-rivalry-ratios --week $global:PrevMonday --no-from-seed
}
Run "aggregate: mine-lexicon --week=$($global:PrevMonday)" {
    python manage.py mine-lexicon --week $global:PrevMonday --no-from-seed
}

# =========================================================================
# E. Player pipeline (tag -> per-week mood -> season rollup)
# =========================================================================
Run "player: tag-player-mentions --season=$($global:CurSeason) --commit" {
    python manage.py tag-player-mentions --season $global:CurSeason --commit
}
Run "player: compute-player-week-mood --week=$($global:IsoWeekKey)" {
    python manage.py compute-player-week-mood --week $global:IsoWeekKey
}
Run "player: compute-player-season-mood --season=$($global:CurSeason)" {
    python manage.py compute-player-season-mood --season $global:CurSeason
}

# =========================================================================
# E.5 Encoder sentiment classify (.venv-ml, before the feature rebuild so
#     features aggregate ENCODER labels). No-op + log if .venv-ml absent.
# =========================================================================
$MlPython = Join-Path $global:RepoRoot ".venv-ml\Scripts\python.exe"
if (Test-Path $MlPython) {
    Run "sentiment: encoder classify (.venv-ml, pinned heads)" {
        & $MlPython scripts/sentiment_classify_daily.py --commit
    }
} else {
    Log "   (.venv-ml absent -- skipping encoder classify; today's new docs keep VADER labels)"
}

# =========================================================================
# E.6 ML relevance scoring (Stage 2, REPORT-ONLY soak — writes
#     relevance_ml_score to conversation_documents; nothing gates on it
#     yet). Own venv (.venv-cls: setfit + transformers>=4.48 for ModernBERT
#     — would conflict with .venv-ml's pinned 4.46). Skips cleanly if the
#     venv or trained model is absent.
# =========================================================================
$ClsPython = Join-Path $global:RepoRoot ".venv-cls\Scripts\python.exe"
$ClsModel  = Join-Path $global:RepoRoot "models\relevance_setfit_v1"
if ((Test-Path $ClsPython) -and (Test-Path $ClsModel)) {
    Run "relevance: ML classify (report-only soak)" {
        & $ClsPython scripts/relevance_classify_daily.py --commit
    }
} else {
    Log "   (.venv-cls or relevance model absent -- skipping ML relevance scoring)"
}

# =========================================================================
# E.7 Language Layer (Wave 1+2): fan-voice keyness (season + current-week
#     cuts), rivalry mirror, and fanbase voice personality profiles. These
#     write team_discourse_terms / team_discourse_mirror / fanbase_voice_profile
#     for the team-page Lexicon, Mirror, and Voice modules. Best-effort —
#     failures must NOT abort the publish (no -Critical), matching E.5/E.6.
#     Season = CFB season year (Jul+ -> this year, else last year); PS 5.1 has
#     no ternary, so compute with if/else.
# =========================================================================
if ((Get-Date).Month -ge 7) {
    $DiscourseSeason = (Get-Date).Year
} else {
    $DiscourseSeason = (Get-Date).Year - 1
}
Run "discourse: keyness (season+weekly)" {
    python manage.py compute-discourse-keyness --season $DiscourseSeason --weekly --commit
}
Run "discourse: rivalry mirror" {
    python manage.py compute-discourse-mirror --season $DiscourseSeason --commit
}
Run "discourse: fanbase voice" {
    python manage.py compute-fanbase-voice --season $DiscourseSeason --commit
}

# =========================================================================
# F. Team feature rebuild (recomputes team_week_conversation_features)
# =========================================================================
Run "features: build-conversation-features --season=$($global:CurSeason) --week=$($global:SeasonWeek)" {
    python manage.py build-conversation-features --season $global:CurSeason --week $global:SeasonWeek
} -Critical

# =========================================================================
# F.5 Backometer (fan_metrics): 0-100 belief + named zones from the feature
#     rows just rebuilt above. Whole-season recompute is cheap and lets the
#     hysteresis walk weeks in order.
# =========================================================================
Run "fan-metrics: compute-backometer --season=$($global:CurSeason)" {
    python manage.py compute-backometer --season $global:CurSeason
}
Run "fan-metrics: compute-aura --season=$($global:CurSeason)" {
    python manage.py compute-aura --season $global:CurSeason
}
Run "fan-metrics: compute-delusion-premium --season=$($global:CurSeason)" {
    python manage.py compute-delusion-premium --season $global:CurSeason
}

# =========================================================================
# F.6 NIL valuations: weekly On3 CFB top-100 snapshot.
#     Non-critical: if On3 is unreachable the build continues unaffected.
# =========================================================================
Run "nil: scrape-nil-valuations --limit 200" {
    python manage.py scrape-nil-valuations --limit 200
}

# =========================================================================
# G. Models (in-season only - require fresh game data)
# =========================================================================
if ($global:IsInSeason) {
    Run "models: run-models --season=$($global:CurSeason) --through-week=$($global:SeasonWeek)" {
        python manage.py run-models --season $global:CurSeason --through-week $global:SeasonWeek
    }
    Run "models: run-heisman-model --season=$($global:CurSeason) --through-week=$($global:SeasonWeek)" {
        python manage.py run-heisman-model --season $global:CurSeason --through-week $global:SeasonWeek
    }
} else {
    Log "   (offseason: skipping run-models + run-heisman-model)"
}

# =========================================================================
# H. Board builders (fast, stateless reads)
# =========================================================================
Run "board: build-the-room-board --season=$($global:CurSeason)" {
    python manage.py build-the-room-board --season $global:CurSeason --week $global:SeasonWeek
}
Run "board: build-players-landing --season=$($global:CurSeason)" {
    python manage.py build-players-landing --season $global:CurSeason --week $global:SeasonWeek
}
Run "board: build-signature-story-board --season=$($global:CurSeason)" {
    python manage.py build-signature-story-board --season $global:CurSeason
}
Run "board: build-methodology" { python manage.py build-methodology }

# =========================================================================
# I. Full static site rebuild - the main product output
# =========================================================================
Run "team-preview: build-team-preview-layer" { python manage.py build-team-preview-layer }
Run "team-preview: generate-team-preview-claims" {
    python manage.py generate-team-preview-claims --season (Get-Date -Format yyyy) --as-of (Get-Date -Format yyyy-MM-dd)
}
Run "site: build-site" { python manage.py build-site } -Critical
Run "site: build-editions-archive" { python manage.py build-editions-archive }
# Section landing pages that build-site does NOT emit. These patch INTO the
# freshly-built output/site, so they MUST run after build-site (which wipes the
# tree). The box used to drop /storylines/, /wire/, /anniversary/today/ on every
# deploy because only the GitHub section-workflows rendered them — and since a
# Vercel deploy is a full snapshot, the box's incomplete output/site clobbered
# them off production. Render them here so the box ships a COMPLETE site.
# All three exit 0 even with no offseason data (they leave a stub index), so
# they stay non-Critical: an empty section must never block the deploy.
Run "site: render-storylines" { python manage.py render-storylines }
Run "site: render-wire --days 30" { python manage.py render-wire --days 30 }
Run "site: render-today-in-history" { python manage.py render-today-in-history }

# =========================================================================
# J. Status dump for the log trailer
# =========================================================================
Run "status: fanintel-status" { python manage.py fanintel-status }

# =========================================================================
# K. Publish to Vercel (gated + smoke-checked + alias-rotated, own log).
#    Skipped if the build failed so a broken build can never deploy.
# =========================================================================
if ($global:FailedSteps -contains "site: build-site") {
    Log "== publish: SKIPPED (build-site failed; refusing to deploy a broken build) =="
} else {
    Log "== publish: scripts\publish_to_vercel.ps1 =="
    & (Join-Path $global:RepoRoot "scripts\publish_to_vercel.ps1") *>&1 | Tee-Object -FilePath $global:LogPath -Append
    Log "   publish_to_vercel returned $LASTEXITCODE"
    if ($LASTEXITCODE -ne 0) { $global:FailedSteps += "publish_to_vercel" }
}

Complete-Pipeline "HEALTHCHECK_URL"
