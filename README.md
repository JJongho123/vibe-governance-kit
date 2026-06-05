# vibe-governance-kit

Claude Code 기반의 AI 보조("바이브") 코딩을 위한, 재사용 가능하고 프로젝트에
구애받지 않는 **하네스 거버넌스 키트**입니다. 어떤 저장소에든 넣기만 하면
결정론적이고 모델이 우회할 수 없는 가드레일과, 그 주변을 감싸는 사람의 판단을
담은 정책 문서를 함께 갖추게 됩니다.

이 키트는 실제 프로덕션 AICC 프로젝트의 `.claude/` 하네스에서 정제·일반화한
것입니다. 프로젝트별로 달라지는 모든 값(프로젝트 이름, 시크릿 패턴, 브랜치
소유권, Git 호스트)은 **단 하나의 파일** — `governance.config.json` — 에
모여 있어, Python 훅을 프로젝트마다 수정할 필요가 없습니다.

---

## 왜 필요한가

`CLAUDE.md`는 *프롬프트*입니다 — 모델이 가끔 무시합니다. `.claude/settings.json`의
`permissions`와 `hooks`는 *결정론적*입니다 — `--dangerously-skip-permissions`
아래에서도 모델이 우회할 수 없습니다. 이 키트는 거버넌스의 1차 방어선을 그
결정론적 계층에 두고, 강제할 수 없는 부분(설계 규칙, 리뷰 판단)은 문서에
남겨 둡니다.

설계를 이끄는 두 가지 원칙:

1. **결정론적 거버넌스 우선** — 산문이 아니라 도구로 강제한다.
2. **기본적으로 입력은 신뢰하지 않는다** — 모든 AI 경로에서 치명적 삼중 위협(Lethal Trifecta)을 경계한다.

---

## 무엇이 들어 있나

```
vibe-governance-kit/
├─ governance.config.json          # ← 프로젝트별로 수정하는 유일한 파일
├─ governance.config.schema.json   # 위 파일의 JSON 스키마
├─ CLAUDE.md                        # 루트 AI 지침 템플릿
├─ .claude/
│  ├─ settings.json                 # permissions.deny + 훅 등록
│  ├─ settings.local.json.example   # 개인용, gitignore 처리되는 오버라이드
│  ├─ hooks/
│  │  ├─ _config.py                 # 공용 설정 로더 (표준 라이브러리만 사용)
│  │  ├─ pre-tool-bash.py           # 위험한 셸 명령 차단
│  │  ├─ pre-tool-write.py          # 시크릿 스캔 + (선택) 브랜치→경로 경계
│  │  ├─ pre-push-check.py          # 원격보다 뒤처졌을 때 push 차단
│  │  ├─ post-tool-edit.py          # 쓰기 시 자동 포맷
│  │  └─ session-start.py           # 저장소 상태 + 열린 PR/MR 주입
│  ├─ commands/                     # /security-audit /review-pr /secret-scan
│  └─ agents/                       # reviewer-agent, researcher-agent
├─ .githooks/pre-push               # CLI를 쓰지 않는 클라이언트용 bash 미러
├─ .github/
│  ├─ pull_request_template.md      # CWE + 삼중 위협 + 환각 체크리스트
│  └─ CODEOWNERS.example
├─ docs/
│  ├─ governance.md                 # 팀 정책 (판단 계층)
│  ├─ injection-defense.md          # 치명적 삼중 위협 플레이북
│  ├─ secret-policy.md              # DLP / 시크릿 정책
│  └─ adr/                          # ADR 인덱스 + 템플릿
└─ tools/
   ├─ install.ps1                   # 키트를 대상 저장소로 복사 (Windows)
   └─ install.sh                    # 키트를 대상 저장소로 복사 (POSIX)
```

### 훅 한눈에 보기

| 훅                  | 이벤트                      | 차단? | 동작                                                        |
| ------------------- | --------------------------- | ------- | ---------------------------------------------------------- |
| `pre-tool-bash.py`  | PreToolUse(Bash)            | 예      | `rm -rf`, 강제 push, 포크 폭탄, 선택형 aws/tf/publish 차단 |
| `pre-tool-write.py` | PreToolUse(Edit/Write)      | 예      | 시크릿 스캔; 선택적 브랜치→경로 소유권 강제                |
| `pre-push-check.py` | PreToolUse(Bash)            | 예      | 로컬이 원격 대상보다 뒤처졌을 때 `git push` 차단           |
| `post-tool-edit.py` | PostToolUse(Edit/Write)     | 아니오  | 자동 포맷 (prettier / ruff / terraform / gofmt / rustfmt)  |
| `session-start.py`  | SessionStart                | 아니오  | 브랜치/분기/미커밋/최근 커밋/열린 PR 출력                  |

> PATH에 **Python 3**(`python`)가 필요합니다. 표준 라이브러리만 사용 — pip 설치 불필요.

---

## 도입 (기존 저장소에)

```powershell
# Windows / PowerShell
C:\workspace\project\vibe-governance-kit\tools\install.ps1 -Target C:\workspace\project\my-app
```

```bash
# macOS / Linux
./tools/install.sh /path/to/my-app           # --force 로 덮어쓰기 (.bak 보존)
```

그다음, 대상 저장소에서:

1. **`governance.config.json` 수정** — `project.name`, `project.mainBranch`를
   설정하고, `dangerousCommands.presets` / `secretScan.presets`를 토글하며,
   (선택적으로) `boundaries`를 켭니다.
2. **git pre-push 미러 활성화** (Claude Code CLI를 쓰지 않는 팀원용):
   ```bash
   git config core.hooksPath .githooks
   ```
3. **`CLAUDE.md`** 자리표시자를 채우고, `CODEOWNERS.example` → `CODEOWNERS`로 복사합니다.
4. 저장소에서 Claude Code를 엽니다 — SessionStart 훅이 저장소 상태를 출력하여
   연결이 제대로 됐는지 확인해 줍니다.

> 팁: 키트를 **GitHub 템플릿 저장소**나 git 서브모듈로 유지하고,
> `install.*`을 다시 실행하여 하네스 업데이트를 하위 프로젝트로 가져오세요.

---

## 설정 (`governance.config.json`)

프로젝트별 값은 전부 여기에 있고, Python 코드는 범용입니다.

### `dangerousCommands`
기본 내장 재앙(`rm -rf`, 강제 push, 포크 폭탄, `mkfs`, 원시 디스크 `dd`)은
항상 차단됩니다. 프리셋 그룹을 선택적으로 켜고 직접 추가하세요:

```jsonc
"presets": { "aws": true, "terraform": true, "publish": true },
"extraPatterns": [
  { "regex": "\\bkubectl\\s+delete\\s+namespace\\b", "reason": "ns 삭제는 파괴적임" }
]
```

### `secretScan`
기본 내장 패턴(AWS 키, JWT, 개인 키, GitHub/GitLab/Slack/OpenAI 토큰, 일반
`password=`/`api_key=`)은 항상 적용됩니다. 로케일 프리셋을 켜고 도메인 패턴을
추가하세요:

```jsonc
"presets": { "krPii": true },
"extraPatterns": [
  { "regex": "\\bCUST-\\d{8}\\b", "label": "내부 고객 ID" }
]
```

### `boundaries` (선택, 기본 OFF)
멀티 에이전트 / 다중 소유자 저장소를 위한 브랜치→경로 소유권. 브랜치의
`(?P<domain>…)` 그룹이 도메인 이름을 정하고, `domainZones`는 `{domain}`
자리표시자를 가진 경로 정규식입니다.

```jsonc
"boundaries": {
  "enabled": true,
  "mode": "soft",                  // "soft"는 미지의 브랜치에 경고; "strict"는 차단
  "branchPattern": "^(?:feat|fix)/(?P<domain>[a-z0-9-]+)(?:/|$)",
  "domainZones": ["^src/{domain}/", "^domains/{domain}/"],
  "bootstrapOnly": ["^\\.claude/", "^governance\\.config\\.json$"]
}
```

`feat/billing/x` 브랜치는 그러면 `src/billing/**`(그리고 `docs/` 같은
`globalWritable` 경로)에만 쓸 수 있으며, 하네스 설정은 bootstrap 전용으로 남습니다.

### `sessionStart`
`host`: `github`(`gh` 사용), `gitlab`(`glab` 사용), 또는 `none`(git 전용).

---

## 훅 검증

```bash
# DENY 라인을 출력하고 종료 코드 2를 반환해야 함:
echo '{"tool_name":"Bash","tool_input":{"command":"rm -rf /"}}' | python .claude/hooks/pre-tool-bash.py; echo "exit=$?"

# 심어 둔 시크릿에 대해 DENY를 출력해야 함:
echo '{"tool_name":"Write","tool_input":{"file_path":"x.txt","content":"AKIAIOSFODNN7EXAMPLE1"}}' | python .claude/hooks/pre-tool-write.py; echo "exit=$?"
```

---

## 더 커스터마이징하기

- **슬래시 명령 추가**: `.claude/commands/`에 `.md` 파일을 넣습니다.
- **서브에이전트 추가**: `.claude/agents/`에 `.md` 파일을 넣습니다.
- **CI 강화**: 파이프라인에서 deny 목록을 미러링합니다(gitleaks, Semgrep).
- **사고 → 훅 루프**: 사고가 발생하면 `governance.config.json`에 패턴을 추가하여
  재발할 수 없게 합니다(`docs/governance.md` §8 참고).

---

## 라이선스

게시 전에 원하는 라이선스를 추가하세요(예: MIT).
