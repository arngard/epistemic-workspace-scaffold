---
date created: 2026-07-06
date modified: 2026-07-06
tags: [agents, 워크플로우, git]
---

# 제출 후 능동 리뷰 확인

PR 생성 뒤 리뷰, 자동 체크, 머지 가능 상태를 능동적으로 감지, 처리해 머지까지 이어가는 루프. [pr-workflow.md](../pr-workflow.md)의 하위 문서다.

## 이중 채널 감지

PR 생성, 푸시 직후 검토자(자동 리뷰 봇, 사용자, 다른 개발자)의 리뷰가 달릴 때까지 시간차가 있다. 본 라운드를 PR 머지로 이어가려면 그 리뷰를 능동적으로 감지, 처리해야 한다. 대기, 확인 대상은 리뷰만이 아니다 - 환경이 자동 체크(GitHub Actions 등 CI(continuous integration) status check)를 운영하면 체크 결과도, main 전진에 따른 머지 가능 상태(충돌 여부)도 같은 방식으로 감지, 처리한다.

확인 방법은 다음 두 채널을 항상 함께 운영한다 - 둘 중 어느 한쪽이 누락, 지연되어도 다른 한쪽이 안전망이 된다. 정책 조건부 분기가 아니라 무조건 이중화.

1. webhook 대기: 환경이 GitHub webhook을 받을 수 있다면 PR 활동 이벤트가 도착할 때까지 세션이 자동으로 깨어나길 기다린다.
2. 10분 타이머 예약: 환경의 자동 wake-up 도구로 PR 생성 직후 10분 후의 능동 확인 턴을 예약한다. 도구는 환경마다 다름 - Claude Code 데스크톱의 `ScheduleWakeup`, Claude Code on the web의 `Monitor`, 외부 cron, GitHub Actions scheduled workflow 등. 5분은 자동 리뷰 봇 응답이 아직 안 들어와 헛 종료되는 빈도가 높았다. 10분 정도가 1차 응답 안착 시점에 더 가깝다. 자동 wake-up 도구가 환경에 전혀 없을 때만 사용자에게 "10분 뒤 PR 리뷰 확인을 트리거해 주세요"라고 명시 요청한다.

두 채널을 동시에 운영하는 이유: webhook 단독 운영은 환경에 따라 비가시적으로 누락, 지연되거나 세션 wake-up과 실제 이벤트 도착 사이가 단절돼 작동하지 않을 수 있다. 10분 타이머를 결정적 안전망으로 항상 동행시킨다.

PR 상태 확인 도구: `gh pr view <number> --repo <owner>/<repository> --json reviewDecision,reviews,comments` + `gh api repos/<owner>/<repository>/pulls/<number>/comments`(gh CLI 환경), 또는 GitHub MCP `pull_request_read`의 `get`, `get_reviews`, `get_review_comments`, `get_check_runs` 메소드(MCP 환경). `reviewDecision`은 PR 전체 상태(APPROVED, CHANGES_REQUESTED, REVIEW_REQUIRED 등)를 열거형으로 제공해 머지 가능 여부 1차 판단을 빠르게 한다.

"잠시 후 자율 확인하겠다"는 표현은 두 채널 어느 쪽도 예약하지 않은 채로는 쓰지 않는다 - 턴 메커니즘 한계로 거짓 약속이 된다.

## 리뷰가 달려 있으면 즉시 처리

- 수용 가능한 지적은 본 PR 안에서 정정 커밋 + 스레드 reply (응답 방식은 [review-response.md](review-response.md)).
- 반박이 필요한 지적은 근거(공식 문서, 경험적 증거)를 갖춰 스레드 reply.
- 대응이 모호한 경우 해당 리뷰 스레드(또는 일반 댓글)에서 사용자(`@<owner>`)를 명시적으로 멘션하여 결정 요청. 모호한 채로 머지, 롤백 결정을 AI가 단정하지 않는다.

## 자동 체크가 실패하면 즉시 처리

- 실패 원인을 로그에서 파악한다. `gh pr checks <number>`로 체크 상태 일람, `gh run view <run-id> --log-failed`로 실패 로그 확인 (GitHub MCP 환경은 `pull_request_read`의 `get_check_runs`).
- 본 PR의 변경이 원인이면 본 PR 안에서 정정 커밋으로 체크를 성공 상태로 만든다. 실패를 방치한 채 리뷰 응답이나 머지를 진행하지 않는다.
- 원인이 본 PR의 변경 밖이면(선존 부채, 인프라, 외부 서비스 장애 등) 사용자에게 짚고 처리 방향을 확인한다.
- 정정 푸시는 체크를 다시 트리거하므로, 전 체크 성공을 확인할 때까지 같은 대기, 확인 사이클을 반복한다.

## 머지 충돌이 생기면 즉시 처리

- PR이 열려 있는 동안 main이 전진해 작업 브랜치와 충돌하면 PR은 머지 불가 상태가 된다. 머지 가능 여부도 능동 확인 대상이다 - `gh pr view <number> --json mergeable,mergeStateStatus`.
- 충돌은 main을 작업 브랜치로 머지해(`git merge main`) 브랜치 안에서 해소하고 푸시한다. 해소 원칙은 양쪽 변경의 의미를 보존하는 결합이 기본이고, 판단이 갈리면 사용자에게 확인한다. 공유된 작업 브랜치의 이력 재작성(rebase 후 force-push)은 피한다 (cf. [original-protection-principle.md](../original-protection-principle.md)).
- 해소 푸시는 자동 체크를 다시 트리거하므로 전 체크 성공 확인까지 같은 사이클을 반복한다.

리뷰 처리 후에도 추가 리뷰가 달릴 수 있으므로 머지 직전까지 같은 사이클을 반복한다.

## 신규 발행 vs edit (알림 트리거)

PR 본문, 제목 edit은 GitHub 알림을 새로 트리거하지 않는 경우가 많다 - 특히 자동 리뷰 봇은 PR opened 이벤트에만 동작한다. PR 본문, 제목 정정이 의미적으로 큰 경우(예: 본문이 비어 있던 상태에서 채워 넣은 경우)는 close -> reopen하거나 새 코멘트로 본문 변경 사실을 알리는 편이 안전하다. 사소한 오탈자, 표현 정정은 트리거 없이 그대로 둬도 무방.
