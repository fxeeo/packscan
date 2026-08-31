# Create a clean portable ZIP of PackScan (excludes venv, node_modules, DB, uploads).
# Usage:  powershell -ExecutionPolicy Bypass -File .\create-portable-zip.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$stamp = Get-Date -Format "yyyyMMdd-HHmm"
$outZip = Join-Path (Split-Path $PSScriptRoot -Parent) "PackScan-portable-$stamp.zip"
$stage = Join-Path $env:TEMP "packscan-portable-stage-$stamp"

if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
New-Item -ItemType Directory -Path $stage | Out-Null
$dest = Join-Path $stage "packscan"
New-Item -ItemType Directory -Path $dest | Out-Null

$excludeDirs = @(
  "\.venv\\",
  "\\node_modules\\",
  "\\dist\\",
  "\\__pycache__\\",
  "\\.git\\",
  "\\uploads\\",
  "\\reports\\"
)

Write-Host "Copying project files..."
Get-ChildItem -Path $PSScriptRoot -Recurse -Force | Where-Object {
  $p = $_.FullName.Substring($PSScriptRoot.Length)
  foreach ($ex in $excludeDirs) {
    if ($p -match $ex) { return $false }
  }
  if ($_.Name -match '\.db$') { return $false }
  if ($_.Name -eq ".env") { return $false }
  return $true
} | ForEach-Object {
  $rel = $_.FullName.Substring($PSScriptRoot.Length).TrimStart("\")
  $target = Join-Path $dest $rel
  if ($_.PSIsContainer) {
    New-Item -ItemType Directory -Path $target -Force | Out-Null
  } else {
    $parent = Split-Path $target -Parent
    if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    Copy-Item $_.FullName $target -Force
  }
}

# Ensure empty runtime folders exist in ZIP
New-Item -ItemType Directory -Path (Join-Path $dest "backend\uploads") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $dest "backend\reports") -Force | Out-Null
"" | Set-Content (Join-Path $dest "backend\uploads\.gitkeep")
"" | Set-Content (Join-Path $dest "backend\reports\.gitkeep")

if (Test-Path $outZip) { Remove-Item $outZip -Force }
Compress-Archive -Path $dest -DestinationPath $outZip -Force
Remove-Item $stage -Recurse -Force

Write-Host ""
Write-Host "Portable ZIP created:"
Write-Host "  $outZip"
Write-Host "Share this file. Recipient: Extract → setup.bat → start.bat"
