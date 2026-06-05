# ADR 인덱스

아키텍처 결정 기록(Architecture Decision Records). 형식:
[MADR](https://adr.github.io/madr/) — 배경, 결정, 결과, 대안.

## 원장(Ledger)

| #   | 제목                                      | 상태     | 날짜       | 대체 대상  |
| --- | ----------------------------------------- | -------- | ---------- | ---------- |
| 001 | 하네스를 위해 vibe-governance-kit 채택     | 승인됨   | YYYY-MM-DD | —          |

## 작성 규칙

- 각 ADR은 추가 전용(append-only)이다. 승인된 ADR의 본문은 상태 변경을 제외하고 절대 수정하지 않는다.
- 결정을 뒤집으려면 `Supersedes: N`을 단 새 ADR을 작성하고 이 INDEX를 갱신한다.
- 상태 어휘: `제안됨(Proposed)` / `승인됨(Accepted)` / `폐기됨(Deprecated)` / `N에 의해 대체됨(Superseded by N)`.
- 모든 `배경`은 다음 중 최소 하나를 인용한다: 사고, 측정된 비용, 외부 제약,
  또는 의존성 마감 기한. "더 좋아 보여서"는 이유가 아니다.
- 모든 `대안` 절은 2개 이상의 대안과 각각 기각된 이유를 나열한다.

새 ADR을 만들 때는 `_template.md`를 출발점으로 사용하세요.
