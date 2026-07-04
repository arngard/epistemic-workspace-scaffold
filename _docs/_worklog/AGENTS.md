---
date created: 2026-07-04
date modified: 2026-07-04
tags: [worklog]
---

# 워크로그 디스크립터

> 단위 작업 흐름의 진입, 종료 시점에 갱신되는 운영 메타 영역 (cf. [AGENTS/unit-task-workflow.md](../../AGENTS/unit-task-workflow.md)). 완료 이력의 SSOT(single source of truth)는 git 이력이며, 이 폴더에 별도 이력 파일을 두지 않는다.
> 규범 폴더이므로 파일별 설명과 "언제 읽는가" 트리거를 명시한다. 각 파일의 갱신, 삭제 규칙은 해당 파일의 프리앰블이 SSOT다.

| 파일 | 설명 | 언제 읽는가 |
|------|------|-------------|
| [TASK_TREE.md](TASK_TREE.md) | 작업 계층 트리 (현재 상태 + 다음 작업 포인터) | 매 세션 시작 시 (최우선), 작업 착수 전 |
| [STATUS.md](STATUS.md) | 감사, 주기 작업 상태 레지스트리 | 매 세션 시작 시 |
