---
date created: 2026-04-18
date modified: 2026-07-06
tags: [agents, 문서관리, 네이밍]
---

# AI 진입점을 AGENTS.md로 하고 CONVENTIONS.md를 쓰지 않는 이유

## 결정

루트에 `AGENTS.md`를 두고, 각 AI 도구의 진입점 파일(CLAUDE.md, .kiro/, .gemini/ 등)은 AGENTS.md를 가리키는 포인터만 담는다.

## 근거
- 각 AI 도구는 자기만의 파일명을 사용함 (Claude->CLAUDE.md, Gemini->.gemini/, Copilot->.github/copilot-instructions.md). 범용 표준 파일명은 존재하지 않음.
- AGENTS.md에 본체(지침)를 두고, 각 도구별 파일은 "AGENTS.md를 읽어라"라는 포인터만 담는 구조로 해결.

## 기각안
- `CONVENTIONS.md` 등 자체 범용 파일명: 어느 AI 도구도 자동으로 읽지 않아 도구별 포인터가 여전히 필요하다. 파일명만 하나 더 늘 뿐 문제를 풀지 못한다.
- 도구별 파일에 본체를 각각 복제: 도구 수만큼 사본이 생겨 갱신 시 정합이 깨진다(SSOT 위배).

## 전제와 재검토 트리거
- 전제: "AI 도구들이 공유하는 범용 진입점 파일명 표준이 없다."
- 재검토 트리거: 도구 생태계가 단일 표준 진입점 파일명으로 수렴하면 포인터 구조의 필요가 사라지므로 이 결정을 재검토한다.
