---
date created: 2026-10-21
date modified: 2026-10-28
tags: [agents, 절차, ingest, epistemic-rules]
---

# `reference/` 폴더 처리

> [ingest-workflow.md](../../../AGENTS/epistemic-rules/ingest-workflow.md)의 하위 절차.

`reference/`는 사용자가 임의로 dump하는 자료의 immutable 보관 영역이다. 형태 무관 (PDF, 이미지, 텍스트 메모, URL 모음 등). see: [`reference/AGENTS.md`](../../AGENTS.md).

## 처리 여부 식별

`reference/` 직속 항목별 처리 상태의 원본은 `reference/INDEX.yaml`의 `status`다 (see: [folder-index.md](../../../AGENTS/epistemic-rules/folder-index.md) "자료 처리 상태"). 별도 처리 로그 파일은 두지 않는다.

자료 폴더 하나 안에 파일이 계속 쌓이는 경우, 그 폴더 안의 내부 진척 기록 형식(건별 목록, 단계별 진행 지점 등)과 갱신 규칙은 자손 규범이 정한다. 단계별 진행 지점만 남기는 방식은 기록량을 상수로 묶는다. 진척 기록은 그 자료 폴더 바로 아래의 `AGENTS/`(`reference/<자료 폴더>/AGENTS/`)에 둔다. 이 폴더는 자료가 아니라 운영 파일이라 작업마다 갱신하며, 원본 불변 점검에서 빠진다.

내부 진척 기록에는 형식과 무관한 제약이 하나 있다. 진척은 그 단계가 **대상을 어디까지 보았는가**를 뜻하므로 **시각은 자료 원천이 만들어진 시각을 적는다.** 중간 산출의 시각도, 작업을 수행한 시각도 아니다. 단계가 여럿을 거쳐도 모두 이 한 축을 쓰기 때문에 단계 간 진도를 견줄 수 있다. 뒤 단계가 뒤늦게 돌았다고 그 시각을 적으면 축이 어긋나고, 작업 시각을 적으면 한 배치 처리분이 모두 같은 값을 가져 진척이 드러나지 않는다.

세션 시작 시 또는 작업 중 트리거가 있을 때:

1. [색인](../../INDEX.md)으로 `reference/` 직속 항목과 처리 상태를 본다.
2. 형식 감사가 `reference/INDEX.yaml`에 낸 경고를 본다.
3. 색인에 `미등록`이거나 `처리 대기`로 보이는 자료는 미처리 자료다. 미등록이면 `INDEX.yaml`에 등록하고 처리 절차를 시작한다.
4. 감사가 `INDEX.yaml` 항목의 대상 자료가 없다고 경고하면 raw 자료가 사라진 것. 사용자에게 짚는다.
5. 미처리로 남은 항목은 처리 절차를 진행하거나 사용자에게 우선순위를 확인한다.

보조 검증으로 본문에서 `reference/<file>` 경로를 grep해 derived 노드의 존재를 교차 확인할 수 있다 (기록된 진척과 실제 cross-reference의 일치 점검).

## 미처리 항목 처리

미처리 항목 발견 시:

1. 자료 내용을 읽고 어떤 카테고리, 노드에 통합할지 판단.
2. 명확하면 [ingest-workflow.md](../../../AGENTS/epistemic-rules/ingest-workflow.md) "표준 시퀀스"로 통합 후 derived 노드에 raw 파일을 `ref:` 표지로 링크한다 (`ref: [<file>](<상대 경로>/reference/<file>)`). `INDEX.yaml`의 `status`를 `처리됨`으로 바꾸고, 자료 폴더의 내부 진척 기록이 있으면 함께 갱신한다.
3. 모호하거나 사용자 의도가 불분명하면 처리를 보류하고 `status`를 `사용자 의견 필요`로 바꾼 뒤 사용자에게 의견을 묻는다. 보류 항목이 기록에서 조용히 사라지지 않게 한다.

## Raw 자료 자체는 immutable

처리 후에도 자료(운영 파일 제외)는 삭제, 수정하지 않는다. 원본 보존이 SSOT다. derived 노드는 변경되더라도 raw 입력으로 항상 되돌아갈 수 있어야 한다. 원본의 수정, 삭제는 의미 감사자가 git 이력으로 점검한다 (see: [agent-roles/epistemic-auditor.md](../../../AGENTS/epistemic-rules/agent-roles/epistemic-auditor.md) "점검 항목").
