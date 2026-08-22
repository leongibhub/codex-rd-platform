param(
    [string]$PythonCommand = "python"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host "=== Codex R&D Platform Setup ==="
Write-Host "Root: $Root"

Set-Location $Root

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git is not installed or not in PATH."
}

if (-not (Get-Command $PythonCommand -ErrorAction SilentlyContinue)) {
    throw "Python is not installed or '$PythonCommand' is not in PATH."
}

if (-not (Test-Path ".git")) {
    git init
    Write-Host "Initialized Git repository."
}

if (-not (Test-Path ".venv")) {
    & $PythonCommand -m venv .venv
}

& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r "tools\mcp\company-context\requirements.txt"

# Default local knowledge root for this repository.
if (-not $env:COMPANY_LOCAL_ROOTS) {
    $env:COMPANY_LOCAL_ROOTS = Join-Path $Root "knowledge\local"
    [Environment]::SetEnvironmentVariable("COMPANY_LOCAL_ROOTS", $env:COMPANY_LOCAL_ROOTS, "User")
    Write-Host "Set user COMPANY_LOCAL_ROOTS=$env:COMPANY_LOCAL_ROOTS"
}

& ".\.venv\Scripts\python.exe" "scripts\validate_platform.py"

if (-not (Test-Path ".gitignore")) {
@"
.venv/
.env
**/.env
__pycache__/
*.pyc
.codex/tmp/
"@ | Set-Content -Encoding UTF8 ".gitignore"
}

Write-Host ""
Write-Host "Setup complete."
Write-Host "Next:"
Write-Host "1) Configure Redmine/RAGFlow/GitLab environment variables if needed."
Write-Host "2) Start Codex from this repo."
Write-Host "3) Ask: 'Read AGENTS.md, inspect available agents/skills/MCP, and run platform self-check.'"
