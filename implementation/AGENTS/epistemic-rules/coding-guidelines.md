---
date created: 2026-07-02
date modified: 2026-11-02
tags: [agents, 코딩, epistemic-rules]
---

# 코딩 지침

> 코드를 다루는 단위 작업에 적용되는 지침. 일반 작업 태도는 [working-principles.md](../../../AGENTS/epistemic-rules/working-principles.md)를 따르고, 본 문서는 코드 특유의 항목만 다룬다. 문서 전용 작업에는 적용되지 않는다.

## 성공 기준을 테스트로

[working-principles.md](../../../AGENTS/epistemic-rules/working-principles.md) 목표 주도 원칙의 코드 형태. 행동 수준의 성공 기준은 테스트로 고정한다.

- "검증을 넣어라" -> 잘못된 입력에 대한 테스트를 먼저 쓰고 통과시킨다.
- "버그를 고쳐라" -> 버그를 재현하는 테스트를 먼저 쓰고 통과시킨다.
- "리팩터링하라" -> 전후로 테스트가 통과하는지 보장한다.

단, 테스트는 타입이 닿지 못하는 행동, 회귀, 경계 조건을 고정하는 보완적 검증이다. [design-principles.md](../../../AGENTS/epistemic-rules/design-principles.md) 설계 원칙의 강타입(correctness by construction)에 따라, 타입이 잡아야 할 오류를 테스트에 위임하지 않는다.

## 메시지

에러 메시지는 첫 문장 영문 + 상세 한국어로 쓴다.
