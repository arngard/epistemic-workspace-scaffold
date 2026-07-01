---
date created: 2026-04-18
date modified: 2026-07-02
tags: [agents]
---

# 에이전트 지침 색인

> AI 에이전트 운영, 워크스페이스 관리 택틱, 도구 환경 정보.
> 프로젝트 컨텐츠 맥락은 [_knowledge/](../_docs/_knowledge/INDEX.md)와 [_strategy/](../_docs/_strategy/INDEX.md), 설계 명세는 [_architecture/](../_docs/_architecture/INDEX.md) 참조.
> 공통 사용 규칙은 [AGENTS.md](../AGENTS.md)의 "색인(INDEX) 사용 규칙" 섹션 참조.

## 도구/환경

| 파일 | 설명 |
|------|------|
| [tools.md](tools.md) | AI 도구별 자동 참조 파일 경로, 기계 감사 스크립트(tools/audit.py), Claude Code 절차 스킬 래퍼 |

## 작업 수행

| 파일 | 설명 |
|------|------|
| [working-principles.md](working-principles.md) | 단위 작업을 대하는 토대 원칙 (넘겨짚지 않기, 단순함, 외과적 변경, 목표 주도, 기억보다 실제 상태) |
| [coding-guidelines.md](coding-guidelines.md) | 코드 작업 전용 지침 (성공 기준을 테스트로, 코드 단순함, 코드 외과적 변경) |

## Git 운영

| 파일 | 설명 |
|------|------|
| [branch-strategy.md](branch-strategy.md) | 트렁크 기반 개발 모델, 브랜치 네이밍 룰 |
| [unit-task-workflow.md](unit-task-workflow.md) | 단위 작업 운영 흐름 (진입, 진행, 종료 패턴 분기 및 재귀 정합화) 및 PR 운영 규약 (본문, 검토, 응답) |

## 공용 태그

| 파일 | 설명 |
|------|------|
| [agent-tag-format.md](agent-tag-format.md) | 코드, 문서에 작업자 간 메모를 남기는 공용 태그 형식 |

## 에이전트 역할

| 파일 | 설명 |
|------|------|
| [agent-roles.md](agent-roles.md) | 서브에이전트 역할 정의 (epistemic-auditor 등). 도구 중립 정의. |

## 워크스페이스 조직화

| 파일 | 설명 |
|------|------|
| [why-agents-md-not-conventions-md.md](why-agents-md-not-conventions-md.md) | AI 진입점을 AGENTS.md로 하고 CONVENTIONS.md를 쓰지 않는 이유 |
| [workspace-and-project-structure.md](workspace-and-project-structure.md) | 워크스페이스 구조: scaffolding 네이밍, 최상위 폴더 배치, 문서와 코드의 역할 분담 |
| [how-to-separate-docs-folders.md](how-to-separate-docs-folders.md) | _docs/ 하위 폴더 분류 기준 (판별 규칙, 교차 링크) |
| [why-scaffolding-not-single-file.md](why-scaffolding-not-single-file.md) | 워크스페이스 scaffolding으로 정보를 분류하는 이유 |
