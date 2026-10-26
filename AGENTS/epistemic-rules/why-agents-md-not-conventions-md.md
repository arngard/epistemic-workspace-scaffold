---
date created: 2026-04-18
date modified: 2026-10-26
tags: [agents, 문서관리, 네이밍, epistemic-rules]
---

# AI 진입점을 AGENTS.md로 하고 CONVENTIONS.md를 쓰지 않는 이유

## 결정

지침 본체는 루트와 각 폴더의 `AGENTS.md`에 둔다. 각 AI 도구의 진입점 파일은 본체를 담지 않는다. Claude Code 진입점은 `AGENTS.md`가 있는 폴더마다 두는 `CLAUDE.md`이며 내용은 `@AGENTS.md` 한 줄이다. Copilot 진입점은 루트 `AGENTS.md`를 먼저 읽고 `@` 줄의 대상과 작업 폴더의 `AGENTS.md`를 함께 읽으라는 포인터다. `AGENTS.md`를 직접 읽는 도구에는 진입점 파일을 두지 않는다. 도구별 읽기 동작과 조회 일자는 [tool-environment.md](tool-environment.md) "도구별 자동 참조 파일"에 있다.

## 근거
- 각 AI 도구는 자기만의 파일명을 사용함 (Claude Code->CLAUDE.md, Copilot->.github/copilot-instructions.md). `AGENTS.md`를 직접 읽는 도구(Codex, Antigravity(미확인))도 있으나 모든 도구가 읽는 범용 표준 파일명은 아직 없음.
- Claude Code는 작업 폴더나 그 상위 폴더에 `CLAUDE.md`가 있으면 `AGENTS.md`를 기본으로 읽지 않는다. 이를 바꾸는 설정은 사용자 설정과 관리 설정에서만 읽혀 저장소가 바꿀 수 없다. 그래서 `CLAUDE.md`가 `AGENTS.md`를 가져와야 한다.
- Claude Code는 폴더의 `CLAUDE.md`를 그 폴더의 파일을 다룰 때 불러들인다. 폴더마다 `@AGENTS.md` 한 줄의 `CLAUDE.md`를 두면 그 폴더의 `AGENTS.md`가 모델의 판단과 상관없이 읽힌다.
- 가져오기는 내용을 복사하지 않으므로 본체는 `AGENTS.md` 한 곳에 남는다.

## 기각안
- `CONVENTIONS.md` 등 자체 범용 파일명: 어느 AI 도구도 자동으로 읽지 않아 도구별 포인터가 여전히 필요하다. 파일명만 하나 더 늘 뿐 문제를 풀지 못한다.
- 도구별 파일에 본체를 각각 복제: 도구 수만큼 사본이 생겨 갱신 시 정합이 깨진다(SSOT(single source of truth) 위배).
- 루트 `CLAUDE.md`를 없애 Claude Code가 `AGENTS.md`를 직접 읽게 하는 안: 작업 폴더나 그 상위 폴더(저장소 밖 포함)에 `CLAUDE.md`가 하나라도 있으면 `AGENTS.md`를 읽지 않으므로, 루트 지침이 읽히는지가 저장소 밖 배치와 세션을 시작한 폴더에 달린다. 폴더 `CLAUDE.md`를 둔 하위 폴더에서 시작한 세션도 루트 `AGENTS.md`를 읽지 않는다.
- 링크만으로 폴더 `AGENTS.md`를 읽게 하는 안(루트 지침의 트리거 목록에서 폴더 `AGENTS.md`를 링크): 링크를 따라 읽는 것은 모델의 준수에 기대며 보장되지 않는다. 폴더 `CLAUDE.md`는 도구가 불러들이므로 그 폴더를 다루면 반드시 읽힌다.

## 전제와 재검토 트리거
- 전제: "AI 도구들이 공유하는 범용 진입점 파일명 표준이 없다." "Claude Code는 `CLAUDE.md`가 있으면 `AGENTS.md`를 읽지 않고, 저장소가 이를 바꿀 수 없다."
- 재검토 트리거: 도구 생태계가 단일 표준 진입점 파일명으로 수렴하면 포인터 구조의 필요가 사라지므로 이 결정을 재검토한다.
- 재검토 트리거: Claude Code가 `CLAUDE.md`와 함께 폴더 `AGENTS.md`를 읽게 되거나 저장소 설정으로 읽기 대상을 정할 수 있게 되면 폴더 `CLAUDE.md`가 필요 없어지므로 재검토한다.
