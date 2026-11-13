# One-time setup for Jarvis on Windows.
# Run from the Jarvis folder:   powershell -ExecutionPolicy Bypass -File setup.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "Setting up Jarvis..." -ForegroundColor Cyan

# 1. Python 3.11+
$py = $null
foreach ($cmd in @("py -3.12", "py -3.11", "py -3.13", "python")) {
    try {
        $v = & ([scriptblock]::Create("$cmd -c `"import sys; print(sys.version_info >= (3, 11))`"")) 2>$null
        if ($v -eq "True") { $py = $cmd; break }
    } catch {}
}
if (-not $py) {
    Write-Host "Installing Python 3.12..." -ForegroundColor Yellow
    winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
    $py = "py -3.12"
}
Write-Host "Using Python: $py"

# 2. Virtual environment + packages
if (-not (Test-Path ".venv")) {
    & ([scriptblock]::Create("$py -m venv .venv"))
}
& .\.venv\Scripts\python.exe -m pip install --upgrade pip --quiet
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 3. Claude Code (the brain)
if (-not (Get-Command claude -ErrorAction SilentlyContinue) -and -not (Test-Path "$HOME\.local\bin\claude.exe")) {
    Write-Host "Installing Claude Code..." -ForegroundColor Yellow
    irm https://claude.ai/install.ps1 | iex
    Write-Host "Now run 'claude' once in a new terminal to log in, then start Jarvis." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Done. Start Jarvis by double-clicking jarvis.bat" -ForegroundColor Green
Write-Host "(Test your claps first with:  jarvis.bat --calibrate)"
