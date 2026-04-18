---
date created: 2026-04-18
date modified: 2026-04-18
tags: [agents, 문서관리, 네이밍]
---

# AI 진입점을 AGENTS.md로 하고 CONVENTIONS.md를 쓰지 않는 이유

## 결정

루트에 `AGENTS.md`를 두고, 각 AI 도구의 진입점 파일(CLAUDE.md, .kiro/, .gemini/ 등)은 AGENTS.md를 가리키는 포인터만 담는다.

## 근거
- 각 AI 도구는 자기만의 파일명을 사용함 (Claude→CLAUDE.md, Gemini→.gemini/, Copilot→.github/copilot-instructions.md). 범용 표준 파일명은 존재하지 않음.
- AGENTS.md에 본체(지침)를 두고, 각 도구별 파일은 "AGENTS.md를 읽어라"라는 포인터만 담는 구조로 해결.
