#requires -Version 5.1
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$PythonExe = Join-Path $RepoRoot '.venv\Scripts\python.exe'
$BackendDir = Join-Path $RepoRoot 'backend'
$RuntimeDir = Join-Path $RepoRoot '.runtime'
$PidFile = Join-Path $RuntimeDir 'app.pid'

& $PythonExe (Join-Path $PSScriptRoot 'setup_local.py')
if ($LASTEXITCODE -ne 0) { throw 'Local database setup or migration failed.' }

# A virtualenv launcher PID may differ from the actual listening Python PID.
$Listener = Get-NetTCPConnection -State Listen -LocalPort 20081 -ErrorAction SilentlyContinue | Select-Object -First 1
$PortOwner = if ($Listener) { $Listener.OwningProcess } else { $null }
if ($PortOwner) {
    $Existing = Get-CimInstance Win32_Process -Filter "ProcessId=$PortOwner"
    if ($Existing.CommandLine -like "*$BackendDir*" -and $Existing.CommandLine -match '-m\s+uvicorn\s+app\.main:app') {
        $PortOwner | Set-Content -LiteralPath $PidFile -Encoding ASCII
        Write-Host 'Campus application already running: http://127.0.0.1:20081/ (restart after code changes).'
        exit 0
    }
    throw "Port 20081 is already used by PID $PortOwner. No process was stopped."
}

$AppProcess = Start-Process -FilePath $PythonExe -WorkingDirectory $BackendDir `
    -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--app-dir', "`"$BackendDir`"", '--host', '127.0.0.1', '--port', '20081') `
    -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $RuntimeDir 'app.log') `
    -RedirectStandardError (Join-Path $RuntimeDir 'app.err')
for ($Attempt = 0; $Attempt -lt 40; $Attempt++) {
    $Listener = Get-NetTCPConnection -State Listen -LocalPort 20081 -ErrorAction SilentlyContinue | Select-Object -First 1
    try {
        $ListeningProcess = if ($Listener) { Get-CimInstance Win32_Process -Filter "ProcessId=$($Listener.OwningProcess)" } else { $null }
        if ($ListeningProcess.CommandLine -like "*$BackendDir*" -and $ListeningProcess.CommandLine -match '-m\s+uvicorn\s+app\.main:app') {
            $Response = Invoke-RestMethod 'http://127.0.0.1:20081/api/v1/ready' -TimeoutSec 2
        } else { $Response = $null }
        if ($Response -and $Response.status -eq 'ok') {
            $Listener.OwningProcess | Set-Content -LiteralPath $PidFile -Encoding ASCII
            Write-Host 'Campus application ready: http://127.0.0.1:20081/'
            Write-Host 'Login details: .runtime/admin.json (local file, ignored by Git).'
            exit 0
        }
    } catch { }
    if ($AppProcess.HasExited) { throw 'Application exited; inspect .runtime/app.err.' }
    Start-Sleep -Milliseconds 500
}
throw 'Application readiness check timed out; inspect .runtime/app.err.'
