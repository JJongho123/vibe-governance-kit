---
description: On-demand secret / DLP scan of staged + unstaged changes.
argument-hint: "[optional path glob]"
---

Scan the working changes for secrets and sensitive data before a push.

## Scope

1. `$ARGUMENTS` empty → scan `git diff` + `git diff --staged` (working changes).
2. Else scan the given path glob.

## What to flag

Walk the diff and report any match with a `file:line` citation:

- Cloud credentials: `AKIA*` / `ASIA*`, secret/session keys, service accounts.
- Tokens: JWT (`eyJ…`), OAuth secrets, `ghp_*`, `glpat-*`, `xox*`, `sk-*`.
- Private keys: `-----BEGIN … PRIVATE KEY-----`.
- Generic literals: `password=`, `api_key=`, connection strings with embedded creds.
- PII per the active `secretScan.presets` in `governance.config.json`
  (e.g. phone numbers, national IDs) plus any `extraPatterns`.
- Real customer data / transcripts / internal identifiers in fixtures or tests.

## Notes

This complements the deterministic `pre-tool-write.py` hook (which blocks
writes) and CI secret scanning. Use it as a pre-push self-check.

## Output

A findings table (`severity | file:line | class | sample(masked)`), then a
`VERDICT:` line — `CLEAN` or `BLOCK (n findings)` with the single most urgent
item called out.
