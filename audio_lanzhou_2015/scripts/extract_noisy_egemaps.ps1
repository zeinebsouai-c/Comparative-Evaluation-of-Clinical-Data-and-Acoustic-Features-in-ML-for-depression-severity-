# Extract eGeMAPS features from a noisy/perturbed resampled WAV tree using openSMILE.
#
# Optional overrides:
#     $env:OPENSMILE_ROOT = "D:\tools\opensmile-3.0-win-x64"   # openSMILE elsewhere
#     $env:MODMA_DATA_DIR = "E:\modma\audio_lanzhou_2015"      # dataset elsewhere

param([string]$Root = "audio_lanzhou_2015_noisy")

$data = if ($env:MODMA_DATA_DIR) { $env:MODMA_DATA_DIR } else { Split-Path -Parent $PSScriptRoot }
$smileRoot = if ($env:OPENSMILE_ROOT) { $env:OPENSMILE_ROOT } else { Join-Path $data "tools\opensmile-3.0-win-x64" }

$smile = Join-Path $smileRoot "bin\SMILExtract.exe"
$cfg   = Join-Path $smileRoot "config\egemaps\v01a\eGeMAPSv01a.conf"
$root  = if ([System.IO.Path]::IsPathRooted($Root)) { $Root } else { Join-Path $data $Root }

# --- Sanity checks ---
if (-not (Test-Path $smile)) { Write-Error "SMILExtract not found: $smile  (set `$env:OPENSMILE_ROOT)"; return }
if (-not (Test-Path $cfg))   { Write-Error "Config not found: $cfg"; return }
if (-not (Test-Path $root))  { Write-Error "Audio tree not found: $root  (generate it first)"; return }

$wavs = Get-ChildItem -Path $root -Recurse -Filter *_resampled.wav
Write-Host "Found $($wavs.Count) WAV files in $Root. Extracting..."

$done = 0; $skipped = 0; $failed = 0
foreach ($wav in $wavs) {
    $outDir = Join-Path $wav.DirectoryName "egemaps"
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null

    $outCsv = Join-Path $outDir ($wav.BaseName + "_egemaps.csv")
    if (Test-Path $outCsv) { $skipped++; continue }

    & $smile -C $cfg -I $wav.FullName -O $outCsv -l 1
    if ($LASTEXITCODE -eq 0) { $done++ } else { Write-Warning "Failed: $($wav.FullName)"; $failed++ }
}

Write-Host "Done. Extracted $done, skipped $skipped existing, $failed failed."
