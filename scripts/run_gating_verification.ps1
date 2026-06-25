# Run plan.md verification via UTF-8 Python harness (no PowerShell Out-File encoding issues).
param(
    [string]$Scratch = $env:QEC_GATING_SCRATCH
)
if ($Scratch) {
    $env:QEC_GATING_SCRATCH = $Scratch
}
Set-Location (Split-Path $PSScriptRoot -Parent)
python scripts/verify_gating.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Gating evidence written to $env:QEC_GATING_SCRATCH"