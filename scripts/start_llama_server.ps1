#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Start llama-server (llama.cpp) for the CFB Index Chronicle pipeline.

.DESCRIPTION
    Launches a single llama-server instance for the Writer role on port 8001,
    tuned for the RTX 5070 (12 GB VRAM) + Core Ultra 7 265K desktop.

    Writer role:  port 8001  — Mistral-Nemo-12B (Q4_K_M ~7.5 GB) or user model
    Planner role: handled by Ollama (already running on port 11434)

    VRAM budget (12 GB):
      Writer  Q4_K_M 12B  = ~7.5 GB
      KV-cache 4 slots    = ~0.5 GB  (at Q8_0, 32K ctx / 4 = 8K effective per slot)
      System headroom     = ~0.8 GB
      Total               ≈ 8.8 GB  → safe margin for 12 GB card
      (DO NOT add a Q5_K_M writer + Ollama simultaneously — 9.3+5.2 = 14.5 GB)

    When you upgrade to 24 GB VRAM:
      1. Switch writer to Q5_K_M (9.3 GB) for higher factual accuracy
      2. Add a second llama-server on port 8002 for Qwen3-8B planner
      3. Set CHRONICLE_PREFER_LLAMASERVER=1 for both roles

.PARAMETER ModelPath
    Path to the GGUF model file for the writer role.
    Default: $env:LLAMA_WRITER_MODEL (env var) or a sensible user-profile guess.

.PARAMETER Port
    Port for the writer server. Default: 8001.

.PARAMETER CtxSize
    Context window per slot. Default: 8192 (4 slots × 8K = 32K total).

.PARAMETER ParallelSlots
    Number of parallel request slots (--parallel N).
    Set to match CHRONICLE_PARALLEL_WORKERS. Default: 4.

.EXAMPLE
    # Start with auto-detected model path
    .\scripts\start_llama_server.ps1

.EXAMPLE
    # Point at a specific GGUF
    .\scripts\start_llama_server.ps1 -ModelPath "D:\models\Mistral-Nemo-12B-Q4_K_M.gguf"

.NOTES
    After this server is running:
      1. Set CHRONICLE_PREFER_LLAMASERVER=1 in your .env or CI secrets
      2. Set CHRONICLE_PARALLEL_WORKERS=4 to fill all GPU slots
      3. Ollama stays running for planner/critic (qwen3:8b)

    Required env vars to set in .env / CI:
      CHRONICLE_PREFER_LLAMASERVER=1
      CHRONICLE_PARALLEL_WORKERS=4
      OLLAMA_FLASH_ATTENTION=1
      OLLAMA_KV_CACHE_TYPE=q8_0
#>

param(
    [string]$ModelPath = "",
    [int]$Port = 8001,
    [int]$CtxSize = 8192,
    [int]$ParallelSlots = 4
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Resolve model path
# ---------------------------------------------------------------------------
if (-not $ModelPath) {
    # Check env var first
    $ModelPath = $env:LLAMA_WRITER_MODEL
}

if (-not $ModelPath) {
    # Auto-discover: look for Mistral-Nemo GGUF in common locations
    $candidates = @(
        "D:\models",
        "C:\models",
        "$env:USERPROFILE\models",
        "$env:USERPROFILE\.cache\huggingface\hub",
    )
    foreach ($dir in $candidates) {
        if (Test-Path $dir) {
            $found = Get-ChildItem -Path $dir -Filter "*Mistral-Nemo*Q4*K*M*.gguf" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
            if (-not $found) {
                $found = Get-ChildItem -Path $dir -Filter "*mistral*nemo*q4*.gguf" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
            }
            if ($found) {
                $ModelPath = $found.FullName
                Write-Host "[llama-server] Auto-discovered model: $ModelPath" -ForegroundColor Cyan
                break
            }
        }
    }
}

if (-not $ModelPath -or -not (Test-Path $ModelPath)) {
    Write-Error @"
Cannot find a writer GGUF model file. Options:
  1. Set the LLAMA_WRITER_MODEL environment variable to the full path of your GGUF
  2. Pass -ModelPath explicitly:
       .\scripts\start_llama_server.ps1 -ModelPath "D:\models\Mistral-Nemo-12B-Q4_K_M.gguf"
  3. Download from HuggingFace:
       # Requires huggingface-cli
       huggingface-cli download bartowski/Mistral-Nemo-Instruct-2407-GGUF Mistral-Nemo-Instruct-2407-Q4_K_M.gguf --local-dir D:\models
"@
}

# ---------------------------------------------------------------------------
# Resolve llama-server binary
# ---------------------------------------------------------------------------
$llamaBin = $null
$llamaCandidates = @(
    "llama-server",                              # On PATH
    "C:\tools\llama.cpp\build\bin\llama-server.exe",
    "C:\llama.cpp\build\bin\llama-server.exe",
    "$env:USERPROFILE\llama.cpp\build\bin\llama-server.exe",
    "D:\llama.cpp\build\bin\llama-server.exe",
)
foreach ($bin in $llamaCandidates) {
    $resolved = Get-Command $bin -ErrorAction SilentlyContinue
    if ($resolved) {
        $llamaBin = $resolved.Source
        break
    }
}

if (-not $llamaBin) {
    Write-Error @"
llama-server binary not found. Build llama.cpp with CUDA support:
  git clone https://github.com/ggerganov/llama.cpp
  cmake -B build -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release
  cmake --build build --config Release -j8

Then add the build/bin directory to your PATH, or set LLAMA_SERVER_BIN
to the full path of llama-server.exe.
"@
}

Write-Host "[llama-server] Binary:  $llamaBin" -ForegroundColor Green
Write-Host "[llama-server] Model:   $ModelPath" -ForegroundColor Green
Write-Host "[llama-server] Port:    $Port" -ForegroundColor Green
Write-Host "[llama-server] Slots:   $ParallelSlots  (CHRONICLE_PARALLEL_WORKERS=$ParallelSlots)" -ForegroundColor Green
Write-Host "[llama-server] Ctx/slot: $CtxSize  (total KV = $($CtxSize * $ParallelSlots) tokens)" -ForegroundColor Green
Write-Host ""

# ---------------------------------------------------------------------------
# Launch llama-server
# RTX 5070 optimisation flags:
#   --n-gpu-layers 99     → all layers on GPU
#   --ctx-size N          → per-slot context (multiply by --parallel for total)
#   --parallel N          → concurrent request slots
#   --batch-size 2048     → token batch size for prompt ingestion
#   --ubatch-size 512     → micro-batch size inside batch (CUDA graph friendly)
#   --cont-batching       → continuous batching (don't wait for all slots to drain)
#   --flash-attn          → FlashAttention-2 (requires CUDA build with FA support)
#   --cache-type-k q8_0   → KV cache in Q8 — half the VRAM of fp16 with ~0 quality loss
#   --cache-type-v q8_0   → same for V cache
#   --mlock               → lock model weights in RAM (prevent OS swapping)
# ---------------------------------------------------------------------------
$args_list = @(
    "--model", $ModelPath,
    "--port", $Port,
    "--host", "127.0.0.1",
    "--n-gpu-layers", 99,
    "--ctx-size", $CtxSize,
    "--parallel", $ParallelSlots,
    "--batch-size", 2048,
    "--ubatch-size", 512,
    "--cont-batching",
    "--flash-attn",
    "--cache-type-k", "q8_0",
    "--cache-type-v", "q8_0",
    "--mlock",
    "--log-prefix"           # Add timestamp prefix to log lines
)

Write-Host "[llama-server] Starting — Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

& $llamaBin @args_list
