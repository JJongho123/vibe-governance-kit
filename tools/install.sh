#!/usr/bin/env bash
# vibe-governance-kit 하네스를 대상 저장소에 설치합니다.
#
# 사용법:
#   ./tools/install.sh /path/to/target-repo          # 기존 파일은 건너뜀
#   ./tools/install.sh /path/to/target-repo --force   # 덮어쓰며 .bak 보존
set -euo pipefail

TARGET="${1:-}"
FORCE="${2:-}"
if [[ -z "$TARGET" ]]; then
  echo "사용법: $0 <대상-저장소> [--force]" >&2
  exit 1
fi
[[ -d "$TARGET" ]] || { echo "대상이 존재하지 않습니다: $TARGET" >&2; exit 1; }

KIT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="$(cd "$TARGET" && pwd)"

ITEMS=(
  ".claude/hooks"
  ".claude/commands"
  ".claude/agents"
  ".claude/settings.json"
  ".claude/settings.local.json.example"
  "governance.config.json"
  "governance.config.schema.json"
  ".githooks/pre-push"
  ".github/pull_request_template.md"
  "docs/governance.md"
  "docs/injection-defense.md"
  "docs/secret-policy.md"
  "CLAUDE.md"
)

for rel in "${ITEMS[@]}"; do
  src="$KIT_ROOT/$rel"
  dst="$TARGET/$rel"
  [[ -e "$src" ]] || { echo "키트에 없음: $rel"; continue; }
  if [[ -e "$dst" && "$FORCE" != "--force" ]]; then
    echo "건너뜀 (이미 존재): $rel"
    continue
  fi
  if [[ -e "$dst" && "$FORCE" == "--force" ]]; then
    cp -r "$dst" "$dst.bak"
    echo "백업: $rel -> $rel.bak"
  fi
  mkdir -p "$(dirname "$dst")"
  cp -r "$src" "$dst"
  echo "복사: $rel"
done

cat <<EOF

완료. 다음 단계:
  1. $TARGET/governance.config.json 수정 (project.name, mainBranch, presets, boundaries).
  2. cd $TARGET && git config core.hooksPath .githooks
  3. 대상 저장소에서 Claude Code를 엽니다; SessionStart 훅이 연결을 확인합니다.
EOF
