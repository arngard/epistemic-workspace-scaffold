---
date created: 2026-11-03
date modified: 2026-11-07
tags: [agents, 역할, 감사, epistemic-rules]
description: 의미 감사를 부를지 정하는 트리거 판정의 기준과 호출 뒤 기준점 커밋을 남기는 방식
---

# 의미 감사의 트리거 판정과 기준점

> [epistemic-auditor.md](../epistemic-auditor.md) "호출 시점"의 하위 문서. 새 세션 시작 때 감사자를 부를지 판정하는 기준과, 부른 뒤 다음 판정의 기준점을 남기는 방식을 정한다.

- 판정: `check_semantic_audit.py`로 한다 (see: [tools.md](../../tools.md) "의미 감사 트리거 판정 스크립트"). 기준은 본 레포(레포지토리) 자신의 클린 커밋 이후 새 커밋이 있고 마지막 수행이 임계 시간을 초과했는가이며, 그 커밋이 없으면 그 자체로 충족이다(최초 1회). 클린 커밋은 trailer를 줄 전체로 갖고(본문 속 언급 제외) 상류 머지로 흘러들지 않은 것만 인정한다.
- 기준점 갱신: 호출 후 STATUS의 해당 행을 새 시각으로 갱신하고, 그 갱신과 발견 사항 정리(수정 또는 TASK_TREE 등재)를 담은 커밋에 trailer `Semantic-Audit: clean`을 남긴다. 작업 브랜치 경유로 main에 머지되면 머지 커밋에도 같은 trailer를 남긴다(기준점이 머지 이후를 가리키도록).
