---
date created: 2026-11-22
date modified: 2026-11-22
tags: [agents, 도구, 환경, IDE, epistemic-rules]
description: AI 도구마다 자동으로 읽는 진입점 파일과 가져오기 펼침 동작의 조회표, 출처, 실측 동작, 재확인 조건
---

# 도구별 자동 참조 파일

[tool-environment.md](../tool-environment.md) "도구별 자동 참조 파일"의 하위 문서다. 진입점 파일을 만들거나 고칠 때, 도구를 더할 때, 도구가 이 표와 다르게 읽는다고 의심될 때 읽는다.

| 도구 | 진입점 파일 | 비고 | 조회 일자 |
|------|------------|------|-----------|
| Claude Code | 루트 [CLAUDE.md](../../../CLAUDE.md)와 `AGENTS.md`가 있는 폴더의 `CLAUDE.md` | 시작 시 작업 폴더와 그 상위 폴더의 `CLAUDE.md`를 읽는다. 하위 폴더의 `CLAUDE.md`는 그 폴더의 파일을 읽거나 쓰거나 고칠 때 읽힌다. `@경로` 가져오기는 그 줄이 든 파일 기준 상대 경로로 해석하고, 네 단계까지 재귀로 펼친다. 코드 스팬과 코드 블록 안의 가져오기는 펼치지 않는다. 작업 폴더나 상위 폴더에 `CLAUDE.md`가 있으면 `AGENTS.md`를 기본으로 읽지 않으며, 이를 바꾸는 설정은 사용자 설정과 관리 설정에서만 읽고 프로젝트 설정에서는 읽지 않는다. | 2026-10-25 |
| Codex | 레포(레포지토리) 루트부터 작업 폴더까지의 `AGENTS.md` | 레포 루트에서 작업 폴더까지 경로에 있는 `AGENTS.md`를 읽는다. `@` 줄을 가져오기로 펼치지 않는다. 별도 진입점 파일을 두지 않는다. | 2026-10-25 |
| GitHub Copilot | [.github/copilot-instructions.md](../../../.github/copilot-instructions.md) | 레포 전체 지침으로 읽는다. 레포의 `AGENTS.md`도 에이전트 지침으로 읽으며 에이전트 작업에서는 가장 가까운 `AGENTS.md`가 우선한다. `@` 가져오기 펼침과 IDE(integrated development environment; 통합 개발 환경)별 읽기 대상은 조회한 문서에 없다. | 2026-10-26 |
| Antigravity | 없음 | `agy`를 실행한 폴더와 그 상위 폴더를 레포 루트까지 올라가며 `AGENTS.md`와 `GEMINI.md`를 읽는다. 하위 폴더의 규칙은 그 안의 파일을 다뤄도 읽지 않는다. 규칙 안의 가져오기는 `@[이름](경로)` 형식만 펼치고, 그 경로는 규칙 파일 기준 상대 경로다. 별도 진입점 파일을 두지 않는다. | 2026-11-08 |

출처: [Claude Code memory](https://code.claude.com/docs/en/memory), [Codex AGENTS.md](https://developers.openai.com/codex/guides/agents-md), [Copilot repository instructions](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions), [Antigravity rules](https://antigravity.google/docs/rules/). "미확인"은 공식 문서로 확인하지 못한 행이다.

Claude Code에서 실측한 동작: 깊은 하위 폴더의 파일을 다루거나 셸 `cat`으로 파일을 볼 때도 그 경로의 폴더 `CLAUDE.md`가 읽힌다. 문장 중간의 `@경로`도 가져오기로 펼친다.

Antigravity에서 실측한 동작: 줄 전체가 `@경로`인 줄은 펼치지 않는다. 펼쳐 넣은 파일 안의 `@[이름](경로)`는 다시 펼치지 않는다.

재확인 조건: 도구의 읽기 동작이 바뀐다는 공지를 보거나 이 표와 다른 동작을 실측하면 공식 문서를 다시 조회하고 표와 조회 일자를 고친다.
