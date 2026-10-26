---
date created: 2026-10-23
date modified: 2026-10-25
tags: [agents, 워크스페이스, 운영, epistemic-rules]
---

# 머지 타입 분기

단위 작업 종료 흐름 4단계(main 머지)의 세부 절차다. 이 문서가 워크플로우 조립 지점이다. 전체 흐름은 [unit-task-workflow.md](../unit-task-workflow.md).

## 타입 결정

두 타입 중 하나로 진행한다. 기본은 PR 타입이며, 브랜치 관리자 타입(직접 머지)은 사용자가 PR 생략을 명시 허용, 지시한 경우에만이다 - "그냥 머지해", "메인 푸시 OK", "PR 생략"처럼 PR 단계 생략 의도가 드러나는 표현. routines, cron 자동 트리거는 PR 타입을 강제한다. 타입 결정이 모호하면 사용자에게 확인하고 AI 자율로 정하지 않는다. 본 절이 머지 타입 분기 규칙의 SSOT(single source of truth)이며, pr-workflow는 PR 타입으로 확정된 뒤 조립되는 모듈이다.

## PR 타입

[pr-workflow.md](../pr-workflow.md)를 조립한다(PR 생성, 검토 대응, 능동 확인, 머지, 브랜치 정리).

## 브랜치 관리자 타입

주 워크트리에서 `git merge <branch> --no-ff && git push origin main && git worktree remove <워크트리 경로> && git branch -d <branch>`. 브랜치는 워크트리를 지운 뒤에야 지워진다. 워크트리 제거가 거부되는 경우의 처리는 [../branch-strategy.md](../branch-strategy.md) "작업 공간"의 정리 항목을 따른다. `--no-ff`로 단위 작업 머지 커밋을 명시적으로 남긴다. 메시지는 `Merge <branch>: <요약>` 형식으로, 무엇을 왜 바꿨는지만 적는다 - 승인, 검토 통과 여부는 커밋 텍스트에 남기지 않는다(검토는 종료 흐름 "사용자 검토 통과" 단계의 상호작용으로 처리되는 절차이지 커밋에 기록할 상태가 아니다).

## 환경 안전망과 잔존 점검

- 환경 안전망이 main 푸시를 차단하면(일부 harness의 "main 직접 푸시 금지") 우회 편법을 자율로 쓰지 않는다. 차단 사실을 보고하고 처리 결정을 요청한다.
- 머지, 푸시, 브랜치 삭제 후 `git worktree list`(작업 워크트리 잔존)와 `git branch -a`(로컬/원격 브랜치 잔존, `git fetch --prune` 동반)를 확인한다. 잔존이 있으면 본 단위 작업의 후속으로 즉시 정리한다.
