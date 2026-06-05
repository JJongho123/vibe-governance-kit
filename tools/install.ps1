<#
.SYNOPSIS
  vibe-governance-kit 하네스를 대상 저장소에 설치합니다.

.DESCRIPTION
  .claude/, governance.config.json (+ 스키마), .githooks/, .github/ 템플릿,
  docs/ 거버넌스 문서를 대상 저장소로 복사합니다. -Force를 주지 않으면 기존
  파일을 덮어쓰지 않으며, .bak 사본을 보존합니다.

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
  throw "대상 경로가 존재하지 않습니다: $Target"
}
$Target = (Resolve-Path $Target).Path

# (키트 루트 기준 상대 경로, 디렉터리 여부와 무관)
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
      Write-Host "건너뜀 (이미 존재): $dst" -ForegroundColor Yellow
      return
    }
    Copy-Item $dst "$dst.bak" -Recurse -Force
    Write-Host "백업: $dst -> $dst.bak" -ForegroundColor DarkYellow
  }
  $parent = Split-Path -Parent $dst
  if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
  Copy-Item $src $dst -Recurse -Force
  Write-Host "복사: $dst" -ForegroundColor Green
}

foreach ($rel in $items) {
  $src = Join-Path $kitRoot $rel
  $dst = Join-Path $Target $rel
  if (-not (Test-Path $src)) { Write-Host "키트에 없음: $rel" -ForegroundColor Red; continue }
  Copy-Item-Safe $src $dst
}

Write-Host ""
Write-Host "완료. 다음 단계:" -ForegroundColor Cyan
Write-Host "  1. $Target\governance.config.json 수정 (project.name, mainBranch, presets, boundaries)."
Write-Host "  2. cd $Target ; git config core.hooksPath .githooks"
Write-Host "  3. 대상 저장소에서 Claude Code를 엽니다; SessionStart 훅이 연결을 확인합니다."
