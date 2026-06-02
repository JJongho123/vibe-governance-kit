<!-- PR template — vibe-governance-kit. Trim sections that don't apply. -->

## What & why

<!-- 1–2 sentences. Link the SPEC / issue. -->

## Scope

- [ ] PR title/description matches the actual change (no out-of-scope files).
- [ ] Branch follows `feat|fix|chore/<area>/<task>`.

## AI attribution

- [ ] Correct commit tag applied: `[ai-generated]` / `[ai-assisted]` / `[ai-reviewed]`.
- [ ] Every AI-generated line was read and understood.

## Security & secrets

- [ ] No hardcoded secrets / credentials / tokens (secret scanner clean).
- [ ] No real customer data / PII in prompts, fixtures, or logs.
- [ ] Least-privilege for any permission change; no wildcard grants.

## Top 5 CWE

- [ ] CWE-862 Missing Authorization
- [ ] CWE-798 Hardcoded Credentials
- [ ] CWE-89 Injection (SQL / NoSQL / command)
- [ ] CWE-79 XSS
- [ ] CWE-200 Sensitive Info Exposure

## Prompt Injection (if any AI/LLM path is touched)

Lethal Trifecta analysis:

| element              | present? | source / mitigation |
| -------------------- | -------- | ------------------- |
| ① sensitive data     |          |                     |
| ② untrusted input    |          |                     |
| ③ external egress    |          |                     |

- [ ] If all three are present, state which was removed and how.

## Hallucination check

- [ ] Every SDK method / API / package / config key used actually exists.
- [ ] Cited doc links / error codes are real.

## Tests

- [ ] Tests added or existing tests pass.
- [ ] Implementation and tests were **not** generated in the same prompt session.
