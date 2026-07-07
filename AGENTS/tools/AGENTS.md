---
date created: 2026-07-04
date modified: 2026-07-07
tags: [agents, 도구]
---

# `AGENTS/tools/` 디스크립터

> 에이전트 운영을 보조하는 실행 스크립트의 자리. 문서가 아닌 도구 파일을 담는다.
> 사용 안내와 의존성 원칙(표준 라이브러리만, git 비의존)의 SSOT(single source of truth)는 [../tool-environment.md](../tool-environment.md) "기계 감사 스크립트"다.

| 파일 | 설명 | 언제 실행하는가 |
|------|------|-----------------|
| [audit.py](audit.py) | 형식 정합성 기계 감사 (도구 중립, 결정론적) | 새 세션 시작 시, push/PR 시 |

audit.py는 진입점이다. 검사 로직은 공용 인프라 `_audit_core.py`와 의미별 검사 모듈 `audit_frontmatter.py`(front matter/스키마), `audit_links.py`(링크/참조), `audit_structure.py`(폴더/디스크립터/이식성), `audit_worklog.py`(STATUS/TASK_TREE), `audit_content.py`(분량/시간성/문장 부호)로 분할돼 있으며, audit.py가 import해 조합한다. 직접 실행 대상은 audit.py뿐이다. 분할은 파일당 크기를 낮춰 편집 안전성과 의미 단위 유지보수성을 높이기 위함이다.
