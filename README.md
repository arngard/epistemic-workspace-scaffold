---
date created: 2026-04-18
date modified: 2026-10-23
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
├── AGENTS/            <- 에이전트 운영 규범 (진입점은 AGENTS.md)
└── _implementation/   <- 구현 프로젝트들 (프로젝트마다 하위 폴더)
    ├── <project-A>/
    └── <project-B>/
```

## 사용법

스캐폴드를 가져오는 방식은 둘이다.

- 상류와 연결하는 방식: GitHub fork나 clone으로 스캐폴드 이력을 받고, 원본을 `upstream` 원격으로 연결한다. clone이면 `git remote rename origin upstream`으로 원본 원격의 이름을 `upstream`으로 바꾸고 자기 저장소를 `origin`으로 추가한다. fork면 `git remote add upstream https://github.com/arngard/epistemic-workspace-scaffold.git`로 추가한다. 부모의 개선은 `git fetch upstream && git merge upstream/main`으로 받는다.
- 이력 없이 가져오는 방식: GitHub template으로 저장소를 만들거나 기존 프로젝트에 파일을 복사한다. 스캐폴드 이력을 받지 않으므로 상류 개선을 머지로 받을 수 없다.

스캐폴드 이력을 받았다면 `upstream` 연결은 고를 수 있는 선택지가 아니라 시작 상태다. 감사는 이 연결로 상류 커밋과 자기 커밋을 구분한다. 고른 방식과 이유는 결정 문서로 남긴다.

가져온 뒤에는 워크스페이스 폴더 이름을 프로젝트에 맞게 바꾸고, `_docs/_worklog/TASK_TREE.md`의 "워크스페이스 초기 세팅" 체크리스트를 따르며, AGENTS.md의 "이 워크스페이스의 정체" 절을 프로젝트에 맞게 특수화한다. 그 밖의 계승 자산을 바꿀 때는 [AGENTS/instance-specialization.md](AGENTS/instance-specialization.md)를 따른다.

## 더 읽을 거리

- see: [AGENTS/why-epistemic-workspace.md](AGENTS/why-epistemic-workspace.md) - 설계 철학과 근거
- see: [AGENTS/workspace-and-project-structure.md](AGENTS/workspace-and-project-structure.md) - 구조 근거
- see: [AGENTS/how-to-separate-docs-folders.md](AGENTS/how-to-separate-docs-folders.md) - `_docs/` 분류 기준
