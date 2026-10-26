#requires -Version 5.1
[CmdletBinding()]
param([switch]$Database)
$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$BackendDir = Join-Path $RepoRoot 'backend'
$PidFile = Join-Path $RepoRoot '.runtime\app.pid'
if (Test-Path -LiteralPath $PidFile) {
    $RecordedPid = [int](Get-Content -LiteralPath $PidFile)
    $AppProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$RecordedPid"
    if ($AppProcess) {
        if ($AppProcess.CommandLine -notlike "*$BackendDir*" -or $AppProcess.CommandLine -notmatch '-m\s+uvicorn\s+app\.main:app') {
            throw 'Recorded PID belongs to another process; refusing to stop it.'
        }
        Stop-Process -Id $RecordedPid
        Write-Host "Stopped campus application PID $RecordedPid."
    }
    Remove-Item -LiteralPath $PidFile
}
if ($Database) {
    & (Join-Path $RepoRoot '.venv\Scripts\python.exe') (Join-Path $PSScriptRoot 'setup_local.py') --stop-db
    if ($LASTEXITCODE -ne 0) { throw 'Database shutdown failed.' }
}
