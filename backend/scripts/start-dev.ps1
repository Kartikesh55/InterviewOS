param(
    [switch]$StopExisting,
    [ValidateRange(1, 65535)]
    [int]$Port = 8000
)

$ErrorActionPreference = 'Stop'
$backendRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = Join-Path $backendRoot '.venv\Scripts\python.exe'
$venvRoot = [System.IO.Path]::GetFullPath((Join-Path $backendRoot '.venv'))

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Backend virtual environment not found at '$python'. Create it and install requirements first."
}

function Test-PathWithinDirectory {
    param(
        [string]$Path,
        [string]$Directory
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return $false
    }

    try {
        $fullPath = [System.IO.Path]::GetFullPath($Path)
        $fullDirectory = [System.IO.Path]::GetFullPath($Directory).TrimEnd('\') + '\'
        return $fullPath.StartsWith($fullDirectory, [System.StringComparison]::OrdinalIgnoreCase)
    } catch {
        return $false
    }
}

function Test-InterviewOSUvicornProcess {
    param(
        $Process,
        [string]$ExpectedVenv,
        [int]$ExpectedPort
    )

    if (-not $Process -or [string]::IsNullOrWhiteSpace($Process.CommandLine)) {
        return $false
    }

    $commandLine = $Process.CommandLine
    $hasAppTarget = $commandLine -match '(?i)(?:-m\s+uvicorn|uvicorn(?:\.exe)?)\s+app\.main:app(?:\s|$)'
    $hasPort = $commandLine -match "(?i)--port(?:\s+|=)$ExpectedPort(?:\s|$)"
    $usesProjectVenv = (Test-PathWithinDirectory -Path $Process.ExecutablePath -Directory $ExpectedVenv) -or
        ($commandLine.IndexOf($ExpectedVenv, [System.StringComparison]::OrdinalIgnoreCase) -ge 0)

    return $hasAppTarget -and $hasPort -and $usesProjectVenv
}

function Test-InterviewOSHealthEndpoint {
    param([int]$ExpectedPort)

    try {
        $health = Invoke-RestMethod `
            -Uri "http://127.0.0.1:$ExpectedPort/api/health" `
            -TimeoutSec 2
        return $health.status -eq 'UP' -and
            $health.service -eq 'InterviewOS Backend'
    } catch {
        return $false
    }
}

$listeners = @(
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
)

if ($listeners.Count -gt 0) {
    $processes = @(Get-CimInstance Win32_Process -ErrorAction Stop)
    $processById = @{}
    foreach ($process in $processes) {
        $processById[[int]$process.ProcessId] = $process
    }

    $confirmedRoots = @{}
    $confirmedOrphanWorkers = @{}
    $unconfirmedListeners = @()
    $confirmedListenerProcesses = @{}

    foreach ($listenerId in $listeners) {
        $listenerProcess = $processById[[int]$listenerId]
        if (-not $listenerProcess) {
            $orphanCandidates = @(
                $processes | Where-Object {
                    ([int]$_.ParentProcessId -eq [int]$listenerId) -and
                    ($_.Name -match '(?i)^python(?:\d+(?:\.\d+)*)?\.exe$') -and
                    ($_.CommandLine -match "(?i)spawn_main\(parent_pid=$([int]$listenerId),")
                }
            )
            if (
                $orphanCandidates.Count -eq 1 -and
                (Test-InterviewOSHealthEndpoint -ExpectedPort $Port)
            ) {
                $orphanId = [int]$orphanCandidates[0].ProcessId
                $confirmedOrphanWorkers[$orphanId] = $orphanCandidates[0]
                $confirmedListenerProcesses[$orphanId] = $orphanCandidates[0]
                continue
            }
            $unconfirmedListeners += [int]$listenerId
            continue
        }

        $current = $listenerProcess
        $visited = @{}
        $root = $null
        while ($current -and -not $visited.ContainsKey([int]$current.ProcessId)) {
            $currentId = [int]$current.ProcessId
            $visited[$currentId] = $true
            if (Test-InterviewOSUvicornProcess `
                -Process $current `
                -ExpectedVenv $venvRoot `
                -ExpectedPort $Port) {
                $root = $current
                break
            }

            $current = $processById[[int]$current.ParentProcessId]
        }

        if (-not $root) {
            $unconfirmedListeners += [int]$listenerId
            continue
        }

        if ($listenerProcess.ProcessId -ne $root.ProcessId) {
            $isDirectUvicornWorker =
                ([int]$listenerProcess.ParentProcessId -eq [int]$root.ProcessId) -and
                ($listenerProcess.Name -match '(?i)^python(?:\d+(?:\.\d+)*)?\.exe$') -and
                ($listenerProcess.CommandLine -match "(?i)spawn_main\(parent_pid=$([int]$root.ProcessId),")
            if (-not $isDirectUvicornWorker) {
                $unconfirmedListeners += [int]$listenerId
                continue
            }
        }

        $confirmedRoots[[int]$root.ProcessId] = $root
        $confirmedListenerProcesses[[int]$listenerProcess.ProcessId] = $listenerProcess
    }

    if ($unconfirmedListeners.Count -gt 0) {
        $ids = ($unconfirmedListeners | Sort-Object -Unique) -join ', '
        throw "Port $Port is occupied by process ID(s) $ids that cannot be confirmed as this InterviewOS backend. Nothing was stopped. Inspect the owning process and stop it manually only after confirming its identity."
    }

    if (-not $StopExisting) {
        $ids = @($confirmedRoots.Keys) + @($confirmedOrphanWorkers.Keys)
        $ids = ($ids | Sort-Object -Unique) -join ', '
        throw "Confirmed InterviewOS backend process(es) $ids already use port $Port. Re-run with -StopExisting to stop only confirmed project Uvicorn processes."
    }

    $stopIds = @($confirmedListenerProcesses.Keys | Sort-Object -Descending)
    foreach ($rootId in $confirmedRoots.Keys) {
        if ($stopIds -notcontains [int]$rootId) {
            $stopIds += [int]$rootId
        }
    }

    foreach ($processId in $stopIds) {
        if (Get-Process -Id $processId -ErrorAction SilentlyContinue) {
            Write-Host "Stopping confirmed InterviewOS backend process $processId."
            Stop-Process -Id $processId -ErrorAction Stop
        }
    }

    $deadline = (Get-Date).AddSeconds(10)
    do {
        Start-Sleep -Milliseconds 250
        $remainingListeners = @(
            Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        )
    } while ($remainingListeners.Count -gt 0 -and (Get-Date) -lt $deadline)

    if ($remainingListeners.Count -gt 0) {
        $ids = ($remainingListeners | Select-Object -ExpandProperty OwningProcess -Unique) -join ', '
        throw "Port $Port is still occupied by process ID(s) $ids after stopping the confirmed InterviewOS process(es). Nothing else was stopped."
    }
}

$env:INTERVIEWOS_LOG_LEVEL = 'DEBUG'
Set-Location -LiteralPath $backendRoot

Write-Host "Starting InterviewOS on http://127.0.0.1:$Port (application DEBUG logs and HTTP access logs enabled)."
Write-Host 'This server runs in the foreground. Press Ctrl+C to stop it.'

& $python -m uvicorn app.main:app `
    --host 127.0.0.1 `
    --port $Port `
    --log-level debug `
    --access-log

exit $LASTEXITCODE
