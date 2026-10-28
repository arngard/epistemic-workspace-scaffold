---
date created: 2026-10-26
date modified: 2026-10-28
tags: [규칙, 도구, epistemic-rules]
---

# 감사 도구

[tools/](tools/) 폴더는 에이전트 운영을 보조하는 실행 스크립트를 담는다. 문서가 아닌 도구 파일만 두며, 폴더 디스크립터를 두지 않고 이 문서가 그 안내를 맡는다. 이 도구의 코드를 만들거나 고칠 때는 [coding-guidelines.md](../../implementation/AGENTS/epistemic-rules/coding-guidelines.md)를 따른다.

## 구성

검사 진입점은 [audit.py](tools/audit.py) 하나, 파일을 쓰는 생성 진입점은 [build_index.py](tools/build_index.py) 하나다. 검사 로직은 공용 인프라([_audit_core.py](tools/_audit_core.py) 등)와 의미별 검사 모듈로 나뉘며 audit.py가 import해 조합한다. 모듈 구성은 audit.py 모듈 docstring의 "구조"에 있다.

그 밖의 도구는 성격으로 나뉜다. 사용자가 승인한 일만 명시적으로 실행하는 편집 도구는 [retag.py](tools/retag.py)이고, 읽기 전용 보조 도구는 [check_semantic_audit.py](tools/check_semantic_audit.py)(git 이력이 있어야 판정해 audit.py와 따로 둔다)와 [tag_inventory.py](tools/tag_inventory.py)다. `_docs/` 아래에 문서 폴더를 두던 옛 배치를 옮기는 배치 이전 도구 `migrate_layout.py`는 지금은 없고, 그 도구가 마지막으로 포함된 커밋은 2f2734c다. 사용 안내는 각 자리에 있다: 상류 묶음 목록은 아래 "색인 생성 스크립트", 태그 도구는 [tags.md](tags.md) "어휘 정리", 확장 지점은 [audit-extensions.md](audit-extensions.md).

## 시험

도구를 고친 뒤 워크스페이스 루트에서 `python3 -m unittest discover -s AGENTS/epistemic-rules/tools/tests -v`로 [tests/](tools/tests/)의 시험을 돌린다.

## 기계 감사 스크립트

[tools/audit.py](tools/audit.py)는 형식 정합성을 결정론적으로 검사한다. 점검 범위는 front matter와 시간성, 문서 분량, 워크로그(STATUS, TASK_TREE) 스키마, 폴더와 디스크립터, 폴더 색인, 링크와 섹션 참조, 참조 표지, 파일명 이식성과 날짜 프리픽스 구분자, 문장 부호, 태그 표기, 상류 묶음의 출처 태그와 동일성이다. 자손의 확장 검사도 실행한다. 점검 항목 목록의 SSOT는 audit.py 모듈 docstring의 "점검 항목"이며 여기에 다시 나열하지 않는다. 의미 판단과 git 맥락 검출은 감사자 몫이다 (see: [agent-roles/epistemic-auditor.md](agent-roles/epistemic-auditor.md)).

- 임계값은 공용 인프라 `tools/_audit_core.py` 상단의 상수이고 상류가 운영하며 조정한다. 상속한 저장소는 이 상수를 고치지 않는다(항목 30). 다른 값이 필요하면 경고를 의식적으로 수용하거나 상류에 변경을 제안한다.
- `.tmp/`는 에이전트의 임시 작업 공간이다. gitignore 대상이며 감사에서 제외된다.
- 실행: 새 세션 시작 시와 push, PR 시. 워크스페이스 루트에서 `python3 AGENTS/epistemic-rules/tools/audit.py .` (윈도우는 `python` 또는 `py`). push와 pull request 시점에는 GitHub Actions([.github/workflows/epistemic-audit.yml](../../.github/workflows/epistemic-audit.yml))가 실행한다. 새 세션 시작 시의 실행 의무는 [session-boundaries.md](session-boundaries.md) "세션 시작".
- 의존성: Python 3.9+ 표준 라이브러리만. 특정 AI 도구, OS(operating system)에 의존하지 않는다. git이 있으면 git이 무시하는 경로를 뺀다.
- 종료 코드: 위반 없음(경고만 있거나 없음) 0, 위반 있음 1, 사용법 오류(인자가 디렉토리가 아님) 2.
- 강제력: 위반(violation)은 CI를 실패시킨다(exit 1). 경고(warning)는 통과시킨다(exit 0) - 사람/LLM 판단이 필요한 신호라 기계적으로 차단하지 않는다. 그래서 경고는 방치하면 무한 누적될 수 있다. 감사 시 경고를 훑어 정리(수정)하거나 의식적으로 수용(현 상태가 맞다고 판단)해 미결 경고가 쌓이지 않게 한다.

## 색인 생성 스크립트

[tools/build_index.py](tools/build_index.py)는 폴더 색인을 만든다. 규칙과 훅 동작은 [folder-index.md](folder-index.md) "생성과 확인".

- 실행: 워크스페이스 루트에서 `python3 AGENTS/epistemic-rules/tools/build_index.py .` (윈도우는 `python` 또는 `py -3`). `--dry-run`은 바뀔 경로만 낸다. `--bundle-manifest`는 색인 대신 상류 묶음 목록만 만든다. 누가 다시 만드는가는 [instance-specialization.md](instance-specialization.md) "특수화 방식".
- 종료 코드: 성공 0, 형식 오류나 git 무시 파일 등으로 실패 2.
- 커밋 전 훅 연결(클론마다 한 번): `git config core.hooksPath AGENTS/epistemic-rules/tools/hooks`. 훅은 색인만 다시 만들고 상류 묶음 목록은 만들지 않는다.

## 의미 감사 트리거 판정 스크립트

[tools/check_semantic_audit.py](tools/check_semantic_audit.py)는 STATUS 레지스트리의 마지막 수행 시각과 git 이력을 대조해 트리거 조건 충족 여부만 판정한다. 감사를 수행하거나 강제하지 않고 판정 비용을 없애는 보조 도구다 - 조건 판정이 수동이면 어겼을 때 아무 신호가 없어 조건 충족을 놓친다.

- 실행: 워크스페이스 루트에서 `python3 AGENTS/epistemic-rules/tools/check_semantic_audit.py .` (윈도우는 `python` 또는 `py`).
- 종료 코드: 미충족 0, 충족 1, 판정 불가 2(수동 판정으로 넘긴다).
- 임계 시간과 trailer 문구를 스크립트에 하드코딩하지 않고 자손 덮어쓰기 표나 상류 규칙의 "주기 조건" 표 등에서 읽는다(출처와 순서는 check_semantic_audit.py docstring). 읽은 곳은 판정 문장 끝의 `(조건 출처: ...)`로 밝힌다. 인스턴스가 주기를 조정하면 스크립트가 따라간다.
- 시각 비교는 KST 고정이라 실행 머신의 시간대에 의존하지 않는다.
