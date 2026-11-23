---
date created: 2026-07-26
date modified: 2026-11-23
tags: [agents, 워크스페이스, 운영, epistemic-rules]
---

# 세션 경계의 진입, 재진입과 격리

새 세션을 시작할 때, 세션이 끊긴 뒤 자기 작업을 이어받을 때, 다른 세션의 산출물을 마주쳤을 때의 규약. 세션 경계에서 발견한 산출물이 내 것이면 복원하고 남의 것이면 건드리지 않는다는 한 판단의 양면이다. 단위 작업 1건의 진입-진행-종료 절차는 [unit-task-workflow.md](unit-task-workflow.md)가 다룬다.

## 세션 시작

새 세션은 아래를 순서대로 밟는다. 인스턴스 고유 절차는 이 표준 절차를 완주한 뒤 이어 따른다 (ref: [instance-specialization.md](instance-specialization.md) "특수화 방식").

1. 워크스페이스 루트에서 세션 시작 요약 `python3 AGENTS/epistemic-rules/tools/session_brief.py .`를 실행한다(윈도우는 `python` 또는 `py`. see: [tools.md](tools.md) "세션 시작 요약 스크립트"). 첫 줄이 `[session-brief]`인 요약이 이미 컨텍스트에 있으면 다시 실행하지 않는다. 훅을 지원하는 도구는 세션 시작 때 이 스크립트를 자동으로 실행한다 (see: [tool-environment.md](tool-environment.md) "세션 시작 훅"). 요약은 열린 작업 워크트리, `git fetch --prune origin` 뒤 main에 머지되지 않은 로컬과 `origin`의 작업 브랜치와 각 브랜치가 TASK_TREE에 더한 진행 노드, main의 최근 머지 5건이 바꾼 문서와 문서마다 `description`(없으면 제목) 한 줄, 아래 2-5단계의 기계 결과를 담는다. 머지 건수는 기간이 아니라 건수로 잡아 쉬었다가 돌아온 세션에서도 직전 작업이 나오며, 인스턴스가 작업 빈도에 맞게 `--merges`로 조정할 수 있다. 조정하면 고유 절차의 실행 명령과 세션 시작 훅의 명령에 같은 값을 준다 (see: [session-start-hook.md](tool-environment/session-start-hook.md)).
   - 이어서 [worklog/TASK_TREE.md](../../worklog/TASK_TREE.md)(진행 중, 다음 할 일)와 [worklog/STATUS.md](../../worklog/STATUS.md)(감사 시각)를 읽는다.
   - 최근 머지가 바꾼 문서는 요약의 한 줄을 보고 지금 작업과 겹치는 문서만 연다.
   - 머지 전 브랜치의 착수 등재는 주 워크트리의 작업 트리에 보이지 않으므로 요약의 진행 노드로 파악해 중복 착수하지 않는다. 진행 노드 없이 나온 브랜치는 기존 노드를 닫기만 하는 브랜치일 수 있으므로 그 첫 커밋을 본다 (ref: [procedure-shrinking.md](unit-task-workflow/procedure-shrinking.md) "노드를 닫기만 하는 변경은 첫 마크 커밋이 시작점을 겸한다"). 그 노드의 작업을 이 세션이 이어받으면 아래 "끊김, 재진입"을, 아니면 "다른 세션 작업과의 격리"를 따른다.
2. 요약의 형식 감사 결과에 위반이 있으면 [working-principles.md](working-principles.md) "1. 넘겨짚지 않는다"의 감사 결과 처리대로 정리한다. 요약에 다 담기지 않은 위반과 경고는 `python3 AGENTS/epistemic-rules/tools/audit.py .`로 직접 본다 (see: [tools.md](tools.md) "기계 감사 스크립트").
3. 요약의 의미 감사 트리거 판정이 충족이면 착수 전 epistemic-auditor로 의미 감사를 받고 STATUS를 갱신한다 (판정 기준과 기준점 커밋은 [trigger-baseline.md](agent-roles/epistemic-auditor/trigger-baseline.md)).
4. 요약의 "환경 갱신" 절이 미적용 갱신을 알리면 [workspace-setup.md](workspace-setup.md) "갱신 흐름"을 따른다.
5. 요약의 `reference/` 미처리 항목(`미등록`, `처리 대기`)과 형식 감사가 `reference/INDEX.yaml`에 낸 경고를 확인한다. 미처리 자료는 [ingest-workflow.md](ingest-workflow.md)로 진행한다.
6. 읽기 목록 [when-to-read.md](when-to-read.md)를 열어 작업 범위의 규범과 `epistemic-structure/` 문서를 읽고 기존 결정과 충돌이 없는지 확인한다. 세션 중 새 정보가 들어오면 [ingest-workflow.md](ingest-workflow.md)를 따른다.

## 끊김, 재진입

세션이 끊긴 뒤 재진입할 때:

- TASK_TREE의 진행 중(`[/]`) 노드와 브랜치 속성이 작업 컨텍스트의 1차 입구다. 브랜치 속성이 어느 작업 브랜치와 워크트리로 진입할지를 가리킨다. 그 워크트리가 없으면(다른 머신에서 재진입하는 경우 등) [branch-strategy.md](branch-strategy.md) "작업 공간"대로 기존 브랜치의 워크트리를 그 경로에 다시 만든다.
- git log와 작업 브랜치 위치로 어디까지 진행됐는지 확인한다. 시작점 커밋 이후 커밋들을 훑어 진행 양상을 복원한다.
- 작업 브랜치에 열린 PR이 있으면(`gh pr list --head <branch>`) 그 PR의 리뷰 상태가 현재 단계이므로 [active-review-loop.md](pr-workflow/active-review-loop.md)의 능동 리뷰 확인 흐름으로 돌아간다.
- 마지막 커밋과 TASK_TREE 노드 상태가 어긋나면 그 사이에서 끊긴 것이다. 정정한 뒤 이어 간다.

## 다른 세션 작업과의 격리

본 세션이 발견한 다른 세션의 산출물(작업 브랜치, 워크트리, 열린 PR, 이슈 등)은 본 세션의 작업 대상이 아니면 건드리지 않는다. 머지, 삭제, force-push, 브랜치 정리는 그 세션 자체에서 처리하거나 사용자의 명시 지시가 있을 때만 한다 - 다른 세션의 컨텍스트를 모르는 상태의 자율 정리는 의도치 않은 작업 손실로 이어진다. 잔존 점검의 정리 대상은 본 세션이 만든 산출물에 한정한다.
