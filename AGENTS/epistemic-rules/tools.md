---
date created: 2026-10-26
date modified: 2026-10-26
tags: [규칙, 도구, epistemic-rules]
---

# 감사 도구

[tools/](tools/) 폴더는 에이전트 운영을 보조하는 실행 스크립트를 담는다. 문서가 아닌 도구 파일만 두며, 폴더 디스크립터를 두지 않고 이 문서가 그 안내를 맡는다.

## 구성

형식 감사의 직접 실행 진입점은 [audit.py](tools/audit.py) 하나다. 검사 로직은 공용 인프라 [_audit_core.py](tools/_audit_core.py)와 의미별 검사 모듈 [audit_frontmatter.py](tools/audit_frontmatter.py)(front matter, 스키마), [audit_links.py](tools/audit_links.py)(링크, 참조), [audit_structure.py](tools/audit_structure.py)(폴더, 디스크립터, 이식성), [audit_worklog.py](tools/audit_worklog.py)(STATUS, TASK_TREE), [audit_content.py](tools/audit_content.py)(분량, 시간성, 문장 부호)로 나뉘며, audit.py가 import해 조합한다. 분할은 파일당 크기를 낮춰 편집 안전성과 의미 단위 유지보수성을 높이기 위함이다.

[check_semantic_audit.py](tools/check_semantic_audit.py)는 git에 의존하므로 audit.py와 따로 둔다. 새 세션 시작 시 의미 감사가 필요한지 판정할 때 실행한다.

[migrate_layout.py](tools/migrate_layout.py)는 옛 폴더 배치를 새 배치로 옮기고 링크를 고치는 일시 도구다. 자식 레포에서 상류를 머지한 직후 실행한다. 자식 레포 전파가 끝나면 지운다.

## 시험

도구의 단위 시험은 [tests/](tools/tests/) 폴더의 [test_audit_norms.py](tools/tests/test_audit_norms.py), [test_migrate_layout.py](tools/tests/test_migrate_layout.py)다. 도구를 고친 뒤 워크스페이스 루트에서 `python3 -m unittest discover -s AGENTS/epistemic-rules/tools/tests -v`로 실행한다(윈도우는 `python` 또는 `py`).

## 기계 감사 스크립트

[tools/audit.py](tools/audit.py)는 형식 정합성을 결정론적으로 검사한다. 점검 범위는 front matter와 시간성, 문서 분량, 워크로그(STATUS, TASK_TREE) 스키마, 폴더와 디스크립터, 링크와 섹션 참조, 참조 표지, 파일명 이식성과 날짜 프리픽스 구분자, 문장 부호다. 점검 항목 목록의 SSOT는 audit.py 모듈 docstring의 "점검 항목"이며 여기에 다시 나열하지 않는다 - 목록을 여러 곳에 두면 검사가 추가될 때 어긋난다. 의미 판단과 git 맥락 검출은 감사자 몫이다 (see: [agent-roles/epistemic-auditor.md](agent-roles/epistemic-auditor.md)).

- 임계값은 보수적 초기값으로 두고 운영하며 조정한다. 공용 인프라 `tools/_audit_core.py` 상단의 상수로 관리한다.
- `.tmp/`는 에이전트의 임시 작업 공간이다. gitignore 대상이며 감사에서 제외된다.
- 실행: 워크스페이스 루트에서 `python3 AGENTS/epistemic-rules/tools/audit.py .` (윈도우는 `python` 또는 `py`).
- 의존성: Python 3.8+ 표준 라이브러리만. 특정 AI 도구, OS(operating system)에 의존하지 않는다. git에도 의존하지 않는다 - git 맥락 검출은 epistemic-auditor가 담당한다. 사람, 어느 AI 도구의 협업자든 동일하게 실행 가능.
- 자동 실행: GitHub Actions([.github/workflows/epistemic-audit.yml](../../.github/workflows/epistemic-audit.yml))가 push, pull request 시점에 실행한다. 새 세션 시작 시의 실행 의무는 [session-boundaries.md](session-boundaries.md) "세션 시작" 참조.
- 종료 코드: 위반 없음(경고만 있거나 없음) 0, 위반 있음 1, 사용법 오류(인자가 디렉토리가 아님) 2.
- 강제력: 위반(violation)은 CI를 실패시킨다(exit 1). 경고(warning)는 통과시킨다(exit 0) - 사람/LLM 판단이 필요한 신호라 기계적으로 차단하지 않는다. 그래서 경고는 방치하면 무한 누적될 수 있다. 감사 시 경고를 훑어 정리(수정)하거나 의식적으로 수용(현 상태가 맞다고 판단)해 미결 경고가 쌓이지 않게 한다.

## 의미 감사 트리거 판정 스크립트

[tools/check_semantic_audit.py](tools/check_semantic_audit.py)는 STATUS 레지스트리의 의미 감사 행과 git 이력을 대조해 트리거 조건 충족 여부만 판정한다. 감사를 수행하거나 강제하지 않고 판정 비용을 없애는 보조 도구다 - 조건 판정이 수동이면 어겼을 때 아무 신호가 없어 조건 충족을 놓친다.

- 실행: 워크스페이스 루트에서 `python3 AGENTS/epistemic-rules/tools/check_semantic_audit.py .` (윈도우는 `python` 또는 `py`).
- 종료 코드: 미충족 0, 충족 1, 판정 불가 2(수동 판정으로 넘긴다).
- audit.py와 달리 git에 의존하므로 별도 스크립트로 둔다. audit.py의 git 비의존 원칙은 유지된다.
- 임계 시간과 trailer 문구를 스크립트에 하드코딩하지 않고 STATUS 레지스트리의 주기/트리거 셀에서 읽는다 - 그 셀이 임계 조건의 SSOT이고, 인스턴스가 주기를 조정하면 스크립트가 따라간다.
- 시각 비교는 KST 고정이라 실행 머신의 시간대에 의존하지 않는다.
