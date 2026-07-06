---
date created: 2026-04-18
date modified: 2026-07-07
tags: [agents, 도구, 환경, IDE]
---

# 도구/환경 정보

## 도구별 자동 참조 파일

각 AI 도구는 프로젝트 루트에서 고유 경로의 파일을 자동으로 참조한다. 모든 진입점 파일은 루트의 [AGENTS.md](../AGENTS.md)를 가리킨다.

| 도구 | 진입점 파일 | 비고 |
|------|------------|------|
| Claude Code | [CLAUDE.md](../CLAUDE.md) | Anthropic CLI/IDE. 세션 시작 시 자동 로드. |
| GitHub Copilot | [.github/copilot-instructions.md](../.github/copilot-instructions.md) | VS Code/JetBrains Copilot이 자동 로드. |
| Gemini (Android Studio) | [.gemini/styleguide.md](../.gemini/styleguide.md) | Android Studio 통합 Gemini가 자동 로드. |
| Kiro | `.kiro/` 디렉토리 | AWS의 VS Code 기반 AI IDE. spec-driven development 지원. 디렉토리 세팅은 도구 자체가 수행. |
| Cursor | `.cursor/rules/` 또는 `.cursorrules` | 현 스캐폴드는 진입점을 포함하지 않는다. Cursor를 사용하는 경우 별도 설정한다. |

## 진입점 유지 원칙

- 진입점 파일은 "[AGENTS.md](../AGENTS.md)를 읽으라"는 포인터 역할만 한다. 지침 자체를 진입점에 적지 않는다. 중복, 불일치 방지.
- 새로운 도구가 추가되면: 해당 도구의 자동 참조 경로에 진입점 파일을 만들고, 이 표에 등록한다.

## 기계 감사 스크립트

[tools/audit.py](tools/audit.py)는 형식 정합성을 결정론적으로 검사한다. 점검 범위: front matter 필수 필드(선택 필드 `date closed`는 히스토리 문서 전용), 문서 유형별 분량 임계(지식/전략 노드, 히스토리 문서, 폴더 디스크립터), 현재적 문서의 시간성 혼합 패턴, 날짜 프리픽스 없는 문서의 `date closed`, STATUS 레지스트리 표 외 서술과 표 스키마/시각 형식, TASK_TREE 속성 노드 표준 키와 완료 노드의 브랜치 속성 잔존, 폴더 디스크립터(AGENTS.md) 부재, 규범 폴더 디스크립터의 파일별 안내 완전성, 폴더 직속 md 파일 수 임계, `_docs/` 4범주 직속 문서의 tags 첫 항목 정합, 실체 0건 폴더(골격 폴더 제외 - 성격 판단은 감사자 몫), 문서 간 상대 링크 정합(대소문자, 유니코드 정규화 불일치 포함), 마크다운 링크 표시텍스트-대상 실존 정합(파일명 형태 표시텍스트가 실존 대상을 가리키는지 - 자연어 문구와 타이틀은 제외), 파일명의 크로스 플랫폼 이식성(윈도우 금지 문자, 예약어), 비ASCII 문장 부호 검출(em dash, 화살표, 가운뎃점, 말줄임표, 둥근 따옴표 - 백틱/코드펜스 예시와 고정폭 box-drawing 트리는 제외). epistemic-auditor의 형식 점검을 이관받은 것이며, 의미 판단과 git 맥락 검출은 감사자 몫이다 (cf. [agent-roles.md](agent-roles.md)).

- 임계값은 보수적 초기값으로 두고 운영하며 조정한다. 스크립트 상단 상수(`SIZE_LIMIT_NODE`, `SIZE_LIMIT_TEMPORAL`, `FOLDER_MD_LIMIT`, `TEMPORAL_MIX_REPEAT`)로 관리한다.
- 실행: 워크스페이스 루트에서 `python3 AGENTS/tools/audit.py .` (윈도우는 `python` 또는 `py`).
- 의존성: Python 3.8+ 표준 라이브러리만. 특정 AI 도구, OS(operating system)에 의존하지 않는다. git에도 의존하지 않는다 - git 맥락 검출은 epistemic-auditor가 담당한다. 사람, 어느 AI 도구의 협업자든 동일하게 실행 가능.
- 자동 실행: GitHub Actions([.github/workflows/epistemic-audit.yml](../.github/workflows/epistemic-audit.yml))가 push, pull request 시점에 실행한다. 새 세션 시작 시의 실행 의무는 [AGENTS.md](../AGENTS.md) "세션 시작" 참조.
- 종료 코드: 위반 없음(경고만 있거나 없음) 0, 위반 있음 1, 사용법 오류(인자가 디렉토리가 아님) 2.
- 강제력: 위반(violation)은 CI를 실패시킨다(exit 1). 경고(warning)는 통과시킨다(exit 0) - 사람/LLM 판단이 필요한 신호라 기계적으로 차단하지 않는다. 그래서 경고는 방치하면 무한 누적될 수 있다. 감사 시 경고를 훑어 정리(수정)하거나 의식적으로 수용(현 상태가 맞다고 판단)해 미결 경고가 쌓이지 않게 한다.

## Claude Code 절차 스킬 래퍼

`.claude/skills/` 하위의 각 SKILL.md(ingest, unit-task-start, unit-task-finish)는 절차 문서를 해당 시점에 로드하는 씬 래퍼다. 절차 내용을 복사하지 않고 트리거 조건과 SSOT(single source of truth) 링크만 담는다 - 복사하면 SSOT 위배 + drift. 다른 도구 사용자는 SSOT 절차 문서를 직접 읽으면 동일 효과를 얻는다.
