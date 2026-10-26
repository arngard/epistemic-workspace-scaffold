---
date created: 2026-04-18
date modified: 2026-10-26
tags: [agents, 도구, 환경, IDE, epistemic-rules]
---

# 도구/환경 정보

감사 스크립트의 구성, 실행, 시험은 [tools.md](tools.md)가 안내한다.

## 도구별 자동 참조 파일

각 AI 도구는 고유 경로의 파일을 자동으로 참조한다. 진입점 파일은 지침을 담지 않고 [AGENTS.md](../../AGENTS.md)를 가져오거나 가리킨다.

| 도구 | 진입점 파일 | 비고 | 조회 일자 |
|------|------------|------|-----------|
| Claude Code | 루트 [CLAUDE.md](../../CLAUDE.md)와 `AGENTS.md`가 있는 폴더의 `CLAUDE.md` | 시작 시 작업 폴더와 그 상위 폴더의 `CLAUDE.md`를 읽는다. 하위 폴더의 `CLAUDE.md`는 그 폴더의 파일을 읽거나 쓰거나 고칠 때 불린다. `@경로` 가져오기를 가져오는 파일 기준 상대 경로로, 네 단계까지 재귀로 펼친다. 코드 스팬과 코드 블록 안의 가져오기는 펼치지 않는다. 작업 폴더나 상위 폴더에 `CLAUDE.md`가 있으면 `AGENTS.md`를 기본으로 읽지 않으며, 이를 바꾸는 설정은 사용자 설정과 관리 설정에서만 읽고 프로젝트 설정에서는 읽지 않는다. | 2026-10-25 |
| Codex | 저장소 루트부터 작업 폴더까지의 `AGENTS.md` | 저장소 루트에서 작업 폴더까지 경로에 있는 `AGENTS.md`를 읽는다. `@` 줄을 가져오기로 펼치지 않는다. 별도 진입점 파일을 두지 않는다. | 2026-10-25 |
| GitHub Copilot | [.github/copilot-instructions.md](../../.github/copilot-instructions.md) | 저장소 전체 지침으로 읽는다. 저장소의 `AGENTS.md`도 에이전트 지침으로 읽으며 에이전트 작업에서는 가장 가까운 `AGENTS.md`가 우선한다. `@` 가져오기 펼침과 IDE별 읽기 대상은 조회한 문서에 없다. | 2026-10-26 |
| Antigravity | 없음 | `agy` CLI가 루트 [AGENTS.md](../../AGENTS.md)를 직접 자동 로드한다(미확인). 별도 진입점 파일을 두지 않는다. | 미확인 |
| Kiro | `.kiro/` 디렉토리 | AWS의 VS Code 기반 AI IDE. spec-driven development 지원. 디렉토리 세팅은 도구 자체가 수행. | 미확인 |
| Cursor | `.cursor/rules/` 또는 `.cursorrules` | 현 스캐폴드는 진입점을 포함하지 않는다. Cursor를 사용하는 경우 별도 설정한다. | 미확인 |

출처: [Claude Code memory](https://code.claude.com/docs/en/memory), [Codex AGENTS.md](https://developers.openai.com/codex/guides/agents-md), [Copilot repository instructions](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions). "미확인"은 공식 문서로 확인하지 못한 행이다.

Claude Code에서 실측한 동작: 깊은 하위 폴더의 파일을 다루거나 셸 `cat`으로 파일을 볼 때도 그 경로의 폴더 `CLAUDE.md`가 불린다. 문장 중간의 `@경로`도 가져오기로 펼친다.

재확인 조건: 도구의 읽기 동작이 바뀐다는 공지를 보거나 이 표와 다른 동작을 실측하면 공식 문서를 다시 조회하고 표와 조회 일자를 고친다.

## 진입점 유지 원칙

- `AGENTS.md`가 있는 폴더(루트 포함)마다 내용이 `@AGENTS.md` 한 줄인 `CLAUDE.md`를 둔다. 지침 자체는 적지 않는다(중복, 불일치 방지). 규범 폴더의 예외는 [folder-structure.md](folder-structure.md) "폴더 구조와 디스크립터".
- Copilot 진입점과 루트 [AGENTS.md](../../AGENTS.md)가 `@` 표기를 설명한다. `@`로 시작하는 줄은 그 경로의 파일을 지금 읽으라는 뜻이다.
- 가져오기를 펼치지 않는 도구에서 `@` 대상과 폴더 `AGENTS.md`를 읽는 것은 모델이 그 설명을 따르는 데 기대며 보장되지 않는다.
- 가져오기가 아닌 글 속의 `@경로` 언급은 인라인 코드로 쓴다. Claude Code는 문장 중간의 `@경로`도 펼친다.
- 새로운 도구가 추가되면: 해당 도구의 자동 참조 경로에 진입점 파일을 만들고, 이 표에 등록하며 공식 문서의 조회 일자(확인하지 못했으면 "미확인")를 적는다.

## Claude Code 래퍼(절차 스킬, 서브에이전트)

`.claude/skills/` 하위의 각 SKILL.md(ingest, unit-task-start, unit-task-finish, pr-create, pr-respond)는 절차 문서를 해당 시점에 로드하는 씬 래퍼다. 절차 내용을 복사하지 않고 트리거 조건과 SSOT(single source of truth) 링크만 담는다 - 복사하면 SSOT 위배 + drift. 다른 도구 사용자는 SSOT 절차 문서를 직접 읽으면 동일 효과를 얻는다.

`.claude/agents/` 하위의 서브에이전트 정의도 같은 원칙을 따른다. 역할 정의 원본([agent-roles.md](agent-roles.md)가 링크하는 역할별 하위 문서)을 읽고 따르라는 지시, 도구별 제한, 호출 판단용 역할 요약(description)만 담고, 점검 항목이나 절차를 옮겨 적지 않는다 - 옮겨 적은 사본은 원본이 바뀔 때 어긋나며, 실제로 실행되는 것은 사본이다.
