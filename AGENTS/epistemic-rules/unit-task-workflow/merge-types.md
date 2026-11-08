---
date created: 2026-10-23
date modified: 2026-11-08
tags: [agents, 워크스페이스, 운영, epistemic-rules]
---

# 머지 타입 분기

단위 작업 종료 흐름 4단계(main 머지)의 세부 절차다. 이 문서가 워크플로 조립 지점이다. 전체 흐름은 [unit-task-workflow.md](../unit-task-workflow.md).

## 타입 결정

두 타입 중 하나로 진행한다. 기본은 PR 타입이며, 브랜치 관리자 타입(직접 머지)은 사용자가 PR 생략을 명시적으로 허용하거나 지시한 경우에만 쓴다. 그런 경우는 "그냥 머지해", "메인 푸시 OK", "PR 생략"처럼 PR 단계 생략 의도가 드러나는 표현이 있을 때다. routines, cron 자동 트리거는 PR 타입을 강제한다. 타입 결정이 모호하면 사용자에게 확인하고 AI 자율로 정하지 않는다. 본 절이 머지 타입 분기 규칙의 SSOT(single source of truth; 단일 진실 공급원)이며, pr-workflow는 PR 타입으로 확정된 뒤 조립되는 모듈이다.

## PR 타입

[pr-workflow.md](../pr-workflow.md)를 조립한다(PR 생성, 검토 대응, 능동 확인, 머지, 브랜치 정리).

## 브랜치 관리자 타입

주 워크트리에서 `git merge <branch> --no-ff && git push origin main && git worktree remove <워크트리 경로> && git branch -d <branch>`. 브랜치는 워크트리를 지운 뒤에야 지워진다. 워크트리 제거가 거부되는 경우의 처리는 [../branch-strategy.md](../branch-strategy.md) "작업 공간"의 정리 항목을 따른다. `--no-ff`로 단위 작업 머지 커밋을 명시적으로 남긴다. 메시지는 `Merge <branch>: <요약>` 형식으로, 무엇을 왜 바꿨는지만 적는다 - 승인, 검토 통과 여부는 커밋 텍스트에 남기지 않는다(검토는 종료 흐름 "사용자 검토 통과" 단계의 상호작용으로 처리되는 절차이지 커밋에 기록할 상태가 아니다).

## main에 직접 올라간 커밋의 정정

브랜치를 거치지 않은 커밋이 이미 main에 올라가 원격에 푸시되었고 원격 main이 아직 마지막 직접 커밋을 가리키면, 이력을 고쳐 쓰거나 강제 푸시하지 않고 그 커밋들을 머지 커밋 하나로 묶어 정정한다. 직접 커밋 전의 main 커밋을 첫 부모로, 마지막 직접 커밋을 둘째 부모로 삼는 머지 커밋은 원격 main의 후손이므로 fast-forward로 푸시된다. 그 머지 커밋의 내용은 마지막 직접 커밋과 같고, first-parent 이력에서는 직접 커밋들이 단위 작업 머지 하나로 보인다. 이 정정도 main 반영이므로 종료 흐름의 사용자 검토를 거친다.

1. 마지막 직접 커밋에 브랜치를 단다: `git branch <branch> <마지막 직접 커밋>`.
2. 직접 커밋 전의 main 커밋에서 HEAD가 분리된(detached) 워크트리를 만들고 그 안에서 머지한다: `git worktree add --detach <워크트리 경로> <직접 커밋 전 main 커밋>` 다음 `git -C <워크트리 경로> merge --no-ff <branch> -m "Merge <branch>: main 직접 커밋 정정 - <요약>"`. 주 워크트리는 main에서 옮기지 않는다([../branch-strategy.md](../branch-strategy.md) "작업 공간"). 이 머지에는 시작점 커밋(워크로그 등재)이 없다. 그래서 메시지의 `main 직접 커밋 정정` 문구로 정정 머지임을 밝힌다. 의미 감사는 이 문구가 있는 머지를 자율 머지로 판정하지 않는다.
3. 주 워크트리에서 main을 그 머지 커밋으로 옮기고 푸시한다: `git merge --ff-only <머지 커밋> && git push origin main`.
4. 정리: `git worktree remove <워크트리 경로> && git branch -d <branch>`.

## 환경 안전망과 잔존 점검

- 환경 안전망이 main 푸시를 차단하면(일부 하네스의 "main 직접 푸시 금지") 우회 편법을 자율로 쓰지 않는다. 차단 사실을 보고하고 처리 결정을 요청한다.
- 머지, 푸시, 브랜치 삭제 후 `git worktree list`(작업 워크트리 잔존)와 `git branch -a`(로컬/원격 브랜치 잔존, `git fetch --prune` 동반)를 확인한다. 잔존이 있으면 본 단위 작업의 후속으로 즉시 정리한다.
