# Stops all Kie AI sidecar / uvicorn processes on the dev port.
$ErrorActionPreference = "Continue"

$SidecarUrl = if ($env:VITE_SIDECAR_URL) { $env:VITE_SIDECAR_URL } else { "http://127.0.0.1:18765" }
$SidecarPort = ([System.Uri]$SidecarUrl).Port
if (-not $SidecarPort) { $SidecarPort = 18765 }

function Stop-ProcessTree {
    param([int]$ProcessId)
    if ($ProcessId -le 0) { return $false }
    if (-not (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)) { return $false }
    Write-Host "Stopping PID $ProcessId ..."
    & taskkill.exe /PID $ProcessId /T /F 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
    }
    return $true
}

function Stop-KieSidecarProcesses {
    Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue |
        Where-Object {
            $_.CommandLine -match "kie_sidecar\.main:app" -or
            $_.CommandLine -match "multiprocessing\.spawn"
        } |
        ForEach-Object { Stop-ProcessTree -ProcessId $_.ProcessId } | Out-Null
}

function Get-PortListenerPids {
    param([int]$Port)
    $processIds = @()
    try {
        $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        foreach ($conn in $connections) {
            if ($conn.OwningProcess -gt 0) { $processIds += $conn.OwningProcess }
        }
    } catch {
        $portPattern = ":$Port\s"
        $lines = netstat -ano | Select-String "LISTENING" | Select-String $portPattern
        foreach ($line in $lines) {
            $parts = ($line.ToString() -replace '\s+', ' ').Trim().Split(' ')
            $processId = [int]$parts[-1]
            if ($processId -gt 0) { $processIds += $processId }
        }
    }
    return $processIds | Select-Object -Unique
}

Write-Host "Stopping sidecar on port $SidecarPort ..." -ForegroundColor Yellow

for ($attempt = 0; $attempt -lt 8; $attempt++) {
    Stop-KieSidecarProcesses

    $listenerPids = Get-PortListenerPids -Port $SidecarPort
    foreach ($processId in $listenerPids) {
        Stop-ProcessTree -ProcessId $processId
    }

    Start-Sleep -Milliseconds 500

    $remainingListeners = Get-PortListenerPids -Port $SidecarPort
    $livePython = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue |
        Where-Object {
            $_.CommandLine -match "kie_sidecar\.main:app" -or
            $_.CommandLine -match "multiprocessing\.spawn"
        }

    if (-not $remainingListeners -and -not $livePython) { break }
}

$remainingListeners = Get-PortListenerPids -Port $SidecarPort
$livePython = @(Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue |
    Where-Object {
        $_.CommandLine -match "kie_sidecar\.main:app" -or
        $_.CommandLine -match "multiprocessing\.spawn"
    })

if ($remainingListeners -or $livePython.Count -gt 0) {
    Write-Host "Could not fully stop sidecar." -ForegroundColor Red
    if ($livePython.Count -gt 0) {
        Write-Host "Remaining python workers:" -ForegroundColor Yellow
        foreach ($proc in $livePython) {
            Write-Host "  taskkill /PID $($proc.ProcessId) /T /F"
        }
    }
    if ($remainingListeners) {
        Write-Host "Port $SidecarPort still has listeners: $($remainingListeners -join ', ')" -ForegroundColor Yellow
    }
    exit 1
}

Write-Host "Port $SidecarPort is free." -ForegroundColor Green
exit 0
