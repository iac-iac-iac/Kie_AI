$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Net.Http

$Root = Split-Path -Parent $PSScriptRoot
$SidecarDir = Join-Path $Root "apps\sidecar"
$DesktopDir = Join-Path $Root "apps\desktop"
$SidecarUrl = if ($env:VITE_SIDECAR_URL) { $env:VITE_SIDECAR_URL } else { "http://127.0.0.1:18765" }
$SidecarPort = ([System.Uri]$SidecarUrl).Port
if (-not $SidecarPort) { $SidecarPort = 18765 }

if (-not $env:KIE_DATA_DIR) {
    $env:KIE_DATA_DIR = Join-Path $env:APPDATA "KieAI"
}

$env:NO_PROXY = "127.0.0.1,localhost"
$env:no_proxy = "127.0.0.1,localhost"

function Get-ListenerPids {
    param([int]$Port)
    $portPattern = ":$Port\s"
    $processIds = @()
    $lines = netstat -ano | Select-String "LISTENING" | Select-String $portPattern
    foreach ($line in $lines) {
        $parts = ($line.ToString() -replace '\s+', ' ').Trim().Split(' ')
        $processId = [int]$parts[-1]
        if ($processId -gt 0) { $processIds += $processId }
    }
    return $processIds | Select-Object -Unique
}

function Stop-ProcessTree {
    param([int]$ProcessId)
    if ($ProcessId -le 0) { return }
    & taskkill.exe /PID $ProcessId /T /F 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
    }
}

function Stop-AllOnPort {
    param([int]$Port)
    for ($attempt = 0; $attempt -lt 10; $attempt++) {
        $processIds = Get-ListenerPids -Port $Port
        if (-not $processIds) { return }
        foreach ($processId in $processIds) {
            Stop-ProcessTree -ProcessId $processId
        }
        Start-Sleep -Milliseconds 400
    }
}

function Stop-KieSidecarPython {
    Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match "kie_sidecar\.main:app" } |
        ForEach-Object { Stop-ProcessTree -ProcessId $_.ProcessId }
}

function Test-PortFree {
    param([int]$Port)
    return -not (Get-ListenerPids -Port $Port)
}

function Wait-PortFree {
    param([int]$Port, [int]$TimeoutSec = 25)
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (Test-PortFree -Port $Port) { return $true }
        Stop-AllOnPort -Port $Port
        Start-Sleep -Milliseconds 400
    }
    return (Test-PortFree -Port $Port)
}

function Test-SidecarReady {
    param([string]$Url)
    $client = $null
    $handler = $null
    try {
        $handler = New-Object System.Net.Http.HttpClientHandler
        $handler.UseProxy = $false
        $client = New-Object System.Net.Http.HttpClient($handler)
        $client.Timeout = [TimeSpan]::FromSeconds(3)

        $health = $client.GetAsync("$Url/health").GetAwaiter().GetResult()
        if (-not $health.IsSuccessStatusCode) { return $false }
        $healthBody = $health.Content.ReadAsStringAsync().GetAwaiter().GetResult() | ConvertFrom-Json
        if ($healthBody.status -ne "ok") { return $false }

        $models = $client.GetAsync("$Url/api/v1/chats/models").GetAwaiter().GetResult()
        if (-not $models.IsSuccessStatusCode) { return $false }

        $imageModels = $client.GetAsync("$Url/api/v1/models?type=image").GetAwaiter().GetResult()
        if (-not $imageModels.IsSuccessStatusCode) { return $false }

        $videoModels = $client.GetAsync("$Url/api/v1/models?type=video").GetAwaiter().GetResult()
        return $videoModels.IsSuccessStatusCode
    } catch {
        return $false
    } finally {
        if ($client) { $client.Dispose() }
        if ($handler) { $handler.Dispose() }
    }
}

Write-Host "Kie AI Desktop - dev mode" -ForegroundColor Cyan
& (Join-Path $PSScriptRoot "ensure-sidecar-binary.ps1")
Write-Host "Sidecar: $SidecarUrl"
Write-Host "Data:    $env:KIE_DATA_DIR"

$venvPython = Join-Path $SidecarDir ".venv\Scripts\python.exe"
$python = if (Test-Path $venvPython) { $venvPython } else { "python" }

Write-Host "Stopping old sidecar processes on port $SidecarPort..." -ForegroundColor Yellow
& (Join-Path $PSScriptRoot "stop-sidecar.ps1")

if (-not (Wait-PortFree -Port $SidecarPort)) {
    $left = Get-ListenerPids -Port $SidecarPort
    throw "Port $SidecarPort is still in use (PIDs: $($left -join ', ')). Run: .\scripts\stop-sidecar.ps1"
}

$logDir = Join-Path $env:KIE_DATA_DIR "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$sessionTag = Get-Date -Format "yyyyMMdd-HHmmss"
$sidecarLogOut = Join-Path $logDir "sidecar-dev-$sessionTag.out.log"
$sidecarLogErr = Join-Path $logDir "sidecar-dev-$sessionTag.err.log"

# Single-process uvicorn avoids zombie reloader children on Windows.
# Set KIE_SIDECAR_RELOAD=1 to enable --reload.
$uvicornArgs = @("-m", "uvicorn", "kie_sidecar.main:app", "--host", "127.0.0.1", "--port", $SidecarPort)
if ($env:KIE_SIDECAR_RELOAD -eq "1") {
    $uvicornArgs += "--reload"
    Write-Host "Sidecar reload enabled (KIE_SIDECAR_RELOAD=1)" -ForegroundColor DarkYellow
}

$sidecarProcess = Start-Process `
    -FilePath $python `
    -ArgumentList $uvicornArgs `
    -WorkingDirectory $SidecarDir `
    -PassThru `
    -WindowStyle Hidden `
    -RedirectStandardOutput $sidecarLogOut `
    -RedirectStandardError $sidecarLogErr

function Stop-Sidecar {
    if ($sidecarProcess -and -not $sidecarProcess.HasExited) {
        Stop-ProcessTree -ProcessId $sidecarProcess.Id
    }
    Stop-KieSidecarPython
    Stop-AllOnPort -Port $SidecarPort
}

Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action { Stop-Sidecar } | Out-Null

try {
    Write-Host "Waiting for sidecar (logs: $sidecarLogOut)..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2

    $deadline = (Get-Date).AddSeconds(45)
    $ready = $false
    while ((Get-Date) -lt $deadline) {
        if ($sidecarProcess.HasExited) {
            Write-Host "Sidecar exited early. Logs:" -ForegroundColor Red
            Get-Content $sidecarLogOut -Tail 20 -ErrorAction SilentlyContinue
            Get-Content $sidecarLogErr -Tail 20 -ErrorAction SilentlyContinue
            throw "Sidecar process exited with code $($sidecarProcess.ExitCode)"
        }
        if (Test-SidecarReady -Url $SidecarUrl) {
            $ready = $true
            break
        }
        Start-Sleep -Milliseconds 500
    }

    if (-not $ready) {
        Write-Host "Sidecar health check failed. Recent logs:" -ForegroundColor Red
        Get-Content $sidecarLogOut -Tail 15 -ErrorAction SilentlyContinue
        Get-Content $sidecarLogErr -Tail 15 -ErrorAction SilentlyContinue
        $left = Get-ListenerPids -Port $SidecarPort
        throw "Sidecar did not become ready at $SidecarUrl (listeners: $($left -join ', '))"
    }

    Write-Host "Sidecar ready." -ForegroundColor Green

    Set-Location $DesktopDir
    $env:VITE_SIDECAR_URL = $SidecarUrl
    npm run tauri dev
} finally {
    Stop-Sidecar
}
