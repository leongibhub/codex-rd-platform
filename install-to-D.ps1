param(
    [string]$Destination = "D:\codex-rd-platform",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$Source = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not (Test-Path "D:\")) {
    throw "D: drive is not available."
}

if (Test-Path $Destination) {
    $existing = Get-ChildItem -Force $Destination -ErrorAction SilentlyContinue
    if ($existing -and -not $Force) {
        throw "Destination '$Destination' already exists and is not empty. Re-run with -Force only if you intend to merge/overwrite files."
    }
} else {
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
}

Write-Host "Copying platform to $Destination ..."
Get-ChildItem -Force $Source | Where-Object {
    $_.Name -notin @("install-to-D.ps1")
} | ForEach-Object {
    Copy-Item $_.FullName -Destination $Destination -Recurse -Force
}

Copy-Item $MyInvocation.MyCommand.Path -Destination (Join-Path $Destination "install-to-D.ps1") -Force

Write-Host "Running platform setup..."
& (Join-Path $Destination "scripts\setup.ps1")

Write-Host ""
Write-Host "Installed at: $Destination"
Write-Host "Open this folder in Codex / ChatGPT desktop Codex workspace."
