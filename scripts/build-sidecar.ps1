$ErrorActionPreference = "Stop"

$Root = Split-Path $PSScriptRoot -Parent
$SidecarDir = Join-Path $Root "apps\sidecar"
$DesktopTauri = Join-Path $Root "apps\desktop\src-tauri"
$BinariesDir = Join-Path $DesktopTauri "binaries"
$VenvDir = Join-Path $SidecarDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

Write-Host "Building Kie sidecar (PyInstaller)..." -ForegroundColor Cyan

if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating sidecar venv..." -ForegroundColor Yellow
    $basePython = (Get-Command python -ErrorAction Stop).Source
    & $basePython -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { throw "Failed to create sidecar venv" }
}

Write-Host "Installing sidecar dependencies..." -ForegroundColor Cyan
Push-Location $SidecarDir
try {
    & $VenvPython -m pip install -q -U pip
    if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }

    & $VenvPython -m pip install -q -e ".[dev]"
    if ($LASTEXITCODE -ne 0) { throw "sidecar package install failed" }

    & $VenvPython -m pip install -q pyinstaller
    if ($LASTEXITCODE -ne 0) { throw "pyinstaller install failed" }

    & $VenvPython -m PyInstaller --noconfirm kie-sidecar.spec
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
} finally {
    Pop-Location
}

$builtExe = Join-Path $SidecarDir "dist\kie-sidecar.exe"
if (-not (Test-Path $builtExe)) {
    throw "Expected sidecar binary at $builtExe"
}

Write-Host "Smoke-testing sidecar binary..." -ForegroundColor Cyan
$testPort = 19876
$testData = Join-Path $env:TEMP ("kie-sidecar-smoke-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
New-Item -ItemType Directory -Force -Path $testData | Out-Null

$proc = Start-Process `
    -FilePath $builtExe `
    -PassThru `
    -WindowStyle Hidden `
    -Environment @{
        KIE_DATA_DIR = $testData
        KIE_PORT     = "$testPort"
    }

try {
    $deadline = (Get-Date).AddSeconds(90)
    $ok = $false
    while ((Get-Date) -lt $deadline) {
        if ($proc.HasExited) { break }
        try {
            $response = Invoke-WebRequest `
                -Uri "http://127.0.0.1:$testPort/health" `
                -UseBasicParsing `
                -TimeoutSec 3
            if ($response.StatusCode -eq 200) {
                $ok = $true
                break
            }
        } catch {
            # still starting
        }
        Start-Sleep -Seconds 2
    }

    if (-not $ok) {
        $exitCode = if ($proc.HasExited) { $proc.ExitCode } else { "running" }
        throw "Sidecar smoke test failed on port $testPort (exit: $exitCode)"
    }

    Write-Host "Sidecar smoke test passed." -ForegroundColor Green
} finally {
    if (-not $proc.HasExited) {
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }
    Remove-Item -Recurse -Force $testData -ErrorAction SilentlyContinue
}

New-Item -ItemType Directory -Force -Path $BinariesDir | Out-Null
$targetName = "kie-sidecar-x86_64-pc-windows-msvc.exe"
$targetPath = Join-Path $BinariesDir $targetName
Copy-Item -Force $builtExe $targetPath

Write-Host "Sidecar copied to $targetPath" -ForegroundColor Green
