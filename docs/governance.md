# Vibe Coding Governance — Team Policy

> Distilled, project-agnostic governance for AI-assisted ("vibe") coding.
> Adapt the bracketed `[…]` placeholders to your team, then commit.
> The harness in `.claude/` enforces the deterministic parts of this document;
> this file carries the human-judgment parts.

## 0. Five core principles

1. **Vibe-but-Check.** AI does the heavy lifting; humans provide governance
   (review, approval, audit). Speed without verification becomes tech debt.
2. **Deterministic Governance First.** A rule a tool *enforces* beats a rule
   a prompt *requests*. Push every enforceable rule into `settings.json` /
   hooks / CI. Keep `CLAUDE.md` for the un-enforceable (design, domain knowledge).
3. **Untrusted Input by Default.** Every external input (tickets, transcripts,
   emails, web pages, MCP tool output) is untrusted. Watch the Lethal Trifecta.
4. **Checkpoint-Heavy Workflow.** Commit on every working change so a failed
   experiment rolls back instantly. Many small commits over one big one.
5. **One-shot then Collaborate.** Try a quick one-shot prompt first; on failure,
   switch to plan → SPEC → implement. Don't over-engineer prompts.

## 1. `CLAUDE.md` — the shared AI directive

- Lives at repo root, committed. Every Claude Code session reads it.
- Keep it under ~50 instructions; frontier models reliably follow only
  150–200, and the harness already spends ~50. Split overflow via `@import`.
- Anything a linter / formatter / type-checker can enforce does **not** belong
  here — move it to a `PostToolUse` hook.
- Mark non-negotiable rules with **IMPORTANT** or **YOU MUST**.
- Personal overrides go in `CLAUDE.local.md` (gitignored), never the shared file.

## 2. Git strategy

| Branch              | Purpose              | Direct push | Merge                       |
| ------------------- | -------------------- | ----------- | --------------------------- |
| `main`              | production           | never       | PR + 1 approval + green CI  |
| `feat/<area>/<task>`| feature work         | free        | PR → main                   |
| `fix/<desc>`        | bug fix              | free        | PR → main                   |
| `hotfix/<desc>`     | urgent prod fix      | never       | PR → main (fast-track)      |

- Branch lifetime ≤ 2–3 days; long-lived branches are the #1 cause of merge pain.
- Rebase onto the main branch at least daily.
- **Checkpoint-heavy commits.** Ask the agent to commit per work unit.
- Commit convention: `feat: / fix: / refactor: / docs: / chore: / test: / perf:`.
- **AI attribution tags** on every AI-touched commit:
  - `[ai-generated]` — AI wrote ≥90% (2-reviewer recommended)
  - `[ai-assisted]` — AI + substantial human edits (1 reviewer + hallucination check)
  - `[ai-reviewed]` — human wrote, AI reviewed (standard review)
- `Co-authored-by:` is attached automatically via `settings.json attribution` —
  do not ask the model to add it.

## 3. File ownership

- Declare ownership in `CODEOWNERS`.
- One file, one owner at a time — avoid concurrent edits to the same file.
- The `boundaries` block in `governance.config.json` can enforce branch→path
  ownership at the harness layer (see README §Boundaries).

## 4. PR review

- Write a 1-page `SPEC.md` (or issue) before prompting for anything non-trivial.
  Keep the SPEC session and the implementation session separate.
- Required checklist lives in `.github/pull_request_template.md`. Highlights:
  - Every AI line was read and understood; correct `[ai-*]` tag applied.
  - Tests added/passing; implementation and tests not generated in the same
    session (avoids self-fulfilling tests).
  - **Top 5 CWE** checked: CWE-862 (missing authz), CWE-798 (hardcoded creds),
    CWE-89 (injection), CWE-79 (XSS), CWE-200 (sensitive info exposure).
  - **Lethal Trifecta** analysis for anything touching an AI/LLM path
    (see `docs/injection-defense.md`).
  - **Hallucination check**: every SDK method / API / package / IAM action /
    doc link the AI used actually exists.
- Reviewer rule: AI code looks confident and harbors quiet bugs — review it
  *more* carefully, not less. 48-hour merge-or-feedback rule.

## 5. CI/CD gates (recommended)

Lint + type-check · unit tests w/ coverage · secret scan (gitleaks/trufflehog)
· dependency audit · SAST (Semgrep OWASP ruleset) · IaC scan (if applicable)
· build. Block merge on any high-severity finding. Protect `main`
(no direct push, code-owner approval, no force-push).

## 6. Prompt injection & the Lethal Trifecta

See `docs/injection-defense.md`. Hard rule: a workflow that simultaneously
has (1) sensitive-data access, (2) untrusted input, and (3) an external egress
path is vulnerable — remove at least one, usually egress.

## 7. Data loss prevention

See `docs/secret-policy.md`. Never paste real secrets, credentials, customer
PII, or internal data into a prompt. The `secretScan` hook is the last line of
defense before disk; CI secret scanning backstops it.

## 8. Incident → Hook loop

Every incident or near-miss produces (1) a post-mortem, and (2) a concrete
harness change — a new dangerous-command pattern, secret pattern, denied path,
or slash command — so the same mistake cannot recur. Don't let lessons die in
a doc.

## 9. Metrics worth tracking

AI-code ratio (`[ai-*]` tag share) · AI-related rollback rate · PR merge time ·
hallucinations caught in review · secret incidents (target: 0) · Top-5-CWE
findings trend. Measure to improve.
