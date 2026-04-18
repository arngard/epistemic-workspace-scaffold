---
date created: 2026-04-18
date modified: 2026-04-18
tags: [에이전트, 규칙, 문서관리]
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

## 문서 작성 스타일

- 과장된 수사를 배제하고 평서문의 담백하고 정확한 표현을 사용한다.
- 볼드는 강한 경고/금지/주의 사항에만 사용한다.
- 문서 간 참조는 마크다운 링크로 작성한다. `[표시 텍스트](상대경로)` 형식.
- 참고 자료/출처 표기는 `cf.` (비교/참고)와 `ref.` (출처/근거)를 사용한다.
- 모든 .md 파일에 YAML front matter를 붙인다. 필수 필드: `date created`, `date modified`, `tags`. 날짜 형식은 `yyyy-MM-dd`. `tags`의 첫 항목은 소속 카테고리.
- **추측으로 문서를 채우지 않는다.** 논의되지 않은 내용을 확정된 것처럼 적지 않는다.
- **예시 코드는 서술만으로 전달하기 어려운 구조에만 사용한다.** 정책이나 규칙은 서술로 충분하면 코드 블록을 두지 않는다.
- **중복 금지.** 같은 사실/규칙/설명을 두 곳 이상에 적지 않는다. 한 사실은 한 캐논 문서에만 두고 다른 문서는 링크로 연결한다.
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
- 코드나 문서 영역에 공용 태그(`[to:@AGENT: ...]`)가 달려 있으면 그 내용을 먼저 읽고 지시에 따른다. 형식은 [AGENTS/agent-tag-format.md](AGENTS/agent-tag-format.md) 참조. 태그가 없다고 해당 영역을 임의로 수정해도 된다는 뜻은 아니다.

## 응답 언어

- 문서 작성 및 코드 주석: 한국어 기본. 에러 메시지와 public API 문서는 영문.
- 대화: 한국어

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
| [_docs/_strategy/project-overview.md](_docs/_strategy/project-overview.md) | 프로젝트 목표, 기능 범위 | 새 feature 작업 시작 전 |
| [_docs/_architecture/INDEX.md](_docs/_architecture/INDEX.md) | 설계 명세 색인 | 새 클래스/모듈 생성 시 |
| [_docs/_architecture/conventions.md](_docs/_architecture/conventions.md) | 네이밍, 코딩 규약, 의존성 규칙 | 모든 코드 작성 시 |

## 핵심 제약

→ [_docs/_architecture/core-constraints.md](_docs/_architecture/core-constraints.md) 참조.
