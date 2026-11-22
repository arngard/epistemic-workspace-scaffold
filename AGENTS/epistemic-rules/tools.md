---
date created: 2026-10-26
date modified: 2026-11-22
tags: [규칙, 도구, epistemic-rules]
---

# 감사 도구

[tools/](tools/) 폴더는 에이전트 운영을 보조하는 실행 스크립트를 담는다. 문서가 아닌 도구 파일만 두며, 폴더 디스크립터를 두지 않고 이 문서가 그 안내를 맡는다. 이 도구의 코드를 만들거나 고칠 때는 [coding-guidelines.md](../../implementation/AGENTS/epistemic-rules/coding-guidelines.md)를 따른다.

아래 명령은 워크스페이스 루트에서 실행하고, 윈도우에서는 `python3` 대신 `python`이나 `py -3`을 쓴다. 인자와 종료 코드의 세부는 각 스크립트의 docstring에 있다.

## 구성

검사 진입점은 [audit.py](tools/audit.py) 하나, 파일을 쓰는 생성 진입점은 [build_index.py](tools/build_index.py) 하나다. 검사 로직은 공용 인프라([_audit_core.py](tools/_audit_core.py) 등)와 의미별 검사 모듈로 나뉘며 audit.py가 import해 조합한다. 모듈 구성은 audit.py 모듈 docstring의 "구조"에 있다.

그 밖의 도구는 성격으로 나뉜다. 사용자가 승인한 일만 명시적으로 실행하는 편집 도구는 [retag.py](tools/retag.py)이고, 읽기 전용 보조 도구는 [check_semantic_audit.py](tools/check_semantic_audit.py)(git 이력이 있어야 판정해 audit.py와 따로 둔다)와 [tag_inventory.py](tools/tag_inventory.py)다. 설치기 [setup.py](tools/setup.py)는 사용자 동의 뒤 클론 설정을 바꾸는 도구다(아래 "설치기"). [session_brief.py](tools/session_brief.py)는 파일을 고치지 않지만 `git fetch`로 원격 참조를 갱신하고, 레포의 확장 코드를 실행하며, 설치 항목마다 점검 명령을 실행한다. 사용 안내는 각 자리에 있다: 상류 묶음 목록은 아래 "색인 생성 스크립트", 태그 도구는 [tags.md](tags.md) "어휘 정리", 확장 지점은 [audit-extensions.md](audit-extensions.md)(감사)와 [session-brief-extensions.md](session-brief-extensions.md)(세션 시작 요약).

## 시험

도구를 고친 뒤 `python3 -m unittest discover -s AGENTS/epistemic-rules/tools/tests -v`로 [tests/](tools/tests/)의 시험을 돌린다.

## 기계 감사 스크립트

[tools/audit.py](tools/audit.py)는 형식 정합성을 결정론적으로 검사하고, 자손의 확장 검사도 실행한다. 점검 항목 목록의 SSOT(single source of truth; 단일 진실 공급원)는 audit.py 모듈 docstring의 "점검 항목"이다. 의미 판단과 git 맥락 검출은 감사자 몫이다 (see: [agent-roles/epistemic-auditor.md](agent-roles/epistemic-auditor.md)).

- 임계값은 공용 인프라 `tools/_audit_core.py` 상단의 상수이고 상류가 운영하며 조정한다. 상속한 레포(레포지토리)는 이 상수를 고치지 않는다(항목 30). 다른 값이 필요하면 경고를 의식적으로 수용하거나 상류에 변경을 제안한다.
- `.tmp/`는 에이전트의 임시 작업 공간이다. gitignore 대상이며 감사에서 제외된다.
- 실행: `python3 AGENTS/epistemic-rules/tools/audit.py .`를 새 세션 시작 시와 push, PR 시에 돌리고, 그 밖의 커밋이나 답변마다 돌리지 않는다. push와 pull request 시점에는 GitHub Actions([.github/workflows/epistemic-audit.yml](../../.github/workflows/epistemic-audit.yml))가, 새 세션 시작 시에는 아래 "세션 시작 요약 스크립트"가 실행한다 (see: [session-boundaries.md](session-boundaries.md) "세션 시작"). 오래 걸릴 수 있는 검증은 커밋과 한 명령으로 묶지 않는다. 묶으면 검증이 끝날 때까지 커밋과 응답이 밀린다.
- 의존성: Python 3.9+ 표준 라이브러리만. 특정 AI 도구, OS에 의존하지 않는다. git이 있으면 git이 무시하는 경로를 뺀다.
- 종료 코드와 강제력: 위반이 없으면(경고만 있거나 없음) 0, 위반이 있으면 1, 사용법 오류는 2다. 위반(violation)은 CI를 실패시키고 경고(warning)는 통과시킨다 - 경고는 사람이나 LLM의 판단이 필요한 신호라 기계적으로 차단하지 않는다. 경고는 방치하면 쌓이므로 감사 시 훑어 정리(수정)하거나 의식적으로 수용(현 상태가 맞다고 판단)한다.

## 색인 생성 스크립트

[tools/build_index.py](tools/build_index.py)는 폴더 색인을 만든다. 규칙은 [folder-index.md](folder-index.md) "생성과 확인", 훅은 [commit-hook.md](folder-index/commit-hook.md).

- 실행: `python3 AGENTS/epistemic-rules/tools/build_index.py .`. `--dry-run`은 바뀔 경로만 내고, `--bundle-manifest`는 색인 대신 상류 묶음 목록만 만든다. 누가 다시 만드는가는 [instance-specialization.md](instance-specialization.md) "특수화 방식".
- 커밋 전 훅 연결: 설치 명세의 `hooks-path` 항목(`core.hooksPath`를 `AGENTS/epistemic-rules/tools/hooks`로)이 맡고, 설치기가 클론마다 맞춘다 (see: [workspace-setup.md](workspace-setup.md)). 훅은 색인만 다시 만들고 상류 묶음 목록은 만들지 않는다.

## 의미 감사 트리거 판정 스크립트

[tools/check_semantic_audit.py](tools/check_semantic_audit.py)는 STATUS 레지스트리의 마지막 수행 시각과 git 이력을 대조해 트리거 조건 충족 여부만 판정한다. 조건 판정이 수동이면 어겼을 때 아무 신호가 없어 조건 충족을 놓친다.

- 실행: `python3 AGENTS/epistemic-rules/tools/check_semantic_audit.py .`. 종료 코드는 미충족 0, 충족 1, 판정 불가 2(수동 판정으로 넘긴다)다.
- 임계 시간과 trailer 문구는 자손 덮어쓰기 표나 상류 규칙의 "주기 조건" 표 등에서 읽고(출처와 순서는 docstring), 읽은 곳을 판정 문장 끝의 `(조건 출처: ...)`로 밝힌다. 인스턴스가 주기를 조정하면 스크립트가 따라간다. 시각 비교는 KST 고정이라 실행 머신의 시간대에 의존하지 않는다.

## 세션 시작 요약 스크립트

[tools/session_brief.py](tools/session_brief.py)는 [session-boundaries.md](session-boundaries.md) "세션 시작" 1-5단계에서 판단이 필요 없는 부분을 모아 요약 하나로 낸다. 명령을 하나씩 돌려 출력을 컨텍스트에 쌓는 대신 요약만 읽게 해 세션 시작의 읽기 분량을 줄인다. 무엇을 모으는지는 그 절이 정하고, 절의 순서, 자르는 방식, 제한 시간 같은 구현은 스크립트 docstring에 있다.

- 실행: `python3 AGENTS/epistemic-rules/tools/session_brief.py .`. `--merges N`은 최근 머지 건수(기본 5), `--no-fetch`는 원격 조회 생략, `--no-audit`는 형식 감사 생략이다. `--hook-json`은 같은 요약을 세션 시작 훅의 JSON 출력으로 감싼다.
- 출력: 첫 줄이 `[session-brief]`와 레포 이름이고 9,000자 안으로 자른다. 세션 시작 훅이 주입할 수 있는 길이 안에 들게 하려는 것이다 (see: [session-start-hook.md](tool-environment/session-start-hook.md)).
- 인스턴스 확장: 자손은 상류 도구를 고치지 않고 레포 루트의 `AGENTS/session-brief/` 바로 아래 `*.py`로 요약에 고유 항목을 더한다. 계약은 [session-brief-extensions.md](session-brief-extensions.md)에 있고, 확장을 만들거나 고칠 때 읽는다. 세션 시작 훅이 있으면 세션마다 레포의 확장 코드가 자동으로 실행되므로, 신뢰하지 않는 레포에서는 세션을 열거나 요약을 실행하지 않는다.
- 종료 코드: 요약을 냈으면 0(감사 위반, 의미 감사 충족, 원격 조회 실패도 요약에 적는다), 사용법 오류 2. 훅이 세션을 막지 않게 하려고 수집 결과로 종료 코드를 바꾸지 않는다.

## 설치기

[tools/setup.py](tools/setup.py)는 설치 명세의 항목을 점검하고 사용자 동의 뒤 적용한다. 공용 로직은 [tools/_setup_core.py](tools/_setup_core.py)에 있고, 세션 시작 요약이 같은 모듈로 "환경 갱신" 절을 낸다. 갱신 흐름, 처음 설치, 명령마다 쓰는 것은 [workspace-setup.md](workspace-setup.md)가 정본이다.

- 실행: AI가 `python3 -B AGENTS/epistemic-rules/tools/setup.py <status|check|plan|apply> .`로 부른다. 하위 명령과 인자, `--json` 출력, 종료 코드는 setup.py docstring에 있다.
- 시험은 홈(`HOME`, `USERPROFILE`)을 임시 폴더로 바꿔 `status`, `check`, `plan`이 아무것도 쓰지 않음을 확인한다.
