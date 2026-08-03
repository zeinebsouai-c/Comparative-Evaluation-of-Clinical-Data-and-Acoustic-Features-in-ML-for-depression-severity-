# Extract eGeMAPS features from the NOISY resampled WAVs using openSMILE.
# Run from anywhere:  & "C:\...\scripts\extract_noisy_egemaps.ps1"

$base  = "C:\Users\zeine\OneDrive\Documents\bachelor thesis\data\audio_lanzhou_2015\audio_lanzhou_2015"
$smile = "$base\tools\opensmile-3.0-win-x64\bin\SMILExtract.exe"
$cfg   = "$base\tools\opensmile-3.0-win-x64\config\egemaps\v01a\eGeMAPSv01a.conf"
$root  = "$base\audio_lanzhou_2015_noisy"

# --- Sanity checks ---
if (-not (Test-Path $smile)) { Write-Error "SMILExtract not found: $smile"; return }
if (-not (Test-Path $cfg))   { Write-Error "Config not found: $cfg"; return }
if (-not (Test-Path $root))  { Write-Error "Noisy audio tree not found: $root  (run the Step 2 noise cell first)"; return }

$wavs = Get-ChildItem -Path $root -Recurse -Filter *_resampled.wav
Write-Host "Found $($wavs.Count) noisy WAV files. Extracting..."

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
