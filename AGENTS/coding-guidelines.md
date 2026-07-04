---
date created: 2026-07-02
date modified: 2026-07-05
tags: [agents, 코딩]
---

# 코딩 지침

> 코드를 다루는 단위 작업에 적용되는 지침. 일반 작업 태도는 [working-principles.md](working-principles.md)를 따르고, 본 문서는 코드 특유의 항목만 다룬다. 문서 전용 작업에는 적용되지 않는다.

## 성공 기준을 테스트로

[working-principles.md](working-principles.md) 목표 주도 원칙의 코드 형태. 행동 수준의 성공 기준은 테스트로 고정한다.

- "검증을 넣어라" -> 잘못된 입력에 대한 테스트를 먼저 쓰고 통과시킨다.
- "버그를 고쳐라" -> 버그를 재현하는 테스트를 먼저 쓰고 통과시킨다.
- "리팩터링하라" -> 전후로 테스트가 통과하는지 보장한다.

단, 테스트는 보완적 검증이다. [core-constraints.md](../_docs/_architecture/core-constraints.md) 설계 원칙의 강타입(correctness by construction)에 따라, 타입이 잡아야 할 오류를 테스트에 위임하지 않는다. 테스트는 타입이 닿지 못하는 행동, 회귀, 경계 조건을 고정하는 도구다.

## 코드의 단순함

[working-principles.md](working-principles.md) 단순함 우선의 코드 형태.

- 20줄로 될 것을 200줄로 쓰지 않는다. 200줄을 쓰고 있는데 50줄로 될 것 같으면 다시 쓴다.
- 미래에도 단일 사용처에서만 쓰일 코드라면, 추상화를 만들지 않는다.
- 요청되지 않은 유연성, 설정 가능성을 넣지 않는다.
- 일어날 수 없는 시나리오에 대한 예외 처리를 넣지 않는다.

## 코드의 외과적 변경

[working-principles.md](working-principles.md) 외과적 변경의 코드 형태.

- 기존 코드를 편집할 때 인접 코드, 주석, 포맷을 덤으로 손대지 않는다.
- 내가 다르게 짰을 코드라도 기존 스타일에 맞춘다.
- 내 변경으로 쓰이지 않게 된 import, 변수, 함수만 정리한다. 원래 있던 데드코드는 요청이 없으면 지우지 말고 언급한다.

## 참고

- [working-principles.md](working-principles.md) - 일반 작업 수행 원칙.
- [core-constraints.md](../_docs/_architecture/core-constraints.md) - 설계 원칙(강타입). 원본 보호 원칙은 [original-protection-principle.md](original-protection-principle.md).
- [unit-task-workflow.md](unit-task-workflow.md) - 단위 작업 운영 흐름.
