---
date created: 2026-07-04
date modified: 2026-07-04
tags: [agents, 도구]
---

# `AGENTS/tools/` 디스크립터

> 에이전트 운영을 보조하는 실행 스크립트의 자리. 문서가 아닌 도구 파일을 담는다.
> 사용 안내와 의존성 원칙(표준 라이브러리만, git 비의존)의 SSOT(single source of truth)는 [../tools.md](../tools.md) "기계 감사 스크립트"다.

| 파일 | 설명 | 언제 실행하는가 |
|------|------|-----------------|
| [audit.py](audit.py) | 형식 정합성 기계 감사 (도구 중립, 결정론적) | 새 세션 시작 시, push/PR 시 |
