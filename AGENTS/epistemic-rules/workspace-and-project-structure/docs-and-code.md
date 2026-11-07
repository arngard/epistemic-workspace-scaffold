---
date created: 2026-11-03
date modified: 2026-11-07
tags: [agents, 워크스페이스, epistemic-rules]
description: epistemic-structure 문서와 코드가 각각 명세로 맡는 것의 분담
---

# 문서와 코드의 역할 분담

[workspace-and-project-structure.md](../workspace-and-project-structure.md)의 하위 문서다. 무엇을 문서에 두고 무엇을 코드에 맡기는가를 정한다.

`epistemic-structure/`는 코드로 표현할 수 없는 것 위주로 담는다. 도메인 개념, 외부 사실, 결정 근거, 상위 수준의 구조 결정이 이에 해당한다.

구현이 시작되면, 모듈의 상세 스펙(인터페이스 시그니처, 데이터 타입, 에러 계약)은 코드 자체가 명세가 된다. 확정된 추상화 레이어에는 `[to:@AGENT: 확정된 추상화 레이어]` 형식의 공용 태그 주석을 달아 변경을 통제한다. 태그 형식은 [agent-tag-format.md](../agent-tag-format.md)에 있다.

코드와 1:1로 대응하는 대규모 명세 문서를 따로 유지 관리하지 않는다. 문서에서 코드의 동작을 설명하거나 맥락을 제공하는 것은 무방하다.

| 위치 | 담는 것 |
|------|---------|
| `epistemic-structure/` | 코드로 표현할 수 없는 것: 도메인 개념, 외부 사실, 결정 근거, 상위 구조 결정. |
| 코드 (인터페이스 + 공용 태그 주석) | 모듈 인터페이스, 타입, 에러 계약. 코드가 곧 명세. 확정된 레이어는 `[to:@AGENT]` 태그로 보호. |
| 코드 (구현) | 모듈 내부 구현. 자기설명적 코드 + 필요 시 주석. |
