#!/usr/bin/env python3
"""SessionStart 훅 — 현재 저장소 상태를 Claude의 컨텍스트에 주입한다.

브랜치 / 분기 / 미커밋 파일 / 최근 커밋 / 열린 풀 리퀘스트의 간결한 요약을
stdout에 쓴다. Claude Code는 SessionStart 훅의 stdout을 세션의 추가 시스템
컨텍스트로 첨부한다.

호스트 연동 (``sessionStart.host``):
  github -> `gh pr list` 사용 (GitHub CLI)
  gitlab -> `glab mr list` 사용 (GitLab CLI)
  none   -> git 전용, PR/MR 목록 없음

외부 CLI는 사용 가능할 때만 빠듯한 타임아웃으로 호출되며, 실패나 누락된 CLI는
조용히 건너뛰어 세션 시작이 절대 막히지 않는다.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _config import cfg, is_enabled  # noqa: E402

TIMEOUT_GIT = 3
TIMEOUT_FETCH = 5
TIMEOUT_CLI = 5


def run(cmd: list[str], *, timeout: int) -> str:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return out.stdout.strip() if out.returncode == 0 else ""
    except (subprocess.SubprocessError, FileNotFoundError):
        return ""


def run_json(cmd: list[str], *, timeout: int):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if out.returncode != 0 or not out.stdout.strip():
            return None
        return json.loads(out.stdout)
    except (subprocess.SubprocessError, FileNotFoundError, json.JSONDecodeError):
        return None


def _fetch(remote: str) -> None:
    try:
        subprocess.run(["git", "fetch", remote, "--prune"], capture_output=True, text=True, timeout=TIMEOUT_FETCH)
    except (subprocess.SubprocessError, FileNotFoundError):
        pass


def _parse_date(s: str):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _days_ago(dt: datetime) -> float:
    return (datetime.now(timezone.utc) - dt).total_seconds() / 86400


def _vs_main(lines: list[str], remote: str, main_branch: str) -> None:
    ref = f"{remote}/{main_branch}"
    divergence = run(["git", "rev-list", "--left-right", "--count", f"HEAD...{ref}"], timeout=TIMEOUT_GIT)
    if not divergence:
        return
    parts = divergence.replace("\t", " ").split()
    if len(parts) != 2:
        return
    ahead, behind = parts
    lines.append(f"- {ref} 대비: +{ahead}/-{behind}")
    if behind.isdigit() and int(behind) > 0:
        print(f"[session-start] 경고: {ref}보다 {behind}개 커밋 뒤처짐 -- rebase를 고려하세요", file=sys.stderr)


def _open_prs_github(lines: list[str], stale_days: int) -> None:
    if not shutil.which("gh"):
        return
    prs = run_json(
        ["gh", "pr", "list", "--state", "open", "--limit", "20",
         "--json", "number,title,author,updatedAt,headRefName"],
        timeout=TIMEOUT_CLI,
    )
    if not isinstance(prs, list) or not prs:
        return
    lines.append(f"- 열린 PR ({len(prs)}건):")
    for pr in prs:
        if not isinstance(pr, dict):
            continue
        num = pr.get("number", "?")
        title = (pr.get("title") or "")[:60]
        author = (pr.get("author") or {}).get("login", "?")
        stale = ""
        dt = _parse_date(pr.get("updatedAt", ""))
        if dt:
            age = _days_ago(dt)
            when = f"{int(age)}일 전" if age >= 1 else f"{int(age * 24)}시간 전"
            if age > stale_days:
                stale = f" [오래됨 >{stale_days}일]"
        else:
            when = "?"
        lines.append(f"    #{num}  {author}  {when}{stale}  {title}")


def _open_mrs_gitlab(lines: list[str], stale_days: int) -> None:
    if not shutil.which("glab"):
        return
    mrs = run_json(["glab", "mr", "list", "--per-page", "20", "--output", "json"], timeout=TIMEOUT_CLI)
    if not isinstance(mrs, list) or not mrs:
        return
    lines.append(f"- 열린 MR ({len(mrs)}건):")
    for mr in mrs:
        if not isinstance(mr, dict):
            continue
        iid = mr.get("iid", "?")
        title = (mr.get("title") or "")[:60]
        author = (mr.get("author") or {}).get("username", "?")
        stale = ""
        dt = _parse_date(mr.get("updated_at", ""))
        if dt:
            age = _days_ago(dt)
            when = f"{int(age)}일 전" if age >= 1 else f"{int(age * 24)}시간 전"
            if age > stale_days:
                stale = f" [오래됨 >{stale_days}일]"
        else:
            when = "?"
        lines.append(f"    !{iid}  {author}  {when}{stale}  {title}")


def summarize() -> list[str]:
    name = cfg("project.name", "repo")
    remote = cfg("project.remote", "origin")
    main_branch = cfg("project.mainBranch", "main")
    host = cfg("sessionStart.host", "github")
    stale_days = cfg("sessionStart.staleDays", 3)

    lines = [f"[session-start] {name} 저장소 상태"]
    _fetch(remote)

    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], timeout=TIMEOUT_GIT)
    if branch:
        lines.append(f"- 브랜치: {branch}")

    divergence = run(["git", "rev-list", "--left-right", "--count", "HEAD...@{u}"], timeout=TIMEOUT_GIT)
    if divergence:
        parts = divergence.replace("\t", " ").split()
        if len(parts) == 2:
            lines.append(f"- 업스트림 대비 앞섬/뒤처짐: +{parts[0]}/-{parts[1]}")

    _vs_main(lines, remote, main_branch)

    status = run(["git", "status", "--porcelain"], timeout=TIMEOUT_GIT)
    if status:
        lines.append(f"- 미커밋 파일: {len(status.splitlines())}개")

    recent = run(["git", "log", "--oneline", "-5"], timeout=TIMEOUT_GIT)
    if recent:
        lines.append("- 최근 커밋:")
        for row in recent.splitlines():
            lines.append(f"    {row}")

    if cfg("sessionStart.showPullRequests", True):
        if host == "github":
            _open_prs_github(lines, stale_days)
        elif host == "gitlab":
            _open_mrs_gitlab(lines, stale_days)

    return lines


def main() -> int:
    if not is_enabled("sessionStart", True):
        return 0
    try:
        print("\n".join(summarize()))
    except Exception as exc:
        print(f"[session-start] 오류 무시됨: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
