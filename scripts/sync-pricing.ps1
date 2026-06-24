param(
    [string]$OverridesPath = "",
    [string]$SidecarUrl = "http://127.0.0.1:3847"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$defaultOverrides = Join-Path $repoRoot "apps\sidecar\pricing\pricing_overrides.json"
$path = if ($OverridesPath) { $OverridesPath } else { $defaultOverrides }

if (-not (Test-Path $path)) {
    Write-Error "Overrides file not found: $path"
}

$raw = Get-Content -Path $path -Raw -Encoding UTF8
$null = $raw | ConvertFrom-Json

$body = @{ overrides_path = $path } | ConvertTo-Json
$response = Invoke-RestMethod -Uri "$SidecarUrl/internal/sync-pricing" -Method POST -Body $body -ContentType "application/json"

Write-Host "Pricing sync complete:"
Write-Host "  seeded: $($response.seeded)"
Write-Host "  overrides_applied: $($response.overrides_applied)"
Write-Host "  latest_updated_at: $($response.latest_updated_at)"
