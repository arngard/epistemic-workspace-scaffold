---
date created: 2026-04-18
date modified: 2026-04-18
tags: [architecture, 규칙, 네이밍, 코딩규약]
---

# Conventions

코드 작성 시 따라야 할 규약. AI 도구가 코드를 생성할 때도 이 규약을 준수한다.

> ⚠️ 이 문서는 스캐폴드 상태이며 현재는 Git 규약만 포함한다. 언어/빌드, 패키지 구조, 네이밍, 의존성 등 프로젝트 고유의 규약은 초기 세팅 시 추가해야 한다. 작업은 [_docs/_worklog/TASK_TREE.md](../_worklog/TASK_TREE.md)에 등록되어 있다.

## Git 규약

### 브랜치 전략

- `main`: 릴리즈 가능 상태 유지
- `develop`: 통합 개발 브랜치
- `feature/{description}`: 기능 개발
- `fix/{description}`: 버그 수정
- `docs/{description}`: 문서만 수정

### 커밋 메시지

```
{type}({scope}): {description}
```

type: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`
