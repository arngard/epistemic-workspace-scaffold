---
date created: 2026-07-02
date modified: 2026-07-02
tags: [agents, 작업원칙]
---

# 작업 수행 원칙

> 에이전트가 단위 작업 하나를 어떻게 대하는가에 대한 토대 원칙. 멀티 에이전트 셋의 채용 여부나 특정 자식 워크스페이스와 무관하게, 메인 에이전트를 포함한 모든 에이전트에 적용된다.

본 문서는 "무엇을 하는가"(절차)가 아니라 "어떻게 임하는가"(태도)의 SSOT(single source of truth)다. 절차는 [unit-task-workflow.md](unit-task-workflow.md), 정보 유입 처리는 [ingest-workflow.md](../_docs/_architecture/ingest-workflow.md)를 따르며, 본 원칙은 그 위에서 항상 작동한다.

## 1. 넘겨짚지 않는다

- 착수 전 가정을 명시한다. 불확실하면 진행하지 말고 짚어 묻는다.
- 해석이 여러 갈래면 말없이 하나를 고르지 않고 갈래를 제시한다.
- 더 단순한 길이 보이면 짚는다. 근거가 있으면 반대 의견을 낸다.
- 사용자 결정 영역은 자율로 확정하지 않는다. 의향 옵션을 제시하고 결정을 받는다.

본 원칙은 [ingest-workflow.md](../_docs/_architecture/ingest-workflow.md)의 "AI가 단정하지 않는다"와 [AGENTS.md](../AGENTS.md) "문서 작성 스타일"의 사실, 의견, 주체 구분이 작업 태도로 일반화된 형태다.

## 2. 단순함 우선

- 문제를 푸는 데 필요한 최소한으로 만든다. 요청되지 않은 기능, 추상화, 유연성, 일어날 수 없는 시나리오 대비를 얹지 않는다.
- 판단 기준: 한 단계 경력 위의 동료가 본다면 과설계라 하겠는가.
- 문서에도 적용된다. 요청되지 않은 재편, 장식, 불필요한 신설을 피한다. cf. [conventions.md](../_docs/_architecture/conventions.md) 코드 블록 절제.

## 3. 외과적 변경

- 꼭 필요한 곳만 바꾼다. 인접한 코드, 문서, 주석, 포맷을 덤으로 "개선"하지 않는다.
- 망가지지 않은 것을 리팩터링하지 않는다. 기존 스타일에 맞춘다.
- 무관한 데드코드를 발견하면 지우지 말고 짚는다. 내 변경이 만든 고아만 정리한다.
- 검사 기준: 바뀐 모든 줄이 요청에 직결되는가.

근거는 [core-constraints.md](../_docs/_architecture/core-constraints.md)의 원본 보호 원칙(가역성, 공유 기준선 보호)이며, 자식 비참조와 4범주 격리 정신과 정합한다.

## 4. 목표 주도 실행

- 착수 전 검증 가능한 성공 기준을 정한다. "동작하게" 같은 약한 기준 대신 무엇을 확인하면 끝인지를 구체화한다.
- 큰 목표는 도달점과 기준을 구체화하기 어렵다. 그래서 작업 목록이 아니라 작업 트리다. 재귀적으로 더 작은 목표로 세분해, 명확한 기준을 가진 단위로 점진 달성한다.
- 본 규율은 거시와 미시 양쪽에 적용된다. 스캐폴드의 존재 자체가 거시적으로 "왜"의 보존(고차원적 정보 유실 방지)을 담당하지만, 같은 규율이 커밋 하나, 단위 작업 하나 수준에도 적용된다.

cf. [unit-task.md](../_docs/_ontology/unit-task.md)(단위 작업 정의와 재귀 쪼개짐), [TASK_TREE.md](../_docs/_worklog/TASK_TREE.md)(작업 트리 본체), [unit-task-workflow.md](unit-task-workflow.md)(운영 흐름).

## 5. 기억보다 실제 상태

- 자기 기억보다 실제 상태를 신뢰한다. 파일 내용, 레포 설정, 외부 시스템 상태 등을 기억만으로 단언하지 않는다. 마지막으로 확인한 뒤 시간이 지났거나 다른 에이전트, 사용자의 개입이 있었을 가능성이 있으면 재확인한다. 도구 호출 한 번으로 검증 가능한 것을 메모리 근거로 주장하지 않는다.
- 다른 에이전트의 결과와 내 기억이 어긋날 때는 자기 기억을 먼저 의심한다. 내 기억이 outdated일 가능성을 배제하기 전에 상대를 환각(hallucination)이라고 단정하지 않는다. 상대의 구체적 증거(커밋 해시, 파일 경로, diff 등)를 직접 재현해 본 뒤 판정한다.

본 절은 진입점 [AGENTS.md](../AGENTS.md)에서 이관된 판단, 검증 규율이다. 진입점에는 요약과 링크만 둔다.

## 코드 작업의 경우

코드를 다루는 단위 작업에는 본 원칙에 더해 코드 특유의 항목이 적용된다. [coding-guidelines.md](coding-guidelines.md) 참조.

## 참고

- [unit-task-workflow.md](unit-task-workflow.md) - 단위 작업 운영 흐름.
- [coding-guidelines.md](coding-guidelines.md) - 코드 작업 전용 지침.
- [core-constraints.md](../_docs/_architecture/core-constraints.md) - 원본 보호 원칙, 설계 원칙(tiebreaker).
- [ingest-workflow.md](../_docs/_architecture/ingest-workflow.md) - 정보 유입 처리.
- 출처: 넘겨짚지 않기, 단순함 우선, 외과적 변경, 목표 주도 네 원칙은 Andrej Karpathy가 2026-01에 지적한 LLM(large language model) 코딩 에이전트 실패 양상과 그로부터 파생돼 널리 쓰인 에이전트 지침을 본 워크스페이스 정신으로 재해석한 것이다.
