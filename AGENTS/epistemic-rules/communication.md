---
date created: 2026-10-26
date modified: 2026-10-28
tags: [규칙, epistemic-rules]
---

# 소통 규약

## 문서 작성 스타일

소통의 기본 규약이라 여기에 이름으로 둔다. 세부와 예외는 [writing-style.md](writing-style.md).

- 담백한 평서문을 쓰고 과장된 수사를 배제한다. 볼드, 이탤릭, 이모지 등 서식 강조는 강한 경고, 금지, 주의에만 쓴다(남발하면 진짜 강조의 진정성을 잃는다).
- 정확한 개념어로 쓰되 겉멋 든 용어나 불필요한 외래어로 치장하지 않는다. 세부는 [writing-style.md](writing-style.md) "정확한 개념어와 담백한 문체".
- 문서 간 참조는 마크다운 링크로 쓰고 본문 문장에 녹이는 것을 우선한다. 따로 둘 때는 이 문서가 대상에 기대는 방식에 따라 `ref:`(이해나 정당화를 기대는 원천), `sub:`(범위의 일부를 맡긴 하위), `see:`(기대지 않는 부연과 관련) 표지를 단다. 세부는 [reference-markers.md](writing-style/reference-markers.md).
- 약어는 첫 등장 시 원문을 병기한다(예: `SSOT(single source of truth)`). 줄임말(truncation; feature -> feat, configuration -> config, repository -> repo 등)은 피하고 공식 형태를 쓴다.
- 모든 .md(생성 색인 제외)에 YAML front matter를 붙인다: `date created`, `date modified`, `tags`(순서 없는 집합, 표기와 어휘는 [tags.md](tags.md)). 도구가 형식을 정하는 파일(어디에 있든 이름이 `CLAUDE.md`, `SKILL.md`, `copilot-instructions.md`인 파일과 도구 폴더 `.claude/`, `.github/`, `.kiro/` 아래 파일)은 그 도구의 형식을 따르고 이 의무에서 빠진다. `.git/`, `node_modules/`, `.tmp/`, `__pycache__/` 아래와 git이 무시하는 경로는 문서 영역이 아니라 대상 밖이다. 새 문서에는 폴더 색인에 보일 한 줄 설명 `description`을 단다. 없어도 감사는 경고하지 않는다 (see: [folder-index.md](folder-index.md)).
- 추측 금지와 사실, 의견, 주체 구분은 [epistemic-rules.md](../epistemic-rules.md) "비협상 게이트"에 둔다.

## 응답 언어

문서, 커밋 메시지, 코드 주석과 in-source 문서는 한국어 평어체, 대화는 한국어 존댓말. 에러 메시지는 첫 문장 영문 + 상세 한국어. 비속어, 욕설, 모욕, 차별 표현은 응답, 문서, 커밋, PR 어디에도 쓰지 않으며, 사용자가 쓰더라도 어휘를 모방하지 않는다.

## 대화 보고

긴 보고는 결론을 앞에 두고, 답을 받아야 하는 질문은 마지막에 모으며, 요청받은 산출물은 산출물만 내놓고, 작업 중 매긴 내부 라벨을 쓰지 않는다. 추론은 추론임을 드러내고, 확인할 수 있는 주장은 확인한 뒤 보고한다. 세부는 [conversation-reporting.md](writing-style/conversation-reporting.md), 추론 표시는 [writing-style.md](writing-style.md) "출처와 주체 표기의 범위", 확인 후 보고는 [working-principles.md](working-principles.md) "기억보다 실제 상태".
