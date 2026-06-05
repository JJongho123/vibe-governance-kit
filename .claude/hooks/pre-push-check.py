#!/usr/bin/env python3
"""PreToolUse(Bash) 훅 — 로컬 브랜치가 뒤처졌을 때 `git push`를 차단한다.

``git push`` 명령에 대해 원격 대상을 fetch하고 ``<remote>/<branch>``가
HEAD의 조상인지 확인한다. 로컬 브랜치가 뒤처져 있으면 종료 코드 2를 반환하여
거부한다. 강제 push나 지저분한 병합이 필요한 분기 이력을 만들어내는, 뒤처진
push를 방지한다.

설계 메모:
- 강제 push(``--force`` / ``-f``)는 여기서 건너뛴다(pre-tool-bash.py +
  settings.json deny가 처리).
- 새 브랜치의 첫 push(원격 브랜치가 아직 없음)는 fail-open(허용).
- 인식되지 않는 push 형태(Gerrit ``refs/for/`` 등)는 건너뛴다.
- 모든 실패(네트워크, git 오류, 파싱 오류)는 fail-open으로 처리하여 훅이
  세션을 영구히 막는 일이 없게 한다.

원격 이름은 ``project.remote``에서 온다(기본 ``origin``).
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
    """git push 명령에서 '<remote>/<branch>'를 반환하거나, 없으면 None."""
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
        print(f"[pre-push-check] 경고: 잘못된 stdin ({exc}); 허용함", file=sys.stderr)
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
            f"[pre-push-check] 거부: 로컬 브랜치가 {target}보다 뒤처짐"
            " -- 먼저 rebase 또는 merge 하세요\n"
            f"  제안: git fetch {remote} {branch} && git rebase {target}",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
