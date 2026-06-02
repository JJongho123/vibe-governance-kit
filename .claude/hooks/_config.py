#!/usr/bin/env python3
"""Shared config loader for the vibe-governance-kit hooks.

Every hook imports this module to read ``governance.config.json`` instead of
hardcoding project-specific values. The config file is discovered by walking
up from the current working directory, so it works from worktrees and
sub-packages alike.

Design contract:
- Missing / malformed config never crashes a hook — callers fall back to the
  built-in defaults baked into each hook.
- All lookups are total: ``cfg("a.b.c", default)`` never raises.

This file lives under .claude/hooks/ so it ships with the harness and has no
external dependencies (standard library only).
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
    # Also check next to the hooks themselves (kit installed standalone).
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
        print(f"[governance] WARN: could not parse {CONFIG_NAME}: {exc}", file=sys.stderr)
        return {}


def cfg(dotted: str, default=None):
    """Total lookup: cfg('boundaries.mode', 'soft')."""
    node = load_config()
    for key in dotted.split("."):
        if isinstance(node, dict) and key in node:
            node = node[key]
        else:
            return default
    return node


def is_enabled(section: str, default: bool = True) -> bool:
    return bool(cfg(f"{section}.enabled", default))
