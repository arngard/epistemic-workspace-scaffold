---
date created: 2026-04-18
date modified: 2026-11-22
tags: [agents, 도구, 환경, IDE, epistemic-rules]
---

# 도구/환경 정보

감사 스크립트의 구성, 실행, 시험은 [tools.md](tools.md)가 안내한다.

## 도구별 자동 참조 파일

각 AI 도구는 고유 경로의 파일을 자동으로 참조한다. 진입점 파일은 지침을 담지 않고 [AGENTS.md](../../AGENTS.md)를 가져오거나 가리킨다. 도구마다 읽는 파일과 가져오기 펼침 동작, 출처와 조회 일자, 실측 동작, 재확인 조건은 [entry-files.md](tool-environment/entry-files.md)에 있다. 진입점 파일을 만들거나 고칠 때, 도구를 더할 때, 도구가 그 표와 다르게 읽는다고 의심될 때 읽고, 표와 다른 동작을 실측하면 공식 문서를 다시 조회해 표를 고친다.

## 도구의 기억 기능

도구가 세션 밖에 두는 기억 기능은 머신이나 계정에 묶여 다른 작업자에게 보이지 않고, 도구에 따라 다른 머신에도 없다. 작업에서 얻은 규칙, 사실, 교훈은 워크스페이스 문서에 기록하고, 기억 기능에는 레포(레포지토리)에 둘 수 없는 개인 사정만 둔다.

## 진입점 유지 원칙

- `AGENTS.md`가 있는 폴더(루트 포함)마다 내용이 `@AGENTS.md` 한 줄인 `CLAUDE.md`를 둔다. 지침 자체는 적지 않는다(중복, 불일치 방지). 규범 폴더의 예외는 [folder-structure.md](folder-structure.md) "폴더 구조와 디스크립터".
- Copilot 진입점과 루트 [AGENTS.md](../../AGENTS.md)가 `@` 표기를 설명한다. `@`로 시작하는 줄은 그 경로의 파일을 지금 읽으라는 뜻이고, 경로는 레포 루트가 아니라 그 줄이 든 파일의 위치 기준이다.
- 루트 [AGENTS.md](../../AGENTS.md)는 요지 가져오기 줄 아래에 요지와 요지가 가져오는 문서를 `@[이름](경로)` 줄로 나란히 둔다. Antigravity가 펼치는 형식이고, Antigravity는 펼친 파일 안의 가져오기를 다시 펼치지 않기 때문이다. 요지의 가져오기 대상이 바뀌면 이 줄도 함께 고친다.
- 가져오기를 펼치지 않는 도구에서 `@` 대상과 폴더 `AGENTS.md`를 읽는 것은 모델이 그 설명을 따르는지에 의존하며 보장되지 않는다.
- 가져오기가 아닌 글 속의 `@경로` 언급은 인라인 코드로 쓴다. Claude Code는 문장 중간의 `@경로`도 펼친다.
- 새 도구가 추가되면 그 도구의 자동 참조 경로에 진입점 파일을 만들고, [entry-files.md](tool-environment/entry-files.md)의 표에 등록하며 공식 문서의 조회 일자(확인하지 못했으면 "미확인")를 적는다.

## Claude Code 래퍼(절차 스킬, 서브에이전트)

`.claude/skills/` 하위의 각 SKILL.md(ingest, unit-task-start, unit-task-finish, pr-create, pr-respond, document-authoring, norm-authoring, workspace-setup, workflow-wrapping)는 절차 문서를 해당 시점에 로드하는 얇은 래퍼(thin wrapper)다. 절차 내용을 복사하지 않고 트리거 조건과 SSOT(single source of truth; 단일 진실 공급원) 링크만 담는다. 복사하면 SSOT를 위배하고 사본이 원본과 어긋난다. 다른 도구 사용자는 SSOT 절차 문서를 직접 읽으면 같은 효과를 얻는다.

`.claude/agents/` 하위의 서브에이전트 정의도 같은 원칙을 따른다. 역할 정의 원본(상류 역할은 [agent-roles.md](agent-roles.md)가 링크하는 역할별 문서, 인스턴스 역할은 루트 `AGENTS.md`가 링크하는 낱개 문서)을 읽고 따르라는 지시, 도구별 제한, 호출 판단용 역할 요약(description)만 담고, 점검 항목이나 절차를 옮겨 적지 않는다 - 옮겨 적은 사본은 원본이 바뀔 때 어긋나며, 실제로 실행되는 것은 사본이다.

## 세션 시작 훅

세션 시작 요약([tools.md](tools.md) "세션 시작 요약 스크립트")은 도구의 세션 시작 훅이 실행하게 한다. 규범이 실행을 요구하는 문장보다 훅이 확실하게 지켜진다. 훅 설정에는 스크립트를 부르는 명령만 두고 절차 내용은 적지 않는다 - 절차의 SSOT는 [session-boundaries.md](session-boundaries.md) "세션 시작"이고, 요약 머리말이 그 절을 가리킨다. 훅이 없는 도구에서는 그 절의 문장대로 모델이 스크립트를 직접 실행한다. 도구마다 훅을 거는 자리, 실행 조건, 주입 길이, 셸과 제한 시간, 인스턴스가 고칠 수 있는 인자는 [session-start-hook.md](tool-environment/session-start-hook.md)에 있고, 훅 명령이나 훅 인자, 요약 출력 형식을 고칠 때 읽는다.
