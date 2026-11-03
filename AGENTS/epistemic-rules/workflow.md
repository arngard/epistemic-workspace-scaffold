---
date created: 2026-10-26
date modified: 2026-11-03
tags: [규칙, epistemic-rules]
---

# 작업 흐름

## 세션 시작

새 세션은 [session-boundaries.md](session-boundaries.md) "세션 시작"을 읽고 순서대로 밟는다. 인스턴스 고유 절차는 이 표준 절차를 완주한 뒤 이어 따른다.

## 단위 작업

단위 작업 시작과 종료 시 TASK_TREE를 갱신하고, main 머지는 사용자 검토를 통과한 뒤에만 한다(AI 자율 머지 금지). 흐름은 [AGENTS/epistemic-rules/unit-task-workflow.md](unit-task-workflow.md), PR 조립은 [AGENTS/epistemic-rules/pr-workflow.md](pr-workflow.md).

## 작업 수행 원칙

넘겨짚지 않기, 단순함 우선, 외과적 변경, 목표 주도, 기억보다 실제 상태. 전체 SSOT는 [AGENTS/epistemic-rules/working-principles.md](working-principles.md), 코드 작업에는 [implementation/AGENTS/epistemic-rules/coding-guidelines.md](../../implementation/AGENTS/epistemic-rules/coding-guidelines.md)가 추가 적용된다.

## 문서 변경

문서는 [AGENTS/epistemic-rules/document-authoring.md](document-authoring.md), 규범과 절차는 [AGENTS/epistemic-rules/norm-authoring.md](norm-authoring.md)의 순서를 따른다. 관심사의 규약 문서를 먼저 갱신하고 정합성(cross-reference)을 확인한다. 폴더나 절차를 신설하면 디스크립터와 첫 실체 1건을 같은 단위 작업에 동반하고, 이동, 리네임은 연쇄 갱신한다([move-cascade.md](folder-structure/move-cascade.md)). 날짜 프리픽스 문서는 수정 전 종결(`date closed`) 여부를 확인한다. 모듈, 의존성, 도메인의 운영 절차 변경은 [epistemic-structure/architecture/AGENTS/epistemic-rules.md](../../epistemic-structure/architecture/AGENTS/epistemic-rules.md). 규칙은 AGENTS 계열에만 적고 도구별 진입점 파일(`CLAUDE.md` 등)에는 적지 않는다 (see: [tool-environment.md](tool-environment.md)).

## 하위 프로젝트 편집

`implementation/` 하위 프로젝트(서브모듈 포함) 편집 시 그 자체 지침을 따르고, 가로지르는 규칙(정보 경계, 브랜치와 PR 흐름, 공개/비공개 경계)을 지킨다. 구조는 [AGENTS/epistemic-rules/workspace-and-project-structure.md](workspace-and-project-structure.md).
