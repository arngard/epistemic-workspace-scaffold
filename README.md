---
date created: 2026-04-18
date modified: 2026-07-06
tags: [소개]
---

한국어 | [English](README.en.md)

# Epistemic Workspace Scaffold

문서를 인식론적 범주로 나누는 워크스페이스 골격. 인간과 AI가 함께 일할 때 상위 의도와 근거가 유실되지 않게 한다. 설계 문서를 네 범주로 분류한다.

- Ontology: 무엇이 존재하는가
- Knowledge: 세상이 어떠한가
- Strategy: 왜 이렇게 결정했는가
- Architecture: 어떻게 만드는가

왜 이렇게 하는가는 [AGENTS/why-epistemic-workspace.md](AGENTS/why-epistemic-workspace.md), 운영 지침과 원칙은 단일 진입점 [AGENTS.md](AGENTS.md)를 본다.

## 디렉토리 구조

```
(workspace-root)/
├── _docs/             <- 코드로 표현할 수 없는 지식
│   ├── _ontology/         <- 도메인 개념
│   ├── _knowledge/        <- 외부 사실
│   ├── _strategy/         <- 결정과 근거
│   ├── _architecture/     <- 설계 명세
│   └── _worklog/          <- 작업 상태, 이력
├── _reference/        <- 사용자가 dump한 raw 자료의 immutable 보관 영역
└── _implementation/   <- 구현체 코드
    ├── backend/
    └── web/
```

## 사용법

스캐폴드를 가져오는 방식은 셋이다. GitHub fork, 단순 복사(clone 또는 template), clone 후 원본을 `upstream` 원격으로 연결(부모 개선을 계속 받으려면 이 방식 - `git fetch upstream && git merge upstream/main`). 채택 방식은 이후 전환이 번거로우니 고른 방식과 이유를 결정 문서로 남기기를 권한다.

가져온 뒤에는 워크스페이스 폴더 이름을 프로젝트에 맞게 바꾸고, `_docs/_worklog/TASK_TREE.md`의 "워크스페이스 초기 세팅" 체크리스트를 따르며, AGENTS.md를 프로젝트 요구에 맞게 조정한다.

## 더 읽을 거리

- [AGENTS/why-epistemic-workspace.md](AGENTS/why-epistemic-workspace.md) - 설계 철학과 근거
- [AGENTS/workspace-and-project-structure.md](AGENTS/workspace-and-project-structure.md) - 구조 근거
- [AGENTS/how-to-separate-docs-folders.md](AGENTS/how-to-separate-docs-folders.md) - `_docs/` 분류 기준
