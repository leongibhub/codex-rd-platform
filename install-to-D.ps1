param(
    [string]$Destination = "D:\codex-rd-platform",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$SourcePath = [System.IO.Path]::GetFullPath($PSScriptRoot)
$DestinationFull = [System.IO.Path]::GetFullPath($Destination)
$CreatedDestination = $false

function Test-IsSameOrDescendantPath {
    param(
        [string]$Parent,
        [string]$Candidate
    )

    $comparison = [System.StringComparison]::OrdinalIgnoreCase
    if ([string]::Equals($Parent, $Candidate, $comparison)) {
        return $true
    }
    return $Candidate.StartsWith($Parent.TrimEnd("\") + "\", $comparison)
}

function Assert-NoReparsePoint {
    param(
        [string]$Path,
        [string]$Label
    )

    $current = [System.IO.Path]::GetFullPath($Path)
    while ($true) {
        if (Test-Path -LiteralPath $current) {
            $item = Get-Item -LiteralPath $current -Force
            if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "$Label path '$Path' contains a reparse point at '$current'."
            }
        }
        $parent = [System.IO.Directory]::GetParent($current)
        if ($null -eq $parent) {
            return
        }
        $current = $parent.FullName
    }
}

function Write-FailureMarker {
    if ($CreatedDestination) {
        Set-Content -LiteralPath (Join-Path $DestinationFull ".install-failed") -Encoding UTF8 -NoNewline `
            -Value "Installation did not complete. Inspect the installer error and remove this newly-created directory before retrying."
    }
}

if ($Force) {
    throw "-Force is not supported: this installer never merges with or overwrites an existing delivery."
}
Assert-NoReparsePoint -Path $SourcePath -Label "Source"
$Source = (Resolve-Path -LiteralPath $SourcePath).Path
if (Test-IsSameOrDescendantPath -Parent $Source -Candidate $DestinationFull) {
    throw "Destination '$DestinationFull' must not be the source directory or a child of the source directory."
}
Assert-NoReparsePoint -Path $DestinationFull -Label "Destination"

if (Test-Path -LiteralPath $DestinationFull) {
    $destinationItem = Get-Item -LiteralPath $DestinationFull -Force
    if (-not $destinationItem.PSIsContainer) {
        throw "Destination '$DestinationFull' must be a directory."
    }
    if (@(Get-ChildItem -LiteralPath $DestinationFull -Force -ErrorAction Stop).Count -ne 0) {
        throw "Destination '$DestinationFull' already exists and is not empty; it will not be overwritten."
    }
} else {
    New-Item -ItemType Directory -Path $DestinationFull -ErrorAction Stop | Out-Null
    $CreatedDestination = $true
}

try {
    $Commit = (& git -C $Source rev-parse --verify "HEAD^{commit}").Trim()
    if ($LASTEXITCODE -ne 0) {
        throw "Source '$Source' must provide a committed Git HEAD."
    }

    $blockedPaths = @(
        & git -C $Source ls-tree -r --name-only $Commit |
            Where-Object { $_ -match '(^|/)(\.git|\.venv|\.rd-platform|\.env|\.worktrees|\.pytest_cache|__pycache__|knowledge/local|cache)(/|$)' }
    )
    if ($LASTEXITCODE -ne 0) {
        throw "Could not inspect committed source paths."
    }
    if ($blockedPaths.Count -ne 0) {
        throw "Committed source contains delivery-blocked sensitive/local path(s): $($blockedPaths -join ', ')."
    }

    Write-Host "Creating isolated committed-source delivery at $DestinationFull ..."
    & git init --quiet -- $DestinationFull
    if ($LASTEXITCODE -ne 0) {
        throw "Clean delivery repository initialization failed with exit code $LASTEXITCODE."
    }
    & git -C $DestinationFull fetch --depth 1 --no-tags -- $Source $Commit
    if ($LASTEXITCODE -ne 0) {
        throw "Pinned committed-source fetch failed with exit code $LASTEXITCODE."
    }
    & git -C $DestinationFull checkout --detach --quiet $Commit
    if ($LASTEXITCODE -ne 0) {
        throw "Pinned committed-source checkout failed with exit code $LASTEXITCODE."
    }

    Write-Host "Running platform setup..."
    & (Join-Path $DestinationFull "scripts\setup.ps1")
    if ($LASTEXITCODE -ne 0) {
        throw "Platform setup failed with exit code $LASTEXITCODE."
    }
}
catch {
    Write-FailureMarker
    throw
}

Write-Host ""
Write-Host "Installed at: $DestinationFull"
Write-Host "Open this folder in Codex / ChatGPT desktop Codex workspace."
