---
name: pr-respond
description: 열린 PR에 대응할 때 사용한다. 리뷰 코멘트 확인과 응답, 자동 체크 실패 처리, 머지 충돌 해소, PR 상태 점검 시점에 트리거된다. 단위 작업 밖에서 기존 PR에 대응하는 세션(routines, cron 등 자동 트리거 포함)에도 적용된다.
---

# PR 대응

이 스킬은 절차를 로드하는 포인터다. 절차 본체(SSOT(single source of truth))는 [AGENTS/pr-workflow/](../../../AGENTS/pr-workflow/AGENTS.md) 하위 문서들.

1. [AGENTS/pr-workflow/review-response.md](../../../AGENTS/pr-workflow/review-response.md)를 지금 읽는다. 기억으로 단언하지 않는다. 응답은 해당 코멘트의 스레드 reply로만 단다.
2. [AGENTS/external-communication.md](../../../AGENTS/external-communication.md)를 지금 읽는다. 응답 본문에 듣는 대상을 명시적으로 멘션하고 AI 시그니처를 단다.
3. [AGENTS/pr-workflow/active-review-loop.md](../../../AGENTS/pr-workflow/active-review-loop.md)의 사이클(리뷰 즉시 처리, 체크 실패 즉시 처리, 머지 충돌 즉시 처리, 재확인 예약)을 머지 직전까지 반복한다.
