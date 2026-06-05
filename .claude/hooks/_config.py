#!/usr/bin/env python3
"""vibe-governance-kit 훅을 위한 공용 설정 로더.

모든 훅은 프로젝트별 값을 하드코딩하는 대신 이 모듈을 임포트하여
``governance.config.json``을 읽는다. 설정 파일은 현재 작업 디렉터리에서
위로 거슬러 올라가며 탐색하므로, worktree나 하위 패키지에서도 동작한다.

설계 계약:
- 설정이 없거나 잘못되어도 훅이 절대 죽지 않는다 — 호출자는 각 훅에 내장된
  기본값으로 폴백한다.
- 모든 조회는 안전하다(total): ``cfg("a.b.c", default)``는 예외를 던지지 않는다.

이 파일은 .claude/hooks/ 아래에 있어 하네스와 함께 배포되며, 외부 의존성이
없다(표준 라이브러리만 사용).
"""
from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path

CONFIG_NAME = "governance.config.json"


def _find_config() -> Path | None:
    cur = Path.cwd().resolve()
    for d in (cur, *cur.parents):
        candidate = d / CONFIG_NAME
        if candidate.is_file():
            return candidate
    # 훅 자체 옆도 확인한다(키트를 독립적으로 설치한 경우).
    here = Path(__file__).resolve()
    for d in here.parents:
        candidate = d / CONFIG_NAME
        if candidate.is_file():
            return candidate
    return None


@lru_cache(maxsize=1)
def load_config() -> dict:
    path = _find_config()
    if path is None:
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[governance] 경고: {CONFIG_NAME} 파싱 실패: {exc}", file=sys.stderr)
        return {}


def cfg(dotted: str, default=None):
    """안전한 조회: cfg('boundaries.mode', 'soft')."""
    node = load_config()
    for key in dotted.split("."):
        if isinstance(node, dict) and key in node:
            node = node[key]
        else:
            return default
    return node


def is_enabled(section: str, default: bool = True) -> bool:
    return bool(cfg(f"{section}.enabled", default))
