param(
    [string]$PythonCommand = "python",
    [switch]$PersistLocalRoot,
    [switch]$SkipDependencyInstall
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$KnowledgeLocal = Join-Path $Root "knowledge\local"

function Invoke-Native {
    param(
        [string]$Description,
        [scriptblock]$Command
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE."
    }
}

Write-Host "=== Codex R&D Platform Setup ==="
Write-Host "Root: $Root"

Set-Location $Root

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git is not installed or not in PATH."
}
Invoke-Native "Git availability check" { git --version }

$isGitRepository = & git rev-parse --is-inside-work-tree
if ($LASTEXITCODE -ne 0 -or $isGitRepository.Trim() -ne "true") {
    throw "The setup directory must be an existing Git work tree."
}
& git status --porcelain | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Git status check failed with exit code $LASTEXITCODE."
}

$gitUserName = & git config --get user.name
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($gitUserName)) {
    throw "Git user.name must be configured before setup."
}
$gitUserEmail = & git config --get user.email
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($gitUserEmail)) {
    throw "Git user.email must be configured before setup."
}

if (-not (Get-Command $PythonCommand -ErrorAction SilentlyContinue)) {
    throw "Python is not installed or '$PythonCommand' is not in PATH."
}
& $PythonCommand -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
if ($LASTEXITCODE -ne 0) {
    throw "Python version must be 3.11 or newer."
}

if (-not (Test-Path -LiteralPath $VenvPython)) {
    Invoke-Native "Python virtual environment creation" { & $PythonCommand -m venv .venv }
}
if (-not (Test-Path -LiteralPath $VenvPython)) {
    throw "Python virtual environment executable was not created."
}

if (-not $SkipDependencyInstall) {
    Invoke-Native "Constrained dependency installation" {
        & $VenvPython -m pip install -r "tools\mcp\company-context\requirements.txt"
    }
}
Invoke-Native "Dependency consistency check" { & $VenvPython -m pip check }

New-Item -ItemType Directory -Path $KnowledgeLocal -Force | Out-Null
if (-not (Test-Path -LiteralPath $KnowledgeLocal -PathType Container)) {
    throw "Local knowledge directory was not created."
}

if (-not $env:COMPANY_LOCAL_ROOTS) {
    $env:COMPANY_LOCAL_ROOTS = $KnowledgeLocal
}
if ($PersistLocalRoot) {
    [Environment]::SetEnvironmentVariable("COMPANY_LOCAL_ROOTS", $env:COMPANY_LOCAL_ROOTS, "User")
    Write-Host "Persisted COMPANY_LOCAL_ROOTS for the current user."
}

Invoke-Native "Platform validation" { & $VenvPython "scripts\validate_platform.py" }

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
