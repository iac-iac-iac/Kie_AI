$ErrorActionPreference = "Stop"

$Root = Split-Path $PSScriptRoot -Parent
$BinariesDir = Join-Path $Root "apps\desktop\src-tauri\binaries"
$Target = Join-Path $BinariesDir "kie-sidecar-x86_64-pc-windows-msvc.exe"

if (Test-Path $Target) {
    Write-Host "Sidecar binary already present: $Target"
    exit 0
}

New-Item -ItemType Directory -Force -Path $BinariesDir | Out-Null

$venvPython = Join-Path $Root "apps\sidecar\.venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    Copy-Item -Force $venvPython $Target
    Write-Host "Created dev placeholder sidecar binary from venv python: $Target"
    Write-Host "Run .\\scripts\\build-sidecar.ps1 before production build."
    exit 0
}

# Minimal valid stub for Tauri compile when Python venv is absent
Set-Content -Path $Target -Value "MZ" -Encoding Byte -NoNewline
Write-Host "Created minimal placeholder at $Target (run build-sidecar.ps1 for production)"
