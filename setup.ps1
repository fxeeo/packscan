# PackScan SETUP (Windows PowerShell)
# Usage:  powershell -ExecutionPolicy Bypass -File .\setup.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "========================================"
Write-Host " PackScan SETUP"
Write-Host "========================================"

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Write-Host "Created .env from .env.example"
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { throw "Python not found in PATH. Install Python 3.10-3.12 x64." }
$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) { throw "Node.js not found in PATH. Install Node.js 20+ LTS." }

Write-Host "`n[1/4] Creating Python venv..."
Set-Location backend
if (-not (Test-Path ".venv\Scripts\python.exe")) {
  python -m venv .venv
}
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
Write-Host "[2/4] Installing backend requirements (PaddleOCR may take several minutes)..."
& .\.venv\Scripts\pip.exe install -r requirements.txt
Write-Host "[3/4] Initializing database..."
& .\.venv\Scripts\python.exe scripts\init_db.py

Set-Location ..\frontend
Write-Host "[4/4] Installing frontend packages..."
npm install
if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
}

Set-Location ..
Write-Host "`nSETUP COMPLETE. Next run: .\start.ps1  (or start.bat)"
Write-Host "UI  http://127.0.0.1:5173"
Write-Host "API http://127.0.0.1:8000/docs"
