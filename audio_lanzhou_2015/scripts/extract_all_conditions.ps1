# Run openSMILE over every robustness audio condition.
# Generate the trees first with the Step 1 cell in robustness_experiments.ipynb.

$conditions = @("audio_snr20","audio_snr10","audio_snr05","audio_snr00","audio_snr-05","audio_random")

foreach ($d in $conditions) {
    Write-Host "`n=== $d ===" -ForegroundColor Cyan
    & (Join-Path $PSScriptRoot "extract_noisy_egemaps.ps1") -Root $d
}
Write-Host "`nAll conditions extracted." -ForegroundColor Green
