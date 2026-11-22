---
date created: 2026-11-22
date modified: 2026-11-22
tags: [agents, 도구, 환경, epistemic-rules]
description: 도구마다 세션 시작 훅을 거는 자리, 실행 조건, 주입 길이, 셸과 제한 시간의 조회표
---

# 세션 시작 훅 설정

[tool-environment.md](../tool-environment.md) "세션 시작 훅"의 하위 문서다. 훅 명령이나 훅 인자, 요약 출력 형식을 고칠 때 읽는다.

| 도구 | 설정 | 비고 | 조회 일자 |
|------|------|------|-----------|
| Claude Code | 루트 `.claude/settings.json`의 `SessionStart` 훅 | 새 세션(`startup`)과 `/clear`에는 전체 요약을, 압축(`compact`) 뒤에는 원격 조회와 형식 감사를 뺀 요약을 다시 낸다. 이어 받는 세션(`resume`, `fork`)은 대화에 요약이 남아 있어 걸지 않는다. 요약은 `--hook-json`으로 `hookSpecificOutput.additionalContext` JSON에 담아 낸다. 주입 텍스트가 10,000자를 넘으면 파일로 빠진다. 프로젝트 설정은 세션을 시작한 폴더의 것만 읽어, 레포(레포지토리)의 하위 폴더에서 시작한 세션에서는 훅이 돌지 않는다. 이때는 [session-boundaries.md](../session-boundaries.md) "세션 시작"의 문장대로 스크립트를 직접 실행한다. 명령은 Python을 실행할 때 `python3`, `python`, `py -3` 순으로 찾고(see: [workspace-setup.md](../workspace-setup.md) "처음 설치"), 찾지 못하면 그 절을 가리키는 안내를 낸다. 명령은 bash로 돌며, 윈도우에서는 Git for Windows의 Git Bash가 있어야 한다. PowerShell로 돌면 명령이 파싱되지 않아 요약 없이 끝난다. 훅의 timeout은 스크립트 내부 제한 시간의 합보다 길게 둔다. 인스턴스는 이 파일의 훅 인자(머지 건수 등)를 고유 절차에 맞게 고칠 수 있다. 훅이 끝날 때까지 세션 시작이 기다리므로, 형식 감사가 오래 걸리는 레포는 `--no-audit`를 주고 감사를 백그라운드로 돌린다. | 2026-11-21 |
| Codex, GitHub Copilot, Antigravity | 미확인 | 세션 시작 훅의 지원 여부를 확인하지 않았다. | 미확인 |

출처: [Claude Code hooks](https://code.claude.com/docs/en/hooks), [Claude Code settings](https://code.claude.com/docs/en/settings).
