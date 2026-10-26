---
date created: 2026-04-18
date modified: 2026-10-26
tags: [worklog]
---

# 작업 트리

> 작업의 계층 구조와 다음 작업 포인터. 노드 유형, 표기, 갱신 규칙, 삭제 규칙은 [task-tree.md](AGENTS/epistemic-rules/task-tree.md).

- [ ] 워크스페이스 초기 세팅
  - 설명: 이 단계의 모든 "선정/작성" 작업은 인간 입력 없이 채울 수 없다. AI는 각 작업 전에 필요한 정보를 인간에게 인터뷰하여 확보한다. 추측으로 채우지 않는다. ref: [epistemic-rules.md](../AGENTS/epistemic-rules.md) "비협상 게이트".
  - [ ] 상류 연결과 채택 방식 기록
    - 설명: 스캐폴드 이력을 받았다면 원본을 `upstream` 원격으로 연결한다. 고른 방식과 이유를 [epistemic-structure/strategy/](../epistemic-structure/strategy/AGENTS.md)에 남긴다. 날짜 처리는 고른 방식에 따라 다르다.
  - [ ] 워크스페이스 폴더 이름을 프로젝트에 맞게 변경
    - 설명: AI는 워크스페이스 부모 디렉토리를 직접 리네임할 수 없다 (현재 작업 디렉토리가 바뀌어 세션 상태가 깨짐). 인간에게 이름을 받은 뒤, 인간이 터미널에서 직접 리네임하고 에디터/세션을 재시작하도록 안내한다. 이미 원하는 이름으로 되어 있으면 이 작업을 `[x]`로 전환하고 다음으로 진행한다.
  - [ ] 문서 날짜 처리
    - 설명: 상류와 연결했다면 날짜를 바꾸지 않는다(바꾸면 상류 머지마다 충돌한다). 이력 없이 가져왔다면 `date created`를 시작일로 갱신할 수 있다. `date modified`는 내용을 바꿀 때만 갱신한다.
  - [ ] 워크스페이스 정체 특수화
    - 설명: [AGENTS.md](../AGENTS.md) "이 워크스페이스의 정체" 절을 도메인 정체성으로 특수화한다. 그 밖의 계승 자산은 [AGENTS/epistemic-rules/instance-specialization.md](../AGENTS/epistemic-rules/instance-specialization.md)를 따른다.
  - [ ] README와 LICENSE 정리
    - 설명: 스캐폴드 소개문인 README.md, README.en.md를 이 워크스페이스의 소개로 교체하고(상류를 받으면 충돌 유의), LICENSE를 정한다.
  - [ ] 감사 주기 값 검토
    - 설명: [STATUS.md](STATUS.md)의 주기 조건([status-registry.md](AGENTS/epistemic-rules/status-registry.md) "주기 조건")이 작업 빈도에 맞는지 검토한다. 바꿀 값은 [AGENTS.md](AGENTS.md)의 덮어쓰기 표에 둔다.
  - [ ] 프로젝트 수준 상위 결정 기록
    - 설명: 프로젝트 목표, 첫 출시 핵심 목표와 스펙, 향후 확장, 대상 고객과 사용자 등 큰 결정을 [epistemic-structure/strategy/](../epistemic-structure/strategy/AGENTS.md) 아래 `why-*.md` 문서들로 분리 작성한다. 샘플 `project-overview.md`는 참고 후 삭제하거나 실제 내용으로 교체한다.
  - [ ] 도메인 온톨로지 정의
    - 설명: 의미가 갈릴 수 있는 핵심 용어를 식별하고 [epistemic-structure/ontology/](../epistemic-structure/ontology/AGENTS.md)에 정의한다. 튜토리얼용 `sample-term.md`를 삭제하고 실제 용어 정의 파일로 교체한다.
  - [ ] 핵심 제약 목록 작성
    - 설명: [epistemic-structure/architecture/core-constraints.md](../epistemic-structure/architecture/core-constraints.md)의 "제약 목록" 섹션을 작성한다. 각 제약은 상세 문서와 링크로 연결한다. 작성 완료 후 '제약 목록' 섹션의 `[주의] 스캐폴드 상태` 주의문을 삭제한다.
  - [ ] 코딩 규약 확장
    - 설명: [epistemic-structure/architecture/conventions.md](../epistemic-structure/architecture/conventions.md)에 언어/빌드, 패키지 구조, 네이밍, 가시성, 의존성, 테스트 등 프로젝트 고유 규약을 추가한다. 작성 완료 후 `[주의] 스캐폴드 상태` 주의문을 삭제한다.
  - [ ] 남은 튜토리얼 샘플 제거
    - 설명: [epistemic-structure/knowledge/sample-fact.md](../epistemic-structure/knowledge/sample-fact.md), [epistemic-structure/architecture/sample-spec.md](../epistemic-structure/architecture/sample-spec.md), [epistemic-structure/strategy/sample-decision.md](../epistemic-structure/strategy/sample-decision.md)를 실제 문서로 교체하거나 삭제한다.
  - [ ] 구현 프로젝트 등록
    - 설명: 실제 소스 코드 프로젝트를 [implementation/](../implementation/AGENTS.md)에 프로젝트별 폴더로 추가한다.
