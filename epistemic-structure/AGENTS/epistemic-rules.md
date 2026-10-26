---
date created: 2026-10-26
date modified: 2026-10-26
tags: [epistemic-structure, epistemic-rules]
---

# 범주 판별

같은 사안에 자손 규범이 있으면 자손 규범이 우선한다. 자손 규범은 이 묶음 옆의 낱개 문서와 그 폴더의 AGENTS.md에 있다.

`epistemic-structure/`는 네 범주로 나뉜다. 각 범주의 정의는 그 범주 묶음 요지의 "정의"가 SSOT(single source of truth)다.

- [온톨로지 규범](../ontology/AGENTS/epistemic-rules.md) "정의": "우리 도메인에 무엇이 존재하는가"
- [지식 규범](../knowledge/AGENTS/epistemic-rules.md) "정의": "세상이 어떠한가"
- [전략 규범](../strategy/AGENTS/epistemic-rules.md) "정의": "왜 이렇게 하기로 했는가"
- [설계 명세 규범](../architecture/AGENTS/epistemic-rules.md) "정의": "무엇을 어떻게 만들겠다"

작업 상태와 작업 트리를 담는 [worklog/](../../worklog/AGENTS.md)는 이 범주가 아니며, `epistemic-structure/` 밖의 별도 최상위 폴더다.

## 판별 규칙

- 같은 단어를 두 사람이 다른 뜻으로 쓸 수 있는가 -> `ontology/`
- 이 내용은 우리 결정과 무관하게 존재하는 외부 사실인가 -> `knowledge/`
- 이 내용을 바꾸면 "왜 그렇게 했나"에 대한 설명만 달라지는가 -> `strategy/`
- 이 내용을 바꾸면 실제 산출물이나 운영 행동이 달라지는가 -> `architecture/` (코드 프로젝트면 코드/빌드/배포, 문서 워크스페이스면 도메인의 운영 절차와 파이프라인이 그 예다)

## 교차 링크

한 주제가 여러 폴더에 걸칠 수 있다. 이때 중복을 피하려면:

- 개념 정의(용어 구분, 엔티티 관계)는 `ontology/`에만 둔다.
- 외부 사실(벤치마크, 환경 조건)은 `knowledge/`에만 둔다.
- 근거(이유/배경)는 `strategy/`에만 둔다.
- 명세(규칙/구조)는 `architecture/`에만 둔다.
- 서로 필요한 곳에서 링크한다.
