#!/usr/bin/env python3
"""PostToolUse(Edit|Write) 훅 — 쓰여진 파일을 자동 포맷한다.

대상 파일의 확장자에 맞는 포매터를 호출하며, 포매터가 설치되어 있지 않으면
조용히 건너뛴다. 도구 호출을 절대 실패시키지 않는다: 포맷은 게이트가 아니라
후처리다.

도구 체인:
  .ts/.tsx/.js/.jsx/.json/.md/.css/.html/.yaml -> prettier --write
  .py                                           -> ruff format ; ruff check --fix
  .tf/.tfvars                                   -> terraform fmt
  .go                                           -> gofmt -w
  .rs                                           -> rustfmt

governance.config.json의 ``format.enabled``로 토글한다.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _config import is_enabled  # noqa: E402

PRETTIER_EXTS = {
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".json", ".md", ".css", ".scss", ".html", ".yaml", ".yml",
}
RUFF_EXTS = {".py"}
TERRAFORM_EXTS = {".tf", ".tfvars"}
GO_EXTS = {".go"}
RUST_EXTS = {".rs"}


def run(cmd: list[str], *, timeout: int = 20) -> None:
    try:
        subprocess.run(cmd, timeout=timeout, capture_output=True, text=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        pass


def read_payload() -> dict:
    raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    return json.loads(raw) if raw.strip() else {}


def main() -> int:
    if not is_enabled("format", True):
        return 0
    try:
        payload = read_payload()
    except Exception:
        return 0

    if payload.get("tool_name") not in ("Write", "Edit"):
        return 0

    target = (payload.get("tool_input") or {}).get("file_path") or ""
    if not target or not Path(target).exists():
        return 0

    ext = Path(target).suffix.lower()

    if ext in PRETTIER_EXTS:
        if shutil.which("prettier"):
            run(["prettier", "--write", target])
        elif shutil.which("npx"):
            run(["npx", "--no-install", "prettier", "--write", target])
    elif ext in RUFF_EXTS:
        if shutil.which("ruff"):
            run(["ruff", "format", target])
            run(["ruff", "check", "--fix", "--exit-zero", target])
    elif ext in TERRAFORM_EXTS:
        if shutil.which("terraform"):
            run(["terraform", "fmt", target])
    elif ext in GO_EXTS:
        if shutil.which("gofmt"):
            run(["gofmt", "-w", target])
    elif ext in RUST_EXTS:
        if shutil.which("rustfmt"):
            run(["rustfmt", target])

    return 0


if __name__ == "__main__":
    sys.exit(main())
