$ErrorActionPreference = "Stop"

$Root = Split-Path $PSScriptRoot -Parent
$SidecarDir = Join-Path $Root "apps\sidecar"
$DesktopTauri = Join-Path $Root "apps\desktop\src-tauri"
$BinariesDir = Join-Path $DesktopTauri "binaries"

Write-Host "Building Kie sidecar (PyInstaller)..." -ForegroundColor Cyan

$venvPython = Join-Path $SidecarDir ".venv\Scripts\python.exe"
$python = if (Test-Path $venvPython) { $venvPython } else { "python" }

Push-Location $SidecarDir
try {
    & $python -m pip install -q pyinstaller
    & $python -m PyInstaller --noconfirm kie-sidecar.spec
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
} finally {
    Pop-Location
}

$builtExe = Join-Path $SidecarDir "dist\kie-sidecar.exe"
if (-not (Test-Path $builtExe)) {
    throw "Expected sidecar binary at $builtExe"
}

New-Item -ItemType Directory -Force -Path $BinariesDir | Out-Null
$targetName = "kie-sidecar-x86_64-pc-windows-msvc.exe"
$targetPath = Join-Path $BinariesDir $targetName
Copy-Item -Force $builtExe $targetPath

Write-Host "Sidecar copied to $targetPath" -ForegroundColor Green
