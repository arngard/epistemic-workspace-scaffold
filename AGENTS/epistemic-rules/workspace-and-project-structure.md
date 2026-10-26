---
date created: 2026-04-18
date modified: 2026-10-26
tags: [agents, 워크스페이스, epistemic-rules]
---

# 워크스페이스 구조

## 목표

하나의 레포를 워크스페이스로 다루면서, 그 안에 설계 문서와 프로젝트를 모두 포함한다.

## 네이밍 규칙: 워크스페이스 scaffolding과 콘텐츠

폴더는 두 종류로 나뉜다.

- 워크스페이스 scaffolding(골격): 워크스페이스를 처음 세팅할 때 만들어지는 고정 골격. 정보가 어디에 놓이는지를 결정하는 구조. 프로젝트 수명 동안 추가되거나 사라지지 않는다. 루트에는 골격만 두고, `epistemic-structure/` 안에는 네 범주만 둔다.
- 콘텐츠: 작업하면서 생기고 변하는 실제 산출물. 문서 파일, 프로젝트 폴더 등. 콘텐츠는 범주 폴더와 `implementation/`, `reference/` 안에서 시작하므로 골격과 같은 층에 섞이지 않는다.

콘텐츠와 같은 층에 놓이는 운영 파일(`AGENTS.md`, `CLAUDE.md`, `AGENTS/`)은 대문자 이름으로 구분되고 파일시스템 정렬에서도 앞에 모인다. 골격이 사라지지 않는다는 성질은 감사 도구가 골격 이름 목록으로 안다.

### 하위 문서 폴더 규칙

어떤 문서가 길어져서 여러 하위 문서로 쪼개야 할 때, 상위 문서와 같은 이름의 폴더를 만들어 하위 문서를 넣는다. 예: `pr-workflow.md`의 하위 문서들은 `pr-workflow/`에 둔다.

- 분류용 하위 폴더도 부모 문서를 둔다(`X.md` + `X/`). 부모 문서 없이 디스크립터만 둔 분류 폴더는 쓰지 않는다. 날짜, 시각, 알파벳 같은 순차 분류는 예외다 (ref: [folder-structure.md](folder-structure.md) "폴더 구조와 디스크립터").
- 자식 파일명에 부모 이름을 프리픽스로 반복하지 않는다. 폴더 경로가 계층 맥락을 준다. 하이픈 나열(`X-sub.md`)이나 부모명과 다른 폴더명(`X.md` + `other/`)은 쓰지 않는다.
- 동명 문서-폴더 쌍(`X.md` + `X/`)은 하위 문서 묶음 관계의 예약 신호다. 그 관계가 아닌 파일과 폴더에 같은 이름을 쓰지 않는다 - 무관한 동명 쌍은 계층 관계로 오독된다. 감사 스크립트가 하위 문서 없는 동명 쌍을 검출한다.
- 자식이 또 자식을 가지면 같은 규칙을 재귀 적용한다 (`X.md`, `X/Y.md`, `X/Y/Z.md`).
- 하위 문서 폴더를 신설하면 그 폴더의 디스크립터(AGENTS.md)와 `CLAUDE.md`를 같은 커밋에 동반한다 (ref: [folder-structure.md](folder-structure.md) "폴더 구조와 디스크립터"). 규범 폴더(`AGENTS/`와 그 아래)는 예외다.
- 이동, 리네임에 따른 연쇄 갱신은 [folder-structure.md "폴더, 파일 이동 시 연쇄 갱신"](folder-structure.md) 참조.

## 최상위 구조

```
(workspace-root)/                      <- 워크스페이스 루트
├── AGENTS.md                           <- AI 에이전트 공통 지침 (모든 도구의 진입점)
├── AGENTS/                             <- 규범 폴더(상류 묶음 `epistemic-rules`)
├── worklog.md                          <- 각 골격 폴더의 부모 문서
├── worklog/                            <- 작업 상태, 작업 트리
├── reference.md
├── reference/                          <- 사용자가 dump한 raw 자료의 immutable 보관 영역
├── epistemic-structure.md
├── epistemic-structure/                <- 코드로 표현할 수 없는 지식
│   ├── ontology.md                     <- 각 범주 폴더의 부모 문서
│   ├── ontology/                       <- 도메인 개념 정의 ("무엇이 존재하는가")
│   ├── knowledge.md
│   ├── knowledge/                      <- 외부 사실, 환경, 벤치마크 ("세상이 어떠한가")
│   ├── strategy.md
│   ├── strategy/                       <- 우리의 결정과 근거 ("왜 이렇게 하기로 했는가")
│   ├── architecture.md
│   └── architecture/                   <- 설계 명세 ("어떻게 만드는가")
├── implementation.md
└── implementation/                     <- 구현 프로젝트들 (프로젝트마다 하위 폴더)
    ├── <project-A>/                    <- 각 프로젝트의 실제 소스 (또는 서브모듈 포인터 등)
    └── <project-B>/
```

`epistemic-structure/` 하위 폴더에 새 문서를 배치할 때의 분류 기준은 [epistemic-structure/AGENTS/epistemic-rules.md](../../epistemic-structure/AGENTS/epistemic-rules.md) "판별 규칙" 참조. `reference/` 운용은 [`../../reference/AGENTS.md`](../../reference/AGENTS.md)와 [`ingest-workflow.md`](ingest-workflow.md) 참조.

워크스페이스 안의 단위 작업(자료 N건 묶음 ingest, 메타 결정, 정책 변경, 큰 마이그레이션 등)은 진입, 진행, 종료 흐름이 정해져 있다. 단위 작업의 정의는 [unit-task.md](unit-task.md) 참조. 단위 작업 시작 시 어떤 절차를 거쳐야 하는지는 [unit-task-workflow.md](unit-task-workflow.md) 참조. 워크로그(`worklog/`)의 TASK_TREE와 STATUS 레지스트리는 그 흐름의 진입, 종료 시점에서 갱신되는 운영 메타다. 완료 이력의 SSOT(single source of truth)는 git 이력이다.

## 문서와 코드의 역할 분담

`epistemic-structure/`는 코드로 표현할 수 없는 것 위주로 담는다. 도메인 개념, 외부 사실, 결정 근거, 상위 수준의 구조 결정이 이에 해당한다.

구현이 시작되면, 모듈의 상세 스펙(인터페이스 시그니처, 데이터 타입, 에러 계약)은 코드 자체가 명세가 된다. 확정된 추상화 레이어에는 `[to:@AGENT: 확정된 추상화 레이어]` 형식의 공용 태그 주석을 달아 변경을 통제한다. 태그 형식은 [agent-tag-format.md](agent-tag-format.md) 참조.

코드와 1:1 대응되는 대규모의 명세 문서를 별도로 유지관리하지 않는다. 문서에서 코드의 동작을 설명하거나 맥락을 제공하는 것은 자연스러운 일이며, 그것 자체가 문제는 아니다.

| 위치 | 담는 것 |
|------|---------|
| `epistemic-structure/` | 코드로 표현할 수 없는 것: 도메인 개념, 외부 사실, 결정 근거, 상위 구조 결정. |
| 코드 (인터페이스 + 공용 태그 주석) | 모듈 인터페이스, 타입, 에러 계약. 코드가 곧 명세. 확정된 레이어는 `[to:@AGENT]` 태그로 보호. |
| 코드 (구현) | 모듈 내부 구현. 자기설명적 코드 + 필요 시 주석. |
