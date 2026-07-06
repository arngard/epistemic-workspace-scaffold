---
date created: 2026-07-06
date modified: 2026-07-06
tags: [agents, 워크플로우, git]
---

# 리뷰 코멘트 응답

PR에 달린 리뷰 코멘트에 응답하는 방식. [pr-workflow.md](../pr-workflow.md)의 하위 문서다. 응답 본문의 멘션과 AI 시그니처 규약은 PR 밖에도 적용되는 범용 규약이라 [external-communication.md](../external-communication.md)에 둔다.

## 응답 위치: 스레드 reply

PR에 달린 인라인 리뷰 코멘트(사용자 본인, 다른 개발자, 자동 리뷰 봇: Gemini Code Assist 등)에 응답할 때는 그 코멘트의 스레드 reply로 단다. PR 본체에 새 issue-level 코멘트를 다는 방식(`gh pr comment`)은 리뷰 스레드와 별개의 평면에 놓여 두 평면의 문맥이 섞이고 이후 추적이 어려워진다.

도구별 호출 형태:

- GitHub Web UI: 해당 리뷰 코멘트의 "Reply" 입력란 사용.
- gh CLI: `gh api repos/<owner>/<repo>/pulls/<num>/comments/<comment_id>/replies -f body="..."`
  - `<comment_id>`는 리뷰 코멘트 URL 끝 `#discussion_r<숫자>`의 숫자 부분. `gh api repos/<owner>/<repo>/pulls/<num>/comments`로도 조회 가능.
- 금지: `gh pr comment <num> --body "..."` - 본 명령은 issue-level 코멘트를 만든다. 본 PR에 새 일반 코멘트를 의도적으로 단다는 게 명백한 경우(머지 알림, 후속 작업 안내 등)에만 사용.

잘못 단 경우 정정: 잘못된 코멘트 ID 조회(`gh api repos/<owner>/<repo>/issues/<num>/comments`) 후 삭제(`gh api repos/<owner>/<repo>/issues/comments/<id> -X DELETE`), 그 뒤 스레드 reply로 재발행. 인라인 리뷰 코멘트 ID는 별도 엔드포인트 - `gh api repos/<owner>/<repo>/pulls/<num>/comments` 또는 코멘트 URL 끝 `#discussion_r<숫자>`.

파괴적 원격 조작(`-X DELETE` 등)은 AI가 이번 작업에서 스스로 만든 산출물에만 적용한다. 위 삭제도 방금 잘못 단 자기 코멘트를 지우는 경우로 한정한다. 사용자, 다른 개발자, 봇이 단 코멘트나 다른 원격 리소스는 지우지 않는다 - 정정이 필요하면 사용자에게 짚어 확인받는다 (cf. [original-protection-principle.md](../original-protection-principle.md) 가역성 원리).

본 정책은 자동 리뷰 봇 응답에도 똑같이 적용 - 봇 코멘트라도 사용자가 같은 PR을 나중에 다시 볼 때 스레드 문맥이 깨져 있으면 디버깅 비용이 커진다.

## 스레드 안 토론은 그 스레드가 SSOT

스레드 안에서 토론, 결론, 정정이 이루어졌으면 그 내용은 그 스레드를 SSOT(single source of truth)로 본다. 같은 결론을 PR 본문, 다른 코멘트, 외부 문서에서 다시 풀어 설명하지 않는다. 외부 위치에서 짚어야 할 때는 해당 스레드(또는 결정 코멘트)의 URL을 가리키는 링크만 제시한다 - `cf. [해당 스레드](url)` 형태가 권장.

근거: 같은 내용을 두 평면에 적으면 SSOT 위배 + 한 평면이 갱신되고 다른 평면이 안 갱신될 때 결론 추적이 깨진다. 토론 흐름은 시간순으로 스레드 안에 형성되며 이걸 외부에 옮기면 그 흐름 자체가 손실된다.
