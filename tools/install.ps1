<#
.SYNOPSIS
  Install the vibe-governance-kit harness into a target repository.

.DESCRIPTION
  Copies .claude/, governance.config.json (+ schema), .githooks/, .github/
  templates and docs/ governance docs into the target repo. Existing files
  are NOT overwritten unless -Force is given; a .bak copy is kept.

.EXAMPLE
  ./tools/install.ps1 -Target C:\workspace\project\my-app
  ./tools/install.ps1 -Target ..\my-app -Force
#>
param(
  [Parameter(Mandatory = $true)][string]$Target,
  [switch]$Force
)

$ErrorActionPreference = "Stop"
$kitRoot = Split-Path -Parent $PSScriptRoot

if (-not (Test-Path $Target)) {
  throw "Target path does not exist: $Target"
}
$Target = (Resolve-Path $Target).Path

# (source relative to kit root, whether it's a directory)
$items = @(
  ".claude/hooks",
  ".claude/commands",
  ".claude/agents",
  ".claude/settings.json",
  ".claude/settings.local.json.example",
  "governance.config.json",
  "governance.config.schema.json",
  ".githooks/pre-push",
  ".github/pull_request_template.md",
  "docs/governance.md",
  "docs/injection-defense.md",
  "docs/secret-policy.md",
  "CLAUDE.md"
)

function Copy-Item-Safe($src, $dst) {
  if (Test-Path $dst) {
    if (-not $Force) {
      Write-Host "SKIP (exists): $dst" -ForegroundColor Yellow
      return
    }
    Copy-Item $dst "$dst.bak" -Recurse -Force
    Write-Host "BACKUP: $dst -> $dst.bak" -ForegroundColor DarkYellow
  }
  $parent = Split-Path -Parent $dst
  if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
  Copy-Item $src $dst -Recurse -Force
  Write-Host "COPY: $dst" -ForegroundColor Green
}

foreach ($rel in $items) {
  $src = Join-Path $kitRoot $rel
  $dst = Join-Path $Target $rel
  if (-not (Test-Path $src)) { Write-Host "MISSING in kit: $rel" -ForegroundColor Red; continue }
  Copy-Item-Safe $src $dst
}

Write-Host ""
Write-Host "Done. Next steps:" -ForegroundColor Cyan
Write-Host "  1. Edit $Target\governance.config.json (project.name, mainBranch, presets, boundaries)."
Write-Host "  2. cd $Target ; git config core.hooksPath .githooks"
Write-Host "  3. Open Claude Code in the target repo; SessionStart hook confirms wiring."
