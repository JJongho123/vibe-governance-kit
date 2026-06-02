#!/usr/bin/env python3
"""SessionStart hook — inject current repo state into Claude's context.

Writes a compact summary of branch / divergence / uncommitted files / recent
commits / open pull requests to stdout. Claude Code attaches stdout from
SessionStart hooks as additional system context for the session.

Host integration (``sessionStart.host``):
  github -> uses `gh pr list` (GitHub CLI)
  gitlab -> uses `glab mr list` (GitLab CLI)
  none   -> git-only, no PR/MR listing

External CLIs are invoked only if available with tight timeouts; failures and
missing CLIs are silently skipped so session start is never blocked.
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
    lines.append(f"- vs {ref}: +{ahead}/-{behind}")
    if behind.isdigit() and int(behind) > 0:
        print(f"[session-start] WARN: behind {ref} by {behind} commits -- consider rebasing", file=sys.stderr)


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
    lines.append(f"- open PRs ({len(prs)}):")
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
            when = f"{int(age)}d ago" if age >= 1 else f"{int(age * 24)}h ago"
            if age > stale_days:
                stale = f" [STALE >{stale_days}d]"
        else:
            when = "?"
        lines.append(f"    #{num}  {author}  {when}{stale}  {title}")


def _open_mrs_gitlab(lines: list[str], stale_days: int) -> None:
    if not shutil.which("glab"):
        return
    mrs = run_json(["glab", "mr", "list", "--per-page", "20", "--output", "json"], timeout=TIMEOUT_CLI)
    if not isinstance(mrs, list) or not mrs:
        return
    lines.append(f"- open MRs ({len(mrs)}):")
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
            when = f"{int(age)}d ago" if age >= 1 else f"{int(age * 24)}h ago"
            if age > stale_days:
                stale = f" [STALE >{stale_days}d]"
        else:
            when = "?"
        lines.append(f"    !{iid}  {author}  {when}{stale}  {title}")


def summarize() -> list[str]:
    name = cfg("project.name", "repo")
    remote = cfg("project.remote", "origin")
    main_branch = cfg("project.mainBranch", "main")
    host = cfg("sessionStart.host", "github")
    stale_days = cfg("sessionStart.staleDays", 3)

    lines = [f"[session-start] {name} repo state"]
    _fetch(remote)

    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], timeout=TIMEOUT_GIT)
    if branch:
        lines.append(f"- branch: {branch}")

    divergence = run(["git", "rev-list", "--left-right", "--count", "HEAD...@{u}"], timeout=TIMEOUT_GIT)
    if divergence:
        parts = divergence.replace("\t", " ").split()
        if len(parts) == 2:
            lines.append(f"- ahead/behind upstream: +{parts[0]}/-{parts[1]}")

    _vs_main(lines, remote, main_branch)

    status = run(["git", "status", "--porcelain"], timeout=TIMEOUT_GIT)
    if status:
        lines.append(f"- uncommitted files: {len(status.splitlines())}")

    recent = run(["git", "log", "--oneline", "-5"], timeout=TIMEOUT_GIT)
    if recent:
        lines.append("- recent commits:")
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
        print(f"[session-start] error suppressed: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
