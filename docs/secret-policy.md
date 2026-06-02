# Secret & Data-Loss Prevention Policy

Project-agnostic. Applies to every agent session and every PR. Backed by the
`secretScan` layer in `.claude/hooks/pre-tool-write.py` (last line before disk)
and CI secret scanning (gitleaks / trufflehog) as backstop.

## 1. Never paste into a prompt (hard NEVER list)

| Class                | Examples                                                  |
| -------------------- | --------------------------------------------------------- |
| Cloud credentials    | AWS `AKIA*`/`ASIA*`, secret/session keys, service-account |
| Tokens               | JWT (`eyJ…`), OAuth secrets, `ghp_*`, `glpat-*`, `xox*`   |
| Private keys         | `-----BEGIN … PRIVATE KEY-----`                           |
| PII                  | Names, phone, email, national IDs, card numbers, address  |
| Customer data        | Real records, transcripts, recordings, ticket bodies      |
| Internal             | Roadmaps, internal design links, infra identifiers        |

The built-in secret scanner blocks the credential/token/key classes. Enable
locale presets (e.g. `krPii`) in `governance.config.json` for regional PII, and
add `extraPatterns` for anything specific to your domain.

## 2. Masking rules

- Phone: `010-****-5678` (display) / `sha256(phone+salt)[:16]` (correlation).
- Email: `c*****@example.com` (display).
- Long resource IDs: show first 8 chars + `…`; hash for cross-log correlation.
- Centralize maskers in a shared module; every log call passes through one.
  No raw PII in logs.

## 3. Approved tools

Route sensitive work through an in-region, enterprise-governed model endpoint.
Personal consumer AI accounts (free ChatGPT / Claude.ai) are out of policy for
company code or data. Document your team's approved-tool list here.

## 4. Fixtures

Test code uses synthetic, masked fixtures only. Each fixture carries a
`DATA_SOURCE: synthetic` header and no real identifiers. Never create a fixture
by copy-pasting production data.

## 5. Incident procedure

If sensitive data reaches an external AI service:

1. Report to the team channel within 15 minutes.
2. Request deletion from the external service's history.
3. Escalate customer PII to the privacy owner within the legally-required
   window (e.g. 72h under many regimes).
4. File a post-mortem; its required output is one concrete prevention change —
   usually a new `secretScan.extraPatterns` entry (governance §8 Incident→Hook).

## References

- `docs/governance.md` §7
- `.claude/hooks/pre-tool-write.py` — implementation
- `governance.config.json` `secretScan` — configuration
