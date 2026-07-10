---
name: unit-task-finish
description: 단위 작업을 마무리할 때 사용한다. 마무리 커밋, 워크로그 이력화, 사용자 검토 요청, main 머지, PR 생성과 리뷰 대응 시점에 트리거된다.
---

# 단위 작업 종료

이 스킬은 절차를 로드하는 포인터다. 절차 본체(SSOT(single source of truth))는 [AGENTS/unit-task-workflow.md](../../../AGENTS/unit-task-workflow.md).

1. 위 SSOT 문서의 "종료 흐름"을 지금 읽는다. 기억으로 단언하지 않는다.
2. 종료 흐름의 각 단계를 순서대로 적용한다. 사용자 검토 통과 없이 머지하지 않는다.
3. 풀리퀘 타입으로 진행하면 pr-create 스킬을 조립한다. 생성 후 리뷰, 체크, 충돌 대응은 pr-respond 스킬.
4. 본 레포가 다른 레포의 서브모듈이면 "서브모듈 커밋 포인트 재귀 정합화"까지가 한 단위다.
