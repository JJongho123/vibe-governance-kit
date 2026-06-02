#!/usr/bin/env python3
"""PreToolUse(Edit|Write|NotebookEdit) hook.

Two independent, independently-toggleable responsibilities:

1. **Secret scan** (``secretScan.enabled``). Blocks writes whose content
   contains credential patterns. Built-in generic patterns (AWS keys, JWT,
   private keys, generic ``password=`` / ``api_key=``) always apply; opt-in
   locale presets (krPii, cognito, connectArn) and project ``extraPatterns``
   extend them. This is the last line of defense before a file hits disk —
   gitleaks / trufflehog catch the rest at CI.

2. **Domain boundary enforcement** (``boundaries.enabled``, OFF by default).
   Infers the owning "domain" from the current git branch and denies writes
   that leave that domain's zone. ``mode: soft`` warns on unrecognized
   branches; ``mode: strict`` denies them. Useful for multi-agent or
   multi-owner repos. See README §Boundaries.

Configure via governance.config.json; you should not need to edit this file.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _config import cfg, is_enabled  # noqa: E402

# --- Built-in secret patterns (project-agnostic) -------------------------
BUILTIN_SECRETS: list[tuple[str, str]] = [
    (r"\bAKIA[0-9A-Z]{16}\b", "AWS access key ID"),
    (r"\bASIA[0-9A-Z]{16}\b", "AWS temporary access key"),
    (r"(?i)aws_secret_access_key\s*=\s*['\"]?[A-Za-z0-9/+=]{40}", "AWS secret access key"),
    (r"(?i)\bsecret[_-]?access[_-]?key\s*[:=]\s*['\"][A-Za-z0-9/+=]{40}", "AWS secret access key"),
    (r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b", "JWT-shaped token"),
    (r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----", "private key block"),
    (r"(?i)\b(password|passwd|pwd)\s*[:=]\s*['\"][^'\"\s]{8,}", "hardcoded password"),
    (r"(?i)\bapi[_-]?key\s*[:=]\s*['\"][A-Za-z0-9_-]{20,}", "API key literal"),
    (r"\bgh[pousr]_[A-Za-z0-9]{36,}\b", "GitHub token"),
    (r"\bglpat-[A-Za-z0-9_-]{20,}\b", "GitLab personal access token"),
    (r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b", "Slack token"),
    (r"\bsk-[A-Za-z0-9]{20,}\b", "OpenAI-style secret key"),
]

# --- Opt-in locale / vendor presets --------------------------------------
PRESET_SECRETS: dict[str, list[tuple[str, str]]] = {
    "krPii": [
        (r"\b01[016789]-?\d{3,4}-?\d{4}\b", "KR mobile phone number"),
        (r"\b\d{6}-[1-4]\d{6}\b", "KR resident registration number"),
    ],
    "cognito": [
        (r"\b[a-z]{2}-[a-z]+-\d_[A-Za-z0-9]{9}\b", "Cognito User Pool ID (full value)"),
        (r"\b[a-z]{2}-[a-z]+-\d:[0-9a-f-]{36}\b", "Cognito Identity Pool ID"),
    ],
    "connectArn": [
        (r"arn:aws:connect:[^:\s]+:\d+:instance/[0-9a-f-]{36}", "full Connect InstanceId ARN"),
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
        label = item.get("label", "project-defined secret")
        if regex:
            patterns.append((regex, label))
    return patterns


# --- Helpers --------------------------------------------------------------
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
            print(f"[pre-tool-write] WARN: bad regex in {key}: {raw!r} ({exc})", file=sys.stderr)
    return out


def check_boundary(rel: str, branch: str | None) -> str | None:
    """Return None to allow; a human reason string to deny. Boundaries OFF -> always None."""
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
                f"protected path '{rel}' requires a bootstrap/infra/shared "
                f"branch; current branch: {branch!r}"
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
            f"branch {branch!r} owns domain '{domain}' but target '{rel}' "
            f"lies outside that domain's zones"
        )

    # Unrecognized branch.
    if cfg("boundaries.mode", "soft") == "strict":
        return f"strict boundaries: unrecognized branch {branch!r} may not write {rel!r}"
    print(
        f"[pre-tool-write] WARN: unrecognized branch {branch!r} writing to "
        f"{rel!r}; allowing (soft mode).",
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
        print(f"[pre-tool-write] WARN: malformed stdin ({exc}); allowing", file=sys.stderr)
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
        print(f"[pre-tool-write] DENY: {reason}", file=sys.stderr)
        return 2

    if is_enabled("secretScan", True):
        haystack = "\n".join(p for p in (inp.get("content") or "", inp.get("new_string") or "") if p)
        if haystack:
            hit = scan_secrets(haystack)
            if hit:
                label, sample = hit
                print(
                    f"[pre-tool-write] DENY: {label} detected in write to {rel}\n"
                    f"  sample: {sample!r}",
                    file=sys.stderr,
                )
                return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
