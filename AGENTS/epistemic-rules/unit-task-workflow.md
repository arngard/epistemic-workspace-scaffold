---
date created: 2026-05-09
date modified: 2026-10-26
tags: [agents, 워크스페이스, 운영, epistemic-rules]
---

# 단위 작업 운영 흐름

단위 작업 하나를 진입-진행-종료로 수행하는 일반 프레임이다. 단위 작업이 무엇인가(의미적 분절, 표현과의 층위, 중첩, 프로젝션)와 워크플로우 조립은 [unit-task.md](unit-task.md), 토대 원칙은 [working-principles.md](working-principles.md) 참조. 본 문서는 그 프레임의 운영 절차를 다룬다. 세션 경계의 재진입과 격리는 [session-boundaries.md](session-boundaries.md).

자료 N건 묶음 ingest, 메타 결정이나 정책 변경, 큰 마이그레이션이나 구조 재편, 도메인 모듈 신설, 한 세션을 넘어갈 가능성이 큰 작업은 본 흐름을 그대로 밟는다. 그보다 작은 변경도 단위 작업이지만 절차를 축약할 수 있다 (sub: [unit-task-workflow/procedure-shrinking.md](unit-task-workflow/procedure-shrinking.md)). 모호하면 축약하지 않는 쪽이 안전하다 - 끊겼을 때 회복 비용이 작다.

## 진입 흐름

순서를 지킨다.

1. 작업 트리 점검, 노드 결정 + 관련 절차 문서 재독: [TASK_TREE.md](../../worklog/TASK_TREE.md)에서 어느 노드에 대한 작업인지 정한다(없으면 신설). 그 노드를 통째로 한 단위 작업으로 잡을지, 자식들을 별도 단위 작업으로 쪼갤지 결정한다 - 이 결정이 곧 브랜치 소유 노드를 정한다 (ref: [unit-task.md](unit-task.md) "프로젝션 - 표현과 절차의 평탄화"). 노드 결정 직후 본 단위 작업 영역에 해당하는 절차 문서(ingest-workflow, how-to-separate-docs-folders, document-units, writing-style, folder-structure, document-temporality, instance-specialization, 자식 도메인 절차 등)를 처음부터 다시 읽는다 - 자기 기억으로 세부 규약을 단언하다 소소한 위반이 누적되는 것을 막는 1차 가드레일이다. 변경 대상 문서를 이미 같은 단위에서 손대는 경우(예: writing-style을 고치는 작업)는 그 문서 재독이 면제된다.
2. 작업 브랜치와 워크트리 생성: `<type>/YYMMDD-<짧은-설명>` 브랜치를 그 브랜치 전용 워크트리와 함께 만든다. 단위 작업마다 격리된 커밋 라인과 작업 공간을 확보한다. 워크트리를 만드는 명령, 위치, 따라오지 않는 파일, 예외는 [branch-strategy.md](branch-strategy.md) "작업 공간"을 따른다.
3. 워크로그 등재: 해당 노드를 `[/]`로 표시하고 브랜치 속성에 작업 브랜치와 그 워크트리 경로를 `브랜치: <브랜치> (워크트리: <경로>)` 형태로 한 줄에 기재한다. 경로는 주 워크트리 기준 상대 경로로 적어 머신이 바뀌어도 그대로 쓰이게 한다. 다음 세션 진입자가 컨텍스트를 복원하는 1차 입구다.
4. 시작점 커밋: 워크로그 등재를 담은 커밋으로 시작점을 마킹한다(`--allow-empty`라도).

## 진행 흐름

중위 노드는 재귀적으로 진행한다 - 자식 단위 작업을 우선순위 순으로 수행하고(각 자식은 자기 워크플로우를 다시 밟는다), 자식 사이사이에 트리를 갱신한다(ref: [unit-task.md](unit-task.md) "워크플로우"). 리프의 구체 작업이 특정 유형이면 그 워크플로우가 조립된다 - 새 정보 유입은 [ingest-workflow.md](ingest-workflow.md).

- 처리 단위(자료 1건, 하위 단계 1개) 완료마다 커밋한다 (ref: [unit-task.md](unit-task.md) "정형 대응"). 여러 건을 한 커밋에 묶으면 되돌릴 단위가 사라져 히스토리가 달라지므로 허용되지 않는다.
- 완료한 처리 단위 노드를 `[x]`로, 새로 드러난 항목은 즉시 추가.
- 컨텍스트 압축이 임박하면 진행 중 노드와 상태 속성을 다음 세션이 이어받을 형태로 다듬는다.
- 작업 브랜치는 자유롭게 푸시해도 되고 안 해도 된다. 세션이 끊길 가능성이 있으면 푸시가 안전.

## 종료 흐름

브랜치를 소유한 노드(진입에서 한 단위 작업으로 정한 그 노드 - 대개 메인 머지 1회 = 브랜치 1개)의 종료에서 아래를 밟는다. 그 아래 자식들의 종료는 트리 마크 + 커밋까지이지 별도 머지가 아니다.

1. 마무리 커밋: 미캡처 보강, 학습 사항 반영, TASK_TREE 완료 마크와 브랜치 속성 제거를 담는다. 이 시점의 워크로그는 main 머지된 이후의 상태를 미리 기록한다 - 머지 직후 그대로 정합이 되어 별도 정정 커밋이 안 생기게.
2. TASK_TREE 정리: 완료 마크(`[x]`/`[-]`)가 커밋에 남은 뒤에만 노드를 삭제한다(마크 커밋과 삭제 커밋 분리). 무엇을 언제 삭제하는가는 [task-tree.md](../../worklog/AGENTS/epistemic-rules/task-tree.md)의 삭제 규칙을 따른다.
3. 사용자 검토 통과: 변경 요약(브랜치명, 변경 파일 수, 핵심 변경 + 짚을 점)을 보고하고 결정 신호를 받는다. AI 자율 판단으로 머지하지 않는다.
   - 결정 갈래: OK 머지 / 추가 정정(명시받아 커밋 후 본 단계 반복) / 롤백(브랜치 폐기).
   - 시그널은 명시적이어야 한다. 침묵이나 다음 작업 시작을 OK로 추론하지 않는다. 채팅 내 명시 승인("머지해")과 PR Approve가 등가다.
   - 단발 작업, 오탈자처럼 절차를 축약해 처리하는 작은 변경은 본 단계도 면제한다 (sub: [procedure-shrinking.md](unit-task-workflow/procedure-shrinking.md)).
4. main 머지 - 타입 분기: PR 타입과 브랜치 관리자 타입(직접 머지) 중 하나로 진행한다. 타입 결정 규칙, 두 타입의 절차, 환경 안전망, 잔존 점검은 [merge-types.md](unit-task-workflow/merge-types.md)를 따른다.
5. 서브모듈 커밋 포인트 재귀 정합화 (해당 시): 본 레포가 다른 레포의 서브모듈이면 [submodule-pointer-sync.md](submodule-pointer-sync.md)를 조립한다.

## 하위 문서

분량이 크고 자체 완결적인 세부 절차는 `unit-task-workflow/` 아래 하위 문서로 둔다.

- [procedure-shrinking.md](unit-task-workflow/procedure-shrinking.md): 절차 축약의 조건, 착수 시점 판정, 브랜치와 등재의 형태 일관성. 작은 변경에 착수하며 절차를 줄일지 정할 때 읽는다.
- [merge-types.md](unit-task-workflow/merge-types.md): main 머지의 타입 결정, PR 타입과 브랜치 관리자 타입의 절차, 환경 안전망과 잔존 점검. 단위 작업 종료에서 main에 머지할 때 읽는다.
