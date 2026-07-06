---
date created: 2026-04-18
date modified: 2026-07-06
tags: [규칙, 문서관리]
---

# AI Agent 지침

> 이 파일은 모든 AI 도구(Claude, Kiro, Gemini, Copilot 등)가 이 프로젝트를 다룰 때의 기본 지침이다. 각 도구의 진입점 파일(CLAUDE.md, .kiro/, .gemini/ 등)은 이 파일을 가리킨다.

always-on 진입층이다. 정체성, 비협상 게이트, 소통 규약, 트리거 색인을 담는다. 세부 규약은 산하 SSOT(single source of truth) 문서에 두되, 어떤 규칙이 존재하는지는 여기서 이름으로 짚어 에이전트가 그 규칙을 인지하고 찾아보게 한다. 본 파일은 작게 유지한다.

## 이 워크스페이스의 정체

에피스테믹 워크스페이스다. 코드로 표현할 수 없는 지식을 인식론적 4범주로 나눠 상위 의도와 근거가 유실되지 않게 한다: `_docs/_ontology`(무엇이 존재하는가), `_knowledge`(우리 결정과 무관한 외부 사실, 환경), `_strategy`(우리가 왜 그렇게 결정했는가), `_architecture`(어떻게 만드는가). 근거는 [AGENTS/why-epistemic-workspace.md](AGENTS/why-epistemic-workspace.md).

이 파일은 스캐폴드 template이다. 인스턴스(자식 워크스페이스)는 이 규범을 upstream으로 상속하고 본 절을 자기 도메인 정체성으로 특수화한다.

## 비협상 게이트

비가역이거나 치명적인 소수만 하드 게이트로 둔다(게이트 피로 방지). 데이터 안전 항목의 근거 원리는 [AGENTS/original-protection-principle.md](AGENTS/original-protection-principle.md).

- **`main` 브랜치에 직접 커밋하지 않는다** (cf. [AGENTS/branch-strategy.md](AGENTS/branch-strategy.md)).
- **`_docs/` 파일을 사람 확인 없이 삭제하거나 대폭 재편하지 않는다.**
- **Git 커밋, 푸시는 명시적 요청 시에만, 요청된 범위만 수행한다.** 푸시 전 사용자가 커밋 내용을 확인할 수 있어야 한다.
- **추측으로 문서를 채우지 않는다.** 논의되지 않은 내용을 확정된 것처럼 적지 않는다.
- 사실과 의견, 의견의 주체를 분명히 구분한다. 의견에는 주체를 명시한다(예: "`@사용자`의 판단", "외부 팀의 설계", "AI 제안").
- 공용 태그(`[to:@AGENT: ...]`)가 달린 영역은 프롬프트로 취급해 먼저 읽고 반영한다 (cf. [AGENTS/agent-tag-format.md](AGENTS/agent-tag-format.md)).

## 세션 시작

1. [_docs/_worklog/TASK_TREE.md](_docs/_worklog/TASK_TREE.md)(진행 중, 다음 할 일)와 [_docs/_worklog/STATUS.md](_docs/_worklog/STATUS.md)(감사 시각)를 읽는다.
2. 형식 감사 `python3 AGENTS/tools/audit.py .`를 실행하고, 보고된 위반은 정리하거나 사용자에게 짚는다 (cf. [AGENTS/tool-environment.md](AGENTS/tool-environment.md)).
3. STATUS의 의미 감사 행이 주기/트리거 조건을 초과했으면 착수 전 epistemic-auditor로 의미 감사를 받고 STATUS를 갱신한다 (cf. [AGENTS/agent-roles.md](AGENTS/agent-roles.md)).
4. [_reference/AGENTS.md](_reference/AGENTS.md)를 읽고 실제 내용과 대조한다. 미처리 자료는 [AGENTS/ingest-workflow.md](AGENTS/ingest-workflow.md)로 진행한다.
5. 작업 범위의 `_docs/` 문서(아래 트리거 색인)를 읽고 기존 결정과 충돌이 없는지 확인한다. 세션 중 새 정보가 들어오면 [AGENTS/ingest-workflow.md](AGENTS/ingest-workflow.md)를 따른다.

## 단위 작업

단위 작업 시작과 종료 시 TASK_TREE를 갱신하고, 사용자 검토를 통과한 뒤 main에 머지한다. AI 자율 머지는 하지 않는다. 완료 이력은 git이 담당하고 별도 이력 파일을 두지 않는다. 흐름은 [AGENTS/unit-task-workflow.md](AGENTS/unit-task-workflow.md), PR 조립은 [AGENTS/pr-workflow.md](AGENTS/pr-workflow.md).

## 작업 수행 원칙

넘겨짚지 않기, 단순함 우선, 외과적 변경, 목표 주도, 기억보다 실제 상태. 전체 SSOT는 [AGENTS/working-principles.md](AGENTS/working-principles.md), 코드 작업에는 [AGENTS/coding-guidelines.md](AGENTS/coding-guidelines.md)가 추가 적용된다.

## 문서 변경

관심사의 규약 문서를 먼저 갱신하고 정합성(cross-reference)을 확인한다. 폴더나 절차를 신설하면 디스크립터와 첫 실체 1건을 같은 단위 작업에 동반하고, 이동, 리네임은 연쇄 갱신한다. 날짜 프리픽스 문서는 수정 전 종결(`date closed`) 여부를 확인한다. 문서 단위와 SSOT(신설, 1관심사, 분량)는 [AGENTS/document-units.md](AGENTS/document-units.md), 구조 규약은 [AGENTS/folder-structure.md](AGENTS/folder-structure.md), 문서 시간성은 [AGENTS/document-temporality.md](AGENTS/document-temporality.md), 모듈, 의존성 변경은 [_docs/_architecture/AGENTS.md](_docs/_architecture/AGENTS.md).

## 문서 작성 스타일

소통의 기본 규약이라 여기에 이름으로 둔다. 세부와 예외는 [AGENTS/writing-style.md](AGENTS/writing-style.md).

- 담백한 평서문을 쓰고 과장된 수사를 배제한다. 볼드, 이탤릭, 이모지 등 서식 강조는 강한 경고, 금지, 주의에만 쓴다(남발하면 진짜 강조의 진정성을 잃는다).
- 문서 간 참조는 마크다운 링크로, 출처는 `cf.`(참고)와 `ref.`(근거)로 표기한다.
- 약어는 첫 등장 시 원문을 병기한다(예: `SSOT(single source of truth)`). 줄임말(truncation; feature -> feat, configuration -> config, repository -> repo 등)은 피하고 공식 형태를 쓴다.
- 모든 .md에 YAML front matter를 붙인다: `date created`, `date modified`, `tags`(첫 항목은 카테고리, `_docs/` 4범주 직속은 감사 스크립트가 검사).
- 추측 금지와 사실, 의견, 주체 구분은 위 비협상 게이트에 둔다.

## 응답 언어

문서, 커밋 메시지, 코드 주석과 in-source 문서는 한국어 평어체, 대화는 한국어 존댓말. 에러 메시지는 첫 문장 영문 + 상세 한국어. 비속어, 욕설, 모욕, 차별 표현은 응답, 문서, 커밋, PR 어디에도 쓰지 않으며, 사용자가 쓰더라도 어휘를 모방하지 않는다.

## 제품 지침 추출

AGENTS 계열이 정전(canonical) SSOT다. 도구별 진입점 파일(CLAUDE.md 등)은 이를 가리키는 파생물이라 규칙을 직접 담지 않는다. 갱신은 AGENTS 수정 후 재추출로만 한다. 진입점 표는 [AGENTS/tool-environment.md](AGENTS/tool-environment.md).

## 하위 프로젝트 편집

`_implementation/` 하위 프로젝트(서브모듈 포함) 편집 시 그 자체 지침을 따르고, 가로지르는 규칙(정보 경계, 브랜치와 PR 흐름, 공개/비공개 경계)을 지킨다. 구조는 [AGENTS/workspace-and-project-structure.md](AGENTS/workspace-and-project-structure.md).

## 필수 참조 문서 (트리거 색인)

디스크립터(폴더별 AGENTS.md)를 먼저 읽고 필요한 문서만 연다.

| 문서 | 언제 참조하는가 |
|------|----------------|
| [AGENTS/AGENTS.md](AGENTS/AGENTS.md) | 규범 문서(문서 단위, 폴더 구조, 시간성, 에이전트 역할 등) 전체 색인 |
| [AGENTS/writing-style.md](AGENTS/writing-style.md) | 문서 작성 세부 규약 |
| [_docs/_ontology/AGENTS.md](_docs/_ontology/AGENTS.md) | 새 용어 도입, 도메인 클래스 설계 전 |
| [_docs/_knowledge/AGENTS.md](_docs/_knowledge/AGENTS.md), [_docs/_strategy/AGENTS.md](_docs/_strategy/AGENTS.md) | 외부 사실, 결정 근거 확인 시 |
| [_docs/_architecture/AGENTS.md](_docs/_architecture/AGENTS.md) | 새 클래스, 모듈 생성 시 |

## 핵심 제약

ref. [_docs/_architecture/core-constraints.md](_docs/_architecture/core-constraints.md).
