---
date created: 2026-04-18
date modified: 2026-07-06
tags: [agents]
---

# 에이전트 지침 디스크립터

> `AGENTS/` 폴더의 로컬 안내. AI 에이전트 운영, 워크스페이스 관리 택틱, 도구 환경 정보를 담는다.
> 규범 폴더이므로 파일별 설명과 "언제 읽는가" 트리거를 명시한다 (cf. [folder-structure.md](folder-structure.md) "폴더 구조와 디스크립터").
> 프로젝트 컨텐츠 맥락은 [_knowledge/](../_docs/_knowledge/AGENTS.md)와 [_strategy/](../_docs/_strategy/AGENTS.md), 설계 명세는 [_architecture/](../_docs/_architecture/AGENTS.md) 참조.

## 도구/환경

| 파일 | 설명 | 언제 읽는가 |
|------|------|-------------|
| [tool-environment.md](tool-environment.md) | AI 도구별 자동 참조 파일 경로, 기계 감사 스크립트(tools/audit.py), Claude Code 절차 스킬 래퍼 | 도구 환경 확인, 감사 스크립트 실행 시 |

## 규약과 절차

| 파일 | 설명 | 언제 읽는가 |
|------|------|-------------|
| [document-units.md](document-units.md) | 문서 단위와 SSOT 규약 - 1관심사, 분량 보조 지표, 중복 금지와 외부 SSOT 비복제, 이름과 식별자의 안정성 | 문서 신설, 분할, 배치 판단 시 |
| [folder-structure.md](folder-structure.md) | 폴더 구조 규약 - 폴더 분화, 디스크립터, 규범성 분기, 이동 시 연쇄 갱신 | 폴더 구조 변경, 디스크립터 작성 시 |
| [document-temporality.md](document-temporality.md) | 문서 시간성 규약 - 히스토리/현재적 구분, 혼합 금지, date closed 종결 신호 | 날짜 프리픽스 문서 작성, 수정, 문서 폐기 시 |
| [writing-style.md](writing-style.md) | 일반 문서 작성 스타일 - 코드 블록 절제, 표준 표현, 출처와 주체 표기, 자체 완결성, 태그 중복 회피, 도구 전용 파일 예외. 하위 문서로 마크다운 링크 표시텍스트, ASCII 부호 규약 | 모든 문서 작성 시 |
| [ingest-workflow.md](ingest-workflow.md) | 새 사실, 의견, 예측, 결정, 자료가 들어올 때의 표준 시퀀스. contradiction flagging, `_reference/` 처리, 빠뜨림 방지 자체 점검 | 새 정보 ingest 시 |
| [original-protection-principle.md](original-protection-principle.md) | 원본 보호 원칙 (가역성 우선, 공유 기준선 보호) - 에이전트가 원본을 다룰 때의 안전 기준 | 원본 삭제, 대폭 재편, 머지 판단 시 |

## 작업 수행

| 파일 | 설명 | 언제 읽는가 |
|------|------|-------------|
| [working-principles.md](working-principles.md) | 단위 작업을 대하는 토대 원칙 (넘겨짚지 않기, 단순함, 외과적 변경, 목표 주도, 기억보다 실제 상태) | 단위 작업 착수 시 |
| [coding-guidelines.md](coding-guidelines.md) | 코드 작업 전용 지침 (성공 기준을 테스트로, 코드 단순함, 코드 외과적 변경) | 코드 생성, 수정 시 |

## 단위 작업, 워크플로우, Git

| 파일 | 설명 | 언제 읽는가 |
|------|------|-------------|
| [unit-task.md](unit-task.md) | 단위 작업과 워크플로우의 개념 - 원자 단위 ↔ 트리 노드(중위 노드 포함, 중첩), 워크플로우의 재귀와 조립 | 단위 작업 개념 확인, 워크플로우 조립 판단 시 |
| [unit-task-workflow.md](unit-task-workflow.md) | 단위 작업 운영 프레임 (진입/진행/종료, 머지 타입 분기, 서브모듈 재귀 정합화, 끊김 재진입, 세션 격리) | 단위 작업 시작, 종료 시 |
| [pr-workflow.md](pr-workflow.md) | 종료 머지의 PR 타입에 조립되는 워크플로우 (PR 생성: 본문, 자기 검토, 속성). 리뷰 응답, 능동 확인은 [pr-workflow/](pr-workflow/AGENTS.md) 하위 | PR 생성, PR 검토 대응 시 |
| [external-communication.md](external-communication.md) | 외부 협업 소통 규약 (명시적 멘션, AI 시그니처) - PR 밖 이슈, 댓글 등에도 적용 | 외부 협업 시스템에 글 쓸 때 |
| [branch-strategy.md](branch-strategy.md) | 트렁크 기반 개발 모델, 브랜치 네이밍 룰 | 브랜치 생성 시 |

## 공용 태그

| 파일 | 설명 | 언제 읽는가 |
|------|------|-------------|
| [agent-tag-format.md](agent-tag-format.md) | 코드, 문서에 작업자 간 메모를 남기는 공용 태그 형식 | 공용 태그 작성, 대면 시 |

## 에이전트 역할

| 파일 | 설명 | 언제 읽는가 |
|------|------|-------------|
| [agent-roles.md](agent-roles.md) | 서브에이전트 역할 정의 (epistemic-auditor 등)와 인스턴스 전용 감사자 확장 패턴. 도구 중립 정의. | 서브에이전트 호출, 감사자 확장 시 |

## 워크스페이스 조직화

| 파일 | 설명 | 언제 읽는가 |
|------|------|-------------|
| [why-epistemic-workspace.md](why-epistemic-workspace.md) | 문서를 인식론적 4범주로 나누는 이유 - 문제, 전제, 접근 (스캐폴드 설계 철학) | 스캐폴드 취지 의문 시, 신규 진입자 온보딩 |
| [why-agents-md-not-conventions-md.md](why-agents-md-not-conventions-md.md) | AI 진입점을 AGENTS.md로 하고 CONVENTIONS.md를 쓰지 않는 이유 | 진입점 구조 의문 시 |
| [workspace-and-project-structure.md](workspace-and-project-structure.md) | 워크스페이스 구조: scaffolding 네이밍, 최상위 폴더 배치, 문서와 코드의 역할 분담 | 폴더 배치, 구현 프로젝트 등록 시 |
| [how-to-separate-docs-folders.md](how-to-separate-docs-folders.md) | _docs/ 하위 폴더 분류 기준 (판별 규칙, 교차 링크) | 문서 카테고리 판별 시 |
| [why-scaffolding-not-single-file.md](why-scaffolding-not-single-file.md) | 워크스페이스 scaffolding으로 정보를 분류하는 이유 | scaffolding 구조 의문 시 |
