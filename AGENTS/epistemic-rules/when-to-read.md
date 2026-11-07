---
date created: 2026-11-03
date modified: 2026-11-07
tags: [규칙, epistemic-rules]
description: 루트 상류 묶음의 상황별 읽기 목록(작업, 상황, 확인). 작업을 시작할 때와 작업의 종류나 상황이 바뀔 때 연다
---

# 이럴 때 읽는 문서

루트 요지 [epistemic-rules.md](../epistemic-rules.md) "이럴 때 읽는다"가 가리키는 상황별 읽기 목록이다. 폴더의 AGENTS.md와 [workflow.md](workflow.md)가 짚는 문서에 더해, 아래에 해당하는 문서를 연다.

## 작업

- 문서 신설, 범주 판단, 날짜 프리픽스 문서 작성과 수정, 문서 폐기 -> [문서 작성](document-authoring.md)
- 규범, 절차, 스킬, 역할 정의의 신설, 변경, 삭제 -> [규범 작성](norm-authoring.md)
- 새 사실, 의견, 예측, 결정, 자료가 들어올 때 -> [정보 유입 처리](ingest-workflow.md)
- 브랜치와 워크트리 생성, 정리 -> [브랜치 전략](branch-strategy.md)
- PR 생성, PR 검토 대응 -> [PR 워크플로우](pr-workflow.md)
- 본 레포(레포지토리)가 상위 레포의 서브모듈일 때 단위 작업 종료 -> [포인터 정합화](submodule-pointer-sync.md)
- 외부 협업 시스템에 글 쓸 때 -> [외부 소통 규약](external-communication.md)
- 폴더 배치, 구현 프로젝트 등록 -> [워크스페이스 구조](workspace-and-project-structure.md)
- 계승된 규범, 절차의 변경이나 특수화를 도출했을 때 -> [상속 자산 특수화](instance-specialization.md)
- 공용 태그 작성, 대면 -> [공용 태그 형식](agent-tag-format.md)
- 서브에이전트 호출, 감사자 확장 -> [서브에이전트 역할](agent-roles.md)
- 감사 스크립트 실행 -> [감사 도구](tools.md)
- 새 용어 도입, 도메인 클래스 설계 전 -> [온톨로지 규범](../../epistemic-structure/ontology/AGENTS/epistemic-rules.md) "용어 도입 전 검증"
- 새 클래스나 모듈 생성, 모듈 구성, 의존성, 도메인의 운영 절차의 변경, 명세 신설 -> [architecture/](../../epistemic-structure/architecture/INDEX.md)
- 구현 착수 전 -> [핵심 제약](../../epistemic-structure/architecture/core-constraints.md)
- 여러 단계로 나뉜 절차나 에이전트 분업 설계 -> [단계 권한 기준](unit-task/stage-authority.md)

## 상황

- 끊긴 뒤 재진입, 다른 세션 산출물 발견 -> [세션 경계 규약](session-boundaries.md)
- 원본 삭제, 대폭 재편, 머지 판단 -> [원본 보호 원칙](original-protection-principle.md)
- 설계 판단이 갈릴 때 -> [설계 원칙](design-principles.md)
- 단위 작업 개념 확인, 단위 크기 판단, 워크플로우 조립 판단 -> [단위 작업 개념](unit-task.md)

## 확인

- 도구 환경 확인, 교정이나 교훈을 기록할 자리 확인 -> [도구 환경](tool-environment.md)
- 외부 사실, 결정 근거 확인 -> [knowledge/](../../epistemic-structure/knowledge/INDEX.md), [strategy/](../../epistemic-structure/strategy/INDEX.md)
- 스캐폴드 구조의 이유를 확인할 때 -> [4범주의 이유](why-epistemic-workspace.md), [진입점 근거](why-agents-md-not-conventions-md.md), [scaffolding 근거](why-scaffolding-not-single-file.md)
