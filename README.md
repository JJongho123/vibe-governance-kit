# vibe-governance-kit

A reusable, project-agnostic **harness governance kit** for AI-assisted ("vibe")
coding with Claude Code. Drop it into any repo to get deterministic, model-proof
guardrails plus the human-judgment policy docs that surround them.

It was distilled from a production AICC project's `.claude/` harness and
generalized: every project-specific value (project name, secret patterns, branch
ownership, Git host) lives in **one file** — `governance.config.json` — so the
Python hooks never need editing per project.

---

## Why

`CLAUDE.md` is a *prompt* — the model sometimes ignores it. `.claude/settings.json`
`permissions` and `hooks` are *deterministic* — the model cannot bypass them, even
under `--dangerously-skip-permissions`. This kit puts the first line of governance
in that deterministic layer, and keeps the un-enforceable parts (design rules,
review judgment) in docs.

Two principles drive the design:

1. **Deterministic Governance First** — enforce in tools, not prose.
2. **Untrusted Input by Default** — guard the Lethal Trifecta on every AI path.

---

## What's inside

```
vibe-governance-kit/
├─ governance.config.json          # ← the ONE file you edit per project
├─ governance.config.schema.json   # JSON schema for the above
├─ CLAUDE.md                        # root AI directive template
├─ .claude/
│  ├─ settings.json                 # permissions.deny + hook registration
│  ├─ settings.local.json.example   # personal, gitignored overrides
│  ├─ hooks/
│  │  ├─ _config.py                 # shared config loader (stdlib only)
│  │  ├─ pre-tool-bash.py           # block dangerous shell commands
│  │  ├─ pre-tool-write.py          # secret scan + (optional) branch→path boundary
│  │  ├─ pre-push-check.py          # block push when behind remote
│  │  ├─ post-tool-edit.py          # auto-format on write
│  │  └─ session-start.py           # inject repo state + open PRs/MRs
│  ├─ commands/                     # /security-audit /review-pr /secret-scan
│  └─ agents/                       # reviewer-agent, researcher-agent
├─ .githooks/pre-push               # bash mirror for non-CLI clients
├─ .github/
│  ├─ pull_request_template.md      # CWE + Trifecta + hallucination checklist
│  └─ CODEOWNERS.example
├─ docs/
│  ├─ governance.md                 # team policy (judgment layer)
│  ├─ injection-defense.md          # Lethal Trifecta playbook
│  ├─ secret-policy.md              # DLP / secret policy
│  └─ adr/                          # ADR index + template
└─ tools/
   ├─ install.ps1                   # copy kit into a target repo (Windows)
   └─ install.sh                    # copy kit into a target repo (POSIX)
```

### Hooks at a glance

| Hook                | Event                       | Blocks? | Does                                                        |
| ------------------- | --------------------------- | ------- | ---------------------------------------------------------- |
| `pre-tool-bash.py`  | PreToolUse(Bash)            | yes     | Denies `rm -rf`, force push, fork bomb, opt-in aws/tf/publish |
| `pre-tool-write.py` | PreToolUse(Edit/Write)      | yes     | Secret scan; optional branch→path ownership enforcement    |
| `pre-push-check.py` | PreToolUse(Bash)            | yes     | Denies `git push` when local is behind the remote target   |
| `post-tool-edit.py` | PostToolUse(Edit/Write)     | no      | Auto-formats (prettier / ruff / terraform / gofmt / rustfmt) |
| `session-start.py`  | SessionStart                | no      | Prints branch/divergence/uncommitted/recent commits/open PRs |

> Requires **Python 3** on PATH (`python`). Stdlib only — no pip installs.

---

## Adopt (into an existing repo)

```powershell
# Windows / PowerShell
C:\workspace\project\vibe-governance-kit\tools\install.ps1 -Target C:\workspace\project\my-app
```

```bash
# macOS / Linux
./tools/install.sh /path/to/my-app           # --force to overwrite (keeps .bak)
```

Then, in the target repo:

1. **Edit `governance.config.json`** — set `project.name`, `project.mainBranch`,
   toggle `dangerousCommands.presets` / `secretScan.presets`, and (optionally)
   turn on `boundaries`.
2. **Enable the git pre-push mirror** (for teammates not on Claude Code CLI):
   ```bash
   git config core.hooksPath .githooks
   ```
3. **Fill in `CLAUDE.md`** placeholders, copy `CODEOWNERS.example` → `CODEOWNERS`.
4. Open Claude Code in the repo — the SessionStart hook prints repo state, which
   confirms the wiring.

> Tip: keep the kit as a **GitHub template repo** or a git submodule, and re-run
> `install.*` to pull harness updates into downstream projects.

---

## Configure (`governance.config.json`)

Everything project-specific is here; the Python is generic.

### `dangerousCommands`
Built-in catastrophes (`rm -rf`, force push, fork bomb, `mkfs`, raw-disk `dd`)
always block. Opt into preset groups and add your own:

```jsonc
"presets": { "aws": true, "terraform": true, "publish": true },
"extraPatterns": [
  { "regex": "\\bkubectl\\s+delete\\s+namespace\\b", "reason": "ns delete is destructive" }
]
```

### `secretScan`
Built-in patterns (AWS keys, JWT, private keys, GitHub/GitLab/Slack/OpenAI
tokens, generic `password=`/`api_key=`) always apply. Enable locale presets and
add domain patterns:

```jsonc
"presets": { "krPii": true },
"extraPatterns": [
  { "regex": "\\bCUST-\\d{8}\\b", "label": "internal customer id" }
]
```

### `boundaries` (optional, OFF by default)
Branch→path ownership for multi-agent / multi-owner repos. The branch's
`(?P<domain>…)` group names the domain; `domainZones` are path regexes with a
`{domain}` placeholder.

```jsonc
"boundaries": {
  "enabled": true,
  "mode": "soft",                  // "soft" warns on unknown branches; "strict" denies
  "branchPattern": "^(?:feat|fix)/(?P<domain>[a-z0-9-]+)(?:/|$)",
  "domainZones": ["^src/{domain}/", "^domains/{domain}/"],
  "bootstrapOnly": ["^\\.claude/", "^governance\\.config\\.json$"]
}
```

A branch `feat/billing/x` may then write only `src/billing/**` (plus
`globalWritable` paths like `docs/`); harness config stays bootstrap-only.

### `sessionStart`
`host`: `github` (uses `gh`), `gitlab` (uses `glab`), or `none` (git-only).

---

## Verify the hooks

```bash
# Should print a DENY line and exit 2:
echo '{"tool_name":"Bash","tool_input":{"command":"rm -rf /"}}' | python .claude/hooks/pre-tool-bash.py; echo "exit=$?"

# Should print a DENY for the planted secret:
echo '{"tool_name":"Write","tool_input":{"file_path":"x.txt","content":"AKIAIOSFODNN7EXAMPLE1"}}' | python .claude/hooks/pre-tool-write.py; echo "exit=$?"
```

---

## Customize further

- **Add a slash command**: drop a `.md` in `.claude/commands/`.
- **Add a subagent**: drop a `.md` in `.claude/agents/`.
- **Tighten CI**: mirror the deny-lists in your pipeline (gitleaks, Semgrep).
- **Incident → Hook loop**: after any incident, add a pattern to
  `governance.config.json` so it can't recur (see `docs/governance.md` §8).

---

## License

Add your license of choice before publishing (e.g. MIT).
