#!/usr/bin/env python3
"""에피스테믹 워크스페이스 기계 감사 (Layer 0, 도구 중립).

epistemic-auditor의 형식 점검 항목을 결정론적으로 검사한다.
의미 판단(카테고리 배치 적절성, 워크로그 최신성)은 다루지 않는다 -
그건 LLM 감사자의 몫으로 남는다. git 맥락이 필요한 검출도 다루지 않는다
(마크 커밋 없는 삭제 등) - 그건 epistemic-auditor의 점검 항목이다.

점검 항목:
  1. YAML front matter 필수 필드 (date created, date modified, tags)와 날짜
     필드 값 형식(yyyy-MM-dd). 선택 필드 date closed는 히스토리 문서 전용.
  2. 문서 유형별 분량 임계 (일반 노드, 히스토리 문서, 진입층/폴더 디스크립터) - 경고
  3. 현재적 문서의 시간성 혼합 패턴 (날짜 헤더/불릿 반복) - 경고
  4. 날짜 프리픽스 없는 문서의 date closed (시간성 혼합 신호) - 위반
  5. STATUS.md 레지스트리 표 외 서술 누적 - 위반
  6. TASK_TREE.md 속성 노드 표준 키 위반 - 위반
  7. 디스크립터(AGENTS.md) 없는 폴더 - 위반
  8. 폴더 직속 md 파일 수 임계 초과 - 경고 (분화 권고)
  9. 문서 간 상대 마크다운 링크 정합 (대소문자, 유니코드 정규화 포함)
 10. 파일명의 크로스 플랫폼 이식성 (윈도우 금지 문자, 예약어 등)
 11. 규범 폴더 디스크립터의 파일별 안내 완전성 - 경고
     (골격 기본 규범 폴더 AGENTS/, _docs/_architecture/ 및 그 하위 전체 +
      파일별 안내 표를 가진 디스크립터의 폴더)
 12. TASK_TREE.md 완료 노드의 브랜치 속성 잔존 - 경고
 13. STATUS.md 레지스트리 표 스키마, 시각 형식 - 경고
 14. _docs/ 4범주 직속 문서의 tags 첫 항목 정합 - 경고
 15. 실체 0건 폴더 (디스크립터 외 항목 없음, 골격 폴더 제외) - 경고
     (찌꺼기인지 사양 동결인지 첫 실체 대기인지는 감사자가 판단)
 16. 하위 문서 없는 동명 문서-폴더 쌍 - 경고
     (동명 쌍은 하위 문서 묶음 관계의 예약 신호. md가 든 동명 쌍의
      실제 관계 판단은 감사자 몫)
 17. 마크다운 링크 표시텍스트-대상 정합 - 위반
     (파일명 형태 표시텍스트가 대상 basename 또는 대상 전체와 일치해야 함.
      자연어 문구, 타이틀은 제외. 폐지 파일명 잔재 오도를 검출)
 18. 전략 문서(_docs/_strategy 4범주 직속)의 추가 필수 속성 - 경고
     (importance, urgency. cf. _strategy/AGENTS.md. 하위 폴더/디스크립터 제외)
 19. 로컬 .md 링크 뒤 인용 섹션명의 대상 헤딩 실존 - 경고
     (dangling 섹션 참조 검출. 헤딩 번호 접두는 정규화. 대상 부재는 항목 9 소관)
 20. 비ASCII 문장 부호 (em dash, 화살표, 가운뎃점, 말줄임표, 둥근 따옴표) - 경고
     (백틱/코드펜스 예시와 고정폭 box-drawing 트리는 제외.
      cf. AGENTS/writing-style/ascii-punctuation.md)

위치: AGENTS/tools/audit.py. 사용 안내 문서는 AGENTS/tool-environment.md "기계 감사 스크립트".

사용법:
    python3 AGENTS/tools/audit.py [워크스페이스 루트]   # 생략 시 현재 디렉토리
    (윈도우에서는 python 또는 py 런처로 동일하게 실행)

종료 코드:
    0  위반 없음 (경고만 있거나 없음)
    1  위반 있음
    2  사용법 오류 (인자가 디렉토리가 아님)

이식성 노트:
- Python 3.8+ 표준 라이브러리만 사용. 특정 AI 도구, OS에 의존하지 않는다.
- 경로는 전부 pathlib로 다루고, 출력은 UTF-8로 강제한다 (윈도우 콘솔의
  cp949 기본값 대비).
- 링크 검사는 OS의 파일시스템 특성(대소문자 무시, 유니코드 정규화 무시)에
  기대지 않고 디렉토리 엔트리를 직접 대조한다. 어느 OS에서 실행해도 같은
  결과가 나오는 것이 목표다.
- git에 의존하지 않는다. 파일시스템 정적 상태만 본다.
- 순회는 심볼릭 링크를 따르지 않고(루트 밖 탈출/순환 방지) 중첩 git 레포와
  도구 전용 폴더를 가지치기한다.

구조 (2026-07-07 모듈 분할):
- 공용 인프라(Finding, 상수, 순회/읽기/링크 해석 헬퍼)는 _audit_core.py.
- 검사 함수는 의미별 모듈에 나뉜다: audit_frontmatter(front matter/스키마),
  audit_links(링크/참조), audit_structure(폴더/디스크립터/이식성),
  audit_worklog(STATUS/TASK_TREE), audit_content(분량/시간성/문장 부호).
- 각 검사 함수는 Finding 리스트를 반환하고 전역 가변 상태를 두지 않는다.
- 본 파일 audit.py가 진입점 - run_audit(root)가 검사들을 모으고, main()은 인자
  해석, 인코딩 설정, 출력, 종료 코드를 담당한다. 실행법과 출력은 분할 전과 동일.
"""

import sys
from pathlib import Path

from _audit_core import Finding, VIOLATION, WARNING
from audit_frontmatter import check_front_matter, check_strategy_fields, check_tags_category
from audit_links import check_links, check_link_text, check_section_refs
from audit_structure import (
    check_descriptors, check_normative_guides, check_empty_folders,
    check_name_collision, check_filename_portability,
)
from audit_worklog import (
    check_status_registry, check_status_schema,
    check_task_tree_attrs, check_task_tree_completed_branch,
)
from audit_content import check_size, check_temporality_mix, check_ascii_punctuation


def run_audit(root: Path) -> list[Finding]:
    """모든 검사를 순서대로 실행해 Finding 리스트를 모은다.

    입출력, 종료 코드와 분리된 순수 오케스트레이션 - 단위 테스트가 이 함수를
    직접 호출해 결과를 검증할 수 있다.
    """
    findings: list[Finding] = []
    findings += check_front_matter(root)
    findings += check_links(root)
    findings += check_link_text(root)
    findings += check_section_refs(root)
    findings += check_descriptors(root)
    findings += check_size(root)
    findings += check_temporality_mix(root)
    findings += check_status_registry(root)
    findings += check_status_schema(root)
    findings += check_strategy_fields(root)
    findings += check_task_tree_attrs(root)
    findings += check_task_tree_completed_branch(root)
    findings += check_normative_guides(root)
    findings += check_tags_category(root)
    findings += check_empty_folders(root)
    findings += check_name_collision(root)
    findings += check_filename_portability(root)
    findings += check_ascii_punctuation(root)
    return findings


def main() -> int:
    # 윈도우 콘솔(cp949 등)에서도 한글 출력이 깨지지 않게 UTF-8로 강제
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    if not root.is_dir():
        print(f"오류: 디렉토리가 아님 - {root}", file=sys.stderr)
        return 2

    findings = run_audit(root)
    violations = [f for f in findings if f.severity == VIOLATION]
    warnings = [f for f in findings if f.severity == WARNING]

    for f in violations:
        print(f.format())
    for f in warnings:
        print(f.format())
    print(f"\n감사 완료: 위반 {len(violations)}건, 경고 {len(warnings)}건 ({root})")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
