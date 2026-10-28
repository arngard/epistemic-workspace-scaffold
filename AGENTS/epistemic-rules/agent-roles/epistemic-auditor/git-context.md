---
date created: 2026-10-28
date modified: 2026-10-28
tags: [agents, 역할, 감사, epistemic-rules]
description: 감사자가 git 이력과 상태로 보는 점검 항목의 기준과 확인 명령
---

# git 맥락 검출

> [epistemic-auditor.md](../epistemic-auditor.md) "점검 항목"의 git 맥락 검출 세부. 감사 스크립트가 맡지 않는 항목을 git 이력과 상태로 확인한다. 수행 순서 안의 자리는 [procedure.md](procedure.md) "수행 순서"가 정한다.

## 점검 대상

- TASK_TREE 루트/1-depth 노드의 마크 커밋 없는 삭제
- 루트가 아닌 완료 노드의 단독 삭제 - 조상 루트와 함께 제거되거나 완료된 중위 노드의 하위로 정리된 경우가 아닌 삭제
- TASK_TREE 브랜치 속성이 가리키는 브랜치와 워크트리의 실존 대조
- `reference/` 원본 파일의 수정, 삭제, 이동(불변 원칙 위반). 운영 파일([workspace-and-project-structure.md](../../workspace-and-project-structure.md) "네이밍 규칙: 워크스페이스 scaffolding과 콘텐츠")과 등재된 진척 기록 폴더의 변경은 제외한다.
- `date closed` 히스토리 문서의 본문 변경(동결 위반 - 후속 문서 링크 추가와 정합 유지 수정은 허용, ref: [document-temporality.md](../../document-temporality.md) "날짜 프리픽스의 의미와 종결 신호")
- TASK_TREE `[x]` 완료 루트의 과다 잔존
- 상류 머지 밖에서 상류 묶음 목록(`tools/bundle-manifest.sha256`)을 바꾼 본 레포 커밋

## 확인 방법

- 브랜치 속성의 실존은 `git branch -a`와 `git worktree list`로, `date closed` 문서의 본문 변경은 `git log -p`로 본다.
- `reference/` 원본의 수정, 삭제, 이동은 `git -c core.quotepath=false log --first-parent --diff-filter=MDR --name-status <범위> -- reference/ ":(exclude)reference/AGENTS.md" ":(exclude)reference/CLAUDE.md" ":(exclude)reference/AGENTS/" ":(exclude)reference/INDEX*.md" ":(exclude)reference/INDEX.yaml"`로 본다(자손이 등재한 진척 기록 폴더도 뺀다). `--first-parent`는 머지 커밋에서만 가한 수정도 잡는다.
  - 범위는 직전 클린 커밋이 있으면 `<직전 클린 커밋>..HEAD`로, 없으면 상속 이력을 빼기 위해 `<상류>/main..HEAD`로 잡는다. 상류 원격이 없으면 이력 없이 가져온 워크스페이스로 보고 범위 지정 없이 본다. 스캐폴드 이력을 받았는데 상류 원격이 없으면 시작 상태가 갖춰지지 않은 것으로 보고한다.
  - 이동(R 행)은 파생 노드의 링크를 끊으므로 위반으로 보고한다. 머지 커밋이 나오면 `git log <머지>^1..<머지>^2`로 원인 커밋을 찾는다.
- 상류 머지 밖에서 상류 묶음 목록을 바꾼 커밋은 `git log --no-merges --full-history --format=%h HEAD --not <상류>/main [<직전 클린 커밋>] -- AGENTS/epistemic-rules/tools/bundle-manifest.sha256`로 보고(`<상류>`는 위의 상류 원격, 직전 클린 커밋은 있을 때만 넣는다), 출력이 있으면 위반이다. `--full-history`는 상류 머지 뒤에도 자손 커밋이 가려지지 않게 한다.
  - 상류 저장소 자신에서는 이 확인이 "해당 없음"이며, 감사 대상이 상류 저장소 자신인지는 의뢰하는 쪽이 의뢰할 때 알린다. 상류 원격이 없으면 이 확인을 하지 않고 보고에 "확인 불가(상류 원격 없음)"로 적는다.
  - 충돌을 풀면서 머지 커밋 안에서 목록을 다시 만든 경우는 이 명령이 잡지 못한다.
