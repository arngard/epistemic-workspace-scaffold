---
date created: 2026-04-18
date modified: 2026-04-22
tags: [규칙, 문서관리]
---

# AI Agent 지침

> 이 파일은 모든 AI 도구(Claude, Kiro, Gemini, Copilot 등)가 이 프로젝트를 다룰 때의 기본 지침이다.
> 각 도구의 진입점 파일(CLAUDE.md, .kiro/, .gemini/ 등)은 이 파일을 가리킨다.

## 새 세션 시작 시 (필수)

1. 이 파일을 읽는다.
2. [_docs/_worklog/STATUS.md](_docs/_worklog/STATUS.md)를 읽고 현재 작업 상태와 다음 할 일을 파악한다.
3. 작업 범위에 해당하는 `_docs/` 문서를 읽는다 (아래 참조 테이블 기준).
4. 코드 생성/수정 전에는 관련 문서의 기존 결정과 충돌이 없는지 확인한다.

## 단위 작업 시작/종료 시 (필수)

### 작업 시작 시
- [_docs/_worklog/STATUS.md](_docs/_worklog/STATUS.md)를 갱신한다. 갱신 규칙은 문서 프리앰블 참조.

### 작업 종료 시
- [_docs/_worklog/STATUS.md](_docs/_worklog/STATUS.md)를 갱신한다. 갱신 규칙은 문서 프리앰블 참조.
- [_docs/_worklog/DONE.md](_docs/_worklog/DONE.md)에 완료 항목을 추가한다. 작성 규칙은 문서 프리앰블 참조.
- [_docs/_worklog/TASK_TREE.md](_docs/_worklog/TASK_TREE.md)를 갱신한다. 갱신 규칙은 문서 프리앰블 참조.
- 세션 중 새로운 관례, 규칙, 스타일이 합의되었으면 해당 내용이 AGENTS.md 또는 관련 영구 문서에 반영되었는지 확인한다.
- 긴 세션이거나 큰 변경이 있었던 세션의 종료 전에는 epistemic-auditor 서브에이전트를 호출해 문서 정합성 감사를 받는다. cf. [AGENTS/agent-roles.md](AGENTS/agent-roles.md).

### 새로운 사실/지식 발견 시
- [_docs/_knowledge/INDEX.md](_docs/_knowledge/INDEX.md)(지식 색인) 또는 [_docs/_strategy/INDEX.md](_docs/_strategy/INDEX.md)(전략 색인)을 읽고, 적절한 카테고리 문서에 기록한다.
- 해당 카테고리가 없으면 새 파일을 만들고 색인에 등록한다.
- 발견 일자와 출처를 반드시 명시한다.
- 설계 문서에 반영할 내용이면 해당 문서도 함께 업데이트한다.

## 문서 변경 시 (필수)

- 모듈/의존성 변경 → [_docs/_architecture/INDEX.md](_docs/_architecture/INDEX.md) 먼저 업데이트
- 네이밍/규약 변경 → [_docs/_architecture/conventions.md](_docs/_architecture/conventions.md) 먼저 업데이트
- 문서 간 정합성 확인을 항상 수행한다 (특히 cross-reference 되는 섹션 번호).
- 문서나 주석을 수정한 경우, "문서 작성 스타일" 섹션의 규칙을 위배하는 것이 없는지 검토한다.
- INDEX를 읽을 때 `date modified`가 오래된 문서가 눈에 띄면 점검한다. INDEX상 설명이 부적절해서 참조되지 않는 건지, 정말 불필요한 문서인지 판단하여 설명 개선 / 다른 문서로 통합 / 삭제 중 하나를 수행한다. 오래 방치된 문서는 유의미한 역할을 하지 못하고 있다는 신호다.
- **폴더·파일 이동 또는 리네임은 연쇄 갱신을 요구한다.** 구조 변경 한 번이 다수 문서의 링크·태그·INDEX 등록·상대경로에 수작업 파급을 유발한다. 반쪽만 정정된 상태로 남으면 이후 수습 비용이 급격히 커진다. 예방이 사후 수습보다 항상 싸다. 같은 커밋 안에서 다음을 일괄로 수행한다:
  1. 이동된 파일을 참조하는 모든 문서의 상대경로 갱신 (`grep -rn "구경로" _docs/ AGENTS/ *.md`로 전수 확인).
  2. front matter `tags`의 첫 항목이 새 소속 카테고리와 일치하는지 확인.
  3. 관련 INDEX.md의 등록 정보 갱신 (기존 링크 수정 또는 삭제, 새 위치에 재등록).
  4. 자매 폴더(`_strategy`/`_knowledge`/`_ontology`/`_architecture` 간) 일괄 작업이라면 한쪽만 반영하고 다른 쪽이 누락되지 않았는지 교차 확인.
  5. 개편 규모가 크면 종료 전 epistemic-auditor를 호출해 사후 문서 정합성 감사를 받는다. 체크리스트(예방)와 감사(치료)는 역할이 다르므로 둘 다 수행한다. cf. [AGENTS/agent-roles.md](AGENTS/agent-roles.md).

## 판단과 검증

- 자기 기억보다 실제 상태를 신뢰한다. 파일 내용·레포 설정·외부 시스템 상태 등을 기억만으로 단언하지 않는다. 마지막으로 확인한 뒤 시간이 지났거나 다른 에이전트·사용자의 개입이 있었을 가능성이 있으면 재확인한다. 도구 호출 한 번으로 검증 가능한 것을 메모리 근거로 주장하지 않는다.
- 다른 에이전트의 결과와 내 기억이 어긋날 때는 자기 기억을 먼저 의심한다. 내 기억이 outdated일 가능성을 배제하기 전에 상대를 환각이라고 단정하지 않는다. 상대의 구체적 증거(커밋 해시, 파일 경로, diff 등)를 직접 재현해 본 뒤 판정한다.

## 문서 작성 스타일

- 과장된 수사를 배제하고 평서문의 담백하고 정확한 표현을 사용한다.
- 볼드·이탤릭·이모지 등 서식/기호 강조는 강한 경고/금지/주의 사항에만 사용한다. 나열·제목·항목 라벨·일반 개념어·장식에는 쓰지 않는다. 남발하면 진짜 강조가 필요할 때의 진정성을 잃는다.
- 문서 간 참조는 마크다운 링크로 작성한다. `[표시 텍스트](상대경로)` 형식.
- 참고 자료/출처 표기는 `cf.` (비교/참고)와 `ref.` (출처/근거)를 사용한다.
- 약어가 처음 등장할 때는 풀어쓴 원문을 병기한다. 예: `SSOT(single source of truth)`, `ADR(Architecture Decision Record)`. 원문이 외국어이고 한국어 설명이 추가로 필요하면 세미콜론으로 덧붙인다. 예: `KAI(Korea Aerospace Industries; 한국항공우주산업)`. 이후 같은 문서 내에서는 약어만 사용한다.
- 모든 .md 파일에 YAML front matter를 붙인다. 필수 필드: `date created`, `date modified`, `tags`. 날짜 형식은 `yyyy-MM-dd`. `tags`의 첫 항목은 소속 카테고리.
- 파일명 자체가 문서의 시스템적 역할을 지시하는 고정 규격 문서(README, AGENTS, INDEX, STATUS, DONE, TASK_TREE 등)는, 그 파일명과 같은 의미의 단어가 태그에 중복되는 경우 해당 태그를 생략한다. 파일명이 콘텐츠 주제를 나타내는 일반 문서는 제목이 바뀔 수 있으므로 생략하지 않는다.
- 도구 전용 설정 파일(`.claude/`, `.gemini/`, `.github/` 등 특정 AI 도구가 고정된 스키마로 읽는 파일)은 해당 도구의 스키마를 우선한다. 위 공통 필수 필드(`date created`, `date modified`, `tags`)를 이 파일들에 강제하지 않는다.
- **추측으로 문서를 채우지 않는다.** 논의되지 않은 내용을 확정된 것처럼 적지 않는다.
- 사실과 의견, 의견의 주체를 분명히 구분한다. 근거 있는 사실, 작성자 본인의 판단, 타인/외부의 판단은 서술 형태를 달리한다. 의견에는 주체를 명시한다 (예: "`@아릉`의 판단", "Klaviyo 팀의 설계", "AI 제안"). 의견을 사실인 양 서술하거나 주체를 흐리면 이후 결정의 근거 추적이 깨진다.
- 문서 내 예시 코드 블록은 서술만으로 전달하기 어려운 구조에만 사용한다. 정책이나 규칙은 서술로 충분하면 코드 블록을 두지 않는다. (이 규칙은 문서 안의 코드 블록에 한정되며, `_implementation/` 하위의 실제 구현 코드에는 적용되지 않는다.)
- **중복 금지.** 같은 사실/규칙/설명을 두 곳 이상에 적지 않는다. 한 사실은 하나의 SSOT 문서에만 두고 다른 문서는 링크로 연결한다.
- 이름과 식별자의 안정성을 염두에 둔다. 여러 문서에서 참조되는 이름·용어·식별자는 시간이 지나면 바뀔 수 있다. 바뀔 수 있는 것을 여러 문서에 박제하면 이후 대량 갱신 부채가 쌓인다. 새 용어를 도입할 때의 검증은 [_docs/_ontology/INDEX.md](_docs/_ontology/INDEX.md) "용어 도입 전 검증" 참조.
  - 계획 순서 식별자(Phase 1, Milestone 2 등)는 [_docs/_worklog/TASK_TREE.md](_docs/_worklog/TASK_TREE.md)와 프로젝트 개요 문서에만 두고, 나머지 문서에서는 "첫 출시"/"후속 확장"처럼 의미 단위 표현으로 참조한다. 순서는 재편될 수 있지만 의미 단위는 덜 변한다.
- 하나의 문서는 하나의 관심사를 다룬다. 두 개의 독립된 주제가 한 파일에 있으면 분량과 무관하게 분리한다.
- 분량 보조 지표: 한글 기준 2,000자 권장 / 3,000자 상한. 단, 위 "하나의 관심사" 원칙이 이 수치보다 앞선다 — 상한 이내여도 두 주제면 분할하고, 상한을 넘더라도 단일 주제로 응집되면 유지한다.
- INDEX 문서는 등록 항목 증가로 자연히 길어질 수 있어 위 분량 상한을 적용하지 않는다. 다만 색인 기능(빠른 탐색)이 떨어질 만큼 길어지면 AI는 자동 분할하지 말고, 하위 카테고리 분화 등의 재편성을 사람에게 제안한다.

## 색인(INDEX) 사용 규칙

모든 INDEX 문서에 공통으로 적용된다. 각 INDEX는 자기 영역 고유의 규칙만 별도로 추가한다.

- 읽기: 색인만 먼저 읽고, 필요한 문서만 선택적으로 연다. 전부 읽지 않는다.
- 쓰기: 내용에 맞는 기존 문서에 추가하거나, 구체적인 제목의 새 파일을 만들고 색인에 등록한다.
- 제목 규칙: 파일명은 내용을 특정할 수 있어야 한다. 포괄적 이름은 금지.
- `_docs/_ontology/`, `_docs/_knowledge/`, `_docs/_strategy/`, `_docs/_architecture/` 하위의 모든 마크다운 파일은 각 INDEX에 등록한다. 하위 폴더 내 파일도 예외 없다. INDEX가 "프로젝트에 어떤 지식 문서가 존재하는가"의 single source of truth여야 한다.

## 경계 (하지 말 것)

- `main` 브랜치에 직접 커밋하지 않는다. 브랜치 전략은 [AGENTS/branch-strategy.md](AGENTS/branch-strategy.md) 참조.
- `_docs/` 파일을 사람 확인 없이 삭제하거나 대폭 재편하지 않는다.
- 코드나 문서 영역에 공용 태그(`[to:@AGENT: ...]`)가 달려 있으면 그 내용을 하나의 프롬프트와 동등하게 취급하여 먼저 읽고 반영한다. 형식은 [AGENTS/agent-tag-format.md](AGENTS/agent-tag-format.md) 참조. 태그가 없다고 해당 영역을 임의로 수정해도 된다는 뜻은 아니다.
- Git 커밋·푸시를 명시적 요청 없이 수행하지 않는다. 요청된 범위만 정확히 수행한다: "커밋"을 요청받으면 커밋까지, "푸시"를 요청받으면 푸시까지. 범위를 임의로 확장하거나 축소하지 않는다. 푸시 전에 사용자가 커밋 내용을 확인할 수 있어야 한다.

## 응답 언어

- 문서 작성: 한국어 기본, 평어체(담백한 서술형).
- 코드 주석 및 in-source 문서(kotlindoc, javadoc 등): 한국어.
- 에러 메시지: 첫 대표 문장은 영문, 상세 설명은 한국어.
- 대화: 한국어, 존댓말.

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
| [_docs/_architecture/conventions.md](_docs/_architecture/conventions.md) | 네이밍, 코딩 규약, 의존성 규칙 | 모든 코드 작성 시 |

## 핵심 제약

→ [_docs/_architecture/core-constraints.md](_docs/_architecture/core-constraints.md) 참조.
