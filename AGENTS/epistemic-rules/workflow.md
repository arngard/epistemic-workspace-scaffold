---
date created: 2026-10-26
date modified: 2026-10-26
tags: [규칙, epistemic-rules]
---

# 작업 흐름

## 세션 시작

워크로그(TASK_TREE, STATUS) 확인, 형식 감사, 의미 감사 트리거 판정, `reference/` 대조, 작업 범위 `epistemic-structure/` 문서 재독을 순서대로 밟는다. 각 단계의 명령과 판정 기준은 [AGENTS/epistemic-rules/session-boundaries.md](session-boundaries.md) "세션 시작". 인스턴스 고유 절차는 이 표준 절차를 완주한 뒤 이어 따른다.

## 단위 작업

단위 작업 시작과 종료 시 TASK_TREE를 갱신하고, main 머지는 사용자 검토를 통과한 뒤에만 한다(AI 자율 머지 금지). 완료 이력은 git이 담당하고 별도 이력 파일을 두지 않는다. 흐름은 [AGENTS/epistemic-rules/unit-task-workflow.md](unit-task-workflow.md), PR 조립은 [AGENTS/epistemic-rules/pr-workflow.md](pr-workflow.md).

## 작업 수행 원칙

넘겨짚지 않기, 단순함 우선, 외과적 변경, 목표 주도, 기억보다 실제 상태. 전체 SSOT는 [AGENTS/epistemic-rules/working-principles.md](working-principles.md), 코드 작업에는 [AGENTS/epistemic-rules/coding-guidelines.md](coding-guidelines.md)가 추가 적용된다.

## 문서 변경

관심사의 규약 문서를 먼저 갱신하고 정합성(cross-reference)을 확인한다. 폴더나 절차를 신설하면 디스크립터와 첫 실체 1건을 같은 단위 작업에 동반하고, 이동, 리네임은 연쇄 갱신한다. 날짜 프리픽스 문서는 수정 전 종결(`date closed`) 여부를 확인한다. 문서 단위와 SSOT(신설, 1관심사, 분량)는 [AGENTS/epistemic-rules/document-units.md](document-units.md), 구조 규약은 [AGENTS/epistemic-rules/folder-structure.md](folder-structure.md), 문서 시간성은 [AGENTS/epistemic-rules/document-temporality.md](document-temporality.md), 모듈, 의존성, 운영 절차 변경은 [epistemic-structure/architecture/AGENTS.md](../../epistemic-structure/architecture/AGENTS.md).

## 제품 지침 추출

AGENTS 계열이 정전(canonical) SSOT다. 도구별 진입점 파일(CLAUDE.md 등)은 이를 가리키는 파생물이라 규칙을 직접 담지 않는다. 갱신은 AGENTS 수정 후 재추출로만 한다. 진입점 표는 [AGENTS/epistemic-rules/tool-environment.md](tool-environment.md).

## 하위 프로젝트 편집

`implementation/` 하위 프로젝트(서브모듈 포함) 편집 시 그 자체 지침을 따르고, 가로지르는 규칙(정보 경계, 브랜치와 PR 흐름, 공개/비공개 경계)을 지킨다. 구조는 [AGENTS/epistemic-rules/workspace-and-project-structure.md](workspace-and-project-structure.md).
