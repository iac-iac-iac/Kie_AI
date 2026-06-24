param(
    [switch]$Release
)

$ErrorActionPreference = "Stop"

$Root = Split-Path $PSScriptRoot -Parent

Write-Host "Kie AI Desktop - production build" -ForegroundColor Cyan

if ($Release) {
    if (-not $env:TAURI_SIGNING_PRIVATE_KEY) {
        Write-Warning "TAURI_SIGNING_PRIVATE_KEY is not set. Updater artifacts may fail to sign."
    }
}

& (Join-Path $PSScriptRoot "build-sidecar.ps1")

Push-Location (Join-Path $Root "apps\desktop")
try {
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "Frontend build failed" }

    if ($Release -and $env:TAURI_SIGNING_PRIVATE_KEY) {
        npm run tauri build -- --config '{"bundle":{"createUpdaterArtifacts":true}}'
    } else {
        npm run tauri build
    }
    if ($LASTEXITCODE -ne 0) { throw "Tauri build failed" }
} finally {
    Pop-Location
}

$bundleDir = Join-Path $Root "apps\desktop\src-tauri\target\release\bundle\nsis"
Write-Host "Build complete. Installer:" -ForegroundColor Green
Get-ChildItem $bundleDir -Filter "*.exe" | ForEach-Object { Write-Host "  $($_.FullName)" }

if ($Release) {
    Write-Host "Updater artifacts:" -ForegroundColor Green
    Get-ChildItem $bundleDir -Include "*.sig", "latest.json", "*.nsis.zip" -Recurse | ForEach-Object {
        Write-Host "  $($_.FullName)"
    }
}
