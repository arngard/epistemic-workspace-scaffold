---
date created: 2026-04-19
date modified: 2026-10-10
tags: [agents, 역할, epistemic-rules]
---

# 서브에이전트 역할 정의

이 스캐폴드를 적용한 프로젝트에서 활용되는 서브에이전트(페르소나) 역할의 도구 중립 정의. 역할 공통 규칙은 본 문서가, 역할별 정의는 [agent-roles/](agent-roles/AGENTS.md) 하위 문서가 담는다.

## 모델 선택

서브에이전트에 작업을 위임할 때 작업 성격에 맞는 모델을 선택한다.

- 단순 검색, 파일 나열, 정형 스캔: 경량 모델로 충분.
- 높은 수준의 언어 이해, 고차 추론, 메타인지가 필요한 작업(문서 평가, 환각(hallucination) 검증, 다중 증거 종합, 사례로부터의 귀납적 일반화, 설계 리뷰 등): opus 등 고수준 모델을 사용한다.
- 의심스러우면 고수준 모델 우선. 경량 모델이 내놓은 잘못된 결과물을 사후에 검증, 재작업하는 비용이 모델 비용 차보다 크다.

## 역할 목록

| 역할 | 목적 | 정의 |
|------|------|------|
| epistemic-auditor | 문서 정합성 감사. 보고만 하고 수정하지 않는다 | [agent-roles/epistemic-auditor.md](agent-roles/epistemic-auditor.md) |

## 인스턴스 전용 감사자

스캐폴드를 적용한 인스턴스가 자기 도메인 고유 정책(예: 출처 표기 강화, 도메인 데이터 정합, 누적 왜곡 점검)을 감사하려면, [epistemic-auditor](agent-roles/epistemic-auditor.md)를 수정하지 않고 인스턴스 전용 감사자를 별도 역할로 둔다. 특수화 방식은 [instance-specialization.md](instance-specialization.md) "특수화 방식"을 따른다.

- 포함 호출: 인스턴스 감사자는 epistemic-auditor를 super로 포함해 호출한다. 한 번의 호출로 스캐폴드 공통 정합성과 인스턴스 고유 점검이 함께 수행된다.
- 등재: 인스턴스 감사자도 본 문서의 역할 목록에 올리고, [agent-roles/](agent-roles/AGENTS.md) 하위 문서에 정의와 도구별 구현 위치를 둔다.
