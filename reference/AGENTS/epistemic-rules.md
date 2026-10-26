---
date created: 2026-10-26
date modified: 2026-10-26
tags: [reference, epistemic-rules]
---

# 자료 폴더 규범

같은 사안에 자손 규범이 있으면 자손 규범이 우선한다. 자손 규범은 이 묶음 옆의 낱개 문서와 그 폴더의 AGENTS.md에 있다.

## 운용 원칙

- 처리 후에도 이 폴더의 파일은 삭제, 수정하지 않는다. derived 노드(`epistemic-structure/*/` 하위)에서 `ref:` 표지로 그 파일을 링크해 참조만 남긴다.
- `reference/AGENTS.md`의 진척 기록이 인벤토리별 처리 진척의 SSOT(single source of truth)다. 처리 상태는 파일시스템으로 대체할 수 없는 정보이므로 일반 폴더와 달리 진척 기록을 유지하는 특수형이다 (ref: [`../../AGENTS/epistemic-rules/folder-structure.md`](../../AGENTS/epistemic-rules/folder-structure.md) "폴더 구조와 디스크립터"). 기본 기록 형식은 아래의 건별 인벤토리 표이며, 워크스페이스가 다른 형식(단계별 진행 지점 등)을 정할 수 있다. 표 형식을 쓰면 새 파일이 추가될 때 표에 등재하고, 통합, 처리 후 상태 컬럼을 갱신한다.
- AI는 새 세션 시작 시 진척 기록과 폴더 실제 내용을 대조한다. 폴더에는 있지만 진척 기록에 없으면 신규 미처리 자료다 (등재하고 처리 절차 시작). 진척 기록에는 있지만 폴더에 없으면 raw 자료가 사라졌다는 뜻이며, 사용자에게 짚는다.
- 자세한 처리 절차: [reference-folder.md](epistemic-rules/reference-folder.md).

## 처리 상태 표기

상태 컬럼에 다음 중 하나를 적는다.

- `처리 대기`: 등재됐지만 derived 노드로 통합되지 않음.
- `처리됨`: derived 노드로 통합 완료. 같은 행에 derived 노드 링크를 함께 적는다.
- `사용자 의견 필요`: 처리 방향이 모호해 사용자 확인 대기.
- `보관용`: 즉각 통합 대상이 아니지만 추후 참조 가능성을 위해 보관.
