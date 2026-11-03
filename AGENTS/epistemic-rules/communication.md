---
date created: 2026-10-26
date modified: 2026-11-03
tags: [규칙, epistemic-rules]
---

# 소통 규약

## 문서 작성 스타일

세부와 예외는 [writing-style.md](writing-style.md).

- 담백한 평서문을 쓰고 과장된 수사를 배제하며, 정확한 개념어를 쓰되 겉멋 든 용어나 불필요한 외래어로 치장하지 않는다. 통용되는 개념의 정의는 새로 적지 않는다. 볼드, 이탤릭, 이모지 등 서식 강조는 강한 경고, 금지, 주의에만 쓴다(남발하면 진짜 강조의 진정성을 잃는다).
- 정의나 앞 문장에서 따라 나오는 것을 부정형으로 다시 말한 문장(예: 도구나 기능의 명세에 그 산출이 무엇이 아닌지 덧댄 문장)은 쓰지 않고, 고치는 문서에서 보이면 지운다. 이런 부정은 독자가 실제로 헷갈릴 자리에만 남긴다.
- 문서 간 참조는 마크다운 링크로 쓰고 본문 문장에 녹이는 것을 우선한다. 따로 둘 때는 이 문서가 대상에 기대는 방식에 따라 `ref:`(이해나 정당화를 기대는 원천), `sub:`(범위의 일부를 맡긴 하위), `see:`(기대지 않는 부연과 관련) 표지를 단다. 세부는 [reference-markers.md](writing-style/reference-markers.md).
- 약어는 첫 등장 시 원문을 병기한다(예: `SSOT(single source of truth)`). 줄임말(truncation; feature -> feat, configuration -> config, repository -> repo 등)은 피하고 공식 형태를 쓴다.
- .md 문서에는 YAML front matter(`date created`, `date modified`, `tags`)를 붙이고 새 문서에는 `description`을 단다. 제외 대상은 [writing-style.md](writing-style.md) "도구 전용 설정 파일 예외", 태그는 [tags.md](tags.md).

## 응답 언어

문서, 커밋 메시지, 코드 주석과 in-source 문서는 한국어 평어체, 대화는 한국어 존댓말. 도구 호출 설명, 에이전트 설명, 진행 알림처럼 사용자 화면에 보이는 글도 한국어로 쓰며, 다른 언어로 된 알림이나 보고를 받은 직후에도 그렇다. 비속어, 욕설, 모욕, 차별 표현은 응답, 문서, 커밋, PR 어디에도 쓰지 않으며, 사용자가 쓰더라도 어휘를 모방하지 않는다.

## 대화 보고

긴 보고는 결론을 앞에 두고, 답을 받아야 하는 질문은 마지막에 모으며, 요청받은 산출물은 산출물만 내놓고, 작업 중 매긴 내부 라벨을 쓰지 않는다. 추론은 추론임을 드러내고, 확인할 수 있는 주장은 확인한 뒤 보고한다. 세부는 [conversation-reporting.md](writing-style/conversation-reporting.md), 추론 표시는 [attribution-scope.md](writing-style/attribution-scope.md), 확인 후 보고는 [working-principles.md](working-principles.md) "기억보다 실제 상태". PR, 이슈, 댓글처럼 외부 협업 시스템에 글을 쓸 때는 [external-communication.md](external-communication.md)를 따른다.
