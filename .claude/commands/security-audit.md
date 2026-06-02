---
description: Top 5 CWE + Lethal Trifecta audit on the current branch's staged/unstaged changes.
argument-hint: "[optional file list or path glob]"
---

Perform a security audit on the current branch's changes.

## Scope selection

1. If `$ARGUMENTS` is empty → use `git diff <mainBranch>...HEAD` (default `main`;
   read `project.mainBranch` from `governance.config.json` if present).
2. Else treat `$ARGUMENTS` as a file list or path glob.

## Top 5 CWE walk-through

For each CWE, enumerate matches with a `file:line` citation and a one-sentence
risk note. Mark ✅ confident-clean, ⚠️ needs-human-verification, ❌ confirmed.

### CWE-862 — Missing Authorization
- Every request handler / endpoint checks authn + authz before reading/writing data.
- No "TODO: add auth" slipping through.

### CWE-798 — Hardcoded Credentials
- No cloud keys, JWTs, tokens, or `password=`/`apiKey=` literals.
- Config comes from env / secrets manager, not inline.

### CWE-89 — Injection (SQL / NoSQL / command)
- Parameterized queries only; no string-concatenated SQL.
- Shell calls use explicit argv arrays, never `sh -c "$userInput"`.

### CWE-79 — XSS
- No `dangerouslySetInnerHTML` / unescaped HTML sinks.
- User strings pass through escape helpers; markdown renderers sanitize.

### CWE-200 — Sensitive Info Exposure
- Error responses strip stack traces, schemas, internal paths.
- Logs mask PII.

## Lethal Trifecta audit

Build a table of every new/modified module on an AI/LLM or data-egress path:

| module | ① sensitive data? | ② untrusted input? | ③ external egress? | trifecta?      |
| ------ | ----------------- | ------------------ | ------------------ | -------------- |
| ...    | yes/no + source   | yes/no + source    | yes/no + source    | YES=❌ / NO=✅ |

For any `YES` row, state which element is cheapest to remove (usually ③ egress)
and give a concrete mitigation.

## Output

CWE walkthrough → Trifecta table → final `SUMMARY:` block with ✅/⚠️/❌ counts,
the highest-severity finding, and a recommended action
(block merge / request fix / annotate and proceed).
