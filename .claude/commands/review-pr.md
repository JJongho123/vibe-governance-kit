---
description: Run the full PR review checklist against a given PR or branch.
argument-hint: <PR number or branch name>
---

You are acting as a senior reviewer.

Target: `$1` (a pull-request number or a branch name).

Fetch the diff: try `gh pr diff $1`; fall back to `git diff <mainBranch>...$1`
(default `main`; read `project.mainBranch` from `governance.config.json`). Do
**not** post review comments back automatically — output only.

Walk the diff section by section. For each item output ✅ / ⚠️ / ❌ with a
**file:line citation** from the diff. Missing evidence = ⚠️ "needs manual
verification" — no shortcuts.

## 1. Basics
- [ ] Evidence the AI-generated code was read line by line (commit body / PR description).
- [ ] Correct `[ai-generated]` / `[ai-assisted]` / `[ai-reviewed]` commit tag.
- [ ] Tests added or existing tests pass.
- [ ] No `CLAUDE.md` rule violations.
- [ ] PR title/description matches the actual change scope (no out-of-scope files).
- [ ] SPEC / issue link attached.

## 2. Security & secrets
- [ ] No hardcoded secrets / credentials / tokens (secret scanner clean).
- [ ] Least-privilege for any permission/IAM change; no wildcard actions.
- [ ] No real customer data / PII in prompts or fixtures.
- [ ] Logs mask sensitive values.

## 3. Top 5 CWE
- [ ] CWE-862 Missing Authorization
- [ ] CWE-798 Hardcoded Credentials
- [ ] CWE-89 Injection (SQL / NoSQL / command)
- [ ] CWE-79 XSS
- [ ] CWE-200 Sensitive Info Exposure

## 4. Prompt Injection (if AI/LLM path touched)
- [ ] Lethal Trifecta analysis present (data / input / egress).
- [ ] Untrusted input wrapped/treated as inert data.
- [ ] MCP servers (if any) are allow-listed.

## 5. Hallucination check
- [ ] Every SDK method / API / package / config key the AI used actually exists.
- [ ] Cited doc links / error codes are real.

## Output

Render each section's verdicts, then a final `REVIEW SUMMARY:` with ✅/⚠️/❌
counts and a merge recommendation (approve / request-changes / needs-discussion).
