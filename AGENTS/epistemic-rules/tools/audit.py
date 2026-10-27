#!/usr/bin/env python3
"""에피스테믹 워크스페이스 기계 감사 (도구 중립).

epistemic-auditor의 형식 점검 항목을 결정론적으로 검사한다.
의미 판단(카테고리 배치 적절성, 워크로그 최신성)은 다루지 않는다 -
그건 LLM 감사자의 몫으로 남는다. git 맥락이 필요한 검출도 다루지 않는다
(마크 커밋 없는 삭제 등) - 그건 epistemic-auditor의 점검 항목이다.

점검 항목:
  1. YAML front matter 필수 필드 (date created, date modified, tags)와 날짜
     필드 값 형식(yyyy-MM-dd). 선택 필드 date closed는 히스토리 문서 전용.
     date created가 date modified보다 늦으면 경고. 생성 색인 쪽 파일(INDEX.md,
     INDEX2.md ...)은 면제.
  2. 문서 유형별 분량 임계 (일반 노드, 히스토리 문서, 진입층/폴더 디스크립터) - 경고
  3. 현재적 문서의 시간성 혼합 패턴 (날짜 헤더/불릿 반복) - 경고
  4. 날짜 프리픽스 없는 문서의 date closed (시간성 혼합 신호) - 위반
  5. STATUS.md 레지스트리 표 외 서술 누적 - 위반
  6. TASK_TREE.md 속성 노드 표준 키 위반 - 위반
  7. 디스크립터(AGENTS.md) 없는 폴더 - 위반 (규범 폴더(`AGENTS/`와 그 아래) 제외)
     (순차 분류로 선언된 폴더의 하위 제외, 그 하위에 남은 AGENTS.md와
      CLAUDE.md는 경고)
  8. 폴더 직속 md 파일 수 임계 초과 - 경고 (분화 권고)
     (reference/ 하위는 제외 - 원본을 재편하지 않으므로 실행 불가능한 권고다.
      순차 분류 하위 제외. 색인 파일은 세지 않음)
  9. 문서 간 상대 마크다운 링크 정합 (대소문자, 유니코드 정규화 포함)
 10. 파일명의 크로스 플랫폼 이식성 (윈도우 금지 문자, 예약어 등)
 11. 색인 정합 - 색인을 둘 폴더(규범 폴더 밖에서 AGENTS.md가 있는 폴더)의
     INDEX.md 누락은 경고, 낡은 내용과 남는 쪽과 색인을 두지 않는 폴더의 색인
     파일과 INDEX.yaml 형식 오류는 위반
     (생성기와 같은 _index_core.render_all 결과와 비교. 줄바꿈은 LF로 맞춘다.
      reference/ 하위 폴더와 중첩 저장소 안은 보지 않음)
 12. TASK_TREE.md 완료 노드의 브랜치 속성 잔존 - 경고
 13. STATUS.md 레지스트리 표 스키마, 시각 형식 - 경고
 14. front matter tags의 형식과 표기 - 경고
     (읽을 수 없는 형식, 공백 든 태그와 숫자만의 태그, NFKC와 대소문자, 공백,
      하이픈, 밑줄만 다른 표기 묶음. 뜻이 같은 다른 낱말은 감사자 몫)
 15. 실체 0건 폴더 (디스크립터 외 항목 없음, 골격 폴더 제외) - 경고
     (`CLAUDE.md`와 규범 폴더, 색인 파일은 실체로 세지 않음)
     (찌꺼기인지 사양 동결인지 첫 실체 대기인지는 감사자가 판단)
 16. 디스크립터와 `CLAUDE.md` 외 항목이 없는 동명 문서-폴더 쌍 - 경고
     (색인 파일은 세지 않음)
     (동명 쌍은 하위 문서 묶음 관계의 예약 신호. md가 든 동명 쌍의
      실제 관계 판단은 감사자 몫)
 17. 마크다운 링크 표시텍스트-대상 정합 - 위반
     (파일명 형태 표시텍스트는 링크 대상 자체를 가리켜야 함. 대상은 문서
      위치에서 풀어낸 경로. / 없으면 대상 basename, / 로 끝나면 대상 경로
      성분의 폴더명, 그 밖의 경로는 루트나 문서 기준 해석이 대상과 같거나
      . 과 .. 없이 대상 루트 상대 경로의 끝부분.
      공백 든 자연어 문구, 타이틀은 제외하되 날짜 문서, 폴더 이름은 검사.
      폐지 파일명과 옛 경로 잔재 오도를 검출)
 18. 전략 문서(epistemic-structure/strategy 4범주 직속)의 추가 필수 속성 - 경고
     (importance, urgency. ref: strategy/AGENTS/epistemic-rules.md. 하위 폴더/디스크립터 제외)
 19. 로컬 .md 링크 뒤 인용 섹션명의 대상 헤딩 실존 - 경고
     (dangling 섹션 참조 검출. 헤딩 번호 접두는 정규화. 대상 부재는 항목 9 소관)
 20. 비ASCII 문장 부호 (em dash, 화살표, 가운뎃점, 말줄임표, 둥근 따옴표) - 경고
     (백틱/코드펜스 예시와 고정폭 box-drawing 트리, 생성 색인 쪽 파일은 제외.
      ref: AGENTS/epistemic-rules/writing-style/ascii-punctuation.md)
 21. front matter description의 스캐폴드 상태 마커와 본문 마커 대조 - 경고
     (description에 "스캐폴드 상태"가 있는데 본문에 없으면 검출. 인스턴스가
      플레이스홀더를 실제 내용으로 채우고 description을 갱신하지 않은 경우,
      또는 본문에서 마커만 지운 경우. 어느 쪽이 낡았는지는 사람/LLM 판단)
 22. 날짜 프리픽스 뒤를 하이픈으로 이은 문서, 폴더 - 경고
     (규약은 띄어쓰기. reference/ 하위 제외. 하이픈 구분자도 프리픽스로는 인정)
 23. 링크 대상에 공백이 든 로컬 파일, 폴더 링크 - 위반
     (공백은 %20으로 쓴다. 대상이 확장자나 / 로 끝나는 것만 본다. 링크 제목
      문법과 외부 URL은 제외)
 24. 참조 표기 - 폐지된 옛 표기 cf., ref.와 표지(ref:, sub:, see:) 뒤 형태
     불량(공백 없음, 뒤가 빔)은 위반, 표지 없이 공백 뒤 괄호에 둔 링크(괄호 안이
     링크와 절 이름뿐)는 경고. 표지는 줄 머리나 여는 괄호 바로 뒤에서만 인식한다.
     표지 뒤 비링크 설명은 링크하기 어려운 대상으로 통과시키며, 내부 문서를 제목만
     적은 것인지는 감사자 몫. 표 행은 경고에서 제외하고 옛 표기와 형태 불량만 본다.
     링크만 있는 목록 항목은 색인 목록과 참고 목록이 형태로 갈리지 않아 보지 않고,
     명사에 붙인 동격 괄호와 화살표 포인터도 보지 않는다(모두 감사자 몫).
     생성 색인 쪽 파일은 제외
     (ref: AGENTS/epistemic-rules/writing-style/reference-markers.md)
 25. AGENTS.md가 있는 폴더(규범 폴더 제외)의 CLAUDE.md 포인터 - 경고
     (CLAUDE.md가 없거나 내용이 `@AGENTS.md`가 아님. 순차 분류 하위 제외)
 26. `@` 가져오기 줄(줄 전체가 @경로)의 대상 부재 - 위반
     (경로는 줄을 둔 파일 위치 기준. 묶음 세부 폴더 AGENTS/epistemic-rules/ 안의
      가져오기는 경고. front matter와 코드 펜스 안은 제외)
 27. 규범 폴더(`AGENTS/`와 그 아래) 안의 AGENTS.md, CLAUDE.md - 위반
 28. 색인 설명 원본 - 경고
     (md 문서 description의 형식 오류와 길이 초과, INDEX.yaml 항목의 대상 부재,
      reference/ 밖에서 md 문서를 가리키는 항목, 동명 문서가 있는 폴더 항목,
      알 수 없는 키, 설명 길이 초과, reference/ 항목의 status 누락이나 어휘 밖
      값, reference/ 밖 항목의 쓰이지 않는 status 키, reference/ 직속의 미등록
      항목, 순차 분류로 선언된 폴더 INDEX.yaml의 "." 밖 항목, 설명의 비ASCII
      문장 부호)
 29. 상류 묶음 md의 출처 태그 epistemic-rules 누락은 위반, 묶음 밖 md의 그
     태그는 경고
     (묶음은 AGENTS/epistemic-rules.md와 AGENTS/epistemic-rules/ 아래. 읽을
      수 없는 tags는 항목 14 소관이라 건너뜀. 생성 색인 쪽 파일은 제외)
 30. 상류 묶음 파일과 상류 목록(tools/bundle-manifest.sha256)의 대조 - 내용
     차이, 누락, 목록 밖 파일, 목록 형식 오류는 위반
     (이 도구가 감사 대상 루트의 묶음에 있을 때만. 상류 저장소는
      build_index.py --bundle-manifest로 목록을 다시 만들고, 상속한 저장소는
      파일을 되돌린다)

확장 검사: 루트 AGENTS/audit-checks/ 바로 아래의 *.py(_와 .으로 시작하는
이름과 부산물 제외)를 별도 프로세스로 실행해 표준 출력의 JSON 줄을 발견으로
받는다. 범주는 ext:<이름>. 실패와 시간 초과는 위반. 실행하지 않는 그 밖의 항목(.py가 아닌
파일, 하위 폴더)은 범주 ext의 경고. 계약은 AGENTS/epistemic-rules/audit-extensions.md

위치: AGENTS/epistemic-rules/tools/audit.py. 사용 안내 문서는 AGENTS/epistemic-rules/tools.md "기계 감사 스크립트".

사용법:
    python3 AGENTS/epistemic-rules/tools/audit.py [워크스페이스 루트]   # 생략 시 현재 디렉토리
    (윈도우에서는 python 또는 py 런처로 동일하게 실행)

종료 코드:
    0  위반 없음 (경고만 있거나 없음)
    1  위반 있음
    2  사용법 오류 (인자가 디렉토리가 아님)

이식성 노트:
- Python 3.9+ 표준 라이브러리만 사용. 특정 AI 도구, OS에 의존하지 않는다.
- 경로는 전부 pathlib로 다루고, 출력은 UTF-8로 강제한다 (윈도우 콘솔의
  cp949 기본값 대비).
- 링크 검사는 OS의 파일시스템 특성(대소문자 무시, 유니코드 정규화 무시)에
  기대지 않고 디렉토리 엔트리를 직접 대조한다. 어느 OS에서 실행해도 같은
  결과가 나오는 것이 목표다.
- git에 의존하지 않는다. 파일시스템 정적 상태만 본다.
- 순회는 심볼릭 링크를 따르지 않고(루트 밖 탈출/순환 방지) 중첩 git 레포와
  도구 전용 폴더를 가지치기한다.

구조:
- 공용 인프라(Finding, 상수, 순회/읽기/링크 해석 헬퍼)는 _audit_core.py.
  색인의 YAML 부분집합 파서와 렌더러는 생성기와 함께 쓰는 _index_core.py.
  front matter tags 읽기와 표기 규칙은 태그 도구와 함께 쓰는 _tags_core.py.
  상류 묶음 파일 목록과 출고 목록은 생성기와 함께 쓰는 _bundle_core.py.
- 검사 함수는 의미별 모듈에 나뉜다: audit_frontmatter(front matter/스키마),
  audit_links(링크/참조), audit_structure(폴더/디스크립터/이식성),
  audit_worklog(STATUS/TASK_TREE), audit_content(분량/시간성/문장 부호),
  audit_index(색인 정합/설명 원본), audit_bundle(상류 묶음 출처 태그/동일성),
  audit_extensions(루트 확장 검사 실행).
- 감사 밖의 태그 도구 tag_inventory.py(읽기 전용)와 retag.py(승인된 병합과
  삭제 실행)는 _tags_core.py를 쓴다. audit.py는 이 둘을 부르지 않는다.
- 각 검사 함수는 Finding 리스트를 반환하고 전역 가변 상태를 두지 않는다.
- 본 파일 audit.py가 진입점 - run_audit(root)가 검사들을 모으고, main()은 인자
  해석, 인코딩 설정, 출력, 종료 코드를 담당한다.
"""

import sys
from pathlib import Path

from _audit_core import Finding, VIOLATION, WARNING
from audit_frontmatter import check_front_matter, check_strategy_fields, check_tags
from audit_links import (
    check_links, check_link_text, check_section_refs, check_link_whitespace,
    check_reference_markers, check_imports,
)
from audit_bundle import check_bundle_identity, check_source_tags
from audit_extensions import run_extensions
from audit_index import check_index_files, check_index_sources
from audit_structure import (
    check_descriptors, check_empty_folders,
    check_name_collision, check_filename_portability, check_scaffold_state_markers,
    check_date_prefix_separator, check_claude_pointers, check_norms_dir_descriptors,
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
    findings += check_link_whitespace(root)
    findings += check_link_text(root)
    findings += check_section_refs(root)
    findings += check_reference_markers(root)
    findings += check_descriptors(root)
    findings += check_size(root)
    findings += check_temporality_mix(root)
    findings += check_status_registry(root)
    findings += check_status_schema(root)
    findings += check_strategy_fields(root)
    findings += check_task_tree_attrs(root)
    findings += check_task_tree_completed_branch(root)
    findings += check_index_files(root)
    findings += check_tags(root)
    findings += check_empty_folders(root)
    findings += check_name_collision(root)
    findings += check_filename_portability(root)
    findings += check_date_prefix_separator(root)
    findings += check_ascii_punctuation(root)
    findings += check_scaffold_state_markers(root)
    findings += check_claude_pointers(root)
    findings += check_imports(root)
    findings += check_norms_dir_descriptors(root)
    findings += check_index_sources(root)
    findings += check_source_tags(root)
    findings += check_bundle_identity(root)
    findings += run_extensions(root)
    return findings


def main() -> int:
    # 윈도우 콘솔(cp949 등)에서도 한글 출력이 깨지지 않게 UTF-8로 강제
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    if not root.is_dir():
        print(f"Error: not a directory. 디렉토리가 아님 - {root}", file=sys.stderr)
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
