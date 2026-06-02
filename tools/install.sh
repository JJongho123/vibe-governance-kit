#!/usr/bin/env bash
# Install the vibe-governance-kit harness into a target repository.
#
# Usage:
#   ./tools/install.sh /path/to/target-repo          # skips existing files
#   ./tools/install.sh /path/to/target-repo --force   # overwrites, keeps .bak
set -euo pipefail

TARGET="${1:-}"
FORCE="${2:-}"
if [[ -z "$TARGET" ]]; then
  echo "usage: $0 <target-repo> [--force]" >&2
  exit 1
fi
[[ -d "$TARGET" ]] || { echo "target does not exist: $TARGET" >&2; exit 1; }

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
  [[ -e "$src" ]] || { echo "MISSING in kit: $rel"; continue; }
  if [[ -e "$dst" && "$FORCE" != "--force" ]]; then
    echo "SKIP (exists): $rel"
    continue
  fi
  if [[ -e "$dst" && "$FORCE" == "--force" ]]; then
    cp -r "$dst" "$dst.bak"
    echo "BACKUP: $rel -> $rel.bak"
  fi
  mkdir -p "$(dirname "$dst")"
  cp -r "$src" "$dst"
  echo "COPY: $rel"
done

cat <<EOF

Done. Next steps:
  1. Edit $TARGET/governance.config.json (project.name, mainBranch, presets, boundaries).
  2. cd $TARGET && git config core.hooksPath .githooks
  3. Open Claude Code in the target repo; SessionStart hook confirms wiring.
EOF
