---
date created: 2026-10-26
date modified: 2026-10-27
tags: [reference, epistemic-rules]
---

# 자료 폴더 규범

같은 사안에 자손 규범이 있으면 자손 규범이 우선한다. 자손 규범은 이 묶음 옆의 낱개 문서와 그 폴더의 AGENTS.md에 있다.

## 운용 원칙

- 처리 후에도 이 폴더의 파일은 삭제, 수정하지 않는다. derived 노드(`epistemic-structure/*/` 하위)에서 `ref:` 표지로 그 파일을 링크해 참조만 남긴다.
- `reference/INDEX.yaml`의 `status`가 자료별 처리 진척의 SSOT(single source of truth)다. 처리 상태는 파일시스템으로 대체할 수 없는 정보라 항목마다 기록한다 (ref: [folder-index.md](../../AGENTS/epistemic-rules/folder-index.md) "자료 처리 상태"). 새 자료가 들어오면 `INDEX.yaml`에 항목을 더하고, 통합, 처리 후 `status`를 갱신한다.
- AI는 새 세션 시작 시 [색인](../INDEX.md)과 형식 감사의 경고를 본다. 색인에 `미등록`으로 보이는 자료는 신규 미처리 자료다 (`INDEX.yaml`에 등록하고 처리 절차 시작). 감사가 `INDEX.yaml` 항목의 대상 자료가 없다고 경고하면 raw 자료가 사라졌다는 뜻이며, 사용자에게 짚는다.
- 자세한 처리 절차: [reference-folder.md](epistemic-rules/reference-folder.md).

## 처리 상태 표기

`status` 필드에 다음 중 하나를 적는다.

- `처리 대기`: 등록됐지만 derived 노드로 통합되지 않음.
- `처리됨`: derived 노드로 통합 완료.
- `사용자 의견 필요`: 처리 방향이 모호해 사용자 확인 대기.
- `보관용`: 즉각 통합 대상이 아니지만 추후 참조 가능성을 위해 보관.
