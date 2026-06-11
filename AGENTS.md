---
date created: 2026-04-18
date modified: 2026-06-12
tags: [규칙, 문서관리]
---

# AI Agent 지침

> 이 파일은 모든 AI 도구(Claude, Kiro, Gemini, Copilot 등)가 이 프로젝트를 다룰 때의 기본 지침이다.
> 각 도구의 진입점 파일(CLAUDE.md, .kiro/, .gemini/ 등)은 이 파일을 가리킨다.

본 파일은 진입점이며, 각 영역의 풀 절차·규약은 산하 SSOT 문서에 둔다. 본 파일은 작게 유지한다.

## 새 세션 시작 시 (필수)

1. 이 파일을 읽는다.
2. [_docs/_worklog/STATUS.md](_docs/_worklog/STATUS.md)를 읽고 현재 작업 상태와 다음 할 일을 파악한다.
3. STATUS.md의 "마지막 정합성 감사" 시각이 12시간 초과면 본 작업 시작 전에 epistemic-auditor 서브에이전트를 호출한다 (cf. [AGENTS/agent-roles.md](AGENTS/agent-roles.md)). 보고된 위반은 정리하거나 사용자에게 짚은 뒤 STATUS.md의 시각 필드를 새로 기록한다.
4. [`_reference/INDEX.md`](_reference/INDEX.md)를 읽고 폴더 실제 내용과 대조한다. 인벤토리·실제 불일치 또는 `처리 대기`/`사용자 의견 필요` 항목이 있으면 [_docs/_architecture/ingest-workflow.md](_docs/_architecture/ingest-workflow.md) "`_reference/` 폴더 처리" 절차로 진행한다.
5. 작업 범위에 해당하는 `_docs/` 문서를 읽는다 (아래 참조 테이블 기준).
6. 코드 생성/수정 전에는 관련 문서의 기존 결정과 충돌이 없는지 확인한다.

새 정보(사실·의견·예측·결정·자료)가 세션 중 들어오면 [_docs/_architecture/ingest-workflow.md](_docs/_architecture/ingest-workflow.md)의 표준 시퀀스를 따른다.

## 단위 작업 시작/종료 시 (필수)

단위 작업의 시작·진행·종료 흐름은 [AGENTS/unit-task-workflow.md](AGENTS/unit-task-workflow.md) 참조 — 진입·진행·종료(머지 패턴 분기[직접 머지·PR 흐름] + 재귀 정합화)·PR 운영·끊김 재진입의 SSOT.

본 진입점에서 강조하는 의무 한 줄: **단위 작업 시작과 종료 시 STATUS, TASK_TREE, DONE 갱신 + 사용자 검토 통과 후 main 머지**. AI 자율 머지 회피. 근거 원리는 [core-constraints.md 원본 보호 원칙](_docs/_architecture/core-constraints.md)이다.

세션 중 새로운 관례·규칙·스타일이 합의되었으면 해당 내용이 본 파일 또는 관련 영구 문서에 반영되었는지 확인한다. 긴 세션이거나 큰 변경이 있었던 세션의 종료 전에는 epistemic-auditor 서브에이전트를 호출해 문서 정합성 감사를 받는다 (cf. [AGENTS/agent-roles.md](AGENTS/agent-roles.md)).

## 문서 변경 시 (필수)

- 모듈/의존성 변경 → [_docs/_architecture/INDEX.md](_docs/_architecture/INDEX.md) 먼저 업데이트
- 네이밍/규약 변경 → [_docs/_architecture/conventions.md](_docs/_architecture/conventions.md) 먼저 업데이트
- 문서 간 정합성 확인을 항상 수행한다 (특히 cross-reference 되는 섹션 번호).
- 문서나 주석을 수정한 경우, "문서 작성 스타일" 섹션의 규칙을 위배하는 것이 없는지 검토한다.
- INDEX를 읽을 때 `date modified`가 오래된 문서가 눈에 띄면 점검한다. INDEX상 설명이 부적절해서 참조되지 않는 건지, 정말 불필요한 문서인지 판단하여 설명 개선 / 다른 문서로 통합 / 삭제 중 하나를 수행한다. 오래 방치된 문서는 유의미한 역할을 하지 못하고 있다는 신호다.
- 폴더·파일 이동 또는 리네임은 연쇄 갱신을 요구한다. 절차는 [`conventions.md` "폴더·파일 이동 시 연쇄 갱신"](_docs/_architecture/conventions.md) 참조.

## 판단과 검증

- 자기 기억보다 실제 상태를 신뢰한다. 파일 내용·레포 설정·외부 시스템 상태 등을 기억만으로 단언하지 않는다. 마지막으로 확인한 뒤 시간이 지났거나 다른 에이전트·사용자의 개입이 있었을 가능성이 있으면 재확인한다. 도구 호출 한 번으로 검증 가능한 것을 메모리 근거로 주장하지 않는다.
- 다른 에이전트의 결과와 내 기억이 어긋날 때는 자기 기억을 먼저 의심한다. 내 기억이 outdated일 가능성을 배제하기 전에 상대를 환각이라고 단정하지 않는다. 상대의 구체적 증거(커밋 해시, 파일 경로, diff 등)를 직접 재현해 본 뒤 판정한다.

## 문서 작성 스타일

진입자가 첫 화면에서 봐야 할 핵심 항목만 본 절에 둔다. 그 외 일반 작성 규약(1관심사·분량 보조 지표·중복 금지·이름 안정성·코드 블록 절제·고정 규격 태그 중복 회피·도구 전용 파일 예외)은 [`conventions.md` "일반 문서 작성 스타일"](_docs/_architecture/conventions.md) SSOT.

- 볼드·이탤릭·이모지 등 서식/기호 강조는 강한 경고/금지/주의 사항에만 사용한다. 나열·제목·항목 라벨·일반 개념어·장식에는 쓰지 않는다. 남발하면 진짜 강조가 필요할 때의 진정성을 잃는다.
- 문서 간 참조는 마크다운 링크로 작성한다. `[표시 텍스트](상대경로)` 형식.
- 참고 자료/출처 표기는 `cf.` (비교/참고)와 `ref.` (출처/근거)를 사용한다.
- 약어가 처음 등장할 때는 풀어쓴 원문을 병기한다. 예: `SSOT(single source of truth)`, `ADR(Architecture Decision Record)`. 원문이 외국어이고 한국어 설명이 추가로 필요하면 세미콜론으로 덧붙인다. 예: `KAI(Korea Aerospace Industries; 한국항공우주산업)`. 이후 같은 문서 내에서는 약어만 사용한다.
- 약어와 줄임말을 구분한다. 약어(acronym; 단어 첫 글자를 모아 만든 형태 — SSOT·ADR·API 등)는 허용. **줄임말(truncation; 단어 중간을 잘라낸 형태 — feature → feat, configuration → config, repository → repo 등)은 피하고 공식 형태(full form)를 그대로 사용한다.** 줄임말 남발은 입문자 진입 비용을 높이고 검색·일치성을 떨어뜨린다. 일반 도메인에 완전히 정착해 공식 형태처럼 통용되는 경우(예: `docs` 폴더명, `dev` 환경명)는 예외 — 그 경우 본 워크스페이스에서 표준 사용 형태를 명시한다.
- 모든 .md 파일에 YAML front matter를 붙인다. 필수 필드: `date created`, `date modified`, `tags`. 날짜 형식은 `yyyy-MM-dd`. `tags`의 첫 항목은 소속 카테고리.
- **추측으로 문서를 채우지 않는다.** 논의되지 않은 내용을 확정된 것처럼 적지 않는다.
- 사실과 의견, 의견의 주체를 분명히 구분한다. 근거 있는 사실, 작성자 본인의 판단, 타인/외부의 판단은 서술 형태를 달리한다. 의견에는 주체를 명시한다 (예: "`@아릉`의 판단", "Klaviyo 팀의 설계", "AI 제안"). 의견을 사실인 양 서술하거나 주체를 흐리면 이후 결정의 근거 추적이 깨진다.

## 색인(INDEX) 사용 규칙

모든 INDEX 문서에 공통으로 적용된다. 각 INDEX는 자기 영역 고유의 규칙만 별도로 추가한다.

- 읽기: 색인만 먼저 읽고, 필요한 문서만 선택적으로 연다. 전부 읽지 않는다.
- 쓰기: 내용에 맞는 기존 문서에 추가하거나, 구체적인 제목의 새 파일을 만들고 색인에 등록한다.
- 제목 규칙: 파일명은 내용을 특정할 수 있어야 한다. 포괄적 이름은 금지.
- `_docs/_ontology/`, `_docs/_knowledge/`, `_docs/_strategy/`, `_docs/_architecture/` 하위의 모든 마크다운 파일은 각 INDEX에 등록한다. 하위 폴더 내 파일도 예외 없다. INDEX가 "프로젝트에 어떤 지식 문서가 존재하는가"의 single source of truth여야 한다.

## 경계 (하지 말 것)

데이터 안전 관련 항목(`main` 직접 커밋, `_docs/` 대폭 재편)의 근거 원리는 [core-constraints.md 원본 보호 원칙](_docs/_architecture/core-constraints.md)이다.

- `main` 브랜치에 직접 커밋하지 않는다. 브랜치 전략은 [AGENTS/branch-strategy.md](AGENTS/branch-strategy.md) 참조.
- `_docs/` 파일을 사람 확인 없이 삭제하거나 대폭 재편하지 않는다.
- 코드나 문서 영역에 공용 태그(`[to:@AGENT: ...]`)가 달려 있으면 그 내용을 하나의 프롬프트와 동등하게 취급하여 먼저 읽고 반영한다. 형식은 [AGENTS/agent-tag-format.md](AGENTS/agent-tag-format.md) 참조. 태그가 없다고 해당 영역을 임의로 수정해도 된다는 뜻은 아니다.
- Git 커밋·푸시를 명시적 요청 없이 수행하지 않는다. 요청된 범위만 정확히 수행한다: "커밋"을 요청받으면 커밋까지, "푸시"를 요청받으면 푸시까지. 범위를 임의로 확장하거나 축소하지 않는다. 푸시 전에 사용자가 커밋 내용을 확인할 수 있어야 한다.
- PR에 달린 인라인 리뷰 코멘트(사용자·다른 개발자·자동 리뷰 봇)에 응답할 때는 **그 코멘트의 스레드 reply**로 단다. 호출 형태·정정 절차·PR 본문 형식·속성 할당·명시적 멘션·AI 시그니처 등 PR 운영 전반 규약은 [AGENTS/unit-task-workflow.md "PR 운영"](AGENTS/unit-task-workflow.md#pr-운영) 참조.

## 응답 언어

- 문서 작성: 한국어 기본, 평어체(담백한 서술형).
- 코드 주석 및 in-source 문서(kotlindoc, javadoc 등): 한국어.
- 에러 메시지: 첫 대표 문장은 영문, 상세 설명은 한국어.
- 대화: 한국어, 존댓말.
- 금지 표현: 비속어·욕설·모욕·차별적 표현 사용 금지(응답·문서·커밋 메시지·PR 본문·댓글 등). 사용자가 사용하더라도 AI는 정중한 톤을 유지하고 어휘를 모방하지 않는다. 인용·정정 대상 명시 등 필요시에만 따옴표로 인용 표시.

## 필수 참조 문서

| 문서 | 용도 | 언제 참조하는가 |
|------|------|----------------|
| [_docs/_worklog/STATUS.md](_docs/_worklog/STATUS.md) | 현재 상태 + 다음 작업 포인터 | 매 세션 시작 시 (최우선) |
| [_docs/_worklog/TASK_TREE.md](_docs/_worklog/TASK_TREE.md) | 작업 계층 트리 | 작업 착수 전, 진행 상황 파악 시 |
| [_docs/_worklog/DONE.md](_docs/_worklog/DONE.md) | 완료 이력 (축약) | 맥락 파악 필요 시 |
| [_docs/_ontology/INDEX.md](_docs/_ontology/INDEX.md) | 온톨로지 색인 | 도메인 클래스 설계 전, 용어 혼동 시 |
| [_docs/_knowledge/INDEX.md](_docs/_knowledge/INDEX.md) | 지식 색인 | 새 세션 시작 시, 문제 해결 시 |
| [_docs/_strategy/INDEX.md](_docs/_strategy/INDEX.md) | 전략 색인 | 새 세션 시작 시, 문제 해결 시 |
| [AGENTS/INDEX.md](AGENTS/INDEX.md) | 에이전트 지침 색인 | 에이전트 운영 방식 확인 시 |
| [_docs/_architecture/INDEX.md](_docs/_architecture/INDEX.md) | 설계 명세 색인 | 새 클래스/모듈 생성 시 |
| [_docs/_architecture/conventions.md](_docs/_architecture/conventions.md) | 네이밍·작성 규약·구조 규약 SSOT | 모든 문서·코드 작성 시 |
| [AGENTS/unit-task-workflow.md](AGENTS/unit-task-workflow.md) | 단위 작업 운영 흐름 SSOT | 단위 작업 시작·종료 시 |
| [_reference/INDEX.md](_reference/INDEX.md) | raw 자료 인벤토리 + 처리 상태 | 매 세션 시작 시 |

## 핵심 제약

→ [_docs/_architecture/core-constraints.md](_docs/_architecture/core-constraints.md) 참조.
