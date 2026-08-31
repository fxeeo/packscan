# PackScan START (Windows PowerShell)
# Usage:  powershell -ExecutionPolicy Bypass -File .\start.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }

# Read .env into process (simple KEY=VALUE)
Get-Content ".env" | ForEach-Object {
  $line = $_.Trim()
  if (-not $line -or $line.StartsWith("#")) { return }
  $i = $line.IndexOf("=")
  if ($i -lt 1) { return }
  $k = $line.Substring(0, $i).Trim()
  $v = $line.Substring($i + 1).Trim()
  [Environment]::SetEnvironmentVariable($k, $v, "Process")
  Set-Item -Path "Env:$k" -Value $v
}

$hostName = if ($env:PACKSCAN_API_HOST) { $env:PACKSCAN_API_HOST } else { "127.0.0.1" }
$port = if ($env:PACKSCAN_API_PORT) { $env:PACKSCAN_API_PORT } else { "8000" }
$ocr = if ($env:PACKSCAN_OCR_ENGINE) { $env:PACKSCAN_OCR_ENGINE } else { "paddle" }
$proxy = if ($env:VITE_API_PROXY_TARGET) { $env:VITE_API_PROXY_TARGET } else { "http://${hostName}:${port}" }
$uiPort = if ($env:VITE_DEV_PORT) { $env:VITE_DEV_PORT } else { "5173" }

if (-not (Test-Path "backend\.venv\Scripts\uvicorn.exe")) {
  throw "Backend venv missing. Run .\setup.ps1 first."
}
if (-not (Test-Path "frontend\node_modules")) {
  throw "frontend\node_modules missing. Run .\setup.ps1 first."
}

Write-Host "Starting API on ${hostName}:${port} (OCR=$ocr)..."
Start-Process powershell -ArgumentList @(
  "-NoExit", "-Command",
  "Set-Location '$PSScriptRoot\backend'; `$env:PACKSCAN_OCR_ENGINE='$ocr'; & .\.venv\Scripts\uvicorn.exe main:app --host $hostName --port $port --reload"
)

Start-Sleep -Seconds 4

Write-Host "Starting UI on port $uiPort (proxy $proxy)..."
Start-Process powershell -ArgumentList @(
  "-NoExit", "-Command",
  "Set-Location '$PSScriptRoot\frontend'; `$env:VITE_API_PROXY_TARGET='$proxy'; `$env:VITE_DEV_PORT='$uiPort'; npm run dev -- --host 0.0.0.0 --port $uiPort"
)

Write-Host ""
Write-Host "Open UI : http://127.0.0.1:$uiPort/"
Write-Host "API docs: http://${hostName}:${port}/docs"
Write-Host "Close the two PowerShell windows to stop."
