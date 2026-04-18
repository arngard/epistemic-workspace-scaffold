---
date created: 2026-04-18
date modified: 2026-04-18
tags: [worklog, 작업트리]
---

# 작업 트리

> 작업의 계층 구조. 큰 작업이 어떤 하위 작업으로 구성되는지를 기록한다.
> 깊이 제한 없음. 깊이별 타입 구분 없음. 모든 노드가 동일한 "작업".
> "다음에 뭘 해야 하는가"는 이 트리에서 `[ ]` ready인 것 중 가장 앞에 있는 리프 노드.
>
> 표기:
> - `[ ]` ready: 대기 중. 시작되지 않음.
> - `[/]` incomplete: 진행 중이거나 중단됨.
> - `[x]` done: 완료됨.
> - `[-]` canceled: 취소됨 또는 큰 난관으로 닫힘.
> - `-` (체크박스 없음): 설명 노드.
> - 들여쓰기로 부모-자식 관계 표현.
> - 같은 깊이의 형제 노드는 위상 정렬(topological order): 의존성상 먼저 해야 하는 것이 앞.
>
> 갱신 규칙:
> - 작업 종료 시: 완료 항목을 `[x]`로 전환하고, 새로 드러난 항목을 추가한다. 위상 정렬을 유지한다.
> - 설명 노드는 최소한으로 유지한다. 해당 작업에 문서가 있으면 cf 링크만 남기고 설명은 문서에 둔다.
> - 완료된 항목의 설명 노드는 제거한다.

- [/] 워크스페이스 초기 세팅
  - 이 단계의 모든 "선정/작성" 작업은 인간 입력 없이 채울 수 없다. AI는 각 작업 전에 필요한 정보를 인간에게 인터뷰하여 확보한다. 추측으로 채우지 않는다. cf. [AGENTS.md](../../AGENTS.md) "문서 작성 스타일".
  - [ ] 워크스페이스 폴더 이름을 프로젝트에 맞게 변경
    - AI는 워크스페이스 부모 디렉토리를 직접 리네임할 수 없다 (현재 작업 디렉토리가 바뀌어 세션 상태가 깨짐). 인간에게 이름을 받은 뒤, 인간이 터미널에서 직접 리네임하고 에디터/세션을 재시작하도록 안내한다. 이미 원하는 이름으로 되어 있으면 이 작업을 `[x]`로 전환하고 다음으로 진행한다.
  - [ ] 모든 `.md` 파일의 `date created` / `date modified`를 오늘 날짜로 일괄 업데이트
    - 스캐폴드에는 생성 시점의 날짜가 박혀 있다. 복제 직후 전체를 현재 날짜로 갱신한다.
  - [ ] 이 워크스페이스의 유일한 목표 선정
    - [_docs/_knowledge/project-overview.md](../_knowledge/project-overview.md)의 "프로젝트 목표" 섹션을 작성한다.
  - [ ] 보조적 목표 선정
    - [_docs/_knowledge/project-overview.md](../_knowledge/project-overview.md)의 나머지 섹션(핵심 결정사항, 첫 출시 핵심 목표/스펙, 향후 확장, 대상 고객/사용자)을 작성한다.
    - 작성 완료 후 문서 상단의 `⚠️ 스캐폴드 상태` 주의문을 삭제한다.
  - [ ] 도메인 온톨로지 정의
    - 의미가 갈릴 수 있는 핵심 용어를 식별하고 [_docs/_ontology/](../_ontology/INDEX.md)에 정의한다.
    - 튜토리얼용 `sample-term.md`를 삭제하고 실제 용어 정의 파일로 교체한 뒤 INDEX를 갱신한다.
  - [ ] 핵심 제약 목록 작성
    - [_docs/_architecture/core-constraints.md](../_architecture/core-constraints.md)의 "제약 목록" 섹션을 작성한다.
    - 각 제약은 상세 문서와 링크로 연결한다. 작성 완료 후 문서 상단의 `⚠️ 스캐폴드 상태` 주의문을 삭제한다.
  - [ ] 코딩 규약 확장
    - [_docs/_architecture/conventions.md](../_architecture/conventions.md)에 언어/빌드, 패키지 구조, 네이밍, 가시성, 의존성, 테스트 등 프로젝트 고유 규약을 추가한다.
    - 작성 완료 후 문서 상단의 `⚠️ 스캐폴드 상태` 주의문을 삭제한다.
  - [ ] 남은 튜토리얼 샘플 제거
    - [_docs/_knowledge/sample-fact.md](../_knowledge/sample-fact.md), [_docs/_architecture/sample-spec.md](../_architecture/sample-spec.md), [_docs/_strategy/sample-decision.md](../_strategy/sample-decision.md)를 실제 문서로 교체하거나 삭제하고 각 INDEX를 갱신한다.
  - [ ] 구현 프로젝트 등록
    - 실제 소스 코드 프로젝트를 [_implementation/](../../_implementation/INDEX.md)에 추가하고 INDEX의 표에 등록한다.
