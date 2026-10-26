---
date created: 2026-07-26
date modified: 2026-10-25
tags: [agents, 워크스페이스, 운영, epistemic-rules]
---

# 세션 경계의 진입, 재진입과 격리

새 세션을 시작할 때, 세션이 끊긴 뒤 자기 작업을 이어받을 때, 다른 세션의 산출물을 마주쳤을 때의 규약. 세션 경계에서 발견한 산출물이 내 것이면 복원하고 남의 것이면 건드리지 않는다는 한 판단의 양면이다. 단위 작업 1건의 진입-진행-종료 절차 자체는 [unit-task-workflow.md](unit-task-workflow.md).

## 세션 시작

새 세션은 아래를 순서대로 밟는다. 인스턴스 고유 절차는 이 표준 절차를 완주한 뒤 이어 따른다 (ref: [instance-specialization.md](instance-specialization.md) "특수화 방식").

1. [worklog/TASK_TREE.md](../../worklog/TASK_TREE.md)(진행 중, 다음 할 일)와 [worklog/STATUS.md](../../worklog/STATUS.md)(감사 시각)를 읽고, main의 최근 머지 5건이 바꾼 문서와 그 문서들이 링크하는 문서(1단계 이웃)를 훑어 직전 작업을 상기한다. 변경 문서 목록은 `git -c core.quotePath=false log --first-parent -m -n 5 --name-only --format="%h %s" main -- '*.md'`로 본다. 기간이 아니라 머지 건수로 잡아 쉬었다가 돌아온 세션에서도 직전 작업이 나온다. 머지 건수는 인스턴스가 작업 빈도에 맞게 고유 절차에서 조정할 수 있다.
2. 형식 감사 `python3 AGENTS/epistemic-rules/tools/audit.py .`를 실행하고, 보고된 위반은 정리하거나 사용자에게 짚는다 (윈도우는 `python` 또는 `py`. see: [tool-environment.md](tool-environment.md)).
3. 의미 감사 트리거를 `python3 AGENTS/epistemic-rules/tools/check_semantic_audit.py .`(윈도우는 위와 같다)로 판정하고, 충족이면 착수 전 epistemic-auditor로 의미 감사를 받고 STATUS를 갱신한다 (판정 기준과 기준점 커밋은 [agent-roles/epistemic-auditor.md](agent-roles/epistemic-auditor.md) "호출 시점").
4. [reference/AGENTS.md](../../reference/AGENTS.md)를 읽고 실제 내용과 대조한다. 미처리 자료는 [ingest-workflow.md](ingest-workflow.md)로 진행한다.
5. 작업 범위의 `epistemic-structure/` 문서([epistemic-rules.md](../epistemic-rules.md) "이럴 때 읽는다")를 읽고 기존 결정과 충돌이 없는지 확인한다. 세션 중 새 정보가 들어오면 [ingest-workflow.md](ingest-workflow.md)를 따른다.

## 끊김, 재진입

세션이 끊긴 뒤 재진입할 때:

- TASK_TREE의 진행 중(`[/]`) 노드와 브랜치 속성이 작업 컨텍스트의 1차 입구. 브랜치 속성이 어느 작업 브랜치와 워크트리로 진입할지를 가리킨다. 그 워크트리가 없으면(다른 머신에서 재진입하는 경우 등) [branch-strategy.md](branch-strategy.md) "작업 공간"대로 기존 브랜치의 워크트리를 그 경로에 다시 만든다.
- git log + 작업 브랜치 위치로 어디까지 진행됐는지 확인. 시작점 커밋 이후 커밋들을 훑어 진행 양상 복원.
- 작업 브랜치에 열린 PR이 있으면(`gh pr list --head <branch>`) 그 PR의 리뷰 상태가 현재 단계 - [active-review-loop.md](pr-workflow/active-review-loop.md)의 능동 리뷰 확인 흐름으로 복귀.
- 마지막 커밋과 TASK_TREE 노드 상태가 어긋나면 그 사이에 끊김이 있던 것 - 정정 후 이어간다.

## 다른 세션 작업과의 격리

본 세션이 발견한 다른 세션의 산출물(작업 브랜치, 워크트리, 열린 PR, 이슈 등)은 본 세션의 작업 대상이 아니면 건드리지 않는다. 머지, 삭제, force-push, 브랜치 정리는 그 세션 자체에서 처리하거나 사용자의 명시 지시가 있을 때만 한다 - 다른 세션의 컨텍스트를 모르는 상태의 자율 정리는 의도치 않은 작업 손실로 이어진다. 잔존 점검의 정리 대상은 본 세션이 만든 산출물에 한정한다.
