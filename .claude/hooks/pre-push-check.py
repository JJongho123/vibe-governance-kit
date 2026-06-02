#!/usr/bin/env python3
"""PreToolUse(Bash) hook — block `git push` when the local branch is behind.

For ``git push`` commands, fetches the remote target and checks whether
``<remote>/<branch>`` is an ancestor of HEAD. If the local branch is behind,
returns exit code 2 to deny. Prevents a stale push that would create a
diverged history requiring a force-push or messy merge.

Design notes:
- Force pushes (``--force`` / ``-f``) are skipped here (handled by
  pre-tool-bash.py + settings.json deny).
- New-branch first push (remote branch does not yet exist) is fail-open.
- Unrecognized push shapes (Gerrit ``refs/for/`` etc.) are skipped.
- All failures (network, git errors, parse errors) are fail-open so the
  hook can never permanently wedge a session.

Remote name comes from ``project.remote`` (default ``origin``).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _config import cfg, is_enabled  # noqa: E402

TIMEOUT_GIT = 3
TIMEOUT_FETCH = 5


def read_payload() -> dict:
    raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    return json.loads(raw) if raw.strip() else {}


def _run(cmd: list[str], *, timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _extract_target(command: str, remote: str) -> str | None:
    """Return '<remote>/<branch>' from a git push command, or None."""
    if re.search(r"\bgit\s+push\s+(?:--force|-f)\b", command):
        return None
    if "refs/for/" in command:
        return None

    safe = re.escape(remote)
    m = re.search(
        rf"\bgit\s+push(?:\s+(?:-u|--set-upstream))?\s+{safe}\s+([^\s:^~]+)$",
        command,
    )
    if m:
        return f"{remote}/{m.group(1)}"

    if re.search(r"\bgit\s+push\s*$", command):
        try:
            result = _run(["git", "rev-parse", "--abbrev-ref", "@{u}"], timeout=TIMEOUT_GIT)
            if result.returncode == 0 and result.stdout.strip():
                upstream = result.stdout.strip()
                if upstream.startswith(f"{remote}/"):
                    return upstream
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        return None

    return None


def _is_behind(target_ref: str, remote: str) -> bool | None:
    prefix = f"{remote}/"
    if not target_ref.startswith(prefix):
        return None
    branch = target_ref[len(prefix):]

    try:
        _run(["git", "fetch", remote, branch], timeout=TIMEOUT_FETCH)
    except (subprocess.SubprocessError, FileNotFoundError):
        return None

    try:
        result = _run(["git", "merge-base", "--is-ancestor", target_ref, "HEAD"], timeout=TIMEOUT_GIT)
        if result.returncode == 0:
            return False
        if result.returncode == 1:
            return True
        return None
    except (subprocess.SubprocessError, FileNotFoundError):
        return None


def main() -> int:
    if not is_enabled("prePush", True):
        return 0
    try:
        payload = read_payload()
    except Exception as exc:
        print(f"[pre-push-check] WARN: malformed stdin ({exc}); allowing", file=sys.stderr)
        return 0

    if payload.get("tool_name") != "Bash":
        return 0

    command = (payload.get("tool_input") or {}).get("command") or ""
    if not re.search(r"\bgit\s+push\b", command):
        return 0

    remote = cfg("project.remote", "origin")
    target = _extract_target(command, remote)
    if target is None:
        return 0

    behind = _is_behind(target, remote)
    if behind is None:
        return 0

    if behind:
        branch = target[len(remote) + 1:]
        print(
            f"[pre-push-check] DENY: local branch is behind {target}"
            " -- rebase or merge first\n"
            f"  suggestion: git fetch {remote} {branch} && git rebase {target}",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
