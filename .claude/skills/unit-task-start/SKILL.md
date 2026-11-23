---
name: unit-task-start
description: 단위 작업(자료 묶음 ingest, 메타 결정이나 정책 변경, 마이그레이션, 모듈 신설, 여러 세션에 걸칠 가능성이 있는 작업)을 시작할 때 사용한다. 작업 착수, 브랜치 생성, 워크로그 등재 전에 트리거된다. main 같은 공용 브랜치에 반영하는 변경은 한 줄 수정이라도 이 스킬을 따른다.
---

# 단위 작업 진입

이 스킬은 절차를 로드하는 포인터다. 절차 본체(SSOT(single source of truth; 단일 진실 공급원))는 [AGENTS/epistemic-rules/unit-task-workflow.md](../../../AGENTS/epistemic-rules/unit-task-workflow.md).

1. 위 SSOT 문서의 "진입 흐름"과 [AGENTS/epistemic-rules/unit-task.md](../../../AGENTS/epistemic-rules/unit-task.md) "단위 작업"을 지금 읽는다. 기억으로 단언하지 않는다.
2. 진입 흐름의 각 단계(작업 트리 노드 결정과 관련 절차 문서 재독, 작업 브랜치와 워크트리 생성, 워크로그 등재, 시작점 커밋)를 순서대로 적용한다. 작업 트리의 기존 노드를 닫기만 하는 변경이면 워크로그 등재와 시작점 커밋 대신 그 노드의 마크 커밋을 첫 커밋으로 한다(see: [procedure-shrinking.md](../../../AGENTS/epistemic-rules/unit-task-workflow/procedure-shrinking.md) "노드를 닫기만 하는 변경은 첫 마크 커밋이 시작점을 겸한다").
3. 작업 중에는 같은 문서의 "진행 흐름"을 따른다.
