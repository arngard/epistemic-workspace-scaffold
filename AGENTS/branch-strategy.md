---
date created: 2026-04-18
date modified: 2026-04-18
tags: [agents, git, 브랜치]
---

# 브랜치 전략

## 개발 모델

트렁크 기반 개발 (Trunk-Based Development).

- 장기 브랜치: `main` 하나만 유지
- feature branch는 수명을 짧게 가져가고 PR을 통해 main에 머지
- release branch는 릴리스 시점에 main에서 분기 (필요 시)

## 브랜치 네이밍 룰

```
<type>/YYMMDD-<짧은-설명>
```

- 설명 부분은 영문 소문자, 케밥 케이스
- 날짜는 브랜치 생성일

### 예시

```
feat/260414-event-queue
fix/260414-retry-timeout
docs/260414-architecture-update
```

## 작업 브랜치 type

| type | 용도 |
|------|------|
| `feat` | 새로운 기능과 관련된 것 |
| `fix` | 오류와 같은 것을 수정했을 때 |
| `docs` | 문서와 관련하여 수정한 부분이 있을 때 |
| `style` | 코드의 변화와 관련없는 포맷이나 세미콜론 누락 등 |
| `refactor` | 코드의 리팩토링 |
| `test` | 테스트를 추가하거나 수정했을 때 |
| `chore` | build 관련, 패키지 매니저 설정 등 production code와 무관한 부분 |

## 커밋 메시지

- 한글로 작성한다.

## 지양 사항

- 지나치게 긴 이름
- 머지 후 방치된 브랜치 (삭제할 것)
