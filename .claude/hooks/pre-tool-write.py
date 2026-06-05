#!/usr/bin/env python3
"""PreToolUse(Edit|Write|NotebookEdit) 훅.

서로 독립적이며 개별적으로 토글 가능한 두 가지 책임:

1. **시크릿 스캔** (``secretScan.enabled``). 내용에 자격 증명 패턴이 포함된
   쓰기를 차단한다. 내장 범용 패턴(AWS 키, JWT, 개인 키, 일반
   ``password=`` / ``api_key=``)은 항상 적용되고, 선택형 로케일 프리셋
   (krPii, cognito, connectArn)과 프로젝트 ``extraPatterns``가 이를 확장한다.
   파일이 디스크에 닿기 전 마지막 방어선이며 — 나머지는 CI에서
   gitleaks / trufflehog가 잡는다.

2. **도메인 경계 강제** (``boundaries.enabled``, 기본 OFF). 현재 git 브랜치에서
   소유 "도메인"을 추론하고, 그 도메인의 영역을 벗어나는 쓰기를 거부한다.
   ``mode: soft``는 인식되지 않는 브랜치에 경고하고, ``mode: strict``는 거부한다.
   멀티 에이전트나 다중 소유자 저장소에 유용하다. README §Boundaries 참고.

governance.config.json으로 설정한다. 이 파일을 수정할 필요는 없다.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _config import cfg, is_enabled  # noqa: E402

# --- 내장 시크릿 패턴 (프로젝트 무관) ------------------------------------
BUILTIN_SECRETS: list[tuple[str, str]] = [
    (r"\bAKIA[0-9A-Z]{16}\b", "AWS 액세스 키 ID"),
    (r"\bASIA[0-9A-Z]{16}\b", "AWS 임시 액세스 키"),
    (r"(?i)aws_secret_access_key\s*=\s*['\"]?[A-Za-z0-9/+=]{40}", "AWS 시크릿 액세스 키"),
    (r"(?i)\bsecret[_-]?access[_-]?key\s*[:=]\s*['\"][A-Za-z0-9/+=]{40}", "AWS 시크릿 액세스 키"),
    (r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b", "JWT 형태 토큰"),
    (r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----", "개인 키 블록"),
    (r"(?i)\b(password|passwd|pwd)\s*[:=]\s*['\"][^'\"\s]{8,}", "하드코딩된 비밀번호"),
    (r"(?i)\bapi[_-]?key\s*[:=]\s*['\"][A-Za-z0-9_-]{20,}", "API 키 리터럴"),
    (r"\bgh[pousr]_[A-Za-z0-9]{36,}\b", "GitHub 토큰"),
    (r"\bglpat-[A-Za-z0-9_-]{20,}\b", "GitLab 개인 액세스 토큰"),
    (r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b", "Slack 토큰"),
    (r"\bsk-[A-Za-z0-9]{20,}\b", "OpenAI 형태 시크릿 키"),
]

# --- 선택형 로케일 / 벤더 프리셋 ------------------------------------------
PRESET_SECRETS: dict[str, list[tuple[str, str]]] = {
    "krPii": [
        (r"\b01[016789]-?\d{3,4}-?\d{4}\b", "한국 휴대폰 번호"),
        (r"\b\d{6}-[1-4]\d{6}\b", "한국 주민등록번호"),
    ],
    "cognito": [
        (r"\b[a-z]{2}-[a-z]+-\d_[A-Za-z0-9]{9}\b", "Cognito User Pool ID (전체 값)"),
        (r"\b[a-z]{2}-[a-z]+-\d:[0-9a-f-]{36}\b", "Cognito Identity Pool ID"),
    ],
    "connectArn": [
        (r"arn:aws:connect:[^:\s]+:\d+:instance/[0-9a-f-]{36}", "전체 Connect InstanceId ARN"),
    ],
}


def build_secret_patterns() -> list[tuple[str, str]]:
    patterns = list(BUILTIN_SECRETS)
    presets = cfg("secretScan.presets", {}) or {}
    for name, enabled in presets.items():
        if enabled and name in PRESET_SECRETS:
            patterns.extend(PRESET_SECRETS[name])
    for item in cfg("secretScan.extraPatterns", []) or []:
        regex = item.get("regex")
        label = item.get("label", "프로젝트에서 정의한 시크릿")
        if regex:
            patterns.append((regex, label))
    return patterns


# --- 헬퍼 -----------------------------------------------------------------
def current_branch() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=3,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return None


def relpath(absolute: str) -> str:
    try:
        return str(Path(absolute).resolve().relative_to(Path.cwd().resolve())).replace("\\", "/")
    except (ValueError, OSError):
        return absolute.replace("\\", "/")


def scan_secrets(text: str) -> tuple[str, str] | None:
    for pattern, reason in build_secret_patterns():
        try:
            m = re.search(pattern, text)
        except re.error:
            continue
        if m:
            return reason, m.group(0)[:40]
    return None


def _compile_all(key: str) -> list[re.Pattern[str]]:
    out = []
    for raw in cfg(key, []) or []:
        try:
            out.append(re.compile(raw))
        except re.error as exc:
            print(f"[pre-tool-write] 경고: {key}의 잘못된 정규식: {raw!r} ({exc})", file=sys.stderr)
    return out


def check_boundary(rel: str, branch: str | None) -> str | None:
    """허용하면 None을, 거부하면 사람이 읽을 이유 문자열을 반환. 경계 OFF -> 항상 None."""
    if not is_enabled("boundaries", False):
        return None

    for pat in _compile_all("boundaries.globalWritable"):
        if pat.search(rel):
            return None

    bootstrap_re = cfg("boundaries.bootstrapBranchPattern")
    if branch and bootstrap_re:
        try:
            if re.match(bootstrap_re, branch):
                return None
        except re.error:
            pass

    for pat in _compile_all("boundaries.bootstrapOnly"):
        if pat.search(rel):
            return (
                f"보호된 경로 '{rel}'에는 bootstrap/infra/shared 브랜치가 "
                f"필요함; 현재 브랜치: {branch!r}"
            )

    branch_re = cfg("boundaries.branchPattern")
    domain = None
    if branch and branch_re:
        try:
            m = re.match(branch_re, branch)
            if m:
                gd = m.groupdict()
                domain = gd.get("domain") or (m.group(1) if m.groups() else None)
        except re.error:
            pass

    if domain:
        zones = []
        for raw in cfg("boundaries.domainZones", []) or []:
            try:
                zones.append(re.compile(raw.replace("{domain}", re.escape(domain))))
            except re.error:
                continue
        for pat in zones:
            if pat.search(rel):
                return None
        return (
            f"브랜치 {branch!r}는 도메인 '{domain}'을 소유하지만 대상 '{rel}'은 "
            f"그 도메인의 영역 밖에 있음"
        )

    # 인식되지 않는 브랜치.
    if cfg("boundaries.mode", "soft") == "strict":
        return f"strict 경계: 인식되지 않는 브랜치 {branch!r}는 {rel!r}에 쓸 수 없음"
    print(
        f"[pre-tool-write] 경고: 인식되지 않는 브랜치 {branch!r}가 "
        f"{rel!r}에 쓰는 중; 허용함 (soft 모드).",
        file=sys.stderr,
    )
    return None


def read_payload() -> dict:
    raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    return json.loads(raw) if raw.strip() else {}


def main() -> int:
    try:
        payload = read_payload()
    except Exception as exc:
        print(f"[pre-tool-write] 경고: 잘못된 stdin ({exc}); 허용함", file=sys.stderr)
        return 0

    if payload.get("tool_name") not in ("Write", "Edit", "NotebookEdit"):
        return 0

    inp = payload.get("tool_input") or {}
    target = inp.get("file_path") or inp.get("notebook_path") or ""
    if not target:
        return 0

    rel = relpath(target)
    branch = current_branch()

    reason = check_boundary(rel, branch)
    if reason:
        print(f"[pre-tool-write] 거부: {reason}", file=sys.stderr)
        return 2

    if is_enabled("secretScan", True):
        haystack = "\n".join(p for p in (inp.get("content") or "", inp.get("new_string") or "") if p)
        if haystack:
            hit = scan_secrets(haystack)
            if hit:
                label, sample = hit
                print(
                    f"[pre-tool-write] 거부: {rel}에 대한 쓰기에서 {label} 감지\n"
                    f"  샘플: {sample!r}",
                    file=sys.stderr,
                )
                return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
