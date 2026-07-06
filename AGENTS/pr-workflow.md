---
date created: 2026-07-06
date modified: 2026-07-06
tags: [agents, 워크플로우, git]
---

# PR 워크플로우

단위 작업의 종료(브랜치 소유 노드의 main 머지)를 PR 타입으로 진행할 때 그 자리에 조립되는 워크플로우 모듈이다. 조립 개념은 [unit-task.md](unit-task.md), 단위 작업 운영 프레임은 [unit-task-workflow.md](unit-task-workflow.md) 참조. 단위 작업 밖에서 기존 PR에 대응할 때도 본 문서와 하위 문서의 규약이 재사용된다.

본 문서는 PR 생성 자체(본문, 자기 검토, 속성)를 다루고, 생성 후 절차는 하위 문서로 둔다. 리뷰 응답 방식은 [pr-workflow/review-response.md](pr-workflow/review-response.md), 제출 후 능동 확인 루프는 [pr-workflow/active-review-loop.md](pr-workflow/active-review-loop.md). 멘션, AI 시그니처 등 PR 밖에도 적용되는 범용 소통 규약은 [external-communication.md](external-communication.md).

## 언제 조립되는가

단위 작업 종료 4단계(main 머지)의 타입 분기가 PR 타입으로 확정됐을 때 이 자리에 조립된다. 타입 결정 규칙(기본 PR, 브랜치 관리자 타입의 조건, 자동 트리거의 PR 강제, 모호 시 사용자 확인)의 SSOT는 [unit-task-workflow.md](unit-task-workflow.md) "종료 흐름" 4단계다 - 브랜치 관리자 타입은 비-PR 경로라 본 모듈에 거처가 없고, 본 모듈은 타입 확정 후 조립되므로 자기 트리거를 재도출하지 않는다.

PR 타입 절차: PR 생성 -> 리뷰, 자동 체크, 머지 가능 대기 + 능동 확인 -> 리뷰 코멘트 응답, 정정 -> 사용자 Approve(3단계 "사용자 검토 통과"의 PR 형태) -> main 머지 -> 브랜치 정리(잔존 점검).

## 본문 형식

PR 본문은 다음 두 섹션을 갖춘다. 추가 섹션은 자유.

- `## 배경`: 이전의 관련 PR, issue, 메일, 채팅 결정, 본 PR을 트리거한 상황 설명, 리뷰어가 본 PR을 이해하는 데 필요한 메타 정보. 본 섹션이 비면 리뷰어는 변경 내용만 보고 의도와 맥락을 추론해야 하며, 리뷰 품질이 떨어진다.
- `## 변경`: 변경 사항의 나열. 단순 PR은 bullet list로 충분, 분량이 크거나 영역이 갈리면 `### 소제목`별로 구분.

추가 섹션은 자유 - 검토 체크리스트, 다음 단위 작업으로 분리한 사항, 동행 chore 안내 등은 본 흐름에 자연스럽게 함께 둔다.

## 제출 전 자기 검토

PR 생성 직전에 본인이 점검할 항목:

- 부모 브랜치 머지 시 더 수정 필요 없는 상태인가? 본 PR의 작업 완료를 의미하는 워크로그 갱신(TASK_TREE, 필요 시 STATUS 레지스트리)은 본 PR의 커밋에 포함되어 있어야 한다. 본 PR이 머지된 뒤에 "이 PR과 의미적으로 합쳐져야 하는 추가 작업"이 남으면 단위 작업 분리가 어긋난다. 머지 후 정정 단위가 별도로 필요할 만한 상태는 본 PR 안에서 흡수해 끝낸다.
- 보는 사람에게 충분한 설명인가? `## 배경`, `## 변경` 본문이 PR을 처음 보는 외부 관찰자(다른 협업자, 리뷰 봇, 사후 본인)에게 의도, 트리거, 변경 영역을 충분히 전달하는지 점검.

본 검토는 객관성을 위해 서브에이전트(예: code-review, report-reviewer 등)에 위임할 수 있다. AI가 본인 작업을 본인이 검토하면 사각지대가 남기 때문이다.

## 속성 할당

PR 생성 시 다음 속성을 적절히 할당한다.

- Assignees: 본 PR의 작업자, 검토 책임자. AI가 PR을 생성한 경우 작업 의뢰한 사용자를 assign.
- Labels: 변경 종류 라벨(chore, docs, feature, fix 등 - [branch-strategy.md](branch-strategy.md) 브랜치 타입과 통일) + 영역 라벨. 라벨 풀이 비어 있으면 본 PR이 첫 라벨을 만들 수도 있다.
- Milestone, Projects: 레포 운영 흐름에 따라 선택. 본 워크플로우는 강제하지 않는다.

## 하위 문서

PR 생성 후 절차는 자체 완결적 세부라 [pr-workflow/](pr-workflow/AGENTS.md) 하위 문서로 둔다.

- [review-response.md](pr-workflow/review-response.md): 리뷰 코멘트 응답 방식 (스레드 reply, 도구별 호출, 스레드 SSOT).
- [active-review-loop.md](pr-workflow/active-review-loop.md): 제출 후 능동 리뷰 확인 (이중 채널 감지, 체크 실패, 머지 충돌, 알림 트리거).
