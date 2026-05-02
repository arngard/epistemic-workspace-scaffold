---
date created: 2026-04-18
date modified: 2026-05-03
tags: [architecture]
---

# 설계 명세 색인

> "우리가 어떻게 만들겠다" — 최종 설계의 스니펫. 현재 상태의 도면.
> 설계의 맥락은 [_knowledge/](../_knowledge/INDEX.md)와 [_strategy/](../_strategy/INDEX.md) 참조.
> 공통 사용 규칙은 [AGENTS.md](../../AGENTS.md)의 "색인(INDEX) 사용 규칙" 섹션 참조.

## 작성 스타일

- 명세 중심. 선언문으로 쓴다.
- 결정의 근거나 배경은 여기에 담지 않는다. 그건 `_strategy/`에 둔다.
- 코드로 표현 가능한 인터페이스·타입·에러 계약은 코드 자체가 명세다. 이 폴더에는 그 외의 상위 구조 결정만 남긴다.

## 문서 목록

### 프로젝트 수준 규약

| 파일 | 설명 |
|------|------|
| [core-constraints.md](core-constraints.md) | 설계 원칙 및 핵심 제약. 스캐폴드 상태 — 제약 목록 작성 필요. |
| [conventions.md](conventions.md) | 코딩 규약 (현재는 Git 규약만). 스캐폴드 상태 — 프로젝트 고유 규약 확장 필요. |

### 운영 절차

| 파일 | 설명 |
|------|------|
| [ingest-workflow.md](ingest-workflow.md) | 새 사실·의견·예측·결정·자료가 들어올 때의 표준 시퀀스. contradiction flagging, `_reference/` 처리, 빠뜨림 방지 자체 점검 포함. |

### 구조/모듈

| 파일 | 설명 |
|------|------|
| [sample-spec.md](sample-spec.md) | (튜토리얼용 샘플) 설계 명세 문서의 위치/형식을 보여주는 예시. 실제 작성 시 삭제·교체. |
