---
date created: 2026-04-18
date modified: 2026-10-25
tags: [agents, 도구, 환경, IDE, epistemic-rules]
---

# 도구/환경 정보

## 도구별 자동 참조 파일

각 AI 도구는 프로젝트 루트에서 고유 경로의 파일을 자동으로 참조한다. 모든 진입점 파일은 루트의 [AGENTS.md](../../AGENTS.md)를 가리킨다.

| 도구 | 진입점 파일 | 비고 |
|------|------------|------|
| Claude Code | [CLAUDE.md](../../CLAUDE.md) | Anthropic CLI/IDE. 세션 시작 시 자동 로드. |
| GitHub Copilot | [.github/copilot-instructions.md](../../.github/copilot-instructions.md) | VS Code/JetBrains Copilot이 자동 로드. |
| Antigravity | 없음 | `agy` CLI가 루트 [AGENTS.md](../../AGENTS.md)를 직접 자동 로드한다. 별도 진입점 파일을 두지 않는다. |
| Kiro | `.kiro/` 디렉토리 | AWS의 VS Code 기반 AI IDE. spec-driven development 지원. 디렉토리 세팅은 도구 자체가 수행. |
| Cursor | `.cursor/rules/` 또는 `.cursorrules` | 현 스캐폴드는 진입점을 포함하지 않는다. Cursor를 사용하는 경우 별도 설정한다. |

## 진입점 유지 원칙

- 진입점 파일은 "[AGENTS.md](../../AGENTS.md)를 읽으라"는 포인터 역할만 하고 지침 자체는 적지 않는다(중복, 불일치 방지).
- 새로운 도구가 추가되면: 해당 도구의 자동 참조 경로에 진입점 파일을 만들고, 이 표에 등록한다.

## 기계 감사 스크립트

[tools/audit.py](tools/audit.py)는 형식 정합성을 결정론적으로 검사한다. 점검 범위는 front matter와 시간성, 문서 분량, 워크로그(STATUS, TASK_TREE) 스키마, 폴더와 디스크립터, 링크와 섹션 참조, 참조 표지, 파일명 이식성과 날짜 프리픽스 구분자, 문장 부호다. 점검 항목 목록의 SSOT는 audit.py 모듈 docstring의 "점검 항목"이며 여기에 다시 나열하지 않는다 - 목록을 여러 곳에 두면 검사가 추가될 때 어긋난다. 의미 판단과 git 맥락 검출은 감사자 몫이다 (see: [agent-roles/epistemic-auditor.md](agent-roles/epistemic-auditor.md)).

- 임계값은 보수적 초기값으로 두고 운영하며 조정한다. 공용 인프라 `tools/_audit_core.py` 상단의 상수로 관리한다.
- `.tmp/`는 에이전트의 임시 작업 공간이다. gitignore 대상이며 감사에서 제외된다.
- 실행: 워크스페이스 루트에서 `python3 AGENTS/epistemic-rules/tools/audit.py .` (윈도우는 `python` 또는 `py`).
- 의존성: Python 3.8+ 표준 라이브러리만. 특정 AI 도구, OS(operating system)에 의존하지 않는다. git에도 의존하지 않는다 - git 맥락 검출은 epistemic-auditor가 담당한다. 사람, 어느 AI 도구의 협업자든 동일하게 실행 가능.
- 자동 실행: GitHub Actions([.github/workflows/epistemic-audit.yml](../../.github/workflows/epistemic-audit.yml))가 push, pull request 시점에 실행한다. 새 세션 시작 시의 실행 의무는 [session-boundaries.md](session-boundaries.md) "세션 시작" 참조.
- 종료 코드: 위반 없음(경고만 있거나 없음) 0, 위반 있음 1, 사용법 오류(인자가 디렉토리가 아님) 2.
- 강제력: 위반(violation)은 CI를 실패시킨다(exit 1). 경고(warning)는 통과시킨다(exit 0) - 사람/LLM 판단이 필요한 신호라 기계적으로 차단하지 않는다. 그래서 경고는 방치하면 무한 누적될 수 있다. 감사 시 경고를 훑어 정리(수정)하거나 의식적으로 수용(현 상태가 맞다고 판단)해 미결 경고가 쌓이지 않게 한다.

## 의미 감사 트리거 판정 스크립트

[tools/check_semantic_audit.py](tools/check_semantic_audit.py)는 STATUS 레지스트리의 의미 감사 행과 git 이력을 대조해 트리거 조건 충족 여부만 판정한다. 감사를 수행하거나 강제하지 않고 판정 비용을 없애는 보조 도구다 - 조건 판정이 수동이면 어겼을 때 아무 신호가 없어 조건 충족을 놓친다.

- 실행: 워크스페이스 루트에서 `python3 AGENTS/epistemic-rules/tools/check_semantic_audit.py .` (윈도우는 `python` 또는 `py`).
- 종료 코드: 미충족 0, 충족 1, 판정 불가 2(수동 판정으로 넘긴다).
- audit.py와 달리 git에 의존하므로 별도 스크립트로 둔다. audit.py의 git 비의존 원칙은 유지된다.
- 임계 시간과 trailer 문구를 스크립트에 하드코딩하지 않고 STATUS 레지스트리의 주기/트리거 셀에서 읽는다 - 그 셀이 임계 조건의 SSOT이고, 인스턴스가 주기를 조정하면 스크립트가 따라간다.
- 시각 비교는 KST 고정이라 실행 머신의 시간대에 의존하지 않는다.

## Claude Code 래퍼(절차 스킬, 서브에이전트)

`.claude/skills/` 하위의 각 SKILL.md(ingest, unit-task-start, unit-task-finish, pr-create, pr-respond)는 절차 문서를 해당 시점에 로드하는 씬 래퍼다. 절차 내용을 복사하지 않고 트리거 조건과 SSOT(single source of truth) 링크만 담는다 - 복사하면 SSOT 위배 + drift. 다른 도구 사용자는 SSOT 절차 문서를 직접 읽으면 동일 효과를 얻는다.

`.claude/agents/` 하위의 서브에이전트 정의도 같은 원칙을 따른다. 역할 정의 원본([agent-roles/](agent-roles/AGENTS.md))을 읽고 따르라는 지시, 도구별 제한, 호출 판단용 역할 요약(description)만 담고, 점검 항목이나 절차를 옮겨 적지 않는다 - 옮겨 적은 사본은 원본이 바뀔 때 어긋나며, 실제로 실행되는 것은 사본이다.
