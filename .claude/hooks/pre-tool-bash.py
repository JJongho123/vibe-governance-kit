#!/usr/bin/env python3
"""PreToolUse(Bash) 훅 — 위험한 셸 명령을 차단한다.

Claude Code의 도구 호출 JSON을 stdin으로 읽는다. tool_name이 "Bash"이면
tool_input.command를 위험 패턴 목록과 대조한다. 거부하려면 종료 코드 2를
반환한다(``--dangerously-skip-permissions``로도 우회할 수 없음).

패턴은 세 계층에서 온다:
  1. BUILTIN — 항상 켜져 있는, 프로젝트 무관 재앙.
  2. PRESETS — governance.config.json을 통한 선택형 그룹(aws / terraform / publish).
  3. 설정의 ``dangerousCommands.extraPatterns`` — 프로젝트별 추가.

governance.config.json으로 설정한다. 이 파일을 수정할 필요는 없다.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _config import cfg, is_enabled  # noqa: E402

# --- 1. 내장, 항상 켜져 있는 패턴 -----------------------------------------
BUILTIN: list[tuple[str, str]] = [
    (r"\brm\s+-rf?\s+/(?:\s|$)", "/ 에 대한 rm -rf -- 재앙적"),
    (r"\brm\s+-rf?\s+\*", "rm -rf * -- 현재 디렉터리 트리 삭제"),
    (r"\brm\s+-rf?\s+~", "홈 디렉터리에 대한 rm -rf"),
    (r"\bgit\s+push\s+(?:--force|-f)\b", "강제 push는 원격 이력을 다시 씀"),
    (r"\bgit\s+reset\s+--hard\b", "git reset --hard는 미커밋 작업을 버림"),
    (r"\bgit\s+clean\s+-[fdx]{2,}\b", "git clean -fdx는 추적되지 않는 파일을 제거함"),
    (r":\(\)\s*\{\s*:\|:\s*&\s*\}\s*;", "포크 폭탄"),
    (r"\bmkfs\.\w+", "mkfs -- 파일시스템 포맷"),
    (r"\bdd\s+[^|]*of=/dev/(?!null|zero)\w", "블록 장치에 대한 dd"),
    (r"\bshutdown\b", "shutdown(시스템 종료)"),
    (r"\bhalt\b", "halt(정지)"),
    (r">\s*/dev/sd[a-z]", "원시 디스크 장치로 리다이렉트"),
    (r"\bchmod\s+-R\s+0?777\s+/", "루트에서 재귀적 chmod 777"),
]

# --- 2. 선택형 프리셋 -----------------------------------------------------
PRESET_PATTERNS: dict[str, list[tuple[str, str]]] = {
    "publish": [
        (r"\bnpm\s+publish\b", "npm publish -- 실수로 패키지 게시"),
        (r"\bpnpm\s+publish\b", "pnpm publish -- 실수로 패키지 게시"),
        (r"\byarn\s+publish\b", "yarn publish -- 실수로 패키지 게시"),
        (r"\bcargo\s+publish\b", "cargo publish -- 실수로 크레이트 게시"),
        (r"\btwine\s+upload\b", "twine upload -- 실수로 PyPI 게시"),
    ],
    "aws": [
        (r"\baws\s+s3\s+rm\b", "aws s3 rm -- 파괴적"),
        (r"\baws\s+s3\s+rb\b", "aws s3 rb -- 버킷 제거"),
        (r"\baws\s+dynamodb\s+delete-table\b", "DynamoDB delete-table -- 데이터 손실"),
        (r"\baws\s+ec2\s+terminate-instances\b", "EC2 terminate -- 파괴적"),
        (r"\baws\s+rds\s+delete-db-instance\b", "RDS delete -- 데이터 손실"),
    ],
    "terraform": [
        (r"\bterraform\s+apply\b", "terraform apply -- plan을 먼저 검토하세요"),
        (r"\bterraform\s+destroy\b", "terraform destroy -- 재앙적"),
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
        reason = item.get("reason", "프로젝트에서 정의한 위험 명령")
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
        print(f"[pre-tool-bash] 경고: 잘못된 stdin ({exc}); 허용함", file=sys.stderr)
        return 0

    if payload.get("tool_name") != "Bash":
        return 0

    command = (payload.get("tool_input") or {}).get("command") or ""
    for pattern, reason in build_patterns():
        try:
            if re.search(pattern, command):
                print(
                    f"[pre-tool-bash] 거부: {reason}\n"
                    f"  패턴: {pattern}\n"
                    f"  명령: {command[:200]}",
                    file=sys.stderr,
                )
                return 2
        except re.error as exc:
            print(f"[pre-tool-bash] 경고: 잘못된 정규식 {pattern!r}: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
