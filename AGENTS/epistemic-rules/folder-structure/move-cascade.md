---
date created: 2026-11-03
date modified: 2026-11-03
tags: [agents, 규칙, 구조, epistemic-rules]
description: 폴더나 파일을 옮기거나 이름을 바꿀 때 같은 커밋에서 함께 고칠 것
---

# 폴더, 파일 이동 시 연쇄 갱신

[folder-structure.md](../folder-structure.md)의 하위 문서다. 폴더나 파일을 옮기거나 이름을 바꿀 때 함께 고칠 것을 정한다.

폴더, 파일 이동 또는 리네임은 연쇄 갱신을 요구한다. 구조 변경 한 번이 다수 문서의 링크, 디스크립터 안내, 상대경로에 수작업 파급을 유발한다. 반쪽만 정정된 상태로 남으면 이후 수습 비용이 예방 비용보다 급격히 커진다.

같은 커밋 안에서 다음을 일괄로 수행한다:

1. 이동된 파일을 참조하는 모든 문서의 상대경로 갱신 (`grep -rn "구경로" . --include="*.md"`로 워크스페이스 전수 확인 - `epistemic-structure/`, `worklog/`, `AGENTS/` 외 `.claude/`, `implementation/` 등 다른 위치의 마크다운도 포함).
2. 관련 폴더 디스크립터(AGENTS.md)의 안내 갱신. `INDEX.yaml` 항목은 파일과 함께 옮기고 색인을 다시 만든다. 규범을 옮기거나 신설하면 그 묶음의 트리거(루트 묶음은 [when-to-read.md](../when-to-read.md))나 부모 문서의 링크를 갱신한다.
3. 자매 폴더(`strategy`/`knowledge`/`ontology`/`architecture` 간) 일괄 작업이라면 한쪽만 반영하고 다른 쪽이 누락되지 않았는지 교차 확인.
4. 개편 규모가 크면 종료 전 epistemic-auditor를 호출해 사후 문서 정합성 감사를 받는다. 체크리스트(예방)와 감사(치료)는 역할이 다르므로 둘 다 수행한다. see: [agent-roles.md](../agent-roles.md).
