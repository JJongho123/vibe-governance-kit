# ADR Index

Architecture Decision Records. Format: [MADR](https://adr.github.io/madr/) —
Context, Decision, Consequences, Alternatives.

## Ledger

| #   | Title                                     | Status   | Date       | Supersedes |
| --- | ----------------------------------------- | -------- | ---------- | ---------- |
| 001 | Adopt vibe-governance-kit for the harness | Accepted | YYYY-MM-DD | —          |

## Authoring rules

- Each ADR is append-only. Never edit an Accepted ADR's body except to change Status.
- To reverse a decision, write a new ADR with `Supersedes: N` and update this INDEX.
- Status vocabulary: `Proposed` / `Accepted` / `Deprecated` / `Superseded by N`.
- Every `Context` cites at least one of: incident, measured cost, external
  constraint, or dependency deadline. "We thought it'd be nicer" is not a reason.
- Every `Alternatives` section lists ≥2 alternatives and why each was rejected.

Use `_template.md` as the starting point for new ADRs.
