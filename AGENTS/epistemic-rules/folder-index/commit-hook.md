---
date created: 2026-11-03
date modified: 2026-11-07
tags: [규칙, 구조, epistemic-rules]
description: 색인을 다시 만드는 커밋 전 훅의 동작, 연결 값, 훅이 막지 못하는 경우
---

# 색인 커밋 전 훅

[folder-index.md](../folder-index.md) "생성과 확인"의 하위 문서다. 커밋할 때 색인을 다시 만드는 훅의 동작과 연결 방법을 정한다.

- 커밋 전 훅 `tools/hooks/pre-commit`은 `git rev-parse --show-toplevel`로 얻은 레포(레포지토리) 루트에 생성기를 돌려 바뀐 색인 파일을 스테이지에 더한다. 생성기는 훅 파일 자신의 위치로 찾는다. Python 3.9 이상을 찾지 못하거나 생성이 실패하면 커밋을 막는다.
- 훅 연결 값(`core.hooksPath`): 상류를 머지로 받은 레포의 기본 명령은 [tools.md](../tools.md) "색인 생성 스크립트". 이 묶음을 머지하지 않고 서브모듈로 포함한 레포는 서브모듈 경로를 앞에 붙인 hooks 폴더(`<서브모듈 경로>/AGENTS/epistemic-rules/tools/hooks`)를 주고 도구도 그 자리에서 실행한다. 이 생성기를 부모 루트에 돌려도 서브모듈 안은 건드리지 않는다. 자기 훅 폴더가 있는 레포는 그 `pre-commit`에서 이 훅을 부른다.
- 훅이 막지 못하는 경우: 연결하지 않은 클론은 색인을 다시 만들지 않고, 부분 스테이징과 경로를 지정한 커밋(`git commit -- <경로>`)은 워킹 트리(working tree) 기준 색인을 커밋할 수 있다. 훅 경로가 없으면(초기화하지 않은 서브모듈 등) git이 훅을 조용히 건너뛴다. 이런 낡은 색인은 CI(continuous integration; 지속적 통합) 감사가 위반으로 잡는다.
