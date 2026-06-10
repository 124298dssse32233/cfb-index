# setup_ml_env.ps1 — install the isolated sentiment-ML stack into .venv-ml.
# Separate from the production .venv so the 24/7 pipeline is never touched.
# Logs to logs/ml_setup.log. Idempotent-ish (pip skips already-satisfied).
$ErrorActionPreference = "Continue"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$py = Join-Path $RepoRoot ".venv-ml\Scripts\python.exe"
$LogDir = Join-Path $RepoRoot "logs"; if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory $LogDir | Out-Null }
$Log = Join-Path $LogDir "ml_setup.log"
function L($m){ $s = Get-Date -Format "HH:mm:ss"; "$s  $m" | Tee-Object -FilePath $Log -Append }

L "==== ML env setup START ===="
L "python: $py"

L "-- upgrade pip --"
& $py -m pip install --upgrade pip *>&1 | Tee-Object -FilePath $Log -Append

# CUDA 12.4 wheels (driver 610.x is forward-compatible). ~2.5GB download.
L "-- install torch (cu124) --"
& $py -m pip install torch --index-url https://download.pytorch.org/whl/cu124 *>&1 | Tee-Object -FilePath $Log -Append

L "-- install transformers + helpers --"
& $py -m pip install "transformers>=4.40" accelerate safetensors scipy *>&1 | Tee-Object -FilePath $Log -Append

L "-- verify --"
& $py -c "import torch, transformers; print('torch', torch.__version__, 'cuda_avail', torch.cuda.is_available(), 'dev', (torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu')); print('transformers', transformers.__version__)" *>&1 | Tee-Object -FilePath $Log -Append

L "==== ML env setup DONE ===="
