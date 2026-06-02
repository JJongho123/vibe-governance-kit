#!/usr/bin/env python3
"""PreToolUse(Bash) hook — block dangerous shell commands.

Reads Claude Code's tool-call JSON on stdin. For tool_name == "Bash",
inspects tool_input.command against a dangerous-pattern list. Returns exit
code 2 to deny (which cannot be bypassed by ``--dangerously-skip-permissions``).

Patterns come from three layers:
  1. BUILTIN — always-on, project-agnostic catastrophes.
  2. PRESETS — opt-in groups (aws / terraform / publish) via governance.config.json.
  3. config ``dangerousCommands.extraPatterns`` — project-specific additions.

Configure via governance.config.json; you should not need to edit this file.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _config import cfg, is_enabled  # noqa: E402

# --- 1. Built-in, always-on patterns -------------------------------------
BUILTIN: list[tuple[str, str]] = [
    (r"\brm\s+-rf?\s+/(?:\s|$)", "rm -rf on / -- catastrophic"),
    (r"\brm\s+-rf?\s+\*", "rm -rf * -- deletes current directory tree"),
    (r"\brm\s+-rf?\s+~", "rm -rf on home directory"),
    (r"\bgit\s+push\s+(?:--force|-f)\b", "force push rewrites remote history"),
    (r"\bgit\s+reset\s+--hard\b", "git reset --hard discards uncommitted work"),
    (r"\bgit\s+clean\s+-[fdx]{2,}\b", "git clean -fdx removes untracked files"),
    (r":\(\)\s*\{\s*:\|:\s*&\s*\}\s*;", "fork bomb"),
    (r"\bmkfs\.\w+", "mkfs -- filesystem format"),
    (r"\bdd\s+[^|]*of=/dev/(?!null|zero)\w", "dd to block device"),
    (r"\bshutdown\b", "shutdown"),
    (r"\bhalt\b", "halt"),
    (r">\s*/dev/sd[a-z]", "redirect to raw disk device"),
    (r"\bchmod\s+-R\s+0?777\s+/", "recursive chmod 777 from root"),
]

# --- 2. Opt-in presets ---------------------------------------------------
PRESET_PATTERNS: dict[str, list[tuple[str, str]]] = {
    "publish": [
        (r"\bnpm\s+publish\b", "npm publish -- accidental package publish"),
        (r"\bpnpm\s+publish\b", "pnpm publish -- accidental package publish"),
        (r"\byarn\s+publish\b", "yarn publish -- accidental package publish"),
        (r"\bcargo\s+publish\b", "cargo publish -- accidental crate publish"),
        (r"\btwine\s+upload\b", "twine upload -- accidental PyPI publish"),
    ],
    "aws": [
        (r"\baws\s+s3\s+rm\b", "aws s3 rm -- destructive"),
        (r"\baws\s+s3\s+rb\b", "aws s3 rb -- removes bucket"),
        (r"\baws\s+dynamodb\s+delete-table\b", "DynamoDB delete-table -- data loss"),
        (r"\baws\s+ec2\s+terminate-instances\b", "EC2 terminate -- destructive"),
        (r"\baws\s+rds\s+delete-db-instance\b", "RDS delete -- data loss"),
    ],
    "terraform": [
        (r"\bterraform\s+apply\b", "terraform apply -- review plan first"),
        (r"\bterraform\s+destroy\b", "terraform destroy -- catastrophic"),
    ],
}


def build_patterns() -> list[tuple[str, str]]:
    patterns = list(BUILTIN)
    presets = cfg("dangerousCommands.presets", {}) or {}
    for name, enabled in presets.items():
        if enabled and name in PRESET_PATTERNS:
            patterns.extend(PRESET_PATTERNS[name])
    for item in cfg("dangerousCommands.extraPatterns", []) or []:
        regex = item.get("regex")
        reason = item.get("reason", "project-defined dangerous command")
        if regex:
            patterns.append((regex, reason))
    return patterns


def read_payload() -> dict:
    raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    return json.loads(raw) if raw.strip() else {}


def main() -> int:
    if not is_enabled("dangerousCommands", True):
        return 0
    try:
        payload = read_payload()
    except Exception as exc:
        print(f"[pre-tool-bash] WARN: malformed stdin ({exc}); allowing", file=sys.stderr)
        return 0

    if payload.get("tool_name") != "Bash":
        return 0

    command = (payload.get("tool_input") or {}).get("command") or ""
    for pattern, reason in build_patterns():
        try:
            if re.search(pattern, command):
                print(
                    f"[pre-tool-bash] DENY: {reason}\n"
                    f"  pattern: {pattern}\n"
                    f"  command: {command[:200]}",
                    file=sys.stderr,
                )
                return 2
        except re.error as exc:
            print(f"[pre-tool-bash] WARN: bad regex {pattern!r}: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
