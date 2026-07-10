---
name: pr-create
description: PR을 생성, 발행할 때 사용한다. 단위 작업 종료의 PR 타입 진행, routines나 cron 등 자동 트리거 세션의 PR 생성 시점에 트리거된다.
---

# PR 생성

이 스킬은 절차를 로드하는 포인터다. 절차 본체(SSOT(single source of truth))는 [AGENTS/pr-workflow.md](../../../AGENTS/pr-workflow.md).

1. 위 SSOT 문서를 지금 읽는다(본문 형식, 제출 전 자기 검토, 속성 할당). 기억으로 단언하지 않는다.
2. 외부로 나가는 글이므로 [AGENTS/external-communication.md](../../../AGENTS/external-communication.md)의 명시적 멘션 의무와 AI 시그니처 의무를 적용한다.
3. 제출 직후 [AGENTS/pr-workflow/active-review-loop.md](../../../AGENTS/pr-workflow/active-review-loop.md)의 이중 채널 감지를 예약한다. 이후 리뷰, 체크, 충돌 대응은 pr-respond 스킬로 진행한다.
