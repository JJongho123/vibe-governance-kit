---
description: 스테이징된 변경과 스테이징되지 않은 변경에 대한 온디맨드 시크릿 / DLP 스캔.
argument-hint: "[선택적 경로 glob]"
---

push 전에 작업 변경분에서 시크릿과 민감 데이터를 스캔합니다.

## 범위

1. `$ARGUMENTS`가 비어 있음 → `git diff` + `git diff --staged`(작업 변경분)를 스캔.
2. 그 외 → 주어진 경로 glob을 스캔.

## 무엇을 플래그할 것인가

diff를 따라가며 `file:line` 인용과 함께 일치 항목을 보고합니다:

- 클라우드 자격 증명: `AKIA*` / `ASIA*`, 시크릿/세션 키, 서비스 계정.
- 토큰: JWT(`eyJ…`), OAuth 시크릿, `ghp_*`, `glpat-*`, `xox*`, `sk-*`.
- 개인 키: `-----BEGIN … PRIVATE KEY-----`.
- 일반 리터럴: `password=`, `api_key=`, 자격 증명이 박힌 연결 문자열.
- `governance.config.json`의 활성 `secretScan.presets`에 따른 PII
  (예: 전화번호, 주민등록번호)와 모든 `extraPatterns`.
- 픽스처나 테스트의 실제 고객 데이터 / 통화 기록 / 내부 식별자.

## 참고

이것은 결정론적 `pre-tool-write.py` 훅(쓰기를 차단)과 CI 시크릿 스캐닝을
보완합니다. push 전 자체 점검으로 사용하세요.

## 출력

발견 테이블(`심각도 | file:line | 분류 | 샘플(마스킹됨)`) 후, `VERDICT:` 라인 —
`CLEAN` 또는 `BLOCK (n건)`과 함께 가장 시급한 항목 하나를 강조합니다.
